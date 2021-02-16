from .injection_context import InjectionContext
from ..pdstorage_thcf.models.saved_personal_storage import SavedPDS
from ..pdstorage_thcf.base import BasePDS
from ..storage.error import StorageNotFoundError


async def personal_data_storage_config(context: InjectionContext):
    """
    When package gets loaded by acapy, create singleton instances for
    all saved personal storages
    """
    all_saved_storages = await SavedPDS.query(context)
    print("SETUP !", all_saved_storages)
    for saved_storage in all_saved_storages:
        pds: BasePDS = await context.inject(
            BasePDS,
            {"personal_storage_type": saved_storage.get_pds_full_name()},
        )
        pds.settings = saved_storage.settings

    if all_saved_storages == []:
        default_storage = SavedPDS(state=SavedPDS.ACTIVE)

        await default_storage.save(context)
        print("CREATED DEFAULT STORAGE")

    # make sure an active storage exists
    try:
        await SavedPDS.retrieve_active(context)
    except StorageNotFoundError:
        default_storage = SavedPDS(state=SavedPDS.ACTIVE)

        await default_storage.save(context)
