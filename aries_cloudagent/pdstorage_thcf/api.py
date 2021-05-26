from ..config.global_variables import USAGE_POLICY_VERIFY
from ..aathcf.utils import build_context, run_standalone_async
from aiohttp.client import ClientSession, ClientTimeout
from .base import BasePDS
from .error import PDSError, PDSNotFoundError
from .models.saved_personal_storage import SavedPDS
import hashlib
import multihash
import logging
import multibase
from aries_cloudagent.storage.error import StorageNotFoundError
from aries_cloudagent.aathcf.credentials import assert_type, assert_type_or
import json
from collections import OrderedDict

LOGGER = logging.getLogger(__name__)


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


async def pds_load(
    context, id: str, *, with_meta: bool = False, with_meta_embed=False
) -> dict:
    if __debug__:
        assert_type(id, str)

    pds = await pds_get_active(context)
    result = await pds.load(id)

    try:
        result["content"] = json.loads(result["content"], object_pairs_hook=OrderedDict)
    except json.JSONDecodeError:
        pass
    except TypeError:
        pass
    except KeyError:
        return result

    if with_meta_embed:
        dri = result.get("dri")
        oca_schema_dri = result.get("oca_schema_dri")
        if dri:
            result["content"]["dri"] = dri
        if oca_schema_dri:
            result["content"]["oca_schema_dri"] = oca_schema_dri

    if with_meta:
        return result
    else:
        return result["content"]


async def pds_load_string(context, id: str, *, with_meta: bool = False) -> str:
    if __debug__:
        assert_type(id, str)

    pds = await pds_get_active(context)
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

    pds = await pds_get_active(context)
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


async def pds_load_item_recursive_(context, key, value):
    new_val = value
    if isinstance(value, dict):
        new_val = await pds_load_dict_recursive(context, value)
    elif key.endswith("_dri") and (not key.endswith("schema_dri")):
        try:
            new_val = await pds_load(context, value)
            new_val = await pds_load_dict_recursive(context, new_val)
        except PDSError as err:
            LOGGER.error("failed to fetch {%s:%s} err:[%s]", key, value, err)
            new_val = value
    return new_val


async def pds_load_dict_recursive(context, dictionary):
    new_dict = {}
    for key, value in dictionary.items():
        if key.endswith("_dri") and (not key.endswith("schema_dri")):
            new_dict[key[:-4]] = await pds_load_item_recursive_(context, key, value)
            new_dict[key] = value
        else:
            new_dict[key] = await pds_load_item_recursive_(context, key, value)

    return new_dict


async def pds_load_recursive(context, payload_dri):
    result = await pds_load_dict_recursive(context, {"payload_dri": payload_dri})
    return result["payload"]


async def oyd_verify_usage_policy(controller_usage_policy, subject_usage_policy):
    timeout = ClientTimeout(total=15)
    async with ClientSession(timeout=timeout) as session:
        result = await session.post(
            USAGE_POLICY_VERIFY,
            json={
                "data-subject": subject_usage_policy,
                "data-controller": controller_usage_policy,
            },
        )
        result = await result.text()
        result = json.loads(result)

        if result["code"] == 0:
            return True, result["message"]
        return False, result["message"]


async def pds_link_dri(context, dri, link_with_dris):
    if isinstance(link_with_dris, str):
        link_with_dris = [link_with_dris]
    elif isinstance(link_with_dris, list):
        pass
    else:
        raise TypeError("Expected: list or string")

    if __debug__:
        assert isinstance(link_with_dris, list)

    pds = await pds_get_active(context)
    if "link" in dir(pds):
        try:
            await pds.link(dri, link_with_dris)
        except PDSError as err:
            LOGGER.error(
                "source_dri: %s target_dris: %s error: %s",
                dri,
                link_with_dris,
                err.roll_up,
            )
            return False
    else:
        LOGGER.warning(
            "This is an own your data pds extension. current pds doesn't support this method"
        )
        return False
    return True


async def __test_pds_link():
    print("one should fail: invalid dri")
    print("two should fail: invalid pds")
    print("----------------------------")
    context = await build_context()
    import random

    dri1 = await pds_save(context, "124inmjfa0dioq-0dq" + str(random.random()))
    dri2 = await pds_save(context, "1asdad24inmjfa0dioq-0dq" + str(random.random()))
    result = await pds_link_dri(context, dri1, dri2)
    assert result is True

    result = await pds_link_dri(context, "1wd1fc", "difhd908f")
    assert result is False

    context = await build_context("local")

    import random

    dri1 = await pds_save(context, "124inmjfa0dioq-0dq" + str(random.random()))
    dri2 = await pds_save(context, "1asdad24inmjfa0dioq-0dq" + str(random.random()))
    result = await pds_link_dri(context, dri1, dri2)
    assert result is False

    result = await pds_link_dri(context, "1wd1fc", "difhd908f")
    assert result is False


