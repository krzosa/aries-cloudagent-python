from attr import __description__
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
        raise PDSRecordNotFoundError(result)

    elif response.status != 200:
        raise PDSError(result)

    return result


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
        LOGGER.info("Begin %s", self.update_token.__name__)
        parsed_url = urlparse(self.settings.get("api_url"))
        self.api_url = "{url.scheme}://{url.netloc}".format(url=parsed_url)
        LOGGER.debug("URL [ %s ]", self.api_url)

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
        LOGGER.info("Begin usage policy download %s", self.update_token.__name__)
        url = f"{self.api_url}/api/meta/usage"
        self.usage_policy = await self.get(url)
        LOGGER.info("usage policy %s", self.usage_policy)

    async def update_token_when_expired(self):
        LOGGER.info("Begin %s", self.update_token_when_expired.__name__)
        time_elapsed = time.time() - (self.token_timestamp - 10)
        if time_elapsed > float(self.token["expires_in"]):
            await self.update_token()

    async def load(self, dri: str) -> dict:
        LOGGER.info("Begin %s", self.load.__name__)
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

    async def save(self, record, oca_schema_dri) -> str:
        LOGGER.info("Begin %s", self.save.__name__)
        """
        meta: {
            "oca_schema_dri"
        }
        """
        assert_type_or(record, str, dict)
        await self.update_token_when_expired()

        table = self.settings.get("repo", "dip.data")
        if oca_schema_dri is not None:
            assert_type(oca_schema_dri, str)
            table += "." + oca_schema_dri
        LOGGER.info("Table name %s", table)

        dri_value = None
        if isinstance(record, str):
            dri_value = encode(record)
        elif isinstance(record, dict):
            dri_value = encode(json.dumps(record))
        LOGGER.info("Record DRI %s", dri_value)

        record = {
            "content": record,
            "dri": dri_value,
            "timestamp": int(round(time.time() * 1000)),  # current time in milliseconds
        }
        LOGGER.info("Record: [ %s ]", record)

        body = {
            "content": record,
            "dri": dri_value,
            "table_name": table,
            "mime_type": "application/json",
        }
        LOGGER.info("Request body: [ %s ]", record)

        url = f"{self.api_url}/api/data"
        result = await self.post(url, body)
        result = json.loads(result)
        LOGGER.debug("Result of POST request %s", result)

        return dri_value

    async def query_by_oca_schema_dri(self, oca_schema_dri: str = None):
        LOGGER.info("Begin %s", self.query_by_oca_schema_dri.__name__)
        if __debug__:
            assert_type(oca_schema_dri, str)

        await self.update_token_when_expired()
        url = f"{self.api_url}/api/data"
        parameter_count = 0

        url = url + f"?table=dip.data.{oca_schema_dri}"
        parameter_count += 1

        url = url + "&f=plain"
        LOGGER.info("URL: [ %s ]", url)

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
