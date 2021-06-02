from aries_cloudagent.wallet.util import b64_to_bytes, bytes_to_b64, str_to_b64
from aries_cloudagent.messaging.util import time_now
from aries_cloudagent.messaging.valid import IndyISO8601DateTime
from collections import OrderedDict
from marshmallow import fields, Schema

import json
from aries_cloudagent.wallet.error import WalletError


def validate_schema(SchemaClass, schema: dict, exception=None, log=print):
    """
    Use Marshmallow Schema class to validate a schema in the form of dictionary
    and also handle fields like @context

    Returns errors if no exception passed
    or
    Throws passed in exception
    """
    assert isinstance(schema, (dict, OrderedDict))

    test_schema = schema
    test_against = SchemaClass()
    if test_schema.get("@context") is not None and test_schema.get("context") is None:
        test_schema = schema.copy()
        test_schema["context"] = test_schema.get("@context")
        test_schema.pop("@context", "skip errors")

    errors = test_against.validate(test_schema)
    if errors != {}:
        log(f"schema validation error: {errors}\n")

        if exception is not None:
            raise exception(f"Invalid Schema! errors: {errors}")
        else:
            return errors


def dictionary_to_base64(dictionary: OrderedDict) -> bytes:
    """Transform a dictionary into base 64."""
    assert isinstance(dictionary, dict)

    dictionary_str = json.dumps(dictionary)
    dictionary_base64 = str_to_b64(dictionary_str, urlsafe=True).encode("utf-8")

    assert isinstance(dictionary_base64, bytes)

    return dictionary_base64


async def verify_proof(wallet, credential: OrderedDict) -> bool:
    """
    Args: Credential: full schema with proof field
    """
    assert isinstance(credential, OrderedDict)

    cred_copy = credential.copy()
    proof = cred_copy["proof"]
    proof_signature = b64_to_bytes(proof["jws"], urlsafe=True)
    if proof["type"] != "Ed25519Signature2018":
        print("This proof type is not implemented, ", proof["type"])
        result = False

    del cred_copy["proof"]
    credential_base64 = dictionary_to_base64(cred_copy)

    try:
        result = await wallet.verify_message(
            credential_base64, proof_signature, proof["verificationMethod"]
        )
    except WalletError as err:
        print(err.roll_up)
        result = False

    assert isinstance(result, bool)
    return result


async def create_proof(wallet, credential: OrderedDict, exception) -> OrderedDict:
    """
    Creates a proof dict with signature for given dictionary
    """
    assert isinstance(credential, OrderedDict)

    try:
        signing_key = await wallet.create_signing_key()

        credential_base64 = dictionary_to_base64(credential)
        signature_bytes: bytes = await wallet.sign_message(
            credential_base64, signing_key.verkey
        )
    except WalletError as err:
        raise exception(err.roll_up)

    proof = OrderedDict()
    proof["jws"] = bytes_to_b64(signature_bytes, urlsafe=True, pad=False)
    proof["type"] = "Ed25519Signature2018"
    proof["created"] = time_now()
    proof["proofPurpose"] = "assertionMethod"
    proof["verificationMethod"] = signing_key.verkey
    # proof_dict = {
    #     "type": "",
    #     "created": ,
    #     # If the cryptographic suite expects a proofPurpose property,
    #     # it is expected to exist and be a valid value, such as assertionMethod.
    #     "proofPurpose": ,
    #     # @TODO: verification method should point to something
    #     # that lets you verify the data, reference to signing entity
    #     # @
    #     # The verificationMethod property specifies,
    #     # for example, the public key that can be used
    #     # to verify the digital signature
    #     # @
    #     # Dereferencing a public key URL reveals information
    #     # about the controller of the key,
    #     # which can be checked against the issuer of the credential.
    #     "verificationMethod": ,
    #
    #     "jws": , SIGNATURE
    # }

    assert isinstance(proof, OrderedDict)
    return proof


class ProofSchema(Schema):
    type = fields.Str(required=True)
    created = fields.Str(required=True, validate=IndyISO8601DateTime())
    proofPurpose = fields.Str(required=True)
    verificationMethod = fields.Str(required=True)
    jws = fields.Str(required=True)


class PresentationSchema(Schema):
    id = fields.Str(required=False)
    type = fields.List(fields.Str(required=True))
    proof = fields.Nested(ProofSchema, required=True)
    # verifiableCredential = fields.List(fields.Dict(required=True), required=True)
    verifiableCredential = fields.Dict()
    context = fields.List(fields.Str(required=True), required=True)


class CredentialSchema(Schema):
    id = fields.Str(required=False)
    issuer = fields.Str(required=True)
    context = fields.List(fields.Str(required=True), required=True)
    type = fields.List(fields.Str(required=True), required=True)
    credentialSubject = fields.Dict(keys=fields.Str(), required=True)
    proof = fields.Nested(ProofSchema(), required=True)
    issuanceDate = fields.Str(required=True)


class PresentationRequestedAttributesSchema(Schema):
    restrictions = fields.List(fields.Dict())


class PresentationRequestSchema(Schema):
    requested_attributes = fields.List(fields.Str(required=False), required=False)
    issuer_did = fields.Str(required=False)
    oca_schema_dri = fields.Str(required=True)
