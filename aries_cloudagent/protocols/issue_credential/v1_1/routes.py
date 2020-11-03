"""Credential exchange admin routes."""

import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from json.decoder import JSONDecodeError
from marshmallow import fields, validate

from ....connections.models.connection_record import ConnectionRecord
from ....issuer.base import IssuerError
from ....ledger.error import LedgerError
from ....messaging.credential_definitions.util import CRED_DEF_TAGS
from ....messaging.models.base import BaseModelError, OpenAPISchema
from ....messaging.valid import (
    NATURAL_NUM,
    UUIDFour,
    UUID4,
)
from ....storage.error import StorageError, StorageNotFoundError
from ....wallet.base import BaseWallet
from ....issuer.base import BaseIssuer
from ....wallet.error import WalletError
from ....utils.outofband import serialize_outofband
from ....utils.tracing import trace_event, get_timer, AdminAPIMessageTracingSchema
from .messages.credential_issue import CredentialIssue


class IssueCredentialSchema(OpenAPISchema):
    credential_values = fields.Dict()
    credential_type = fields.Str()
    connection_id = fields.Str()


@docs(tags=["issue-credential"], summary="Issue credential ")
@request_schema(IssueCredentialSchema())
async def issue_credential(request: web.BaseRequest):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()
    credential_type = body.get("credential_type")
    credential_values = body.get("credential_values")
    connection_id = body.get("connection_id")

    if None in [credential_type, credential_values, connection_id]:
        raise web.HTTPBadRequest(
            reason=f"""[credential_type, credential_values, connection_id] {[credential_type, credential_values, connection_id]} Some fields need to be filled in"""
        )

    try:
        connection_record: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(
            reason="Couldnt find a connection_record through the connection_id"
        )
    if not connection_record.is_ready:
        raise web.HTTPRequestTimeout(reason="Connection with this agent is not ready")

    try:
        issuer: BaseIssuer = await context.inject(BaseIssuer)
        credential, _ = await issuer.create_credential(
            schema={
                "credential_type": credential_type,
            },
            credential_values=credential_values,
            credential_offer={},
            credential_request={
                "connection_record": connection_record,
            },
        )
    except IssuerError as err:
        raise web.HTTPError(reason=err.roll_up)

    issue = CredentialIssue(credential=credential)
    await outbound_handler(issue, connection_id=connection_record.connection_id)

    return web.json_response(json.loads(credential))


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/issue-credential/send", issue_credential),
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
            "description": "Credential issue, revocation",
            # "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
