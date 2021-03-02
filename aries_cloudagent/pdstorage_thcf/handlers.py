from .error import PDSNotFoundError
from .api import pds_load_string
from .message_types import ExchangeDataB, ExchangeDataA
from aries_cloudagent.messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)
import logging

LOGGER = logging.getLogger(__name__)


class ExchangeDataAHandler(BaseHandler):
    """
    Stage first, this fires for the agent2, receive request to send data
    """

    async def handle(self, context: RequestContext, responder: BaseResponder):
        LOGGER.info("ExchangeDataAHandler called with context %s", context)
        assert isinstance(context.message, ExchangeDataA)
        payload_dri = context.message.payload_dri

        try:
            payload = await pds_load_string(context, payload_dri)
            if payload is None:
                raise PDSNotFoundError(f"Data with dri {payload_dri} not found")
        except PDSNotFoundError as err:
            LOGGER.warning("%s", err.roll_up)
            return

        response = ExchangeDataB(payload=payload, payload_dri=payload_dri)
        response.assign_thread_from(context.message)
        await responder.send_reply(response)


class ExchangeDataBHandler(BaseHandler):
    """
    Stage second, this fires for the agent1, the initiator
    """

    async def handle(self, context: RequestContext, responder: BaseResponder):
        LOGGER.info("ExchangeDataBHandler called with context %s", context)
        assert isinstance(context.message, ExchangeDataB)
        msg = context.message

        await responder.send_webhook(
            "pds/payload",
            {"dri": msg.payload_dri, "payload": msg.payload},
        )
