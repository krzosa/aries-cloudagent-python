"""Admin routes for presentations."""

from uuid import uuid4
from aiohttp_apispec.decorators.response import response_schema
import aries_cloudagent.generated_models as Model
from aries_cloudagent.config.global_variables import CREDENTIALS_TABLE
import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    querystring_schema,
    request_schema,
)
from marshmallow import fields
from ....holder.base import BaseHolder, HolderError
from .models.presentation_exchange import THCFPresentationExchange
from ....messaging.models.openapi import OpenAPISchema
from aries_cloudagent.protocols.issue_credential.v1_1.utils import retrieve_connection
from .messages.request_proof import RequestProof
from .messages.present_proof import PresentProof
from .models.utils import retrieve_exchange
import logging
from aries_cloudagent.pdstorage_thcf.api import (
    oyd_verify_usage_policy,
    pds_get_usage_policy_if_active_pds_supports_it,
    pds_query_by_oca_schema_dri,
)
from aries_cloudagent.pdstorage_thcf.error import PDSError
from aries_cloudagent.protocols.issue_credential.v1_1.routes import (
    routes_get_public_did,
)
from aries_cloudagent.issuer.base import BaseIssuer, IssuerError
from .messages.acknowledge_proof import AcknowledgeProof
import aries_cloudagent.config.global_variables as globals

LOGGER = logging.getLogger(__name__)


class PresentationRequestAPISchema(OpenAPISchema):
    connection_id = fields.Str(required=True)
    requested_attributes = fields.List(fields.Str(required=True), required=True)
    issuer_did = fields.Str(required=False)  # Requested issuer did
    oca_schema_dri = fields.Str(required=True)


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


class Empty(OpenAPISchema):
    pass


async def request_presentation(context, connection_id, oca_schema_dri, issuer_did=None):
    await retrieve_connection(context, connection_id)
    presentation_request = {"oca_schema_dri": oca_schema_dri}
    if issuer_did is not None:
        presentation_request["issuer_did"] = issuer_did

    usage_policy = await pds_get_usage_policy_if_active_pds_supports_it(context)
    message = RequestProof(
        presentation_request=presentation_request, usage_policy=usage_policy
    )
    message.assign_thread_id(str(uuid4()))

    exchange_record = THCFPresentationExchange(
        connection_id=connection_id,
        thread_id=message._thread_id,
        initiator=THCFPresentationExchange.INITIATOR_SELF,
        role=THCFPresentationExchange.ROLE_VERIFIER,
        state=THCFPresentationExchange.STATE_REQUEST_SENT,
        presentation_request=presentation_request,
    )
    await exchange_record.save(context)

    return message, exchange_record


@docs(tags=["present-proof"], summary="Send a presentation request to other agent")
@request_schema(Model.PresentationRequest)
@response_schema(Empty)
async def request_presentation_route(request: web.BaseRequest):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    body = await request.json()
    message, exchange_record = await request_presentation(
        context,
        body.get("connection_id"),
        body.get("oca_schema_dri"),
        body.get("issuer_did"),
    )
    await outbound_handler(message, connection_id=exchange_record.connection_id)
    return web.json_response({})


async def present_proof(context, exchange_record_id, credential_id=None):
    exchange = await retrieve_exchange(context, exchange_record_id, web.HTTPNotFound)
    if exchange.role != exchange.ROLE_PROVER:
        raise web.HTTPBadRequest(reason="Invalid exchange role")
    if exchange.state != exchange.STATE_REQUEST_RECEIVED:
        raise web.HTTPBadRequest(reason="Invalid exchange state")
    await retrieve_connection(context, exchange.connection_id)
    presentation = None
    if credential_id:
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
    return message, presentation, exchange


async def present_proof_save(context, exchange, presentation):
    if presentation:
        exchange.state = exchange.STATE_PRESENTATION_SENT
        await exchange.presentation_pds_set(context, json.loads(presentation))
    else:
        presentation.state = exchange.STATE_REQUEST_DENIED
    await exchange.save(context)


