from asynctest import TestCase as AsyncTestCase, mock
import asyncio


class TestPDSSettasdings(AsyncTestCase):
    async def test_set_pds_settings(self):
        test_mock = mock.MagicMock()
        test_mock.a = mock.MagicMock(return_value=asyncio.Future())
        test_mock.a.return_value.set_result("asdav")
        test_mock_return = await test_mock.a()
        assert test_mock_return == "asdav"