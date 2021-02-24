from .base import BasePDS
from .api import encode
import json


class LocalPDS(BasePDS):
    def __init__(self):
        super().__init__()
        self.storage = {}
        self.preview_settings = {
            "oca_schema_namespace": "pds",
            "oca_schema_dri": "3Fb68s1EPcX4HZhhT23HXrYpuMfcZdreD8xNmEMDc6nC",
        }

        self.settings = {"no_configuration_needed": "yes"}

    async def load(self, id: str) -> dict:
        """
        returns: None, on record not found
        """
        result = self.storage.get(id)

        return {"content": result}

    async def save(self, record, metadata: dict) -> str:
        dri_value = None
        if isinstance(record, str):
            dri_value = encode(record)
        elif isinstance(record, dict):
            dri_value = encode(json.dumps(record))
        else:
            raise AssertionError("Invalid type")

        self.storage[dri_value] = record

        return dri_value

    async def query_by_oca_schema_dri(self, oca_schema_dri: str = None) -> str:
        assert not """Not implemented"""

    async def ping(self) -> [bool, str]:
        return [True, None]
