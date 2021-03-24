from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)
from ..messages.request_proof import RequestProof
from aries_cloudagent.aathcf.utils import debug_handler
from aries_cloudagent.protocols.present_proof.v1_1.models.presentation_exchange import (
    THCFPresentationExchange,
)


class RequestProofHandler(BaseHandler):
    """
    Message handler logic for incoming credential requests.
    """

    async def handle(self, context: RequestContext, responder: BaseResponder):
        debug_handler(self._logger.info, context, RequestProof)
        message: RequestProof = context.message
        exchange_record = THCFPresentationExchange(
            connection_id=responder.connection_id,
            thread_id=message._thread_id,
            initiator=THCFPresentationExchange.INITIATOR_EXTERNAL,
            role=THCFPresentationExchange.ROLE_PROVER,
            state=THCFPresentationExchange.STATE_REQUEST_RECEIVED,
            presentation_request=message.presentation_request,
            requester_usage_policy=context.message.usage_policy,
        )
        record_id = await exchange_record.save(context)
        self._logger.info("credential_exchange_record_id = %s", record_id)

        await responder.send_webhook(
            "present_proof",
            {
                "type": "request_proof",
                "exchange_record_id": record_id,
                "connection_id": responder.connection_id,
            },
        )
