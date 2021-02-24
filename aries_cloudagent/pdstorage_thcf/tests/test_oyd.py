from asynctest import TestCase as AsyncTestCase
import aries_cloudagent.pdstorage_thcf.own_your_data_data_vault as oyd
from types import MethodType


class TestOYD(AsyncTestCase):
    async def setUp(self):
        pass

    async def test_query_by_oca_schema_dri(self):
        pds = oyd.OwnYourDataVault()

        async def update_token(self):
            pass

        async def get(self, url):
            assert url == "None/api/data?table=oca.schema.dri.1234&f=plain"

        pds.update_token = MethodType(update_token, pds)
        pds.get = MethodType(get, pds)
        await pds.query_by_oca_schema_dri("1234")
        awaitable = pds.query_by_oca_schema_dri(["1234"])
        self.assertAsyncRaises(AssertionError, awaitable)