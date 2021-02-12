from aiohttp import web
from aiohttp_apispec import (
    docs,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import Schema, fields
from .base import BasePDS
from .api import load_multiple, pds_load, pds_save, pds_save_chunks
from .error import PDSError
from ..connections.models.connection_record import ConnectionRecord
from ..storage.error import StorageNotFoundError, StorageError
from .message_types import ExchangeDataA
from .models.saved_personal_storage import SavedPDS
import aries_cloudagent.generated_models as Model


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


@docs(tags=["Personal Data Storage"], summary="Save data in a public data storage")
@request_schema(Model.Payload)
@response_schema(Model.DRIResponse)
async def save_record(request: web.BaseRequest):
    context = request.app["request_context"]
    body = await request.json()

    try:
        payload_id = await pds_save(context, body.get("payload"))
    except PDSError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    return web.json_response({"success": True, "payload_id": payload_id})


@docs(
    tags=["Personal Data Storage"],
    summary="Retrieve data from a public data storage using data id",
)
@response_schema(Model.Payload)
async def get_record(request: web.BaseRequest):
    context = request.app["request_context"]
    payload_id = request.match_info["payload_id"]

    try:
        result = await pds_load(context, payload_id)
    except PDSError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    return web.json_response({"payload": result})


async def pds_request_record_from_other_agent(
    context, connection_id, payload_id, outbound_handler
):
    await ConnectionRecord.retrieve_by_id(context, connection_id)
    message = ExchangeDataA(payload_dri=payload_id)
    await outbound_handler(message, connection_id=connection_id)


async def pds_request_record_from_other_agent_ex(request, connection_id, payload_id):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    await pds_request_record_from_other_agent(
        context, connection_id, payload_id, outbound_handler
    )


@docs(
    tags=["Personal Data Storage"],
    summary="Retrieve data from a public data storage using data id",
)
@querystring_schema(GetRecordFromAgentSchema())
async def get_record_from_agent(request: web.BaseRequest):
    connection_id = request.query.get("connection_id")
    payload_id = request.query.get("payload_id")
    try:
        await pds_request_record_from_other_agent_ex(request, connection_id, payload_id)
    except StorageNotFoundError:
        raise web.HTTPNotFound(reason="Connection not found")

    return web.json_response({"success": True})


async def pds_set_settings(context, settings: dict):
    """
    Get all pds configurations from the user's input json
    and either update all specified instances or create new instances
    for types which are not existent
    """
    assert isinstance(settings, dict) and settings is not {}

    user_message = {}
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

        user_message[type] = {}
        user_message[type]["connected"] = connected
        if exception is not None:
            user_message[type]["exception"] = exception

    return user_message


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

    try:
        user_message = await pds_set_settings(context, settings)
    except PDSError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    return web.json_response(user_message)


@docs(
    tags=["PersonalDataStorage"],
    summary="Get all registered public storage types and show their configuration",
)
@response_schema(Model.ArrayOfPDSSettings)
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

    return web.json_response(response_message)


async def pds_activate(context, pds_type, instance_name="default"):
    check_if_storage_type_is_registered = context.settings.get_value(
        "personal_storage_registered_types"
    )

    if check_if_storage_type_is_registered is None:
        raise PDSError("List of PDSes is not initialized!")

    check_if_storage_type_is_registered = check_if_storage_type_is_registered.get(
        pds_type
    )

    if check_if_storage_type_is_registered is None:
        raise PDSError(
            "Chosen type is not in the registered list, "
            "make sure there are no typos!"
            "Use GET settings to look for registered types"
        )

    try:
        pds_to_activate = await SavedPDS.retrieve_type_name(
            context, pds_type, instance_name
        )
    except StorageNotFoundError as err:
        raise PDSError("Couldn't find PDS " + err.roll_up)

    try:
        active_pds = await SavedPDS.retrieve_active(context)

    except StorageNotFoundError as err:
        raise PDSError("Couldn't find active PDS " + err.roll_up)

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
    try:
        await pds_activate(context, pds_type, instance_name)
    except PDSError as err:
        raise web.HTTPNotFound(reason=err.roll_up)

    return web.json_response(
        {
            "message": f"PDS of type ({pds_type}, {instance_name}) set succesfully",
        }
    )


@docs(
    tags=["PersonalDataStorage"],
    summary="Get all registered public storage types, get which storage_type is active",
)
# @response_schema(Model.PDSResponse)
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
            "active_pds": f"{active_pds.type}, {active_pds.name}",
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
    oca_schema_base_dris = fields.List(fields.Str(required=True), required=True)


@docs(
    tags=["PersonalDataStorage"],
)
@querystring_schema(GetMultipleRecordsForOcaSchema)
async def get_oca_schema_chunks(request: web.BaseRequest):
    context = request.app["request_context"]
    dri_list = request.query
    dri_list = dri_list.getall("oca_schema_base_dris", None)
    if dri_list is None:
        raise web.HTTPBadRequest(reason="Missing data in query parameters")

    try:
        result = await load_multiple(context, oca_schema_base_dri=dri_list)
    except PDSError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    return web.json_response({"success": True, "result": result})


class PostMultipleRecordsForOcaSchema(Schema):
    data = fields.Dict(keys=fields.Str(), values=fields.Dict())


@docs(
    tags=["PersonalDataStorage"],
    summary="Post data in bulk",
)
@request_schema(Model.ArrayOfOCASchemaChunks)
async def post_oca_schema_chunks(request: web.BaseRequest):
    context = request.app["request_context"]
    body = await request.json()
    if __debug__:
        assert isinstance(body, list)

    try:
        result = await pds_save_chunks(context, body)
    except PDSError as err:
        raise web.HTTPInternalServerError(err)

    return web.json_response(result)


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
                "/pds/oca-schema-chunks/",
                get_oca_schema_chunks,
                allow_head=False,
            ),
            web.post(
                "/pds/oca-schema-chunks/",
                post_oca_schema_chunks,
            ),
        ]
    )
