"""Credential exchange admin routes."""

from aiohttp_apispec import (
    docs,
    querystring_schema,
    request_schema,
)
from aiohttp import web
from marshmallow import fields
import logging
from ....messaging.models.base import OpenAPISchema
from .messages.credential_issue import CredentialIssue
from aries_cloudagent.protocols.issue_credential.v1_1.messages.credential_request import (
    CredentialRequest,
)
from .utils import (
    CredentialExchangeRecord,
    retrieve_credential_exchange,
    retrieve_connection,
)
from aries_cloudagent.wallet.base import BaseWallet
from aries_cloudagent.pdstorage_thcf.error import PDSError
from aries_cloudagent.issuer.base import BaseIssuer, IssuerError


LOGGER = logging.getLogger(__name__)


class RequestCredentialSchema(OpenAPISchema):
    credential_values = fields.Dict()
    connection_id = fields.Str(required=True)


class IssueCredentialQuerySchema(OpenAPISchema):
    credential_exchange_id = fields.Str(required=False)


class RetrieveCredentialExchangeQuerySchema(OpenAPISchema):
    connection_id = fields.Str(required=False)
    thread_id = fields.Str(required=False)
    initiator = fields.Str(required=False)
    role = fields.Str(required=False)
    state = fields.Str(required=False)


@docs(tags=["issue-credential"], summary="Issue credential ")
@querystring_schema(IssueCredentialQuerySchema())
async def issue_credential(request: web.BaseRequest):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    credential_exchange_id = request.query.get("credential_exchange_id")
    exchange = await retrieve_credential_exchange(context, credential_exchange_id)

    if exchange.role != exchange.ROLE_ISSUER:
        raise web.HTTPBadRequest(reason="Invalid exchange role")
    if exchange.state != exchange.STATE_REQUEST_RECEIVED:
        raise web.HTTPBadRequest(reason="Invalid exchange state")

    connection = await retrieve_connection(context, exchange.connection_id)
    request = exchange.credential_request

    try:
        issuer: BaseIssuer = await context.inject(BaseIssuer)
        credential = await issuer.create_credential_ex(
            request.get("credential_values"),
            request.get("credential_type"),
            exchange.their_public_did,
        )
    except IssuerError as err:
        raise web.HTTPInternalServerError(
            reason=f"Error occured while creating a credential {err.roll_up}"
        )

    LOGGER.info("CREDENTIAL %s", credential)
    issue = CredentialIssue(credential=credential)
    issue.assign_thread_id(exchange.thread_id)
    await outbound_handler(issue, connection_id=connection.connection_id)

    exchange.state = CredentialExchangeRecord.STATE_ISSUED
    try:
        await exchange.issuer_credential_pds_set(context, credential)
    except PDSError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    await exchange.save(context)

    return web.json_response(
        {
            "success": True,
            "credential_exchange_id": exchange._id,
        }
    )


async def routes_get_public_did(context):
    wallet: BaseWallet = await context.inject(BaseWallet)
    public_did = await wallet.get_public_did()

    if public_did is None:
        raise web.HTTPBadRequest(
            reason="Your public did is None!, acquire a public did before requesting a credential"
        )

    public_did = public_did[0]

    if public_did is None:
        raise web.HTTPBadRequest(
            reason="Your public did is None!, acquire a public did before requesting a credential"
        )

    return public_did


@docs(tags=["issue-credential"], summary="Request Credential")
@request_schema(RequestCredentialSchema())
async def request_credential(request: web.BaseRequest):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()
    credential_values = body.get("credential_values")
    connection_id = body.get("connection_id")
    connection_record = await retrieve_connection(context, connection_id)
    public_did = await routes_get_public_did(context)
    print("Public DID: ", public_did)

    issue = CredentialRequest(
        credential={"credential_values": credential_values}, did=public_did
    )
    await outbound_handler(issue, connection_id=connection_record.connection_id)

    exchange = CredentialExchangeRecord(
        connection_id=connection_id,
        thread_id=issue._thread_id,
        initiator=CredentialExchangeRecord.INITIATOR_SELF,
        role=CredentialExchangeRecord.ROLE_HOLDER,
        state=CredentialExchangeRecord.STATE_REQUEST_SENT,
        credential_request={"credential_values": credential_values},
    )

    exchange_id = await exchange.save(
        context, reason="Save record of agent credential exchange"
    )

    return web.json_response(
        {
            "success": True,
            "thread_id": issue._thread_id,
            "credential_exchange_id": exchange_id,
        }
    )


@docs(tags=["issue-credential"], summary="Retrieve Credential Exchange")
@querystring_schema(RetrieveCredentialExchangeQuerySchema())
async def retrieve_credential_exchange_endpoint(request: web.BaseRequest):
    context = request.app["request_context"]

    records = await CredentialExchangeRecord.query(context, tag_filter=request.query)

    result = []
    for i in records:
        serialized = i.serialize()
        credential_exists = await i.credential_pds_get(context)
        if credential_exists is not None:
            serialized["credential"] = credential_exists
        result.append(serialized)

    return web.json_response({"success": True, "result": result})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/issue-credential/issue", issue_credential),
            web.post("/issue-credential/request", request_credential),
            web.get(
                "/issue-credential/exchange/record",
                retrieve_credential_exchange_endpoint,
                allow_head=False,
            ),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "issue-credential",
            "description": "Credential issuance",
            # "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
