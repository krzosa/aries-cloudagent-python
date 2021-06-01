from aries_cloudagent.wallet.util import b64_to_bytes, bytes_to_b64, str_to_b64
from aries_cloudagent.messaging.util import time_now
from aries_cloudagent.messaging.valid import IndyISO8601DateTime
from collections import OrderedDict
from marshmallow import fields, Schema

import json
import inspect
from aries_cloudagent.wallet.error import WalletError


def get_line_and_file_at_callsite(indirection_number):
    """
    Prints the line and filename.

    If 1 is passed it prints at function call site

    If 2 is passed it prints at callsite of a function
    which called the function which contained this

    Purpose:
        When you use VSCode it should jump you to the line from clicking on cmd

    """
    caller_frame_record = inspect.stack()[indirection_number]

    frame = caller_frame_record[0]
    info = inspect.getframeinfo(frame)
    filename = info.filename
    filename = filename.replace("/home/indy/", "")

    msg = (
        f"\n-------------------------------------------------------------------\n"
        f"ASSERT Incorrect type\n"
        f"FILE: {filename}:{info.lineno}\n"
        f"-------------------------------------------------------------------\n"
    )
    return msg


def assert_type(value, Type):
    result = isinstance(value, Type)
    if not result:
        assert 0, (
            f"ERROR: Incorrect type! should be {Type} but is of type {type(value)}"
            + get_line_and_file_at_callsite(2)
        )


def assert_type_or(value, Type1, Type2):
    result1 = isinstance(value, Type1)
    result2 = isinstance(value, Type2)
    if not result1 and not result2:
        print("Value: ", value)
        assert 0, (
            f"ERROR: Incorrect type! should be {Type1}"
            f"or {Type2} but is of type {type(value) }"
            + get_line_and_file_at_callsite(2)
        )


def validate_schema(SchemaClass, schema: dict, exception=None, log=print):
    """
    Use Marshmallow Schema class to validate a schema in the form of dictionary
    and also handle fields like @context

    Returns errors if no exception passed
    or
    Throws passed in exception
    """
    assert_type_or(schema, dict, OrderedDict)

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
    assert_type(dictionary, dict)

    dictionary_str = json.dumps(dictionary)
    dictionary_base64 = str_to_b64(dictionary_str, urlsafe=True).encode("utf-8")

    assert_type(dictionary_base64, bytes)

    return dictionary_base64


async def verify_proof(wallet, credential: OrderedDict) -> bool:
    """
    Args: Credential: full schema with proof field
    """
    assert_type(credential, OrderedDict)

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

    assert_type(result, bool)
    return result


async def create_proof(wallet, credential: OrderedDict, exception) -> OrderedDict:
    """
    Creates a proof dict with signature for given dictionary
    """
    assert_type(credential, OrderedDict)

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

    assert_type(proof, OrderedDict)
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
    requested_attributes = fields.List(fields.Str(required=True), required=True)
    issuer_did = fields.Str(required=False)
    oca_schema_dri = fields.Str(required=True)


# TODO: JWT
async def create_proof_jwt(wallet, credential):
    def dictionary_to_base64_jwt(dictionary) -> bytes:
        dictionary_str = json.dumps(dictionary)
        dictionary_base64 = str_to_b64(dictionary_str, urlsafe=True).encode("utf-8")

        return dictionary_base64

    """
    JWT:
    https://tools.ietf.org/html/rfc7519
    JWS:
    https://tools.ietf.org/html/rfc7515
    """
    signing_key = await wallet.create_signing_key()
    header = {"alg": "EdDSA", "typ": "JWT"}
    payload_fields = {
        "iss": "",  # issuer
        "aud": "",  # audience
        "sub": "",  # subject
        "iat": time_now(),  # Issued At epoch
        "exp": time_now(),  # expiration epoch
    }
    payload_fields.update(credential)

    test_2 = {"iss": "joe", "exp": 1300819380, "http://example.com/is_root": True}
    test = {"typ": "JWT", "alg": "HS256"}
    test_abc = dictionary_to_base64_jwt(test_2)
    return test_abc

    """
        * The "iss" value is a case-sensitive string containing a StringOrURI
        value.  Use of this claim is OPTIONAL
        * sub - who jwt is about, subject
        * aud - audience, receiver of jwt
        * The "nbf" (not before) claim identifies the time before which the JWT
        MUST NOT be accepted for processing.
        * The "jti" (JWT ID) claim provides a unique identifier for the JWT.
        The identifier value MUST be assigned in a manner that ensures that
        there is a negligible probability that the same value will be
        accidentally assigned to a different data object
    """

    header_base64: bytes = dictionary_to_base64_jwt(header)
    payload_base64: bytes = dictionary_to_base64_jwt(payload_fields)
    header_payload = (
        header_base64.decode("utf-8") + "." + payload_base64.decode("utf-8")
    )
    header_payload_base64 = str_to_b64(header_payload).encode("utf-8")

    signature_bytes: bytes = await wallet.sign_message(
        header_payload_base64, signing_key.verkey
    )
    signature_str = signature_bytes.decode("utf-8")
    header_payload_signature = header_payload + "." + signature_str
    return header_payload_signature
