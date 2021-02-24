import logging

from ..config.base import BaseProvider, BaseInjector, BaseSettings
from ..utils.classloader import ClassLoader

LOGGER = logging.getLogger(__name__)


class PersonalDataStorageProvider(BaseProvider):
    def __init__(self):
        self.cached_instances = {}

    async def provide(self, settings: BaseSettings, injector: BaseInjector):
        storage_type = settings.get("personal_storage_type")
        registered_types = settings.get("personal_storage_registered_types")

        # error checking code
        LOGGER.info("PersonalDataStorage type %s", storage_type)
        assert storage_type[0] is not None, "active personal_storage_type, is None"
        if type(storage_type) == list:
            storage_type = tuple(storage_type)
        assert isinstance(storage_type, tuple), f"storage_type is not a tuple, type: "
        f"{type(storage_type)}, storage_type: {storage_type}"

        # create a singleton object if there is no object of specified name tuple
        if storage_type not in self.cached_instances:
            storage_class = registered_types.get(storage_type[0])
            assert storage_class is not None, "Storage type / class is not registered"

            public_data_storage = ClassLoader.load_class(storage_class)
            self.cached_instances[storage_type] = public_data_storage()

            LOGGER.info(
                f"""CREATE storage_type: {storage_type}
                    self.cached_instances: {self.cached_instances}
                    """
            )

        return self.cached_instances[storage_type]
