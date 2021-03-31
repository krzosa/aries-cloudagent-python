from ..config.global_variables import OYD_OCA_CHUNKS_PREFIX, USAGE_POLICY_PARSE
from ..aathcf.utils import run_standalone_async
from .base import BasePDS
from .api import encode
from .error import PDSError, PDSRecordNotFoundError

import json
import logging
from urllib.parse import urlparse

from aiohttp import ClientSession, ClientConnectionError, ClientError
from aries_cloudagent.aathcf.credentials import assert_type
import time
from collections import OrderedDict

LOGGER = logging.getLogger(__name__)


async def unpack_response(response):
    result: str = await response.text()
    if response.status == 404:
        raise PDSRecordNotFoundError(result)

    elif response.status != 200:
        raise PDSError(result)

    return result


def map_parsed_usage_policy(usage_policy, map_against):
    new_base = {}
    missing = {}
    for key, value in usage_policy.items():
        list_of_attrs = []
        possibilities = map_against["attr_entries"].get(key)
        if possibilities is None:
            missing[key] = "missing"
        else:
            for i in value:
                found = False
                for p in range(len(possibilities)):
                    if possibilities[p] == i["value"]:
                        found = True
                        list_of_attrs.append(str(p))
                if found == False:
                    if missing.get(key) == None:
                        missing[key] = {}
                    missing[key][i["value"]] = "missing"
            if list_of_attrs != []:
                new_base[key] = list_of_attrs
    return new_base, missing


class OwnYourDataVault(BasePDS):
    def __init__(self):
        super().__init__()
        self.api_url = None
        self.token = {"expires_in": "-1000"}
        self.token_timestamp = 0
        self.usage_policy = None
        self.preview_settings = {
            "oca_schema_namespace": "pds",
            "oca_schema_dri": "9bABtmHu628Ss4oHmyTU5gy7QB1VftngewTmh7wdmN1j",
        }

    async def get(self, url):
        async with ClientSession() as session:
            result = await session.get(
                url, headers={"Authorization": "Bearer " + self.token["access_token"]}
            )
            result = await unpack_response(result)
            return result

    async def post(self, url, body):
        async with ClientSession() as session:
            response = await session.post(
                url,
                headers={"Authorization": "Bearer " + self.token["access_token"]},
                json=body,
            )
            result = await unpack_response(response)
            return result

    async def get_usage_policy(self):
        if self.usage_policy is None:
            await self.update_token()

        return self.usage_policy

    async def update_token(self):
        parsed_url = urlparse(self.settings.get("api_url"))
        self.api_url = "{url.scheme}://{url.netloc}".format(url=parsed_url)

        client_id = self.settings.get("client_id")
        client_secret = self.settings.get("client_secret")
        grant_type = self.settings.get("grant_type", "client_credentials")
        scope = self.settings.get("scope")

        if self.api_url is None:
            raise PDSError("Please configure the plugin, api_url is empty")
        if client_id is None:
            raise PDSError("Please configure the plugin, client_id is empty")
        if client_secret is None:
            raise PDSError("Please configure the plugin, client_secret is empty")

        body = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": grant_type,
        }
        if scope is not None:
            body["scope"] = scope

        async with ClientSession() as session:
            result = await session.post(
                self.api_url + "/oauth/token",
                json=body,
            )
            result = await unpack_response(result)
            token = json.loads(result)
            self.token = token
            self.token_timestamp = time.time()
            LOGGER.info("update token: %s", self.token)

        """
        Download the usage policy

        """
        url = f"{self.api_url}/api/meta/usage"
        self.usage_policy = await self.get(url)

        result = await self.post(
            USAGE_POLICY_PARSE,
            {"ttl": self.usage_policy},
        )
        result = json.loads(result)
        result, err = map_parsed_usage_policy(result, cached_schema_to_map_against)
        meta = {}
        if err:
            meta = {"missing": err}
        await self.save(
            result,
            "H5F2YgEbXpSZjcNqAYevfGPFXSWUV1d2PnVg2ubkkKb",
            meta=meta,
        )

    async def update_token_when_expired(self):
        time_elapsed = time.time() - (self.token_timestamp - 10)
        if time_elapsed > float(self.token["expires_in"]):
            await self.update_token()

    async def load(self, dri: str) -> dict:
        assert_type(dri, str)
        await self.update_token_when_expired()

        url = f"{self.api_url}/api/data/{dri}?p=dri&f=plain"
        async with ClientSession() as session:
            result = await session.get(
                url, headers={"Authorization": "Bearer " + self.token["access_token"]}
            )
            result = await unpack_response(result)
            result_dict: dict = json.loads(result, object_pairs_hook=OrderedDict)

        return result_dict

    async def save(self, record, oca_schema_dri, *, meta={}) -> str:
        assert isinstance(record, (str, dict))
        await self.update_token_when_expired()

        table = self.settings.get("repo", "dip.data")
        if oca_schema_dri is not None:
            assert_type(oca_schema_dri, str)
            table += "." + OYD_OCA_CHUNKS_PREFIX + oca_schema_dri

        dri_value = None
        if isinstance(record, str):
            dri_value = encode(record)
        elif isinstance(record, dict):
            dri_value = encode(json.dumps(record))

        record = {
            "content": record,
            "dri": dri_value,
            "timestamp": int(round(time.time() * 1000)),  # current time in milliseconds
        }

        if oca_schema_dri is not None:
            record.update({"oca_schema_dri": oca_schema_dri})

        body = {
            "content": record,
            "dri": dri_value,
            "table_name": table,
            "mime_type": "application/json",
        }
        body.update(meta)

        url = f"{self.api_url}/api/data"
        result = await self.post(url, body)
        result = json.loads(result)

        return dri_value

    async def query_by_oca_schema_dri(self, oca_schema_dri: str = None):
        if __debug__:
            assert_type(oca_schema_dri, str)

        await self.update_token_when_expired()
        url = f"{self.api_url}/api/data"
        parameter_count = 0

        url = url + f"?table=dip.data.{oca_schema_dri}"
        parameter_count += 1

        url = url + "&f=plain"

        result = await self.get(url)
        result = json.loads(result)

        return result

    async def ping(self) -> [bool, dict]:
        try:
            await self.update_token()
        except (ClientConnectionError, ClientError) as err:
            return [False, err]
        except PDSError as err:
            return [False, err]

        return [True, None]


