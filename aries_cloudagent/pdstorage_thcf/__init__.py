from ..config.injection_context import InjectionContext
from .models.saved_personal_storage import SavedPersonalStorage
from .base import BasePersonalDataStorage
from aries_cloudagent.storage.error import StorageNotFoundError


async def setup(context: InjectionContext):
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

    # TODO make sure an active storage exists
    try:
        active_storage = await SavedPersonalStorage.retrieve_active(context)
    except StorageNotFoundError:
        default_storage = SavedPersonalStorage(state=SavedPersonalStorage.ACTIVE)

        await default_storage.save(context)