async def test_usage_policy():
    usage_pol_1 = "<http://w3id.org/semcon/ns/ontology#ContainerPolicy> a <http://www.w3.org/2002/07/owl#Class>;\n    <http://www.w3.org/2002/07/owl#equivalentClass> [\n    a <http://www.w3.org/2002/07/owl#Class>;\n    <http://www.w3.org/2002/07/owl#intersectionOf> ([\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasData>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> [<http://www.w3.org/2002/07/owl#unionOf> (<http://www.specialprivacy.eu/vocabs/data#Profile>)]\n    ] [\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasRecipient>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> [<http://www.w3.org/2002/07/owl#unionOf> (<http://www.specialprivacy.eu/vocabs/recipients#Ours>)]\n    ] [\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasPurpose>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> [<http://www.w3.org/2002/07/owl#unionOf> (<http://www.specialprivacy.eu/vocabs/purposes#Health>)]\n    ] [\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasProcessing>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> [<http://www.w3.org/2002/07/owl#unionOf> (<http://www.specialprivacy.eu/vocabs/processing#Aggregate> <http://www.specialprivacy.eu/vocabs/processing#Analyze> <http://www.specialprivacy.eu/vocabs/processing#Collect> <http://www.specialprivacy.eu/vocabs/processing#Copy> <http://www.specialprivacy.eu/vocabs/processing#Move> <http://www.specialprivacy.eu/vocabs/processing#Query> <http://www.specialprivacy.eu/vocabs/processing#Transfer>)]\n    ] [\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasStorage>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> [<http://www.w3.org/2002/07/owl#intersectionOf> ([\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasLocation>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> [<http://www.w3.org/2002/07/owl#unionOf> (<http://www.specialprivacy.eu/vocabs/locations#EU>)]\n    ] [\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasDuration>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> <http://www.specialprivacy.eu/vocabs/duration#LegalRequirement>\n    ])]\n    ])\n    ] ."
    usage_pol_2 = "<http://w3id.org/semcon/ns/ontology#ContainerPolicy> a <http://www.w3.org/2002/07/owl#Class>;\n    <http://www.w3.org/2002/07/owl#equivalentClass> [\n    a <http://www.w3.org/2002/07/owl#Class>;\n    <http://www.w3.org/2002/07/owl#intersectionOf> ([\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasData>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> [<http://www.w3.org/2002/07/owl#unionOf> (<http://www.specialprivacy.eu/vocabs/data#Profile>)]\n    ] [\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasRecipient>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> [<http://www.w3.org/2002/07/owl#unionOf> (<http://www.specialprivacy.eu/vocabs/recipients#Ours>)]\n    ] [\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasPurpose>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> [<http://www.w3.org/2002/07/owl#unionOf> (<http://www.specialprivacy.eu/vocabs/purposes#Health>)]\n    ] [\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasProcessing>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> [<http://www.w3.org/2002/07/owl#unionOf> (<http://www.specialprivacy.eu/vocabs/processing#Aggregate> <http://www.specialprivacy.eu/vocabs/processing#Analyze> <http://www.specialprivacy.eu/vocabs/processing#Collect> <http://www.specialprivacy.eu/vocabs/processing#Copy> <http://www.specialprivacy.eu/vocabs/processing#Move> <http://www.specialprivacy.eu/vocabs/processing#Query> <http://www.specialprivacy.eu/vocabs/processing#Transfer>)]\n    ] [\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasStorage>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> [<http://www.w3.org/2002/07/owl#intersectionOf> ([\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasLocation>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> [<http://www.w3.org/2002/07/owl#unionOf> (<http://www.specialprivacy.eu/vocabs/locations#EU>)]\n    ] [\n    a <http://www.w3.org/2002/07/owl#Restriction>;\n    <http://www.w3.org/2002/07/owl#onProperty> <http://www.specialprivacy.eu/langs/usage-policy#hasDuration>;\n    <http://www.w3.org/2002/07/owl#someValuesFrom> <http://www.specialprivacy.eu/vocabs/duration#LegalRequirement>\n    ])]\n    ])\n    ] ."
    usage, msg = await oyd_verify_usage_policy(usage_pol_2, usage_pol_1)
    print(msg)
    assert usage is True
    print(await oyd_verify_usage_policy(usage_pol_1, usage_pol_2))


async def test_start():
    await __test_pds_link()
    await test_usage_policy()


run_standalone_async(__name__, test_start)