cached_schema_to_map_against = {
    "@context": "https://odca.tech/overlays/v1",
    "type": "spec/overlay/entry/1.0",
    "issued_by": "",
    "role": "",
    "purpose": "",
    "schema_base": "hl:8gkUPenRUXU15qrUZufoeLriqxqNMAtmUqRJCC8ajULr",
    "language": "en_US",
    "attr_entries": {
        "data": [
            "AnyData",
            "Activity",
            "Anonymized",
            "AudiovisualActivity",
            "Computer",
            "Content",
            "Demographic",
            "Derived",
            "EarthObservation",
            "Meteorology",
            "MeteorologicMeasurement",
            "MeteorologicForecast",
            "MeteorologicCurrent",
            "MeteorologicHistoric",
            "MeteorologicRaster",
            "Geophysics",
            "GeophysicsSeismology",
            "GeophysicsMagneticField",
            "GeophysicsGravimetry",
            "Financial",
            "Government",
            "Health",
            "Diabetes",
            "Sensor",
            "InsulinPump",
            "Interactive",
            "Judicial",
            "Location",
            "Navigation",
            "Online",
            "OnlineActivity",
            "Physical",
            "PhysicalActivity",
            "Political",
            "Preference",
            "Profile",
            "Purchase",
            "Social",
            "State",
            "Statistical",
            "TelecomActivity",
            "UniqueId",
        ],
        "purpose": [
            "AnyPurpose",
            "Account",
            "Admin",
            "Arts",
            "Browsing",
            "Charity",
            "Communicate",
            "Current",
            "Custom",
            "Delivery",
            "Develop",
            "Downloads",
            "Education",
            "Feedback",
            "Finmgt",
            "Gambling",
            "Gaming",
            "Government",
            "Health",
            "Historical",
            "Login",
            "Marketing",
            "MeteorologicalService",
            "News",
            "Payment",
            "Sales",
            "Search",
            "State",
            "Tailoring",
            "Telemarketing",
        ],
        "processing": [
            "AnyProcessing",
            "Aggregate",
            "Analyze",
            "Anonymize",
            "Collect",
            "Copy",
            "Derive",
            "Move",
            "Query",
            "Transfer",
        ],
        "recipient": [
            "AnyRecipient",
            "Ours",
            "Delivery",
            "Same",
            "OtherRecipient",
            "Unrelated",
            "Public",
        ],
        "location": [
            "AnyLocation",
            "OurServers",
            "ThirdParty",
            "EU",
            "EULike",
            "ThirdCountries",
        ],
        "duration": [
            "AnyDuration",
            "StatedPurpose",
            "LegalRequirement",
            "BusinessPractices",
            "Indefinitely",
        ],
    },
}


