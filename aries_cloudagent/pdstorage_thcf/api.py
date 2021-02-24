from .base import BasePDS
from .error import PDSError, PDSNotFoundError
from .models.saved_personal_storage import SavedPDS
import hashlib
import multihash
import logging
import multibase
from aries_cloudagent.storage.error import StorageNotFoundError
from .models.table_that_matches_dris_with_pds import DriStorageMatchTable
from aries_cloudagent.aathcf.credentials import assert_type, assert_type_or
import json
from collections import OrderedDict

LOGGER = logging.getLogger(__name__)


async def match_save_save_record_id(context, record_id, pds_name):
    match_table = DriStorageMatchTable(record_id, pds_name)
    record_id = await match_table.save(context)
    return record_id


async def match_table_query_id(context, id):
    try:
        match = await DriStorageMatchTable.retrieve_by_id(context, id)
    except StorageNotFoundError as err:
        if __debug__:
            LOGGER.error(
                f"table_that_matches_plugins_with_ids id that matches with None value\n",
                f"input id: {id}\n",
                f"ERROR: {err.roll_up}",
            )
            # debug_all_records = await DriStorageMatchTable.query(context)
            # LOGGER.error("All records in table: ", debug_all_records)
        raise PDSNotFoundError(err)

    return match


async def pds_active_get_full_name(context):
    """Retrieves saved pds information from the storage"""
    try:
        active_pds = await SavedPDS.retrieve_active(context)
    except StorageNotFoundError as err:
        raise PDSNotFoundError(f"No active pds found {err.roll_up}")

    return active_pds.get_pds_full_name()


async def pds_get_by_full_name(context, name):
    """Creates a pds new instance(singleton) if it doesn't exits"""
    pds: BasePDS = await context.inject(BasePDS, {"personal_storage_type": name})

    return pds


async def pds_get(context, driver, instance_name):
    """Creates a pds new instance(singleton) if it doesn't exits"""
    full_name = tuple([driver, instance_name])
    result = await pds_get_by_full_name(context, full_name)
    return result


async def pds_get_active(context):
    """Creates a pds new instance(singleton) if it doesn't exits"""
    active_pds_name = await pds_active_get_full_name(context)
    pds = await pds_get_by_full_name(context, active_pds_name)
    return pds


async def pds_load(context, id: str, *, with_meta: bool = False) -> dict:
    if __debug__:
        assert_type(id, str)

    match = await match_table_query_id(context, id)
    pds = await pds_get_by_full_name(context, match.pds_type)
    result = await pds.load(id)

    try:
        result["content"] = json.loads(result["content"], object_pairs_hook=OrderedDict)
    except json.JSONDecodeError:
        pass
    except TypeError:
        pass

    if with_meta:
        return result
    else:
        return result["content"]


async def pds_load_string(context, id: str, *, with_meta: bool = False) -> str:
    if __debug__:
        assert_type(id, str)

    match = await match_table_query_id(context, id)
    pds = await pds_get_by_full_name(context, match.pds_type)
    result = await pds.load(id)

    if with_meta:
        return result
    else:
        return result["content"]


async def pds_save(context, payload, oca_schema_dri: str = None) -> str:
    if __debug__:
        assert_type_or(payload, str, dict)
        if oca_schema_dri is not None:
            assert_type(oca_schema_dri, str)

    active_pds_name = await pds_active_get_full_name(context)
    pds = await pds_get_by_full_name(context, active_pds_name)
    payload_id = await pds.save(payload, oca_schema_dri)
    payload_id = await match_save_save_record_id(context, payload_id, active_pds_name)

    if __debug__:
        assert_type(payload_id, str)

    return payload_id


async def pds_query_by_oca_schema_dri(context, oca_schema_dri: str or list):
    if __debug__:
        assert_type_or(oca_schema_dri, str, list)

    if isinstance(oca_schema_dri, str):
        oca_schema_dri = [oca_schema_dri]

    pds = await pds_get_active(context)
    result = []
    for dri in oca_schema_dri:
        result_record = {"dri": dri}
        try:
            result_record["payload"] = await pds.query_by_oca_schema_dri(dri)
        except PDSError:
            result_record["payload"] = [{}]

        result.append(result_record)

    return result


