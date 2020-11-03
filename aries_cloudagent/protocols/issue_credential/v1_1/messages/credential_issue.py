"""A credential content message."""

from typing import Sequence

from marshmallow import fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import CREDENTIAL_ISSUE, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.credential_issue.CredentialIssueHandler"


class CredentialIssue(AgentMessage):
    class Meta:
        handler_class = HANDLER_CLASS
        schema_class = "CredentialIssueSchema"
        message_type = CREDENTIAL_ISSUE

    def __init__(
        self,
        _id: str = None,
        *,
        credential: dict = {},
        **kwargs,
    ):
        """
        Initialize credential issue object.
        """
        super().__init__(_id=_id, **kwargs)
        # TODO; Schema
        self.credential = credential


class CredentialIssueSchema(AgentMessageSchema):
    """Credential schema."""

    class Meta:
        """Credential schema metadata."""

        model_class = CredentialIssue
