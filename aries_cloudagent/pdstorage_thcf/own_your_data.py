from .base import BasePDS
from .api import encode
from .error import PDSError, PDSRecordNotFoundError

import json
import logging
from urllib.parse import urlparse

from aiohttp import ClientSession, ClientConnectionError, ClientError
from aries_cloudagent.aathcf.credentials import assert_type, assert_type_or
import time
from collections import OrderedDict

LOGGER = logging.getLogger(__name__)


async def unpack_response(response):
    result: str = await response.text()
    if response.status == 404:
        LOGGER.error("Error Own Your Data PDS", result)
        raise PDSRecordNotFoundError("Record not found in Own your data PDS", result)

    elif response.status != 200:
        LOGGER.error("Error Own Your Data PDS", result)
        raise PDSError("Error Own Your Data PDS", result)

    return result


def get_delimiter(parameter_count_in):
    if parameter_count_in == 0:
        return "?"
    else:
        return "&"


class OwnYourDataVault(BasePDS):
    def __init__(self):
        super().__init__()
        self.api_url = None
        self.token = {"expires_in": "-1000"}
        self.token_timestamp = 0
        self.preview_settings = {
            "oca_schema_namespace": "pds",
            "oca_schema_dri": "9bABtmHu628Ss4oHmyTU5gy7QB1VftngewTmh7wdmN1j",
        }

    async def get_usage_policy(self):
        if self.settings.get("usage_policy") is None:
            await self.update_token()

        return self.settings["usage_policy"]

    async def update_token(self):
        parsed_url = urlparse(self.settings.get("api_url"))
        self.api_url = "{url.scheme}://{url.netloc}".format(url=parsed_url)
        LOGGER.debug("API URL OYD %s", self.api_url)

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

        async with ClientSession() as session:
            body = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": grant_type,
            }
            if scope is not None:
                body["scope"] = scope
            print(body)
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
        async with ClientSession() as session:
            result = await session.get(
                url,
                headers={"Authorization": "Bearer " + self.token["access_token"]},
            )
            result = await unpack_response(result)
            self.settings["usage_policy"] = result
            LOGGER.debug("Usage policy %s", self.settings["usage_policy"])

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

    async def save(self, record, metadata: dict) -> str:
        """
        meta: {
            "table" - specifies the table name into which save the data
            "oca_schema_dri"
        }
        """
        assert_type_or(record, str, dict)
        assert_type(metadata, dict)
        await self.update_token_when_expired()

        table = self.settings.get("repo")
        table = table if table is not None else "dip.data"

        meta = metadata
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
        LOGGER.debug("OYD save record %s metadata %s", record, meta)
        async with ClientSession() as session:
            """
            Pack request body
            """

            if meta.get("table") is not None:
                table = f"{table}.{meta.get('table')}"

            body = {
                "content": record,
                "dri": dri_value,
                "table_name": table,
                "mime_type": "application/json",
            }

            if meta.get("oca_schema_dri") is not None:
                record["oca_schema_dri"] = meta["oca_schema_dri"]
                body["schema_dri"] = meta["oca_schema_dri"]

            """
            Request
            """

            url = f"{self.api_url}/api/data"
            response = await session.post(
                url,
                headers={"Authorization": "Bearer " + self.token["access_token"]},
                json=body,
            )
            result = await unpack_response(response)
            result = json.loads(result)
            LOGGER.debug("Result of POST request %s", result)

        return dri_value

    async def load_multiple(
        self, *, table: str = None, oca_schema_base_dri: str = None
    ):
        await self.update_token_when_expired()
        url = f"{self.api_url}/api/data"

        parameter_count = 0

        if table is not None:
            url = url + get_delimiter(parameter_count) + f"table=dip.data.{table}"
            parameter_count += 1
        if oca_schema_base_dri is not None:
            url = (
                url
                + get_delimiter(parameter_count)
                + f"schema_dri={oca_schema_base_dri}"
            )
            parameter_count += 1

        url = url + get_delimiter(parameter_count) + "f=plain"

        LOGGER.info("OYD LOAD TABLE url [ %s ]", url)
        async with ClientSession() as session:
            result = await session.get(
                url, headers={"Authorization": "Bearer " + self.token["access_token"]}
            )
            result = await unpack_response(result)
            LOGGER.debug("OYD LOAD TABLE result: [ %s ]", result)

        return result

    async def ping(self) -> [bool, str]:
        try:
            await self.update_token()
        except (ClientConnectionError, ClientError) as err:
            return [False, str(err)]
        except PDSError as err:
            return [False, str(err)]

        return [True, None]
