import json
import logging
from typing import Sequence, Tuple

from ..wallet.base import BaseWallet, DIDInfo

from .base import (
    BaseIssuer,
    IssuerError,
    DEFAULT_CRED_DEF_TAG,
    DEFAULT_SIGNATURE_TYPE,
)
from ..messaging.util import time_now
from ..aathcf.credentials import create_proof
from aries_cloudagent.aathcf.credentials import (
    CredentialSchema,
    validate_schema,
)
from collections import OrderedDict


def raise_exception_on_null(value, value_name, exception=IssuerError):
    if value is None or value is {}:
        raise exception(
            f"""{value_name} is empty, it needs to be filled out! currently it looks like this {value}"""
        )


class PDSIssuer(BaseIssuer):
    def __init__(self, wallet: BaseWallet):
        """
        Initialize an PDSIssuer instance.

        Args:

        """
        self.wallet: BaseWallet = wallet
        self.logger = logging.getLogger(__name__)

    def make_schema_id(
        self, origin_did: str, schema_name: str, schema_version: str
    ) -> str:
        """Derive the ID for a schema."""
        return f"{origin_did}:2:{schema_name}:{schema_version}"

    async def create_and_store_schema(
        self,
        origin_did: str,
        schema_name: str,
        schema_version: str,
        attribute_names: Sequence[str],
    ) -> Tuple[str, str]:
        """
        Create a new credential schema and store it in the wallet.

        Args:
            origin_did: the DID issuing the credential definition
            schema_name: the schema name
            schema_version: the schema version
            attribute_names: a sequence of schema attribute names

        Returns:
            A tuple of the schema ID and JSON

        """

        return (schema_id, schema_json)

    def make_credential_definition_id(
        self, origin_did: str, schema: dict, signature_type: str = None, tag: str = None
    ) -> str:
        """Derive the ID for a credential definition."""
        signature_type = signature_type or DEFAULT_SIGNATURE_TYPE
        tag = tag or DEFAULT_CRED_DEF_TAG
        return f"{origin_did}:3:{signature_type}:{str(schema['seqNo'])}:{tag}"

    async def credential_definition_in_wallet(
        self, credential_definition_id: str
    ) -> bool:
        """
        Check whether a given credential definition ID is present in the wallet.

        Args:
            credential_definition_id: The credential definition ID to check
        """
        return False

    async def create_and_store_credential_definition(
        self,
        origin_did: str,
        schema: dict,
        signature_type: str = None,
        tag: str = None,
        support_revocation: bool = False,
    ) -> Tuple[str, str]:
        """
        Create a new credential definition and store it in the wallet.

        Args:
            origin_did: the DID issuing the credential definition
            schema: the schema used as a basis
            signature_type: the credential definition signature type (default 'CL')
            tag: the credential definition tag
            support_revocation: whether to enable revocation for this credential def

        Returns:
            A tuple of the credential definition ID and JSON

        """

        return (credential_definition_id, credential_definition_json)

    async def create_credential_offer(self, credential_definition_id: str) -> str:
        """
        Create a credential offer for the given credential definition id.

        Args:
            credential_definition_id: The credential definition to create an offer for

        Returns:
            The created credential offer

        """

        return credential_offer_json

    async def create_credential(
        self,
        schema: dict,
        credential_offer: dict,
        credential_request: dict,
        credential_values: dict,
        revoc_reg_id: str = None,
        tails_file_path: str = None,
    ) -> Tuple[str, str]:
        credential = await self.create_credential_ex(
            credential_values, schema.get("credential_type")
        )
        return [credential, None]

    async def create_credential_ex(
        self,
        credential_values,
        credential_type: str or list = None,
        subject_public_did: str = None,
    ) -> str:
        my_did = await self.wallet.get_public_did()
        if not isinstance(my_did, DIDInfo) or my_did[0] is None:
            raise IssuerError("Public did is not registered!")
        if not isinstance(credential_values, dict) or credential_values == {}:
            raise IssuerError("credential_values is Null")

        my_did = my_did[0]
        credential_dict = OrderedDict()

        if isinstance(subject_public_did, str):
            credential_values.update({"subject_id": subject_public_did})
        else:
            self.logger.warn("Invalid type of their public did")

        # This documents should exist, those should be cached
        # it seems to be establishing a semantic context, meaning
        # that it contains explanations of what credential fields mean
        # and what credential fields and types are possible
        # We should create it and it should be unchanging so that you can
        # cache it
        # if words in context overlapp, we should read the contexts from
        # top to bottom, so that later contexts overwrite earlier contexts
        credential_dict["context"] = [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.schema.org",
            # TODO: Point to some OCA Credential schema
        ]

        # This partly seems to be an extension of context
        # for example URI = https://www.schema.org has a json
        # and that json has VerifiableCredential with all possible fields
        # which we can reach through https://www.schema.org/VerifiableCredential
        credential_dict["type"] = ["VerifiableCredential"]
        if isinstance(credential_type, str):
            credential_dict["type"].append(credential_type)
        elif isinstance(credential_type, list):
            credential_dict["type"].extend(credential_type)

        credential_dict["issuer"] = my_did
        credential_dict["issuanceDate"] = time_now()
        credential_dict["credentialSubject"] = credential_values
        # "credentialSubject": {
        #     # This should point to some info about the subject of credenial?
        #     # machine readable document, about the subject
        #     "id": "Did of subject",
        #     "ocaSchema": {
        #         "dri": "1234",
        #         "dataDri": "1234",
        #     },
        credential_dict["proof"] = await create_proof(
            self.wallet, credential_dict, IssuerError
        )
        validate_schema(
            CredentialSchema, credential_dict, IssuerError, self.logger.error
        )

        return json.dumps(credential_dict)

    async def revoke_credentials(
        self, revoc_reg_id: str, tails_file_path: str, cred_revoc_ids: Sequence[str]
    ) -> (str, Sequence[str]):
        """
        Revoke a set of credentials in a revocation registry.

        Args:
            revoc_reg_id: ID of the revocation registry
            tails_file_path: path to the local tails file
            cred_revoc_ids: sequences of credential indexes in the revocation registry

        Returns:
            Tuple with the combined revocation delta, list of cred rev ids not revoked

        """

    async def merge_revocation_registry_deltas(
        self, fro_delta: str, to_delta: str
    ) -> str:
        """
        Merge revocation registry deltas.

        Args:
            fro_delta: original delta in JSON format
            to_delta: incoming delta in JSON format

        Returns:
            Merged delta in JSON format

        """

    async def create_and_store_revocation_registry(
        self,
        origin_did: str,
        cred_def_id: str,
        revoc_def_type: str,
        tag: str,
        max_cred_num: int,
        tails_base_path: str,
    ) -> Tuple[str, str, str]:
        """
        Create a new revocation registry and store it in the wallet.

        Args:
            origin_did: the DID issuing the revocation registry
            cred_def_id: the identifier of the related credential definition
            revoc_def_type: the revocation registry type (default CL_ACCUM)
            tag: the unique revocation registry tag
            max_cred_num: the number of credentials supported in the registry
            tails_base_path: where to store the tails file

        Returns:
            A tuple of the revocation registry ID, JSON, and entry JSON

        """
