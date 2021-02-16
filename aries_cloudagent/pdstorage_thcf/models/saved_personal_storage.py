from ...messaging.models.base_record import BaseRecord, BaseRecordSchema

from marshmallow import fields
from aries_cloudagent.storage.error import StorageNotFoundError


class SavedPDS(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "saved_personal_storage"

    ACTIVE = "active"
    INACTIVE = "inactive"

    class Meta:
        schema_class = "SavedPDSSchema"

    def __init__(
        self,
        *,
        type: str = "local",
        name: str = "default",
        state: str = INACTIVE,
        settings: dict = {},
        record_id: str = None,
        **keywordArgs,
    ):
        super().__init__(record_id, state)
        self.type = type
        self.name = name
        self.settings = settings

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {
            prop: getattr(self, prop) for prop in ("type", "name", "state", "settings")
        }

    @property
    def record_tags(self) -> dict:
        return {"type": self.type, "name": self.name, "state": self.state}

    def get_pds_full_name(self) -> tuple:
        result = tuple([self.type, self.name])
        return result

    @classmethod
    async def retrieve_active(cls, context):
        active_pds = await cls.query(context, {"state": cls.ACTIVE})
        assert isinstance(
            active_pds, list
        ), f"not list {active_pds}, {type(active_pds)}"

        assert len(active_pds) <= 1, f"More than one active PDS {active_pds}"

        if len(active_pds) == 0:
            raise StorageNotFoundError

        return active_pds[0]

    @classmethod
    async def retrieve_type_name(cls, context, type, name):
        record = await cls.query(context, {"type": type, "name": name})
        assert isinstance(record, list), f"not list {record}, {type(record)}"
        assert (
            len(record) <= 1
        ), f"More than one PDS with specified type and name {record}"
        if len(record) == 0:
            raise StorageNotFoundError

        return record[0]


class SavedPDSSchema(BaseRecordSchema):
    class Meta:
        model_class = "SavedPDS"

    type = fields.Str(required=False)
    name = fields.Str(required=False)
    state = fields.Str(required=False)
    settings = fields.Dict()
