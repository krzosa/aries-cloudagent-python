from ..aathcf.utils import run_standalone_async
from typing import Sequence
from .base import BaseWallet, DIDInfo, KeyInfo
from .libkel_utils import Controller
import tempfile
import base64


class KeriWallet(BaseWallet):
    WALLET_TYPE = "keri"

    def __init__(self, config: dict = {}):
        super().__init__(config)
        keri_address = config.get("keri_address")
        self._name = config.get("name")
        self._open = False
        self._keys = {}

        self.temp_dir = tempfile.TemporaryDirectory()
        self.provider_path = "./adr_db"

        self.controller = Controller.new(
            self.temp_dir.name, keri_address, self.provider_path
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self.WALLET_TYPE

    @property
    def handle(self):
        return self.controller

    @property
    def created(self) -> bool:
        return True

    @property
    def opened(self) -> bool:
        return self._open

    def prefix(self):
        return self.controller.get_prefix()

    def did_doc(self):
        return self.controller.get_did_doc(self.prefix())

    async def open(self):
        self.controller.run()
        # print("\nBobs prefix: " + self.prefix() + "\n")
        # ddoc = self.did_doc()
        # print(ddoc)
        self._open = True

    async def close(self):
        pass

    async def create_signing_key(
        self, seed: str = None, metadata: dict = None
    ) -> KeyInfo:
        self.controller.add_identifier(self.temp_dir.name)
        get_id = self.controller.current_identifiers()[-1]
        result = KeyInfo(get_id, {})
        return result

    async def get_signing_key(self, verkey: str) -> KeyInfo:
        pass

    async def replace_signing_key_metadata(self, verkey: str, metadata: dict):
        pass

    async def rotate_did_keypair_start(self, did: str, next_seed: str = None) -> str:
        pass

    async def rotate_did_keypair_apply(self, did: str) -> None:
        pass

    async def create_local_did(
        self, seed: str = None, did: str = None, metadata: dict = None
    ) -> DIDInfo:
        pass

    async def get_local_dids(self) -> Sequence[DIDInfo]:
        pass

    async def get_local_did(self, did: str) -> DIDInfo:
        pass

    async def get_local_did_for_verkey(self, verkey: str) -> DIDInfo:
        pass

    async def replace_local_did_metadata(self, did: str, metadata: dict):
        pass

    async def sign_message(self, message: bytes, from_verkey: str) -> bytes:
        signature: list = self.controller.sign_by(from_verkey, message)
        result = base64.urlsafe_b64encode(bytes(signature)).decode("utf-8")

        return result

    async def verify_message(
        self, message: bytes, signature: bytes, from_verkey: str
    ) -> bool:
        result = self.controller.verify(from_verkey, message, signature)
        return result

    async def pack_message(
        self, message: str, to_verkeys: Sequence[str], from_verkey: str = None
    ) -> bytes:
        pass

    async def unpack_message(self, enc_message: bytes) -> (str, str, str):
        pass

    def __repr__(self) -> str:
        """Get a human readable string."""
        return "<{}(opened={})>".format(self.__class__.__name__, self.opened)


async def test_keri_wallet():
    wallet = KeriWallet({"keri_address": "localhost:8498"})
    await wallet.open()
    key = await wallet.create_signing_key()

    msg = "message"
    sig = await wallet.sign_message(msg, key.verkey)
    print("Signature type: ", type(sig))
    verify = await wallet.verify_message(msg, sig, key.verkey)
    print(verify)


run_standalone_async(__name__, test_keri_wallet)