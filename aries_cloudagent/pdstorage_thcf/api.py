from .base import BasePDS
from .error import PDSNotFoundError
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
        LOGGER.error(
            f"table_that_matches_plugins_with_ids id that matches with None value\n",
            f"input id: {id}\n",
            f"ERROR: {err.roll_up}",
        )
        debug_all_records = await DriStorageMatchTable.query(context)
        LOGGER.error("All records in table: ", debug_all_records)
        raise PDSNotFoundError(err)

    return match


async def pds_get_active_name(context):
    try:
        active_pds = await SavedPDS.retrieve_active(context)
    except StorageNotFoundError as err:
        raise PDSNotFoundError(f"No active pds found {err.roll_up}")

    return active_pds.get_pds_name()


async def pds_get_by_name(context, name):
    pds: BasePDS = await context.inject(BasePDS, {"personal_storage_type": name})

    return pds


async def pds_get_active(context):
    active_pds_name = await pds_get_active_name(context)
    pds = await pds_get_by_name(context, active_pds_name)
    return pds


async def pds_load(context, id: str, *, with_meta: bool = False) -> dict:
    assert_type(id, str)

    match = await match_table_query_id(context, id)
    pds = await pds_get_by_name(context, match.pds_type)
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
    assert_type(id, str)

    match = await match_table_query_id(context, id)
    pds = await pds_get_by_name(context, match.pds_type)
    result = await pds.load(id)

    if with_meta:
        return result
    else:
        return result["content"]


async def pds_save(context, payload, metadata: str = "{}") -> str:
    assert_type_or(payload, str, dict)
    assert_type(metadata, str)

    active_pds_name = await pds_get_active_name(context)
    pds = await pds_get_by_name(context, active_pds_name)
    payload_id = await pds.save(payload, json.loads(metadata))
    payload_id = await match_save_save_record_id(context, payload_id, active_pds_name)

    return payload_id


async def pds_save_a(
    context, payload, *, oca_schema_dri: str = None, table: str = None
) -> str:
    assert_type_or(payload, str, dict)

    meta = {"table": table, "oca_schema_dri": oca_schema_dri}
    active_pds_name = await pds_get_active_name(context)
    pds = await pds_get_by_name(context, active_pds_name)
    payload_id = await pds.save(payload, meta)
    payload_id = await match_save_save_record_id(context, payload_id, active_pds_name)

    return payload_id


async def load_multiple(context, *, table: str = None, oca_schema_base_dri=None):
    """ Load multiple records, if oca_schema_base_dri is a list then returns a dictionary"""
    pds = await pds_get_active(context)
    if isinstance(oca_schema_base_dri, list):
        result = {}
        for dri in oca_schema_base_dri:
            result[dri] = await pds.load_multiple(table=table, oca_schema_base_dri=dri)
            result[dri] = json.loads(result[dri])
        return result

    else:
        result = await pds.load_multiple(
            table=table, oca_schema_base_dri=oca_schema_base_dri
        )
        result = json.loads(result)
        return result


async def delete_record(context, id: str) -> str:
    assert_type(id, str)

    match = await match_table_query_id(context, id)
    pds = await pds_get_by_name(context, match.pds_type)
    result = await pds.delete(id)

    return result


async def pds_get_usage_policy_if_active_pds_supports_it(context):
    active_pds_name = await pds_get_active_name(context)
    if active_pds_name[0] != "own_your_data":
        return None

    pds = await pds_get_by_name(context, active_pds_name)
    result = await pds.get_usage_policy()

    return result


def encode(data: str) -> str:
    assert_type(data, str)
    hash_object = hashlib.sha256()
    hash_object.update(bytes(data, "utf-8"))
    multi = multihash.encode(hash_object.digest(), "sha2-256")
    result = multibase.encode("base58btc", multi)

    return result.decode("utf-8")
