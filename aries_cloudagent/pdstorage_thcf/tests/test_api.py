from asynctest import TestCase as AsyncTestCase
import aries_cloudagent.pdstorage_thcf.api as api
from aries_cloudagent.messaging.models.base_record import BaseRecord

pds_load = api.pds_load
pds_save = api.pds_save


class TestModel:
    def __init__(self, field1, field2):
        self.field1 = field1
        self.field2 = field2


class TestBaseRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "defined_consent"

    class Meta:
        schema_class = "TestBaseRecordSchema"

    def __init__(
        self,
        *,
        label: str = None,
        oca_schema_dri: str = None,
        oca_data_dri: str = None,
        pds_name: str = None,
        usage_policy: str = None,
        state: str = None,
        record_id: str = None,
        **keyword_args,
    ):
        super().__init__(record_id, state, **keyword_args)
        self.label = label
        self.oca_data_dri = oca_data_dri
        self.oca_schema_dri = oca_schema_dri
        self.pds_name = pds_name
        self.usage_policy = usage_policy


class TestPDSApi(AsyncTestCase):
    async def setUp(self):
        self.acapy_record_dict = {
            "label": "test_label",
            "oca_schema_dri": "12345",
            "oca_data_dri": "12345",
            "pds_name": "test_pds_name",
            "state": "1234-state",
        }
        self.acapy_record = TestBaseRecord(**self.acapy_record_dict)

    async def test_pds_save_model(self):
        data = {"field1": "str1", "field2": "str2"}
        model = TestModel(**data)

        async def pds_save_stub(context, payload, dri):
            assert payload == model.__dict__
            assert payload == data
            return "12345"

        api.pds_save = pds_save_stub

        result = await api.pds_save_model(None, model)
        assert result == "12345"

        await self.assertAsyncRaises(
            AssertionError, api.pds_save_model(None, {"invalid": "data"})
        )

    async def test_pds_load_model(self):
        data = {"field1": "str1", "field2": "str2"}
        self_id = "1234"

        async def pds_load_stub(context, id):
            assert self_id == id
            return data

        api.pds_load = pds_load_stub
        result = await api.pds_load_model(None, self_id, TestModel)
        assert result.__dict__ == data

        async def pds_load_stub_invalid(context, id):
            return {"invalid": "data"}

        api.pds_load = pds_load_stub_invalid
        awaitable = api.pds_load_model(None, self_id, TestModel)
        await self.assertAsyncRaises(TypeError, awaitable)

        async def pds_load_stub_invalid(context, id):
            return {"field1": "data"}

        api.pds_load = pds_load_stub_invalid
        awaitable = api.pds_load_model(None, self_id, TestModel)
        await self.assertAsyncRaises(TypeError, awaitable)

    async def test_pds_load_acapy_record(self):
        async def pds_load_stub(context, id):
            return self.acapy_record_dict

        api.pds_load = pds_load_stub
        result = await api.pds_load_model(None, "1234", TestBaseRecord)
        assert result == self.acapy_record

    async def test_pds_save_acapy_record(self):
        async def pds_save_stub(context, payload, dri):
            assert payload == self.acapy_record.value
            return "12345"

        api.pds_save = pds_save_stub
        result = await api.pds_save_model(None, self.acapy_record)
        assert result == "12345"