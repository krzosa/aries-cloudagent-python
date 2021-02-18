import re
from aiohttp import web
from aiohttp_apispec import (
    docs,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import Schema, fields
from .base import BasePDS
from .api import (
    load_multiple,
    pds_get,
    pds_load,
    pds_save,
    pds_save_chunks,
    pds_set_settings,
)
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


@docs(tags=["PersonalDataStorage"], summary="Save data in a public data storage")
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
    tags=["PersonalDataStorage"],
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
    tags=["PersonalDataStorage"],
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


@docs(
    tags=["PersonalDataStorage"],
    summary="Set and configure current PersonalDataStorage",
)
@request_schema(Model.ArrayOfPDSSettings)
@response_schema(Model.ArrayOfPDSDriverStatuses)
async def set_settings(request: web.BaseRequest):
    context = request.app["request_context"]
    body = await request.json()
    if __debug__:
        assert (
            isinstance(body, list) and body is not []
        ), "Error invalid input value, check the schema!"

    try:
        user_message = await pds_set_settings(context, body)
    except PDSError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    return web.json_response(user_message)


def unpack_pds_settings_to_user_facing_schema(list_of_pds):
    if __debug__:
        assert isinstance(list_of_pds, list)
        assert len(list_of_pds) > 0
    result = []
    for pds in list_of_pds:
        pds_setting = {}
        current_driver_setting = pds.settings.copy()
        client_id = current_driver_setting.pop("client_id", None)
        client_secret = current_driver_setting.pop("client_secret", None)
        if client_id:
            pds_setting["client_id"] = client_id
        if client_secret:
            pds_setting["client_secret"] = client_secret
        pds_setting["instance_name"] = pds.name
        pds_setting["driver"] = {"name": pds.type, pds.type: current_driver_setting}
        result.append(pds_setting)
    return result


@docs(
    tags=["PersonalDataStorage"],
    summary="Get all registered public storage types and show their configuration",
)
@response_schema(Model.ArrayOfPDSSettings)
async def get_settings(request: web.BaseRequest):
    context = request.app["request_context"]

    try:
        pds_list = await SavedPDS.query(context)
        if __debug__:
            assert isinstance(pds_list, list)
    except StorageError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    result = unpack_pds_settings_to_user_facing_schema(pds_list)
    return web.json_response(result)


def pds_check_if_driver_is_registered(settings, pds_driver):
    check_if_pds_driver_is_registered = settings.get_value(
        "personal_storage_registered_types"
    )

    if check_if_pds_driver_is_registered is None:
        raise PDSError("List of PDSes is not initialized!")

    check_if_pds_driver_is_registered = check_if_pds_driver_is_registered.get(
        pds_driver
    )

    if check_if_pds_driver_is_registered is None:
        raise PDSError(
            "Chosen driver is not in the registered list, "
            "make sure there are no typos!"
            "Use GET settings to look for registered types"
        )


async def pds_activate(context, pds_type, instance_name="default"):
    pds_check_if_driver_is_registered(context.settings, pds_type)
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
@request_schema(Model.PDSActivate)
async def pds_post_activate(request: web.BaseRequest):
    context = request.app["request_context"]
    body = await request.json()
    instance_name = body.get("instance_name", "default")
    driver = body.get("driver", None)
    try:
        await pds_activate(context, driver, instance_name)
    except PDSError as err:
        raise web.HTTPNotFound(reason=err.roll_up)

    return web.json_response()


async def pds_drivers_oca_schema_dris_also_creates_default_instances(context):
    drivers = context.settings.get("personal_storage_registered_types")
    registered = []
    for key in drivers:
        personal_storage = await pds_get(context, key, "default")
        driver = {
            "name": key,
            "oca_schema_dri": personal_storage.preview_settings["oca_schema_dri"],
        }
        registered.append(driver)

    return registered


@docs(
    tags=["PersonalDataStorage"],
    summary="Get all registered public storage types, get which storage_type is active",
)
@response_schema(Model.ArrayOfPDSDrivers)
async def get_pds_drivers(request: web.BaseRequest):
    context = request.app["request_context"]

    # try:
    #     active_pds = await SavedPDS.retrieve_active(context)
    # except StorageNotFoundError as err:
    #     raise web.HTTPNotFound(reason="Couldn't find active storage" + err.roll_up)

    registered = await pds_drivers_oca_schema_dris_also_creates_default_instances(
        context
    )
    return web.json_response(registered)


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
            web.post("/pds/activate", pds_post_activate),
            web.post(
                "/pds/get_from",
                get_record_from_agent,
            ),
            web.get(
                "/pds/drivers",
                get_pds_drivers,
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
