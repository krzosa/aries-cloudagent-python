from .base import BasePersonalDataStorage
from .api import encode
from .error import *

import json
import logging

from aiohttp import ClientSession, FormData

LOGGER = logging.getLogger(__name__)

API_DATA_VAULT = "https://data-vault.eu"
API_TOKEN = API_DATA_VAULT + "/oauth/token"
API_ON_SAVE = API_DATA_VAULT + "/api/repos/dip.data/items"
API_ON_READ = API_DATA_VAULT + "/api/items"


class OwnYourDataVault(BasePersonalDataStorage):
    def __init__(self):
        super().__init__()
        self.token = None
        self.preview_settings = {
            "oca_schema_namespace": "pds",
            "oca_schema_dri": "4ZsViHFpyTYFdrrpRQmgun1qG4WKaC9rEXU3BpT7Foq2",
        }

    async def update_token(self):
        # TODO: Add timestamp check because token expires
        # if self.token != None:
        #     return

        client_id = self.settings.get("client_id")
        client_secret = self.settings.get("client_secret")

        if client_id == None:
            raise PersonalDataStorageLackingConfigurationError(
                "Please configure the plugin, Client_id is empty"
            )
        if client_secret == None:
            raise PersonalDataStorageLackingConfigurationError(
                "Please configure the plugin, Client_secret is empty"
            )

        async with ClientSession() as session:
            result = await session.post(
                API_TOKEN,
                json={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                },
            )
            if result.status != 200:
                raise PersonalDataStorageServerError(
                    "Server Error, Could be that the connection is invalid or some other unforseen error, check if the server is up"
                )

            result = await result.text()
            token = json.loads(result)
            self.token = token
            LOGGER.info("update token: %s", self.token)

    async def load(self, id: str) -> str:
        """
        TODO: Errors checking
        """
        await self.update_token()

        url = f"https://data-vault.eu/api/data?dri={id}"
        # url = f"https://data-vault.eu/api/data?dri={dri_value}&schema_dri={dri_schema_value}"
        async with ClientSession() as session:
            result = await session.get(
                url, headers={"Authorization": "Bearer " + self.token["access_token"]}
            )
            result = await result.text()
            result = json.loads(result)
            LOGGER.info("Result of GET request %s", result)

        return result.get("content")

    async def save(self, record: str) -> str:
        dri_value = encode(record)
        await self.update_token()
        async with ClientSession() as session:
            result = await session.post(
                "https://data-vault.eu/api/data",
                headers={"Authorization": "Bearer " + self.token["access_token"]},
                json={
                    "content": record,
                    "dri": dri_value,
                    #               "schema_dri": dri_schema_value,
                    "mime_type": "application/json",
                    "table_name": "dip.data",
                },
            )
            result = await result.text()
            result = json.loads(result)
            LOGGER.info("Result of POST request %s", result)

        return dri_value
