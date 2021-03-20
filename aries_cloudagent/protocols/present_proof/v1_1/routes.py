"""Admin routes for presentations."""

import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    querystring_schema,
    request_schema,
)
from marshmallow import fields
from ....connections.models.connection_record import ConnectionRecord
from ....holder.base import BaseHolder, HolderError
from .models.presentation_exchange import THCFPresentationExchange
from ....messaging.models.openapi import OpenAPISchema
from aries_cloudagent.protocols.issue_credential.v1_1.utils import retrieve_connection
from .messages.request_proof import RequestProof
from .messages.present_proof import PresentProof
from .models.utils import retrieve_exchange
import logging
from aries_cloudagent.pdstorage_thcf.api import (
    load_multiple,
    pds_load,
    pds_oca_data_format_save,
    pds_save_a,
    pds_get_usage_policy_if_active_pds_supports_it,
)
from aries_cloudagent.holder.pds import CREDENTIALS_TABLE
from aries_cloudagent.pdstorage_thcf.error import PDSError
from aries_cloudagent.protocols.issue_credential.v1_1.routes import (
    routes_get_public_did,
)
from aries_cloudagent.issuer.base import BaseIssuer, IssuerError
from .messages.acknowledge_proof import AcknowledgeProof

LOGGER = logging.getLogger(__name__)


class PresentationRequestAPISchema(OpenAPISchema):
    connection_id = fields.Str(required=True)
    requested_attributes = fields.List(fields.Str(required=True), required=True)
    issuer_did = fields.Str(required=False)
    schema_base_dri = fields.Str(required=True)


class PresentProofAPISchema(OpenAPISchema):
    exchange_record_id = fields.Str(required=True)
    credential_id = fields.Str(required=True)


class RetrieveExchangeQuerySchema(OpenAPISchema):
    connection_id = fields.Str(required=False)
    thread_id = fields.Str(required=False)
    initiator = fields.Str(required=False)
    role = fields.Str(required=False)
    state = fields.Str(required=False)


class AcknowledgeProofSchema(OpenAPISchema):
    exchange_record_id = fields.Str(required=True)
    status = fields.Boolean(required=True)


@docs(tags=["present-proof"], summary="Sends a proof presentation")
@request_schema(PresentationRequestAPISchema())
async def request_presentation_api(request: web.BaseRequest):
    """Request handler for sending a presentation."""
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    body = await request.json()

    connection_id = body.get("connection_id")
    await retrieve_connection(context, connection_id)  # throw exception if not found

    presentation_request = {
        "requested_attributes": body.get("requested_attributes"),
        "schema_base_dri": body.get("schema_base_dri"),
    }
    issuer_did = body.get("issuer_did")
    if issuer_did is not None:
        presentation_request["issuer_did"] = issuer_did

    usage_policy = await pds_get_usage_policy_if_active_pds_supports_it(context)
    message = RequestProof(
        presentation_request=presentation_request, usage_policy=usage_policy
    )
    await outbound_handler(message, connection_id=connection_id)

    exchange_record = THCFPresentationExchange(
        connection_id=connection_id,
        thread_id=message._thread_id,
        initiator=THCFPresentationExchange.INITIATOR_SELF,
        role=THCFPresentationExchange.ROLE_VERIFIER,
        state=THCFPresentationExchange.STATE_REQUEST_SENT,
        presentation_request=presentation_request,
    )

    LOGGER.debug("exchange_record %s", exchange_record)
    await exchange_record.save(context)

    return web.json_response(
        {
            "success": True,
            "message": "proof sent and exchange updated",
            "exchange_id": exchange_record._id,
            "thread_id": message._thread_id,
            "connection_id": connection_id,
        }
    )


