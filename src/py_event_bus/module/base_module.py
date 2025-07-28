from abc import ABC, abstractmethod
from typing import Union

from ..event import Event


class BaseModule(ABC):
    """
    EventBus 模块基类
    """

    @abstractmethod
    async def resolve(self, event: Union[Event, str], args, kwargs) -> bool:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError
