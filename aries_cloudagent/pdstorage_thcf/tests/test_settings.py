from aries_cloudagent.aathcf.credentials import assert_type
from aries_cloudagent.pdstorage_thcf.base import BasePDS
from aries_cloudagent.storage.error import StorageNotFoundError
from aries_cloudagent.pdstorage_thcf.models.saved_personal_storage import SavedPDS
from asynctest import TestCase as AsyncTestCase, mock
import asyncio, pytest, asynctest
import aries_cloudagent.pdstorage_thcf.api as api

pds_set_setting = api.pds_set_setting


class TestPDSSettings(AsyncTestCase):
    async def setUp(self):
        self.settings = [
            {
                "driver": {
                    "name": "own_your_data",
                    "thcf_data_vault": {"host": "string"},
                    "own_your_data": {
                        "scope": "admin",
                        "grant_type": "client_credentials",
                    },
                },
                "client_id": "string",
                "client_secret": "string",
                "instance_name": "string",
            }
        ]

    async def test_set_pds_setting(self):
        async def stub(context, driver_name, instance_name, driver_setting):
            assert driver_name == self.settings[0]["driver"]["name"]
            assert instance_name == self.settings[0]["instance_name"]
            assert driver_setting["client_id"] is not None

            pds_object = mock.MagicMock()
            pds_object.ping = mock.MagicMock(return_value=asyncio.Future())
            pds_object.ping.return_value.set_result([True, "except"])
            return pds_object

        api.pds_configure_instance = stub
        api.pds_configure_saved_instance = stub

        driver = self.settings[0]["driver"]["name"]
        connected, exception = await pds_set_setting(
            None,
            driver,
            self.settings[0]["instance_name"],
            self.settings[0]["client_id"],
            self.settings[0]["client_secret"],
            self.settings[0]["driver"][driver],
        )
        assert connected == True and exception == "except"

    async def test_set_pds_settings(self):
        call_count = 0

        async def stub_set_setting(
            context,
            driver_name,
            instance_name,
            client_id,
            client_secret,
            driver_setting: dict,
        ):
            context is "unused"
            nonlocal call_count
            call_count += 1
            assert driver_name == self.settings[0]["driver"]["name"]
            assert instance_name == self.settings[0]["instance_name"]
            assert client_id == self.settings[0]["client_id"]
            assert client_secret == self.settings[0]["client_secret"]
            assert driver_setting == self.settings[0]["driver"][driver_name]
            assert (
                driver_setting["scope"]
                == self.settings[0]["driver"][driver_name]["scope"]
            )
            return [True, "except"]

        # pds_set_setting = stub_set_setting
        self.settings.append(self.settings[0])
        api.pds_set_setting = stub_set_setting
        message = await api.pds_set_settings(None, self.settings)
        assert call_count == 2
        assert message["own_your_data"]["connected"] == True
        assert message["own_your_data"]["exception"] == "except"
