"""Base Verifier class."""

from .base import BaseVerifier
from aries_cloudagent.aathcf.credentials import (
    PresentationRequestSchema,
    PresentationSchema,
    assert_type,
    validate_schema,
)
from ..aathcf.credentials import verify_proof
import logging
from collections import OrderedDict


class PDSVerifier(BaseVerifier):
    """PDS class for verifier."""

    def __init__(self, wallet):
        self.logger = logging.getLogger(__name__)
        self.wallet = wallet

    async def verify_presentation(
        self,
        presentation_request,
        presentation,
        schemas={},
        credential_definitions={},
        rev_reg_defs={},
        rev_reg_entries={},
    ):
        """
        Verify a presentation.

        Args:
            presentation_request: Presentation request data
            presentation: Presentation data
            schemas: Schema data
            credential_definitions: credential definition data
            rev_reg_defs: revocation registry definitions
            rev_reg_entries: revocation registry entries
        """
        self.logger.info(
            f"""verify_presentation input
        presentation_request {presentation_request}
        presentation         {presentation}"""
        )

        errors1 = validate_schema(
            PresentationRequestSchema, presentation_request, log=self.logger.error
        )
        errors2 = validate_schema(
            PresentationSchema, presentation, log=self.logger.error
        )
        if errors1 or errors2:
            self.logger.error(
                f"presentation_request errors: {errors1} "
                f"presentation errors: {errors2} "
            )
            return False

        assert isinstance(
            presentation, OrderedDict
        ), "to preserve order presentation should be OrderedDict"

        proofVerified = await verify_proof(self.wallet, presentation)
        if proofVerified is False:
            self.logger.warning("verify_proof presentation proof: %s", proofVerified)
            return False

        for subcred in presentation.get("verifiableCredential"):
            subproof_verified = await verify_proof(
                self.wallet, presentation.get("verifiableCredential")[subcred]
            )
            if subproof_verified is False:
                self.logger.warning("verify_proof subproof: %s", subproof_verified)
                return False

        return True
