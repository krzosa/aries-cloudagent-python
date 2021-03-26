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
from .base import BasePDS
from .api import pds_load, pds_save, load_multiple
from .error import PDSError
from ..connections.models.connection_record import ConnectionRecord
from ..wallet.error import WalletError
from ..storage.error import StorageNotFoundError, StorageError
from .message_types import ExchangeDataA
from .models.saved_personal_storage import SavedPDS
from aries_cloudagent.pdstorage_thcf.api import pds_oca_data_format_save
import aries_cloudagent.generated_models as model

OCA_DATA_CHUNKS = "tda.oca_chunks"

class SaveRecordSchema(Schema):
    payload = fields.Str(required=True)


class SetActiveStorageTypeSchema(Schema):
    type = fields.Str(required=True)
    optional_name = fields.Str(required=False)


class GetRecordFromAgentSchema(Schema):
    connection_id = fields.Str(required=True)
    payload_id = fields.Str(required=True)


class SaveSettingsSchema(Schema):
    settings = fields.Dict(required=True)


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

    try:
        payload_id = await pds_save(context, body.get("payload"))
    except PDSError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    return web.json_response({"success": True, "payload_id": payload_id})


@docs(
    tags=["PersonalDataStorage"],
    summary="Retrieve data from a public data storage using data id",
)
async def get_record(request: web.BaseRequest):
    context = request.app["request_context"]
    payload_id = request.match_info["payload_id"]

    try:
        result = await pds_load(context, payload_id)
    except PDSError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    return web.json_response({"success": True, "payload": result})


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
        await ConnectionRecord.retrieve_by_id(context, connection_id)
    except (WalletError, StorageError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    outbound_handler = request.app["outbound_message_router"]
    message = ExchangeDataA(payload_dri=payload_id)
    await outbound_handler(message, connection_id=connection_id)
    return web.json_response({"success": True})


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
                "optional_instance_name: "not_default",
                "no_configuration_needed": "yes-1234"
            },
            "own_your_data": {
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

    if settings is None:
        raise web.HTTPNotFound(reason="Settings schema is empty")

    # get all pds configurations from the user's input json
    # and either update all specified instances or create new instances
    # for types which are not existent
    user_msg = {}
    for type in settings:
        per_type_setting = settings.get(type)
        instance_name = per_type_setting.get("optional_instance_name", "default")
        per_type_setting.pop("optional_instance_name", None)

        scope = per_type_setting.get("scope")
        if scope is not None:
            if not scope:
                per_type_setting.pop("scope")
            elif scope.isnumeric():
                scope_options = {"0": "admin", "1": "write", "2": "read"}
                per_type_setting["scope"] = scope_options.get(scope, "")
        if scope is None:
            per_type_setting["scope"] = None

        # create or update a saved pds
        try:
            saved_pds = await SavedPDS.retrieve_type_name(context, type, instance_name)
            saved_pds.settings = per_type_setting
        except StorageNotFoundError:
            saved_pds = SavedPDS(
                type=type,
                name=instance_name,
                state=SavedPDS.INACTIVE,
                settings=per_type_setting,
            )

        await saved_pds.save(context)

        # update active pds instances with new settings
        personal_storage: BasePDS = await context.inject(
            BasePDS, {"personal_storage_type": (type, instance_name)}
        )
        personal_storage.settings.update(per_type_setting)
        connected, exception = await personal_storage.ping()

        user_msg[type] = {}
        user_msg[type]["connected"] = connected
        if exception is not None:
            user_msg[type]["exception"] = exception

    return web.json_response({"success": "True", "status": user_msg})


@docs(
    tags=["PersonalDataStorage"],
    summary="Get all registered public storage types and show their configuration",
)
@response_schema(model.PDSGetSettingsSchemaResponse)
async def get_settings(request: web.BaseRequest):
    context = request.app["request_context"]

    try:
        saved_pds = await SavedPDS.query(context)
        assert isinstance(saved_pds, list), f"not list {saved_pds}, {type(saved_pds)}"
        print("get_settings saved_pds:", saved_pds)
    except StorageError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    response_message = {}
    for pds in saved_pds:
        response_message.update({f"{pds.type}, {pds.name}": pds.settings})

    # TODO "success": True,
    return web.json_response(response_message)


async def pds_activate(context, pds_type, instance_name="default"):
    check_if_storage_type_is_registered = context.settings.get_value(
        "personal_storage_registered_types"
    )

    if check_if_storage_type_is_registered is None:
        raise web.HTTPNotFound(reason="List of PDSes is not initialized!")

    check_if_storage_type_is_registered = check_if_storage_type_is_registered.get(
        pds_type
    )

    if check_if_storage_type_is_registered is None:
        raise web.HTTPNotFound(
            reason="Chosen type is not in the registered list, "
            "make sure there are no typos!"
            "Use GET settings to look for registered types"
        )

    try:
        pds_to_activate = await SavedPDS.retrieve_type_name(
            context, pds_type, instance_name
        )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason="Couldn't find PDS " + err.roll_up)

    try:
        active_pds = await SavedPDS.retrieve_active(context)

    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason="Couldn't find active PDS " + err.roll_up)

    active_pds.state = SavedPDS.INACTIVE
    pds_to_activate.state = SavedPDS.ACTIVE

    await active_pds.save(context)
    await pds_to_activate.save(context)


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
    await pds_activate(context, pds_type, instance_name)

    return web.json_response(
        {
            "success": True,
            "message": f"PDS of type{pds_type}, {instance_name} set succesfully",
        }
    )


