from abc import ABC
from enum import Enum
from typing import TypeAlias


# Enum event
class EnumEvent(Enum):
    pass


# Event class there is more room for customization
class AbstractEvent(ABC):
    pass


EventType: TypeAlias = EnumEvent | type[AbstractEvent] | str
