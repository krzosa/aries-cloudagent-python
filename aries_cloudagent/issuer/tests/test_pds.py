import json

import pytest

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from ...wallet.basic import BasicWallet
from ..pds import *
from ...aathcf.credentials import verify_proof
from aries_cloudagent.connections.models.connection_record import ConnectionRecord


credential_test_schema = OrderedDict(
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.schema.org",
        ],
        "type": [
            "VerifiableCredential",
            "@TODO should this be oca schema or what dri points to",
        ],
        "issuer": "1234",
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
)


def assert_that_contains(base: dict, to_verify: dict):
    # assert that contains at least values of base or more
    # and these least values are not NULL
    for key in base:
        if key == "@context":
            key = "context"
        assert to_verify[key] != None
        assert to_verify[key] != {}
        assert to_verify[key] != []


async def create_test_credential(issuer):
    test_cred = {
        "credentialSubject": {
            "id": "TODO: Did of subject",
            "ocaSchema": {
                "dri": "1234",
                "dataDri": "1234",
            },
            "first_name": "Karol",
        },
    }

    credential, _ = await issuer.create_credential(
        schema={"credential_type": "TestType"},
        credential_values=test_cred["credentialSubject"],
        credential_offer={},
        credential_request={},
    )
    credential_dict = json.loads(credential, object_pairs_hook=OrderedDict)

    assert credential_dict.get("proof") != None
    assert credential_dict["credentialSubject"] == test_cred["credentialSubject"]

    return credential_dict


class TestPDSIssuer(AsyncTestCase):
    async def setUp(self):
        self.wallet = BasicWallet()
        self.issuer: PDSIssuer = PDSIssuer(self.wallet)
        assert self.issuer.wallet is self.wallet
        await self.wallet.create_public_did()

    async def test_create_credential(self):
        credential_dict = await create_test_credential(self.issuer)

        assert_that_contains(credential_test_schema, credential_dict)
        assert_that_contains(credential_test_schema["proof"], credential_dict["proof"])

        assert await verify_proof(self.wallet, credential_dict) == True

    async def test_create_credential_null(self):
        connection = ConnectionRecord(my_did="1234-my", their_did="1234-their")
        with self.assertRaises(IssuerError):
            credential, _ = await self.issuer.create_credential(
                schema={"credential_type": "TestType"},
                credential_values={},
                credential_offer={},
                credential_request={"connection_record": connection},
            )
        with self.assertRaises(IssuerError):
            credential, _ = await self.issuer.create_credential(
                schema={},
                credential_values={},
                credential_offer={},
                credential_request={"connection_record": connection},
            )

    async def test_credentials_are_equal(self):
        test_cred = {
            "credentialSubject": {
                "id": "TODO: Did of subject",
                "ocaSchema": {
                    "dri": "1234",
                    "dataDri": "1234",
                },
                "first_name": "Karol",
            },
        }
        credential_ex = await self.issuer.create_credential_ex(
            test_cred["credentialSubject"], "TestType"
        )
        credential = await create_test_credential(self.issuer)

        assert credential["credentialSubject"] == credential_ex["credentialSubject"]
        assert credential.keys() == credential_ex.keys()


class TestPDSIssuerNoActiveDid(AsyncTestCase):
    async def test_create_credential_active_did_is_none(self):
        self.wallet = BasicWallet()
        self.issuer: PDSIssuer = PDSIssuer(self.wallet)
        assert self.issuer.wallet is self.wallet
        with self.assertRaises(IssuerError):
            await self.issuer.create_credential_ex({})
        with self.assertRaises(IssuerError):
            credential, _ = await self.issuer.create_credential(
                schema={"credential_type": "TestType"},
                credential_values={},
                credential_offer={},
                credential_request={},
            )