from abc import ABC
from enum import Enum
from typing import Type, Union


class EnumEvent(Enum):
    pass


class AbstractEvent(ABC):
    pass


EventType: Type = Union[EnumEvent, Type[AbstractEvent], str]
