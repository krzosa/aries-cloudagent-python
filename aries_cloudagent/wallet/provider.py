"""Default wallet provider classes."""

import logging

from ..config.base import BaseProvider, BaseInjector, BaseSettings
from ..utils.classloader import ClassLoader

LOGGER = logging.getLogger(__name__)


class WalletProvider(BaseProvider):
    """Provider for the default configurable wallet classes."""

    def __init__(self):
        self.cached_wallets = {}

    WALLET_TYPES = {
        "basic": "aries_cloudagent.wallet.basic.BasicWallet",
        "indy": "aries_cloudagent.wallet.indy.IndyWallet",
        "http": "aries_cloudagent.wallet.http.HttpWallet",
    }

    async def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create and open the wallet instance."""
        # print("Provide Wallet")
        # (Krzosa)
        # wallet_type = settings.get_value("wallet.type", default="basic").lower()
        # wallet_class = self.WALLET_TYPES.get(wallet_type, wallet_type)
        wallet_type = settings.get_value("wallet.type", default="basic").lower()
        # print("wallet type to inject: ", wallet_type)

        if wallet_type in self.cached_wallets:
            # print("Cached Wallets ", self.cached_wallets)
            return self.cached_wallets[wallet_type]

        wallet_class = self.WALLET_TYPES.get(wallet_type, wallet_type)
        print("Creating a wallet: ", wallet_type, wallet_class)

        LOGGER.info("Opening wallet type: %s", wallet_type)

        wallet_cfg = {}
        if "wallet.key" in settings:
            wallet_cfg["key"] = settings["wallet.key"]
        if "wallet.rekey" in settings:
            wallet_cfg["rekey"] = settings["wallet.rekey"]
        if "wallet.name" in settings:
            wallet_cfg["name"] = settings["wallet.name"]
        if "wallet.storage_type" in settings:
            wallet_cfg["storage_type"] = settings["wallet.storage_type"]
        # storage.config and storage.creds are required if using postgres plugin
        if "wallet.storage_config" in settings:
            wallet_cfg["storage_config"] = settings["wallet.storage_config"]
        if "wallet.storage_creds" in settings:
            wallet_cfg["storage_creds"] = settings["wallet.storage_creds"]
        wallet = ClassLoader.load_class(wallet_class)(wallet_cfg)
        await wallet.open()

        if "wallet.rekey" in settings:
            await wallet.close()
            await wallet.open()
            LOGGER.info(
                "Rotated wallet %s master encryption key", wallet_cfg.get("name", "")
            )

        self.cached_wallets[wallet_type] = wallet

        return wallet
