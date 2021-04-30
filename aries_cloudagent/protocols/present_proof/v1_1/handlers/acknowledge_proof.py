from aries_cloudagent.pdstorage_thcf.api import pds_link_dri
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from aries_cloudagent.aathcf.utils import debug_handler
from aries_cloudagent.protocols.present_proof.v1_1.models.presentation_exchange import (
    THCFPresentationExchange,
)
from aries_cloudagent.protocols.present_proof.v1_1.messages.acknowledge_proof import (
    AcknowledgeProof,
)
from ..models.utils import retrieve_exchange_by_thread
from aries_cloudagent.holder.base import BaseHolder, HolderError
import json
from collections import OrderedDict


class AcknowledgeProofHandler(BaseHandler):
    """
    Message handler logic for incoming credential presentations / incoming proofs.
    """

    async def handle(self, context: RequestContext, responder: BaseResponder):
        debug_handler(self._logger.info, context, AcknowledgeProof)

        exchange: THCFPresentationExchange = await retrieve_exchange_by_thread(
            context,
            responder.connection_id,
            context.message._thread_id,
            HandlerException,
        )

        if exchange.role != exchange.ROLE_PROVER:
            raise HandlerException(reason="Invalid exchange role")
        if exchange.state != exchange.STATE_PRESENTATION_SENT:
            raise HandlerException(reason="Invalid exchange state")

        holder: BaseHolder = await context.inject(BaseHolder)
        credential_data = json.loads(
            context.message.credential, object_pairs_hook=OrderedDict
        )

        try:
            ack_credential_dri = await holder.store_credential(
                credential_definition={},
                credential_data=credential_data,
                credential_request_metadata={},
            )
        except HolderError as err:
            raise HandlerException("Error on store_credential async!", err.roll_up)

        exchange.acknowledgment_credential_dri = ack_credential_dri
        await pds_link_dri(
            context, exchange.presentation_dri, exchange.acknowledgment_credential_dri
        )
        exchange.state = exchange.STATE_ACKNOWLEDGED
        await exchange.save(context)

        await responder.send_webhook(
            "present_proof",
            {
                "type": "acknowledge_proof",
                "exchange_record_id": exchange._id,
                "connection_id": responder.connection_id,
                "acknowledgment_credential_dri": ack_credential_dri,
            },
        )
