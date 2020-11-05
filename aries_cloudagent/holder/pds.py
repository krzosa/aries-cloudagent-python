import logging
from typing import Tuple, Union
from ..core.error import BaseError
from .base import *
from .models.credential import *
from ..storage.base import BaseStorage
from ..storage.error import StorageNotFoundError, StorageError
from ..config.injection_context import InjectionContext
from aries_cloudagent.issuer.pds import dictionary_to_base64
from aries_cloudagent.wallet.base import BaseWallet

# TODO verifier
async def verify_credential(credential: dict, wallet) -> bool:
    proof = credential["proof"]
    if proof["type"] != "Ed25519Signature2018":
        print("This proof type is not implemented, ", proof["type"])
        result = False

    del credential["proof"]
    proof_signature = bytes.fromhex(proof["jws"])
    credential_base64 = dictionary_to_base64(credential)

    result = await wallet.verify_message(
        credential_base64, proof_signature, proof["verificationMethod"]
    )

    return result


# def assert_holder(expression, message):
#     if not expression:
#         raise HolderError(message)


# TODO: Better error handling
class PDSHolder(BaseHolder):
    """PDS class for holder."""

    def __init__(self, context):
        self.log = logging.getLogger(__name__).info
        self.context: InjectionContext = context

    async def get_credential(self, credential_id: str) -> str:
        """
        Get a stored credential.

        Args:
            credential_id: Credential id to retrieve

        """
        self.log("get_credential invoked")

        try:
            credential: THCFCredential = await THCFCredential.retrieve_by_id(
                self.context, credential_id
            )
        except StorageError as err:
            raise HolderError(err.roll_up)

        return credential.serialize(as_string=True)

    async def delete_credential(self, credential_id: str):
        """
        Remove a credential stored in the wallet.

        Args:
            credential_id: Credential id to remove

        """
        self.log("delete_credential invoked")

        try:
            credential: THCFCredential = await THCFCredential.retrieve_by_id(
                self.context, credential_id
            )
            await credential.delete_record(self.context)
        except StorageError as err:
            raise HolderError(err.roll_up)

    async def get_mime_type(
        self, credential_id: str, attr: str = None
    ) -> Union[dict, str]:
        """
        Get MIME type per attribute (or for all attributes).

        Args:
            credential_id: credential id
            attr: attribute of interest or omit for all

        Returns: Attribute MIME type or dict mapping attribute names to MIME types
            attr_meta_json = all_meta.tags.get(attr)

        """
        pass

    async def create_presentation(
        self,
        presentation_request: dict,
        requested_credentials: dict,
        schemas: dict,
        credential_definitions: dict,
        rev_states: dict = None,
    ) -> str:
        """
        Get credentials stored in the wallet.

        Args:
            presentation_request: Valid indy format presentation request
            requested_credentials: Indy format requested credentials
            schemas: Indy formatted schemas JSON
            credential_definitions: Indy formatted credential definitions JSON
            rev_states: Indy format revocation states JSON
        """
        pass

    async def create_credential_request(
        self, credential_offer: dict, credential_definition: dict, holder_did: str
    ) -> Tuple[str, str]:
        """
        Create a credential request for the given credential offer.

        Args:
            credential_offer: The credential offer to create request for
            credential_definition: The credential definition to create an offer for
            holder_did: the DID of the agent making the request

        Returns:
            A tuple of the credential request and credential request metadata

        """
        pass

    async def store_credential(
        self,
        credential_definition: dict,
        credential_data: dict,
        credential_request_metadata: dict,
        credential_attr_mime_types=None,
        credential_id: str = None,
        rev_reg_def: dict = None,
    ):
        """
        Store a credential in the wallet.

        Args:
            credential_definition: Credential definition for this credential
            credential_data: Credential data generated by the issuer
            credential_request_metadata: credential request metadata generated
                by the issuer
            credential_attr_mime_types: dict mapping attribute names to (optional)
                MIME types to store as non-secret record, if specified
            credential_id: optionally override the stored credential id
            rev_reg_def: revocation registry definition in json

        Returns:
            the ID of the stored credential

        """
        self.log("store_credential invoked credential_data %s", credential_data)

        if not isinstance(credential_data, dict):
            raise HolderError("Credential data has invalid type")

        issuanceDate = credential_data.get("issuanceDate")
        subject = credential_data.get("credentialSubject")
        context = credential_data.get("@context")
        issuer = credential_data.get("issuer")
        proof = credential_data.get("proof")
        type = credential_data.get("type")
        id = credential_data.get("id")

        error_msg = " field of credential is empty! It needs to be filled in"
        if issuer is None or "":
            raise HolderError("issuer" + error_msg)
        if proof is None or {}:
            raise HolderError("proof" + error_msg)
        if type is None or []:
            raise HolderError("type" + error_msg)
        if subject is None or {}:
            raise HolderError("subject" + error_msg)
        if context is None or []:
            raise HolderError("@context" + error_msg)
        if issuanceDate is None or "":
            raise HolderError("issuanceDate" + error_msg)

        error_msg = " field of credential is of incorrect type!"
        if not isinstance(issuer, str):
            raise HolderError("Issuer" + error_msg)
        if not isinstance(id, str) and id != None:
            raise HolderError("id" + error_msg)
        if not isinstance(proof, dict):
            raise HolderError("proof" + error_msg)
        if not isinstance(subject, dict):
            raise HolderError("subject" + error_msg)
        if not isinstance(context, list):
            raise HolderError("context" + error_msg)
        if not isinstance(type, list):
            raise HolderError("type" + error_msg)

        wallet = await self.context.inject(BaseWallet)
        isVerified = await verify_credential(credential_data, wallet)
        if isVerified == False:
            raise HolderError("Proof is incorrect, could not verify")

        credential = THCFCredential(
            issuanceDate=issuanceDate,
            credentialSubject=subject,
            context=context,
            issuer=issuer,
            proof=proof,
            type=type,
            id=id,
        )

        id = await credential.save(self.context, reason="Credential saved to storage")
        self.log("Saved Credential id: %s serialized %s", id, credential.serialize())

        return id

    async def get_credentials(self) -> list:
        """
        Retrieve credential list based on a filter(TODO)

        """
        self.log("get_credential invoked")

        try:
            credentials: THCFCredential = await THCFCredential.query(self.context)
        except StorageError as err:
            raise HolderError(err.roll_up)

        result = []
        for cred in credentials:
            result.append(cred.serialize())

        return result

    async def create_revocation_state(
        self,
        cred_rev_id: str,
        rev_reg_def: dict,
        rev_reg_delta: dict,
        timestamp: int,
        tails_file_path: str,
    ) -> str:
        """
        Create current revocation state for a received credential.

        Args:
            cred_rev_id: credential revocation id in revocation registry
            rev_reg_def: revocation registry definition
            rev_reg_delta: revocation delta
            timestamp: delta timestamp

        Returns:
            the revocation state

        """
        pass
