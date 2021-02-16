from asynctest import TestCase as AsyncTestCase
from ..api import _save_chunks


class TestPDSChunks(AsyncTestCase):
    async def setUp(self):
        self.chunks = [
            {
                "dri": "vgwdgfwg93t2",
                "payload": [
                    {
                        "additionalProp1": "string",
                        "additionalProp2": "string",
                        "additionalProp3": "string",
                    }
                ],
            },
            {
                "dri": "1252t1g2eg",
                "payload": [
                    {
                        "additionalProp1": "string",
                        "additionalProp2": "string",
                        "additionalProp3": "string",
                    }
                ],
            },
        ]

    async def test_oca_schema_chunks(self):
        payload_id = "vas3t3df213:test_payload_id"

        async def stub_save(context, data, *, oca_schema_dri):
            context is "unused"
            assert isinstance(data, str) or isinstance(data, dict)
            assert isinstance(oca_schema_dri, str)
            return payload_id

        result = await _save_chunks("unused", self.chunks, stub_save)
        assert isinstance(result, list)
        for chunk in result:
            assert chunk["dri"] is not None
            for chunk_payload in chunk["payload"]:
                assert chunk_payload["_payload_id"] == payload_id
