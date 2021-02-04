from asynctest import TestCase as AsyncTestCase
from aries_cloudagent.wallet.basic import BasicWallet
from aries_cloudagent.config.injection_context import InjectionContext
from ..pds import PDSVerifier
from collections import OrderedDict

pres = OrderedDict(
    [
        (
            "context",
            [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
        ),
        ("id", "urn:uuid:f811f144-9544-4576-864f-a900133fa3ca"),
        ("type", ["VerifiablePresentation"]),
        (
            "verifiableCredential",
            OrderedDict(
                [
                    (
                        "zQmVBN7bC27zcvjkR52YTrvK7Qo89DVgCYuMpWZ5bUsfnmN",
                        OrderedDict(
                            [
                                (
                                    "context",
                                    [
                                        "https://www.w3.org/2018/credentials/v1",
                                        "https://www.schema.org",
                                    ],
                                ),
                                ("type", ["VerifiableCredential"]),
                                ("issuer", "9cKXSg5jj9MM8n1ThURpKb"),
                                ("issuanceDate", "2021-01-22 07:34:47.525771Z"),
                                (
                                    "credentialSubject",
                                    OrderedDict(
                                        [
                                            ("oca_schema_dri", "12345"),
                                            ("oca_schema_namespace", "string"),
                                            (
                                                "oca_data_dri",
                                                "zQmSnRDrp3sNzsB194RaKwqKWmFS7mbT8oiF7qMWUCoNGgQ",
                                            ),
                                            (
                                                "service_consent_match_id",
                                                "4de0de9e-5738-4616-97a9-4e656abcbc89",
                                            ),
                                            ("subject_id", "L2U3CrMypQXTCkr5TzT97x"),
                                        ]
                                    ),
                                ),
                                (
                                    "proof",
                                    OrderedDict(
                                        [
                                            (
                                                "jws",
                                                "BSOJEbPUVg60nQrHSwyGfwWoooxi70XfbBiB26v_26rotQcraQ8xRTJ38xoSh7ITXxN5_ptIah06HEpYREYpCw",
                                            ),
                                            ("type", "Ed25519Signature2018"),
                                            ("created", "2021-01-22 07:34:47.532058Z"),
                                            ("proofPurpose", "assertionMethod"),
                                            (
                                                "verificationMethod",
                                                "CH3ihjcbD22HrTwKAtujmKehGnU4bmwD5ELocuvSiU3D",
                                            ),
                                        ]
                                    ),
                                ),
                            ]
                        ),
                    )
                ]
            ),
        ),
        (
            "proof",
            OrderedDict(
                [
                    (
                        "jws",
                        "TolWsBytjDV1K1zjALUwoDDtTjmZELvvtz6iOFhAdW2iPwjf_pjGQtnu9VdOyNt7lO0k-PuNg2U78nWiEBelAg",
                    ),
                    ("type", "Ed25519Signature2018"),
                    ("created", "2021-02-01 13:51:12.979860Z"),
                    ("proofPurpose", "assertionMethod"),
                    (
                        "verificationMethod",
                        "BKaqqDxkU7TRQ875LQEqLtZJcV6JMPGL8qTLc5FV7vPo",
                    ),
                ]
            ),
        ),
    ]
)


pres_request = {
    "schema_base_dri": "1234",
    "requested_attributes": ["test"],
}


class TestPDSVerifier(AsyncTestCase):
    async def setUp(self):
        self.context: InjectionContext = InjectionContext()

        wallet = BasicWallet()

        self.verifier = PDSVerifier(wallet)

    async def test_presentation_verification(self):

        result = await self.verifier.verify_presentation(pres_request, pres)
        assert result == True

        result = await self.verifier.verify_presentation({}, pres, {}, {}, {}, {})
        assert result == False

        result = await self.verifier.verify_presentation({}, {}, {}, {}, {}, {})
        assert result == False

        # pres["proof"]["jws"][4] += hex(12)
        # result = await self.verifier.verify_presentation(
        #     pres_request, pres, {}, {}, {}, {}
        # )
        # assert result == False