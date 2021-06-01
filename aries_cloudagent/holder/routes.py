"""Holder admin routes."""

from aries_cloudagent.aathcf.utils import build_context, run_standalone_async
import aries_cloudagent.config.global_variables as globals
from aries_cloudagent.pdstorage_thcf.api import pds_query_by_oca_schema_dri
import json

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, response_schema
from marshmallow import fields

from .base import BaseHolder, HolderError
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.valid import (
    INDY_CRED_DEF_ID,
    INDY_REV_REG_ID,
    INDY_SCHEMA_ID,
    UUIDFour,
)
from ..wallet.error import WalletNotFoundError


class AttributeMimeTypesResultSchema(OpenAPISchema):
    """Result schema for credential attribute MIME type."""


class RawEncCredAttrSchema(OpenAPISchema):
    """Credential attribute schema."""

    raw = fields.Str(description="Raw value", example="Alex")
    encoded = fields.Str(
        description="(Numeric string) encoded value",
        example="412821674062189604125602903860586582569826459817431467861859655321",
    )


class RevRegSchema(OpenAPISchema):
    """Revocation registry schema."""

    accum = fields.Str(
        description="Revocation registry accumulator state",
        example="21 136D54EA439FC26F03DB4b812 21 123DE9F624B86823A00D ...",
    )


class WitnessSchema(OpenAPISchema):
    """Witness schema."""

    omega = fields.Str(
        description="Revocation registry witness omega state",
        example="21 129EA8716C921058BB91826FD 21 8F19B91313862FE916C0 ...",
    )


class CredentialSchema(OpenAPISchema):
    """Result schema for a credential query."""

    schema_id = fields.Str(description="Schema identifier", **INDY_SCHEMA_ID)
    cred_def_id = fields.Str(
        description="Credential definition identifier", **INDY_CRED_DEF_ID
    )
    rev_reg_id = fields.Str(
        description="Revocation registry identifier", **INDY_REV_REG_ID
    )
    values = fields.Dict(
        keys=fields.Str(description="Attribute name"),
        values=fields.Nested(RawEncCredAttrSchema),
        description="Attribute names mapped to their raw and encoded values",
    )
    signature = fields.Dict(description="Digital signature")
    signature_correctness_proof = fields.Dict(description="Signature correctness proof")
    rev_reg = fields.Nested(RevRegSchema)
    witness = fields.Nested(WitnessSchema)


class CredentialsListSchema(OpenAPISchema):
    """Result schema for a credential query."""

    results = fields.List(fields.Nested(CredentialSchema()))


class CredIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    credential_id = fields.Str(
        description="Credential identifier", required=True, example=UUIDFour.EXAMPLE
    )


@docs(tags=["credentials"], summary="Fetch a credential from wallet by id")
@match_info_schema(CredIdMatchInfoSchema())
@response_schema(CredentialSchema(), 200)
async def credentials_get(request: web.BaseRequest):
    """
    Request handler for retrieving a credential.

    Args:
        request: aiohttp request object

    Returns:
        The credential response

    """
    context = request.app["request_context"]

    credential_id = request.match_info["credential_id"]

    holder: BaseHolder = await context.inject(BaseHolder)
    try:
        credential = await holder.get_credential(credential_id)
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    credential_json = json.loads(credential)
    return web.json_response(credential_json)


@docs(tags=["credentials"], summary="Get attribute MIME types from wallet")
@match_info_schema(CredIdMatchInfoSchema())
@response_schema(AttributeMimeTypesResultSchema(), 200)
async def credentials_attr_mime_types_get(request: web.BaseRequest):
    """
    Request handler for getting credential attribute MIME types.

    Args:
        request: aiohttp request object

    Returns:
        The MIME types response

    """
    context = request.app["request_context"]
    credential_id = request.match_info["credential_id"]
    holder: BaseHolder = await context.inject(BaseHolder)

    return web.json_response(await holder.get_mime_type(credential_id))


@docs(tags=["credentials"], summary="Remove a credential from the wallet by id")
@match_info_schema(CredIdMatchInfoSchema())
async def credentials_remove(request: web.BaseRequest):
    """
    Request handler for searching connection records.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context = request.app["request_context"]

    credential_id = request.match_info["credential_id"]

    holder: BaseHolder = await context.inject(BaseHolder)
    try:
        await holder.delete_credential(credential_id)
    except WalletNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response({})


async def documents_get(context, dri_list):
    result = []
    for i in dri_list:
        credentials = await pds_query_by_oca_schema_dri(context, i)
        for j in credentials:
            result.extend(j["payload"])
    return result


async def documents_given_get(context):
    result = await documents_get(context, globals.DOCUMENTS_GIVEN)
    return result


async def documents_mine_get(context):
    result = await documents_get(context, globals.DOCUMENTS_MINE)
    return result


@docs(
    tags=["credentials"],
    summary="Fetch credentials from wallet",
)
async def credentials_list(request: web.BaseRequest):
    context = request.app["request_context"]
    docs = await documents_mine_get(context)
    return web.json_response(docs)


@docs(
    tags=["credentials"],
    summary="Fetch given documents",
)
async def credentials_list_given(request: web.BaseRequest):
    context = request.app["request_context"]
    result = await documents_given_get(context)
    return web.json_response(result)


async def register(app: web.Application):
    app.add_routes(
        [
            web.get("/credential/{credential_id}", credentials_get, allow_head=False),
            web.get(
                "/credential/mime-types/{credential_id}",
                credentials_attr_mime_types_get,
                allow_head=False,
            ),
            web.post("/credential/{credential_id}/remove", credentials_remove),
            web.get("/credentials", credentials_list, allow_head=False),
            web.get("/documents/mine", credentials_list, allow_head=False),
            web.get("/documents/given", credentials_list_given, allow_head=False),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "credentials",
            "description": "Holder credential management",
            "externalDocs": {
                "description": "Overview",
                "url": ("https://w3c.github.io/vc-data-model/#credentials"),
            },
        }
    )


async def test_credentials_list_given():
    context = await build_context()
    credentials_list = await documents_given_get(context)
    credentials_list = await documents_mine_get(context)
    print(credentials_list)


async def tests():
    await test_credentials_list_given()


run_standalone_async(__name__, tests)
