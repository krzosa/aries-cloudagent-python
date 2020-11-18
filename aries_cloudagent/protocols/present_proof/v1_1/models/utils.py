from aries_cloudagent.protocols.present_proof.v1_1.models.presentation_exchange import (
    THCFPresentationExchange,
)
from aries_cloudagent.storage.error import StorageError, StorageNotFoundError


async def retrieve_exchange(context, record_id, exception):
    try:
        exchange_record: THCFPresentationExchange = (
            await THCFPresentationExchange.retrieve_by_id(context, record_id)
        )
    except StorageNotFoundError as err:
        raise exception(
            reason=f"Couldnt find exchange_record through this id {record_id}"
        )
    except StorageError as err:
        raise exception(reason=err.roll_up)

    return exchange_record


async def retrieve_exchange_by_thread(context, connection_id, thread_id, exception):
    try:
        exchange_record: THCFPresentationExchange = (
            await THCFPresentationExchange.retrieve_by_connection_and_thread(
                context, connection_id, thread_id
            )
        )
    except StorageNotFoundError as err:
        raise exception(
            f"""Couldnt find exchange_record through this: 
                connection id: {connection_id}
                thread id: {thread_id}"""
        )
    except StorageError as err:
        raise exception(err.roll_up)

    return exchange_record


def validate_exchange_state(
    presentation_exchange, required_state, required_role, exception
):
    if presentation_exchange.state != required_state:
        raise exception(
            f"""Invalid exchange state, should be {required_state}
        currently is {presentation_exchange.state}"""
        )
    if presentation_exchange.role != required_role:
        raise exception(
            f"""Invalid exchange role, should be {required_role}
        currently is {presentation_exchange.role}"""
        )
