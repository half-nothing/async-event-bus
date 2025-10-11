from abc import ABC
from enum import Enum
from typing import Type, Union


# Enum event
class EnumEvent(Enum):
    pass


# Event class there is more room for customization
class AbstractEvent(ABC):
    pass


EventType: Type = Union[EnumEvent, Type[AbstractEvent], str]
