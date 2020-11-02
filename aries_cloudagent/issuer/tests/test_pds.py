import json

import pytest

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from ...wallet.basic import BasicWallet
from ..pds import *


TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
SCHEMA_NAME = "resident"
SCHEMA_VERSION = "1.0"
SCHEMA_TXN = 1234
SCHEMA_ID = f"{TEST_DID}:2:{SCHEMA_NAME}:{SCHEMA_VERSION}"
CRED_DEF_ID = f"{TEST_DID}:3:CL:{SCHEMA_TXN}:default"

credential_test_schema = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.schema.org",
    ],
    "type": [
        "VerifiableCredential",
        "@TODO should this be oca schema or what dri points to",
    ],
    "issuer": 1234,
    "issuanceDate": time_now(),
    "credentialSubject": {
        "id": "TODO: Did of subject",
        "ocaSchema": {
            "dri": "1234",
            "dataDri": "1234",
        },
    },
    "proof": {
        "type": "Ed25519Signature2018",
        "created": time_now(),
        "proofPurpose": "assertionMethod",
        "verificationMethod": "1234",
        "jws": "1234",
    },
}


class TestPDSIssuer(AsyncTestCase):
    async def setUp(self):

        self.wallet = BasicWallet()
        self.issuer: PDSIssuer = PDSIssuer(self.wallet)
        assert self.issuer.wallet is self.wallet
        await self.wallet.create_public_did()

    async def test_create_credential(self):

        credential, _ = await self.issuer.create_credential(
            schema={"credential_type": "TestType"},
            credential_values=credential_test_schema["credentialSubject"],
            credential_offer={},
            credential_request={},
        )
        credential_dict = json.loads(credential)

        # assert schema contains test schema fields
        assert (
            credential_dict["credentialSubject"]
            == credential_test_schema["credentialSubject"]
        )
        assert isinstance(credential, str)
        for key in credential_test_schema:
            assert credential_dict[key]
            for key_proof in credential_test_schema["proof"]:
                assert credential_dict["proof"][key_proof]

        proof = credential_dict["proof"]
        proof_signature = bytes.fromhex(proof["jws"])

        del credential_dict["proof"]
        credential_base64 = dictionary_to_base64(credential_dict)

        isVerified = await self.wallet.verify_message(
            credential_base64, proof_signature, proof["verificationMethod"]
        )

        assert isVerified == True
