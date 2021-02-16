from aries_cloudagent.aathcf.credentials import assert_type
from aries_cloudagent.pdstorage_thcf.base import BasePDS
from aries_cloudagent.storage.error import StorageNotFoundError
from aries_cloudagent.pdstorage_thcf.models.saved_personal_storage import SavedPDS
from asynctest import TestCase as AsyncTestCase, mock
import asyncio, pytest
from ..api import pds_set_settings


class TestPDSSettasdings(AsyncTestCase):
    async def test_set_pds_settings(self):
        test_mock = mock.MagicMock()
        test_mock.a = mock.MagicMock(return_value=asyncio.Future())
        test_mock.a.return_value.set_result("asdav")
        test_mock_return = await test_mock.a()
        assert test_mock_return == "asdav"