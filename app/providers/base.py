from abc import ABC, abstractmethod


class BaseProvider(ABC):
    @abstractmethod
    async def send(self, notification) -> bool:
        """Send the notification. Returns True on success, raises on failure."""
        ...
