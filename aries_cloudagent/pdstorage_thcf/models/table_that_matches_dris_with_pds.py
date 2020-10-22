from ...messaging.models.base_record import BaseRecord, BaseRecordSchema
from ...storage.base import BaseStorage
from marshmallow import fields, Schema
from aries_cloudagent.messaging.util import time_now
from aries_cloudagent.storage.error import StorageDuplicateError
from ...config.injection_context import InjectionContext
from typing import Any, Mapping, Sequence, Union
import uuid


class DriStorageMatchTable(BaseRecord):
    RECORD_ID_NAME = "dri"
    RECORD_TYPE = "dri_storage_matchtable"

    class Meta:
        schema_class = "DriStorageMatchTableSchema"

    def __init__(
        self, dri: str, pds_type: tuple, **keywordArgs,
    ):
        super().__init__(dri)
        self.pds_type = pds_type

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {"pds_type": self.pds_type}

    async def save(
        self,
        context: InjectionContext,
        *,
        reason: str = None,
        log_params: Mapping[str, Any] = None,
        log_override: bool = False,
        webhook: bool = None,
    ) -> str:
        """Persist the record to storage.

        Args:
            context: The injection context to use
            reason: A reason to add to the log
            log_params: Additional parameters to log
            webhook: Flag to override whether the webhook is sent
        """
        new_record = None
        log_reason = reason or ("Updated record" if self._id else "Created record")
        try:
            self.updated_at = time_now()
            storage: BaseStorage = await context.inject(BaseStorage)

            record = self.storage_record
            await storage.add_record(self.storage_record)
            new_record = True
        except StorageDuplicateError:
            return self._id
        finally:
            params = {self.RECORD_TYPE: self.serialize()}
            if log_params:
                params.update(log_params)
            if new_record is None:
                log_reason = f"FAILED: {log_reason}"
            self.log_state(context, log_reason, params, override=log_override)

        await self.post_save(context, new_record, self._last_state, webhook)
        self._last_state = self.state

        return self._id


class DriStorageMatchTableSchema(BaseRecordSchema):
    class Meta:
        model_class = "DriStorageMatchTable"

    pds_type = fields.Str(required=False)