def test_format():
    base = {
        "sick": [{"ns": "...", "value": "No"}],
        "allergies": [{"ns": "...", "value": "Yes"}],
        "seriousReaction": [
            {"ns": "...", "value": "Yes"},
            {"ns": "...", "value": "Don't Know"},
        ],
        "test_not_existent": [{"ns": "...", "value": "Yes"}],
        "test_not_existent_value": [{"ns": "...", "value": "CoolValue"}],
    }
    schema = {
        "@context": "https://odca.tech/overlays/v1",
        "type": "spec/overlay/entry/1.0",
        "issued_by": "",
        "role": "",
        "purpose": "",
        "schema_base": "hl:afW1EfhWNh76BL3FUV8mniQAU4jRAb6Q6vxuCpLy5Nf6",
        "language": "en_US",
        "attr_entries": {
            "sick": ["Yes", "No", "Don't Know"],
            "allergies": ["Yes", "No", "Don't Know"],
            "seriousReaction": ["Yes", "No", "Don't Know"],
            "healthProblem": ["Yes", "No", "Don't Know"],
            "immuneSystemProblem": ["Yes", "No", "Don't Know"],
            "radiationTreatments": ["Yes", "No", "Don't Know"],
            "nervousSystemProblem": ["Yes", "No", "Don't Know"],
            "bloodProducts": ["Yes", "No", "Don't Know"],
            "pregnant": ["Yes", "No", "Don't Know"],
            "recentVaccinations": ["Yes", "No", "Don't Know"],
            "additionalDataRequest": ["Yes", "No"],
            "immunizationRecordCard": ["Yes", "No"],
            "test_not_existent_value": ["Yes", "No"],
        },
    }

    result, err = map_parsed_usage_policy(base, schema)
    assert err["test_not_existent"] == "missing"
    assert err["test_not_existent_value"]["CoolValue"] == "missing"
    assert result == {
        "sick": ["1"],
        "allergies": ["0"],
        "seriousReaction": ["0", "2"],
    }


def test_format_2():
    schema = cached_schema_to_map_against
    base = {
        "duration": [
            {
                "ns": "http://www.specialprivacy.eu/vocabs/duration#",
                "value": "LegalRequirement",
            }
        ],
        "data": [
            {"ns": "http://www.specialprivacy.eu/vocabs/data#", "value": "Profile"}
        ],
        "purpose": [
            {"ns": "http://www.specialprivacy.eu/vocabs/purposes#", "value": "Health"}
        ],
        "recipient": [
            {"ns": "http://www.specialprivacy.eu/vocabs/recipients#", "value": "Ours"}
        ],
        "processing": [
            {
                "ns": "http://www.specialprivacy.eu/vocabs/processing#",
                "value": "Aggregate",
            },
            {
                "ns": "http://www.specialprivacy.eu/vocabs/processing#",
                "value": "Analyze",
            },
            {
                "ns": "http://www.specialprivacy.eu/vocabs/processing#",
                "value": "Collect",
            },
            {"ns": "http://www.specialprivacy.eu/vocabs/processing#", "value": "Copy"},
            {"ns": "http://www.specialprivacy.eu/vocabs/processing#", "value": "Move"},
            {"ns": "http://www.specialprivacy.eu/vocabs/processing#", "value": "Query"},
            {
                "ns": "http://www.specialprivacy.eu/vocabs/processing#",
                "value": "Transfer",
            },
        ],
        "location": [
            {"ns": "http://www.specialprivacy.eu/vocabs/locations#", "value": "EU"}
        ],
    }
    result, err = map_parsed_usage_policy(base, schema)

    assert err == {}
    assert result == {
        "data": ["35"],
        "purpose": ["18"],
        "processing": ["1", "2", "4", "5", "7", "8", "9"],
        "recipient": ["1"],
        "location": ["3"],
        "duration": ["2"],
    }, result


async def test_usage_policy_parse():
    vault = OwnYourDataVault()

    vault.settings["client_id"] = "-s2bdkM_cv7KYDF5xg_Lj6vil1ZJaLQJ79duOW7J9g4"
    vault.settings["client_secret"] = "s_dR8dzbVES_vvc1-nyb1O_cuzyCz2_bRd3Lr12s4ug"
    vault.settings["api_url"] = "https://data-vault.eu"
    await vault.update_token()
    test_format()
    test_format_2()


run_standalone_async(__name__, test_usage_policy_parse)
