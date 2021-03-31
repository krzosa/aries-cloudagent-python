from aries_cloudagent.pdstorage_thcf.api import OCARecord
from asynctest import TestCase as AsyncTestCase
import aries_cloudagent.pdstorage_thcf.api as api
from aries_cloudagent.messaging.models.base_record import BaseRecord

pds_load = api.pds_load
pds_save = api.pds_save


class _TestBaseRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "defined_consent"

    class Meta:
        schema_class = "_TestBaseRecordSchema"

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
        self.acapy_record = _TestBaseRecord(**self.acapy_record_dict)

    async def test_pds_record(self):
        class Inherit(OCARecord):
            def __init__(self, test, *, oca_schema_dri=None, dri=None):
                self.test = test
                super().__init__(oca_schema_dri, dri)

        inherit = Inherit("asd", oca_schema_dri="123", dri="123")
        assert inherit.serialize() == {
            "test": "asd",
            "dri": "123",
            "oca_schema_dri": "123",
        }
        assert inherit.values() == {"test": "asd"}
        inherit = Inherit("asd", oca_schema_dri="123")
        assert inherit.serialize() == {"test": "asd", "oca_schema_dri": "123"}

    async def test_pds_load_recursive(self):
        payload_dri_1234 = {
            "consent_dri": "12345",
            "test_data": "abc",
            "dict": {"consent_dri": "12345"},
            "consent_schema_dri": "123",
        }

        payload_dri_12345 = {
            "test_data_2222": "abcasdasd",
        }

        final_dict = {
            "consent": {
                "test_data_2222": "abcasdasd",
            },
            "consent_dri": "12345",
            "consent_schema_dri": "123",
            "test_data": "abc",
            "dict": {
                "consent_dri": "12345",
                "consent": {
                    "test_data_2222": "abcasdasd",
                },
            },
        }

        async def pds_load_stub(context, payload_dri):
            if payload_dri == "1234":
                return payload_dri_1234
            elif payload_dri == "12345":
                return payload_dri_12345
            else:
                assert not "invalid codepath"

        api.pds_load = pds_load_stub
        result = await api.pds_load_recursive(None, "1234")
        assert result == final_dict
