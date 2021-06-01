from aries_cloudagent.storage.error import StorageError, StorageNotFoundError
from aiohttp import web
from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.protocols.issue_credential.v1_1.models.credential_exchange import (
    CredentialExchangeRecord,
)
import logging

LOGGER = logging.getLogger(__name__)


async def retrieve_connection(context, connection_id):
    """
    Retrieve ConnectionRecord and handle exceptions.

    Raises AioHTTP exceptions so only should be used in routes.py.
    """
    try:
        connection_record: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound(
            reason="Couldnt find a connection_record through the connection_id"
        )
    except StorageError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)
    if not connection_record.is_ready:
        raise web.HTTPRequestTimeout(reason=f"Connection {connection_id} not ready")

    return connection_record


async def retrieve_credential_exchange(context, credential_exchange_id):
    """
    Retrieve Credential Exchange Record and handle exceptions.

    Raises AioHTTP exceptions so only should be used in routes.py.
    """
    try:
        exchange_record: CredentialExchangeRecord = (
            await CredentialExchangeRecord.retrieve_by_id(
                context, credential_exchange_id
            )
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound(
            reason="Couldnt find a exchange_record through the credential_exchange_id"
        )
    except StorageError as err:
        raise web.HTTPInternalServerError(reason=err.roll_up)

    return exchange_record
