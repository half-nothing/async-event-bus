from abc import ABC, abstractmethod

from ..event import EventType


class BaseModule(ABC):
    """
    Event module base class
    """

    @abstractmethod
    async def resolve(self, event: EventType, args, kwargs) -> bool:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError
