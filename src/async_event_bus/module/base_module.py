from abc import ABC, abstractmethod

from ..event import EventType


class BaseModule(ABC):
    """
    EventBus 模块基类
    """

    @abstractmethod
    async def resolve(self, event: EventType, args, kwargs) -> bool:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError
