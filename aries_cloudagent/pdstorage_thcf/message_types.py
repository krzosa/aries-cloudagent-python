PROTOCOL_URI = "/debug/pds/1.0"
PROTOCOL_PACKAGE = "aries_cloudagent.pdstorage_thcf"

EXCHANGE_DATA_A = f"{PROTOCOL_URI}/exchange_data_a"
EXCHANGE_DATA_B = f"{PROTOCOL_URI}/exchange_data_b"

MESSAGE_TYPES = {
    EXCHANGE_DATA_A: f"{PROTOCOL_PACKAGE}.message_types.ExchangeDataA",
    EXCHANGE_DATA_B: f"{PROTOCOL_PACKAGE}.message_types.ExchangeDataB",
}

# MESSAGE CLASSES

from marshmallow import fields
from ..messaging.agent_message import AgentMessage, AgentMessageSchema


class ExchangeDataA(AgentMessage):
    class Meta:
        handler_class = f"{PROTOCOL_PACKAGE}.handlers.ExchangeDataAHandler"
        schema_class = "ExchangeDataASchema"
        message_type = EXCHANGE_DATA_A

    def __init__(
        self,
        *,
        payload_dri,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.payload_dri = payload_dri


class ExchangeDataASchema(AgentMessageSchema):
    class Meta:
        model_class = ExchangeDataA

    payload_dri = fields.Str(required=True)


class ExchangeDataB(AgentMessage):
    class Meta:
        handler_class = f"{PROTOCOL_PACKAGE}.handlers.ExchangeDataBHandler"
        schema_class = "ExchangeDataBSchema"
        message_type = EXCHANGE_DATA_B

    def __init__(
        self,
        *,
        payload,
        payload_dri,  # optional to check if payload_dris are equal on both sides
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.payload = payload
        self.payload_dri = payload_dri


class ExchangeDataBSchema(AgentMessageSchema):
    class Meta:
        model_class = ExchangeDataB

    payload = fields.Str(required=True)
    payload_dri = fields.Str(required=False)
