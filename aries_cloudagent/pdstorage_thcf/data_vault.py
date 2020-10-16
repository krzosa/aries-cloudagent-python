from .base import BasePersonalDataStorage
from .error import PersonalDataStorageNotFoundError
from aiohttp import ClientSession, FormData
import json

API_ENDPOINT = "/api/v1/files"


class DataVault(BasePersonalDataStorage):
    def __init__(self):
        super().__init__()
        self.preview_settings = {
            "oca_schema_namespace": "pds",
            "oca_schema_dri": "ejHFuhg2v1ZrL5uQrHe3Arcxy62GWNakjTwL38swC9RB",
        }
        self.settings = {}
        # self.settings = {"host": "https://data-vault.argo.colossi.network"}

    async def load(self, id: str) -> str:
        """
        Returns: None on record not found
        """
        url = f"{self.settings['host']}{API_ENDPOINT}{'/'}{id}"
        print("URL: ", url)

        async with ClientSession() as session:
            response = await session.get(url)
            response_text = await response.text()
            print(response_text)

        # seek errors
        try:
            response_json = json.loads(response_text)
            if "errors" in response_json:
                return None
        except json.JSONDecodeError:
            pass

        return response_text

    async def save(self, record: str) -> str:
        data = FormData()
        data.add_field("file", record, filename="data", content_type="application/json")
        url = f"{self.settings['host']}{API_ENDPOINT}"
        print("URL: ", url)

        async with ClientSession() as session:
            response = await session.post(url=url, data=data)
            response_text = await response.text()
            response_json = json.loads(response_text)

        return response_json["content_dri"]
