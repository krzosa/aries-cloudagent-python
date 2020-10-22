from .injection_context import InjectionContext
from ..pdstorage_thcf.models.saved_personal_storage import SavedPersonalStorage
from ..pdstorage_thcf.base import BasePersonalDataStorage
from ..storage.error import StorageNotFoundError
from ..core.protocol_registry import ProtocolRegistry


async def personal_data_storage_config(context: InjectionContext):
    """
    When package gets loaded by acapy, create singleton instances for 
    all saved personal storages
    """
    all_saved_storages = await SavedPersonalStorage.query(context)
    print("SETUP !", all_saved_storages)
    for saved_storage in all_saved_storages:
        pds: BasePersonalDataStorage = await context.inject(
            BasePersonalDataStorage,
            {"personal_storage_type": saved_storage.get_pds_name()},
        )
        pds.settings = saved_storage.settings

    if all_saved_storages == []:
        default_storage = SavedPersonalStorage(state=SavedPersonalStorage.ACTIVE)

        await default_storage.save(context)
        print("CREATED DEFAULT STORAGE")

    # make sure an active storage exists
    try:
        active_storage = await SavedPersonalStorage.retrieve_active(context)
    except StorageNotFoundError:
        default_storage = SavedPersonalStorage(state=SavedPersonalStorage.ACTIVE)

        await default_storage.save(context)

