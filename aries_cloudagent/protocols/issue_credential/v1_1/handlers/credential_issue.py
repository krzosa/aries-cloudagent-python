from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from ..messages.credential_issue import CredentialIssue


class CredentialIssueHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for incoming credential issues.
        """
        self._logger.debug("CredentialHandler called with context %s", context)
        assert isinstance(context.message, CredentialIssue)
        self._logger.info(
            "Received credential message: %s", context.message.serialize(as_string=True)
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for credential request")

        print("\n\n\n\n\nHANDLER", context.message)