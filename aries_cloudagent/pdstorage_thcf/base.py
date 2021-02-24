from abc import ABC, abstractmethod


class BasePDS(ABC):
    def __init__(self):
        self.settings = {}
        self.preview_settings = {}

    @abstractmethod
    async def save(self, record, oca_schema_dri: str = None) -> str:
        """Returns: saved data id, (should maybe return None on key not found?)."""

    @abstractmethod
    async def load(self, id: str) -> str:
        """Returns: data represented by id."""

    @abstractmethod
    async def query_by_oca_schema_dri(self, oca_schema_dri: str = None) -> str:
        """Load all records with specified oca_schema_dri."""

    @abstractmethod
    async def ping(self) -> [bool, str]:
        """
        Returns: true if we connected at all, false if service is not responding.
                 and additional info about the failure

        connected, exception = await personal_storage.ping()
        """

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        return "<{}>".format(self.__class__.__name__)