@docs(
    tags=["PersonalDataStorage"],
    summary="Get all registered public storage types, get which storage_type is active",
)
async def get_storage_types(request: web.BaseRequest):
    context = request.app["request_context"]
    registered_types = context.settings.get("personal_storage_registered_types")
    instance_name = "default"

    try:
        active_pds = await SavedPDS.retrieve_active(context)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason="Couldn't find active storage" + err.roll_up)

    registered_type_names = {}
    for key in registered_types:
        personal_storage = await context.inject(
            BasePDS, {"personal_storage_type": (key, instance_name)}
        )
        registered_type_names[key] = personal_storage.preview_settings

    return web.json_response(
        {
            "success": True,
            "active": f"{active_pds.type}, {active_pds.name}",
            "types": registered_type_names,
        }
    )


class GetMultipleRecordsSchema(Schema):
    table = fields.Str(required=False)
    oca_schema_base_dri = fields.Str(required=False)


@docs(
    tags=["PersonalDataStorage"],
    summary="Retrieve data from a public data storage using data id",
)
@querystring_schema(GetMultipleRecordsSchema)
async def get_multiple_records(request: web.BaseRequest):
    context = request.app["request_context"]
    table = request.query.get("table")
    oca_schema_base_dri = request.query.get("oca_schema_base_dri")

    try:
        result = await load_multiple(
            context, table=table, oca_schema_base_dri=oca_schema_base_dri
        )
    except PDSError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    return web.json_response({"success": True, "result": result})


class GetMultipleRecordsForOcaSchema(Schema):
    oca_schema_base_dris = fields.List(fields.Str(required=True))


@docs(
    tags=["PersonalDataStorage"],
)
@querystring_schema(GetMultipleRecordsForOcaSchema)
async def get_multiple_records_for_oca_form_filling(request: web.BaseRequest):
    context = request.app["request_context"]
    dri_list = request.query
    dri_list = dri_list.getall("oca_schema_base_dris")
    OCA_DATA_CHUNKS = "tda.oca_chunks"

    result = {}
    try:
        for dri in dri_list:
            result[dri] = await load_multiple(
                context, table=OCA_DATA_CHUNKS + "." + dri
            )
    except PDSError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    return web.json_response({"success": True, "result": result})


class PostMultipleRecordsForOcaSchema(Schema):
    data = fields.Dict(keys=fields.Str(), values=fields.Dict())


@docs(
    tags=["PersonalDataStorage"],
    summary="Post data in bulk",
    description="""
    Example input:
    {
        "data":{
            "DRI:12345":{
                "t":"o",
                "p":{
                    "address":"DRI:123456",
                    "test_value":"ok"
                }
            },
            "DRI:123456":{
                "t":"o",
                "p":{
                    "second_dri":"DRI:1234567",
                    "test_value":"ok"
                }
            },
            "DRI:1234567":{
                "t":"o",
                "p":{
                    "third_dri":"DRI:123456",
                    "test_value":"ok"
                }
            },
            "1234567":{
                "t":"o",
                "p":{
                    "third_dri":"DRI:123456",
                    "test_value":"ok"
                }
            }
        }
    }
    """,
)
@request_schema(PostMultipleRecordsForOcaSchema)
async def post_multiple_records_for_oca_form_filling(request: web.BaseRequest):
    context = request.app["request_context"]
    body = await request.json()
    data = body.get("data")

    try:
        result = await pds_oca_data_format_save(context, data)
    except PDSError as err:
        raise web.HTTPInternalServerError(err)

    return web.json_response({"success": True, "result": result})


# @docs(tags=["Swagger"], summary="Get agent's swagger schema in json format")
# async def get_swagger_schema(request: web.BaseRequest):
#     return web.json_response(request.app._state["swagger_dict"])


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post("/pds/save", save_record),
            web.post("/pds/settings", set_settings),
            web.post("/pds/activate", set_active_storage_type),
            web.post(
                "/pds/get_from",
                get_record_from_agent,
            ),
            web.get(
                "/pds",
                get_storage_types,
                allow_head=False,
            ),
            web.get(
                "/pds/settings",
                get_settings,
                allow_head=False,
            ),
            web.get(
                "/pds/{payload_id}",
                get_record,
                allow_head=False,
            ),
            web.get(
                "/pds/current/",
                get_multiple_records_for_oca_form_filling,
                allow_head=False,
            ),
            web.post(
                "/pds/current/",
                post_multiple_records_for_oca_form_filling,
            ),
            # web.get("/swagger", get_swagger_schema, allow_head=False),
        ]
    )