@docs(tags=["present-proof"], summary="Send a credential presentation")
@request_schema(PresentProofAPISchema())
async def present_proof_api(request: web.BaseRequest):
    """
    Allows to respond to an already existing exchange with a proof presentation.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()
    exchange_record_id = body.get("exchange_record_id")
    credential_id = body.get("credential_id")

    exchange = await retrieve_exchange(context, exchange_record_id, web.HTTPNotFound)

    if exchange.role != exchange.ROLE_PROVER:
        raise web.HTTPBadRequest(reason="Invalid exchange role")
    if exchange.state != exchange.STATE_REQUEST_RECEIVED:
        raise web.HTTPBadRequest(reason="Invalid exchange state")

    connection_record: ConnectionRecord = await retrieve_connection(
        context, exchange.connection_id
    )

    try:
        holder: BaseHolder = await context.inject(BaseHolder)
        requested_credentials = {"credential_id": credential_id}
        presentation = await holder.create_presentation(
            presentation_request=exchange.presentation_request,
            requested_credentials=requested_credentials,
            schemas={},
            credential_definitions={},
        )
    except HolderError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    public_did = await routes_get_public_did(context)
    message = PresentProof(
        credential_presentation=presentation, prover_public_did=public_did
    )
    message.assign_thread_id(exchange.thread_id)
    await outbound_handler(message, connection_id=connection_record.connection_id)

    exchange.state = exchange.STATE_PRESENTATION_SENT
    await exchange.presentation_pds_set(context, json.loads(presentation))
    await exchange.save(context)

    return web.json_response(
        {
            "success": True,
            "message": "proof sent and exchange updated",
            "exchange_id": exchange._id,
        }
    )


@docs(tags=["present-proof"], summary="retrieve exchange record")
@querystring_schema(AcknowledgeProofSchema())
async def acknowledge_proof(request: web.BaseRequest):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    query = request.query

    exchange: THCFPresentationExchange = await retrieve_exchange(
        context, query.get("exchange_record_id"), web.HTTPNotFound
    )

    if exchange.role != exchange.ROLE_VERIFIER:
        raise web.HTTPBadRequest(reason="Invalid exchange role")
    if exchange.state != exchange.STATE_PRESENTATION_RECEIVED:
        raise web.HTTPBadRequest(reason="Invalid exchange state")

    connection_record: ConnectionRecord = await retrieve_connection(
        context, exchange.connection_id
    )

    try:
        issuer: BaseIssuer = await context.inject(BaseIssuer)
        credential = await issuer.create_credential_ex(
            credential_values={
                "oca_data": {
                    "verified": str(query.get("status")),
                    "presentation_dri": exchange.presentation_dri,
                    "issuer_name": context.settings.get("default_label"),
                },
                "oca_schema_dri": "bCN4tzZssT4sDDFFTh5AmoesdQeeTSyjNrQ6gxnCerkn",
            },
            credential_type="ProofAcknowledgment",
            subject_public_did=exchange.prover_public_did,
        )
    except IssuerError as err:
        raise web.HTTPInternalServerError(
            reason=f"Error occured while creating a credential {err.roll_up}"
        )

    message = AcknowledgeProof(credential=credential)
    message.assign_thread_id(exchange.thread_id)
    await outbound_handler(message, connection_id=connection_record.connection_id)

    exchange.state = exchange.STATE_ACKNOWLEDGED
    await exchange.verifier_ack_cred_pds_set(context, credential)
    await exchange.save(context)
    return web.json_response(
        {
            "success": True,
            "message": "ack sent and exchange record updated",
            "exchange_record_id": exchange._id,
            "ack_credential_dri": exchange.acknowledgment_credential_dri,
        }
    )


class DebugEndpointSchema(OpenAPISchema):
    # {DRI1: [{timestamp: 23423453453534, data: {...}},{}], DRI2: [{},{}], DRI3: [{},{}] }
    #     {d: {456...}, t: Date.current.getMilliseconds()} } d - data; t - timestamp
    oca_data = fields.List(fields.Str())


@docs(tags=["PersonalDataStorage"])
@querystring_schema(DebugEndpointSchema)
async def debug_endpoint(request: web.BaseRequest):
    context = request.app["request_context"]

    data = {"data": "data"}
    payload_id = await pds_save_a(context, data, oca_schema_dri="12345", table="test")
    ret = await pds_load(context, payload_id)
    assert ret == data

    # body = await request.json()
    # oca_data = body["oca_data"]
    # print(oca_data)

    data = {
        "DRI:12345": {"t": "o", "p": {"address": "DRI:123456", "test_value": "ok"}},
        "DRI:123456": {
            "t": "o",
            "p": {"second_dri": "DRI:1234567", "test_value": "ok"},
        },
        "DRI:1234567": {"t": "o", "p": {"third_dri": "DRI:123456", "test_value": "ok"}},
        "1234567": {"t": "o", "p": {"third_dri": "DRI:123456", "test_value": "ok"}},
    }

    ids = await pds_oca_data_format_save(context, data)
    # serialized = await pds_oca_data_format_serialize_dict_recursive(context, data)
    multiple = await load_multiple(context, oca_schema_base_dri=["12345", "123456"])

    return web.json_response({"success": True, "result": ids, "multiple": multiple})


from aiohttp import ClientSession, FormData, ClientTimeout


async def verify_usage_policy(controller_usage_policy, subject_usage_policy):
    timeout = ClientTimeout(total=15)
    async with ClientSession(timeout=timeout) as session:
        result = await session.post(
            "https://governance.ownyourdata.eu/api/usage-policy/match",
            json={
                "data-subject": subject_usage_policy,
                "data-controller": controller_usage_policy,
            },
        )
        result = await result.text()
        return result


@docs(tags=["present-proof"], summary="retrieve exchange record")
@querystring_schema(RetrieveExchangeQuerySchema())
async def retrieve_credential_exchange_api(request: web.BaseRequest):
    context = request.app["request_context"]

    records = await THCFPresentationExchange.query(context, tag_filter=request.query)
    usage_policy = await pds_get_usage_policy_if_active_pds_supports_it(context)

    result = []
    for i in records:
        serialize = i.serialize()
        if i.presentation_dri is not None:
            serialize["presentation"] = await i.presentation_pds_get(context)
        if usage_policy and i.requester_usage_policy:
            serialize["usage_policies_match"] = await verify_usage_policy(
                i.requester_usage_policy, usage_policy
            )
        result.append(serialize)

    """
    Download credentials
    """

    try:
        credentials = await load_multiple(context, table=CREDENTIALS_TABLE)
    except json.JSONDecodeError:
        LOGGER.warn(
            "Error parsing credentials, perhaps there are no credentials in store %s",
            credentials,
        )
        credentials = {}
    except PDSError as err:
        LOGGER.warn("PDSError %s", err.roll_up)
        credentials = {}

    """
    Match the credential requests with credentials in the possesion of the agent
    in this case we check if both issuer_did and oca_schema_dri are correct
    """

    for rec in result:
        rec["list_of_matching_credentials"] = []
        for cred in credentials:
            try:
                cred_content = json.loads(cred["content"])
            except (json.JSONDecodeError, TypeError):
                cred_content = cred["content"]

            print("Cred content:", cred_content)

            record_base_dri = rec["presentation_request"].get(
                "schema_base_dri", "INVALIDA"
            )
            cred_base_dri = cred_content["credentialSubject"].get(
                "oca_schema_dri", "INVALIDC"
            )
            if record_base_dri == cred_base_dri:
                rec["list_of_matching_credentials"].append(cred["dri"])

    return web.json_response({"success": True, "result": result})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post(
                "/present-proof/request",
                request_presentation_api,
            ),
            web.post(
                "/present-proof/present",
                present_proof_api,
            ),
            web.post(
                "/present-proof/acknowledge",
                acknowledge_proof,
            ),
            web.get(
                "/present-proof/exchange/record",
                retrieve_credential_exchange_api,
                allow_head=False,
            ),
            web.post("/present-proof/debug", debug_endpoint),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "present-proof",
            "description": "Proof presentation",
            "externalDocs": {"description": "Specification"},
        }
    )
