from aries_cloudagent.messaging.base_handler import HandlerException


from aries_cloudagent.pdstorage_thcf.models.saved_personal_storage import SavedPDS
from aries_cloudagent.config.settings import Settings
from aries_cloudagent.config.default_context import DefaultContextBuilder


def run_standalone_async(name, func):
    if name == "__main__":
        import asyncio

        loop = asyncio.get_event_loop()
        loop.run_until_complete(func())
        loop.close()


async def build_standalone_context():
    settings = Settings(
        {
            "personal_storage_registered_types": {
                "local": "aries_cloudagent.pdstorage_thcf.local.LocalPDS",
                "data_vault": "aries_cloudagent.pdstorage_thcf.data_vault.DataVault",
                "own_your_data": "aries_cloudagent.pdstorage_thcf.own_your_data.OwnYourDataVault",
            }
        }
    )
    context_builder = DefaultContextBuilder(settings)
    context = await context_builder.build()

    return context


async def build_context(pds_type="own_your_data", connection_record={}):
    context = await build_standalone_context()
    default_storage = SavedPDS(type=pds_type, state=SavedPDS.ACTIVE)
    await default_storage.save(context)
    from aries_cloudagent.pdstorage_thcf.api import pds_get_active

    pds = await pds_get_active(context)

    if pds_type == "own_your_data":

        pds.settings["client_id"] = "-s2bdkM_cv7KYDF5xg_Lj6vil1ZJaLQJ79duOW7J9g4"
        pds.settings["client_secret"] = "s_dR8dzbVES_vvc1-nyb1O_cuzyCz2_bRd3Lr12s4ug"
        pds.settings["api_url"] = "https://data-vault.eu"

    return context


def build_request_stub(context, body={}, *, match_info={}):
    async def outbound_handler(model_to_send, connection_id):
        msg = (
            "outbound_handler model:"
            + str(model_to_send)
            + " connection_id: "
            + connection_id
        )
        # print(msg)

    class Stub:
        def __init__(self, _context, _body):
            self.app = {
                "request_context": _context,
                "outbound_message_router": outbound_handler,
            }
            self._body = _body
            self.send_models = []
            self.match_info = match_info

        async def json(self):
            return self._body

    stub = Stub(context, body)
    return stub


def debug_handler(log, context, MessageClass):
    """
    Checks if MessageClass is of correct type, checks if connection is intact
    And logs info about Handler, just a utility procedure

    Args:
        log - logging procedure
    """
    log("%s called with context %s", MessageClass.__name__, context)
    assert isinstance(context.message, MessageClass)
    log(
        "Received %s: %s",
        MessageClass.__name__,
        context.message.serialize(as_string=True),
    )
    if not context.connection_ready:
        raise HandlerException("No connection established for " + MessageClass.__name__)