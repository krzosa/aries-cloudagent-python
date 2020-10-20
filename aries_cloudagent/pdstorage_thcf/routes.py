import logging
import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields, validate, Schema
from .base import BasePersonalDataStorage
from .api import load_string, save_string
from .error import *
from ..connections.models.connection_record import ConnectionRecord
from ..wallet.error import WalletError
from ..storage.error import StorageError
from .message_types import *


class SaveRecordSchema(Schema):
    payload = fields.Str(required=False)


class SetActiveStorageTypeSchema(Schema):
    type = fields.Str(required=True)
    optional_name = fields.Str(required=False)


class GetRecordFromAgentSchema(Schema):
    connection_id = fields.Str(required=False)
    payload_id = fields.Str(required=False)


class SaveSettingsSchema(Schema):
    settings = fields.Dict(required=False)


class GetSettingsSchema(Schema):
    optional_name: fields.Str(
        description="By providing a different name a new instance is created",
        required=False,
    )


@docs(tags=["PersonalDataStorage"], summary="Save data in a public data storage")
@request_schema(SaveRecordSchema())
async def save_record(request: web.BaseRequest):
    context = request.app["request_context"]
    body = await request.json()

    payload = body.get("payload", None)
    assert payload != None, "payload field is None"

    try:
        payload_id = await save_string(context, payload)
    except PersonalDataStorageError as err:
        raise web.HTTPError(reason=err.roll_up)

    return web.json_response({"payload_id": payload_id})


@docs(
    tags=["PersonalDataStorage"],
    summary="Retrieve data from a public data storage using data id",
)
async def get_record(request: web.BaseRequest):
    context = request.app["request_context"]
    payload_id = request.match_info["payload_id"]

    assert payload_id != None, "payload_id field is empty"

    try:
        result = await load_string(context, payload_id)
    except PersonalDataStorageError as err:
        raise web.HTTPError(reason=err.roll_up)

    return web.json_response({"payload": result})


@docs(
    tags=["PersonalDataStorage"],
    summary="Retrieve data from a public data storage using data id",
)
@querystring_schema(GetRecordFromAgentSchema())
async def get_record_from_agent(request: web.BaseRequest):
    context = request.app["request_context"]
    connection_id = request.query.get("connection_id")
    payload_id = request.query.get("payload_id")

    try:
        connection_record: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except (WalletError, StorageError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    outbound_handler = request.app["outbound_message_router"]
    message = ExchangeDataA(payload_dri=payload_id)
    await outbound_handler(message, connection_id=connection_id)
    return web.json_response({"message_sent": "success"})


@docs(
    tags=["PersonalDataStorage"],
    summary="Set and configure current PersonalDataStorage",
    description="""
    Example of a correct schema:
    {
        "settings":
        {
            "local": {
                "optional_instance_name: "default",
                "no_configuration_needed": "yes-1234"
            },
            "data_vault": {
                "optional_instance_name: "default",
                "no_configuration_needed": "yes-1234"
            },
            "own_your_data": {
                "optional_instance_name: "default",
                "client_id": "test-1234",
                "client_secret": "test-1234",
                "grant_type": "client_credentials"
            }
        }
    }
    """,
)
@request_schema(SaveSettingsSchema())
async def set_settings(request: web.BaseRequest):
    context = request.app["request_context"]
    body = await request.json()
    settings: dict = body.get("settings", None)

    if settings == None:
        raise web.HTTPNotFound(reason="Settings schema is empty")

    for key in settings:
        current_setting = settings.get(key)
        instance_name = current_setting.get("optional_instance_name", "default")

        personal_storage: BasePersonalDataStorage = await context.inject(
            BasePersonalDataStorage, {"personal_storage_type": (key, instance_name)}
        )

        current_setting.pop("optional_instance_name", None)
        personal_storage.settings.update(current_setting)

    return web.json_response({"success": "settings_updated"})


@docs(
    tags=["PersonalDataStorage"],
    summary="Get all registered public storage types and show their configuration",
)
async def get_settings(request: web.BaseRequest):
    context = request.app["request_context"]
    registered_types = context.settings.get("personal_storage_registered_types")
    active_storage_type = context.settings.get("personal_storage_type")
    instance_name = "default"

    response_message = {}
    for key in registered_types:
        personal_storage = await context.inject(
            BasePersonalDataStorage, {"personal_storage_type": (key, instance_name)}
        )
        response_message.update({key: personal_storage.preview_settings})

    return web.json_response(response_message)


@docs(
    tags=["PersonalDataStorage"],
    summary="Set a public data storage type by name",
    description="for example: 'local', get possible types by calling 'GET /pds' endpoint",
)
@querystring_schema(SetActiveStorageTypeSchema())
async def set_active_storage_type(request: web.BaseRequest):
    context = request.app["request_context"]
    instance_name = request.query.get("optional_name", "default")
    pds_type = request.query.get("type", None)
    pds_type_tuple = (pds_type, instance_name)

    check_if_storage_type_is_registered = context.settings.get_value(
        "personal_storage_registered_types"
    ).get(pds_type)

    if check_if_storage_type_is_registered == None:
        raise web.HTTPNotFound(
            reason="Chosen type is not in the registered list, make sure there are no typos! Use GET settings to look for registered types"
        )

    context.settings.set_value("personal_storage_type", pds_type_tuple)
    return web.json_response({"success_type_exists": pds_type_tuple})


@docs(
    tags=["PersonalDataStorage"],
    summary="Get all registered public storage types, get which storage_type is active",
)
async def get_storage_types(request: web.BaseRequest):
    context = request.app["request_context"]
    registered_types = context.settings.get("personal_storage_registered_types")
    active_storage_type = context.settings.get("personal_storage_type")
    instance_name = "default"

    registered_type_names = []
    for key in registered_types:
        personal_storage = await context.inject(
            BasePersonalDataStorage, {"personal_storage_type": (key, instance_name)}
        )
        if personal_storage.settings != {}:
            registered_type_names.append(key)

    return web.json_response(
        {"active": active_storage_type, "types": registered_type_names}
    )


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post("/pds/save", save_record),
            web.post("/pds/settings", set_settings),
            web.post("/pds/activate", set_active_storage_type),
            web.post("/pds/get_from", get_record_from_agent,),
            web.get("/pds", get_storage_types, allow_head=False,),
            web.get("/pds/settings", get_settings, allow_head=False,),
            web.get("/pds/{payload_id}", get_record, allow_head=False,),
        ]
    )