async def presentation_request(request):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    body = await request.json()
    message, presentation, exchange = await present_proof(
        context, request.match_info["presentation_request_id"], body.get("document_dri")
    )
    await outbound_handler(message, connection_id=exchange.connection_id)
    await present_proof_save(context, exchange, presentation)

    return web.json_response()


class DocumentDRI(OpenAPISchema):
    document_dri = fields.Str(required=False)


@docs(tags=["present-proof"], summary="Send a credential presentation")
@request_schema(DocumentDRI())
@response_schema(Empty)
async def accept_presentation_request_route(request: web.BaseRequest):
    result = await presentation_request(request)
    return result


@docs(tags=["present-proof"], summary="Send a credential presentation")
@response_schema(Empty)
async def reject_presentation_request_route(request: web.BaseRequest):
    result = await presentation_request(request)
    return result


async def process_presentation(context, exchange_record_id, accept):
    exchange: THCFPresentationExchange = await retrieve_exchange(
        context, exchange_record_id, web.HTTPNotFound
    )

    if exchange.role != exchange.ROLE_VERIFIER:
        raise web.HTTPBadRequest(reason="Invalid exchange role")
    if exchange.state != exchange.STATE_PRESENTATION_RECEIVED:
        raise web.HTTPBadRequest(reason="Invalid exchange state")

    await retrieve_connection(context, exchange.connection_id)

    message = None
    if accept:
        try:
            issuer: BaseIssuer = await context.inject(BaseIssuer)
            credential = await issuer.create_credential_ex(
                credential_values={
                    "oca_data": {
                        "presentation_dri": exchange.presentation_dri,
                        "issuer_name": context.settings.get("default_label"),
                    },
                    "oca_schema_dri": globals.ACK_CREDENTIAL_DRI,
                },
                credential_type="ProofAcknowledgment",
                subject_public_did=exchange.prover_public_did,
            )
        except IssuerError as err:
            raise web.HTTPInternalServerError(
                reason=f"Error occured while creating a credential {err.roll_up}"
            )

        message = AcknowledgeProof(credential=credential)
        exchange.state = exchange.STATE_ACCEPTED
    else:
        message = AcknowledgeProof(credential=None)
        exchange.state = exchange.STATE_REJECTED
    message.assign_thread_id(exchange.thread_id)

    return message, exchange


async def process_presentation_save(context, exchange, credential):
    await exchange.verifier_ack_cred_pds_set(context, credential)
    await exchange.save(context)


async def accept_or_reject_presentation_route(request, accept):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    presentation_id = request.match_info["presentation_id"]
    message, exchange = await process_presentation(context, presentation_id, accept)
    await outbound_handler(message, connection_id=exchange.connection_id)
    return web.json_response()


@docs(tags=["present-proof"], summary="Accept presentation")
async def accept_presentation_route(request: web.BaseRequest):
    result = await accept_or_reject_presentation_route(request, True)
    return result


@docs(tags=["present-proof"], summary="Reject a presentation")
async def reject_presentation_route(request: web.BaseRequest):
    result = await accept_or_reject_presentation_route(request, False)
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
            serialize["usage_policies_match"] = await oyd_verify_usage_policy(
                i.requester_usage_policy, usage_policy
            )
        result.append(serialize)

    """
    Download credentials
    """

    try:
        credentials = await pds_query_by_oca_schema_dri(context, CREDENTIALS_TABLE)
    except json.JSONDecodeError:
        LOGGER.warn(
            "Error parsing credentials, perhaps there are no credentials in store %s",
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
                "oca_schema_dri", "INVALIDA"
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
                "/presentation-requests",
                request_presentation_route,
            ),
            web.put(
                "/presentation-requests/{presentation_request_id}/reject",
                reject_presentation_request_route,
            ),
            web.put(
                "/presentation-requests/{presentation_request_id}/accept",
                accept_presentation_request_route,
            ),
            web.put(
                "/presentations/{presentation_id}/reject", reject_presentation_route
            ),
            web.put(
                "/presentations/{presentation_id}/accept", accept_presentation_route
            ),
            web.get(
                "/present-proof/exchange/record",
                retrieve_credential_exchange_api,
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
            "name": "present-proof",
            "description": "Proof presentation",
            "externalDocs": {"description": "Specification"},
        }
    )
