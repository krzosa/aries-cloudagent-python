from marshmallow import fields
from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import REQUEST_PROOF, PROTOCOL_PACKAGE
from aries_cloudagent.aathcf.credentials import (
    PresentationRequestSchema,
)

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.request_proof.RequestProofHandler"


class RequestProof(AgentMessage):
    class Meta:
        handler_class = HANDLER_CLASS
        schema_class = "RequestProofSchema"
        message_type = REQUEST_PROOF

    def __init__(
        self,
        _id: str = None,
        *,
        presentation_request: dict = None,
        usage_policy=None,
        **kwargs,
    ):
        """Initialize credential issue object."""
        super().__init__(_id=_id, **kwargs)
        self.presentation_request = presentation_request
        self.usage_policy = usage_policy


class RequestProofSchema(AgentMessageSchema):
    """Credential schema."""

    class Meta:
        """Credential schema metadata."""

        model_class = RequestProof

    presentation_request = fields.Nested(
        PresentationRequestSchema,
        required=False,
        description="presentation request (also known as proof request)",
    )
    usage_policy = fields.Str(required=False)
