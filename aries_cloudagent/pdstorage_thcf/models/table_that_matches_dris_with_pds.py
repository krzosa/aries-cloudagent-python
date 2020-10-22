from ...messaging.models.base_record import BaseRecord, BaseRecordSchema
from ...storage.base import BaseStorage
from marshmallow import fields, Schema


class DriStorageMatchTable(BaseRecord):
    RECORD_ID_NAME = "dri"
    RECORD_TYPE = "dri_storage_matchtable"

    class Meta:
        schema_class = "DriStorageMatchTableSchema"

    def __init__(
        self,
        dri: str,
        pds_type: str,
        *,
        **keywordArgs,
    ):
        super().__init__(dri)
        self.pds_type = pds_type

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {"pds_type": self.pds_type}




class DriStorageMatchTableSchema(BaseRecordSchema):
    class Meta:
        model_class = "DriStorageMatchTable"

    pds_type = fields.Str(required=False)