async def delete_record(context, id: str) -> str:
    if __debug__:
        assert_type(id, str)

    match = await match_table_query_id(context, id)
    pds = await pds_get_by_full_name(context, match.pds_type)
    result = await pds.delete(id)

    return result


async def pds_get_usage_policy_if_active_pds_supports_it(context):
    active_pds_name = await pds_active_get_full_name(context)
    if active_pds_name[0] != "own_your_data_data_vault":
        return None

    pds = await pds_get_by_full_name(context, active_pds_name)
    result = await pds.get_usage_policy()

    return result


async def _save_chunks(context, chunks, save_function):
    if __debug__:
        assert isinstance(chunks, list)
    for chunk in chunks:
        chunk_dri = chunk["dri"]
        if __debug__:
            assert isinstance(chunk_dri, str)
            assert isinstance(chunk["payload"], list)
        for chunk_payload in chunk["payload"]:
            if __debug__:
                assert isinstance(chunk_payload, dict)
            payload_id = await save_function(context, chunk_payload, chunk_dri)
            chunk_payload["_payload_id"] = payload_id

    return chunks


async def pds_save_chunks(context, chunks):
    result = await _save_chunks(context, chunks, pds_save)
    return result


def encode(data: str) -> str:
    assert_type(data, str)
    hash_object = hashlib.sha256()
    hash_object.update(bytes(data, "utf-8"))
    multi = multihash.encode(hash_object.digest(), "sha2-256")
    result = multibase.encode("base58btc", multi)

    return result.decode("utf-8")


async def pds_configure_instance(context, driver_name, instance_name, driver_setting):
    """Creates a new instance if it doesn't exists"""
    if __debug__:
        assert_type(driver_setting, dict) and driver_setting is not {}
        assert_type(driver_name, str)
        assert_type(instance_name, str)

    pds = await pds_get(context, driver_name, instance_name)
    pds.settings = driver_setting

    """ Save to db after creating an instance because pds_get
    invokes the pds provider which checks if pds is even valid"""
    try:
        saved_pds = await SavedPDS.retrieve_type_name(
            context, driver_name, instance_name
        )
        saved_pds.settings = driver_setting
    except StorageNotFoundError:
        saved_pds = SavedPDS(
            type=driver_name,
            name=instance_name,
            state=SavedPDS.INACTIVE,
            settings=driver_setting,
        )

    await saved_pds.save(context)

    return pds


async def pds_set_setting(
    context, driver_name, instance_name, client_id, client_secret, driver_setting: dict
):
    if __debug__:
        assert_type(driver_setting, dict) and driver_setting is not {}
        assert_type(driver_name, str)
        assert_type(instance_name, str)
        assert_type(client_id, str)
        assert_type(client_secret, str)

    driver_setting["client_secret"] = client_secret
    driver_setting["client_id"] = client_id

    pds = await pds_configure_instance(
        context, driver_name, instance_name, driver_setting
    )
    connected, exception = await pds.ping()

    return [connected, exception]


async def pds_set_settings(context, settings: list):
    messages = []
    if __debug__:
        assert isinstance(settings, list) and settings is not []
        assert isinstance(settings[0], dict)
    for s in settings:
        instance_name = s.get("instance_name", None)
        client_id = s.get("client_id", None)
        client_secret = s.get("client_secret", None)
        driver_setting = s.get("driver", None)
        driver_name = driver_setting.get("name", None)
        driver_setting = driver_setting.get(driver_name, None)
        if __debug__:
            assert_type(instance_name, str)
            assert_type(client_id, str)
            assert_type(client_secret, str)
            assert_type(driver_setting, dict)
            assert_type(driver_name, str)
        connected, exception = await pds_set_setting(
            context,
            driver_name,
            instance_name,
            client_id,
            client_secret,
            driver_setting,
        )
        if __debug__:
            assert isinstance(connected, bool)
        message = {}
        message["driver"] = driver_name
        message["instance_name"] = instance_name
        message["connected"] = connected
        if exception is not None:
            message["exception"] = exception
        messages.append(message)
    return messages
