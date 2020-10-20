from .base import BasePersonalDataStorage
from .error import *
from ..messaging.request_context import RequestContext
import hashlib
import multihash
import multibase

table_that_matches_plugins_with_ids = {}


async def load_string(context: RequestContext, id: str) -> str:
    if id == None:
        return None
    assert isinstance(id, str), "Id is not a string"

    plugin = table_that_matches_plugins_with_ids.get(id, None)
    assert (
        plugin != None
    ), f"""table_that_matches_plugins_with_ids has an id that matches with None value 
        table_that_matches_plugins_with_ids: {table_that_matches_plugins_with_ids}
        input id: {id}
        plugin: {plugin}
        """

    pds: BasePersonalDataStorage = await context.inject(
        BasePersonalDataStorage, {"personal_storage_type": plugin}
    )
    result = await pds.load(id)

    return result


async def save_string(context: RequestContext, payload: str) -> str:
    if payload == None:
        return None
    assert isinstance(payload, str), "payload is not a string"

    pds: BasePersonalDataStorage = await context.inject(BasePersonalDataStorage)
    active_plugin = context.settings.get("personal_storage_type")

    payload_id = await pds.save(payload)
    table_that_matches_plugins_with_ids[payload_id] = active_plugin

    return payload_id


def encode(data: str) -> str:
    hash_object = hashlib.sha256()
    hash_object.update(bytes(data, "utf-8"))
    multi = multihash.encode(hash_object.digest(), "sha2-256")
    result = multibase.encode("base58btc", multi)

    return result.decode("utf-8")

