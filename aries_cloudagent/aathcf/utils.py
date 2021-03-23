from aries_cloudagent.messaging.base_handler import HandlerException


def run_repl_async(name, func):
    if name == "__main__":
        import asyncio

        loop = asyncio.get_event_loop()
        loop.run_until_complete(func())
        loop.close()


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