import json

import pytest

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from ..pds import *
from aries_cloudagent.storage.basic import BasicStorage
from ..models.credential import THCFCredential
from aries_cloudagent.wallet.basic import BasicWallet
from aries_cloudagent.issuer.pds import PDSIssuer
from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from ...issuer.tests.test_pds import create_test_credential
from aries_cloudagent.messaging.util import time_now
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.wallet.base import BaseWallet
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.pdstorage_thcf.routes import pds_activate
from aries_cloudagent.config.pdstorage import personal_data_storage_config
from aries_cloudagent.pdstorage_thcf.base import BasePDS
from aries_cloudagent.pdstorage_thcf.local import LocalPDS
from aries_cloudagent.pdstorage_thcf.models.saved_personal_storage import (
    SavedPDS,
)

presentation_request = {
    "schema_base_dri": "12345",
    "requested_attributes": ["first_name"],
}

requested_credentials = {"credential_id": "12345"}

presentation_example = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
    ],
    "type": ["VerifiablePresentation"],
    "verifiableCredential": [{}],
    "proof": {},
}


class TestPDSHolder(AsyncTestCase):
    async def setUp(self):
        self.context: InjectionContext = InjectionContext()
        storage = BasicStorage()
        self.wallet = BasicWallet()
        await self.wallet.create_public_did()
        public_did = await self.wallet.get_public_did()
        assert public_did != None
        self.holder = PDSHolder(self.wallet, storage, self.context)
        issuer = PDSIssuer(self.wallet)

        self.context.injector.bind_instance(BaseWallet, self.wallet)
        self.context.injector.bind_instance(BaseStorage, storage)

        self.context.settings.set_value(
            "personal_storage_registered_types",
            {"local": "aries_cloudagent.pdstorage_thcf.local.LocalPDS"},
        )

        pds = LocalPDS()
        self.context.injector.bind_instance(BasePDS, pds)
        new_storage = SavedPDS(state=SavedPDS.ACTIVE)
        await new_storage.save(self.context)

        self.credential = await create_test_credential(issuer)
        self.cred_id = await self.holder.store_credential({}, self.credential, {})
        requested_credentials["credential_id"] = self.cred_id

    async def test_retrieve_records_are_the_same(self):
        cred_holder = await self.holder.get_credential(self.cred_id)
        assert isinstance(cred_holder, str)
        cred_holder_json = json.loads(cred_holder)
        assert cred_holder_json == self.credential

    async def test_store_credential_retrieve_and_delete(self):
        cred = await self.holder.get_credential(self.cred_id)
        cred_serialized = json.loads(cred)
        assert cred_serialized == self.credential

        # await self.holder.delete_credential(self.cred_id)
        # with self.assertRaises(HolderError):
        #     cred = await self.holder.get_credential(self.cred_id)
        # with self.assertRaises(HolderError):
        #     cred = await self.holder.delete_credential(self.cred_id)

    async def test_invalid_parameters_getters(self):
        with self.assertRaises(HolderError):
            cred = await self.holder.get_credential("12")

        # with self.assertRaises(HolderError):
        #     await self.holder.delete_credential("34")

    async def test_invalid_parameters_create_pres(self):
        schema_with_credential_ids = requested_credentials.copy()

        with self.assertRaises(HolderError):
            await self.holder.create_presentation(
                {}, schema_with_credential_ids, {}, {}
            )
        with self.assertRaises(HolderError):
            await self.holder.create_presentation(presentation_request, {}, {}, {})

    async def test_create_presentation(self):
        cred = requested_credentials.copy()
        presentation = await self.holder.create_presentation(
            presentation_request, cred, {}, {}
        )
        presentation = json.loads(presentation, object_pairs_hook=OrderedDict)
        assert await verify_proof(self.wallet, presentation) == True
        assert isinstance(presentation["id"], str)
        assert presentation["id"].startswith("urn:uuid:")
        assert presentation["context"] == presentation_example["@context"]
        assert len(presentation["context"]) == 2

    async def test_create_presentation_invalid_parameters_passed(self):
        with self.assertRaises(HolderError):
            request = presentation_request.copy()
            request.pop("requested_attributes")
            await self.holder.create_presentation(
                request, requested_credentials, {}, {}
            )
