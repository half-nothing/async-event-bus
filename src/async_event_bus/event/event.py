from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from time import time


class EnumEvent(Enum):
    """Base class for enum-style events. Inherit and define members with auto()."""
    pass


class AbstractEvent(ABC):
    """Base class for class-style events with custom fields and logic."""
    pass


# EventType covers all supported event key forms
EventType = EnumEvent | type[AbstractEvent] | str


@dataclass
class EventContext:
    """
    Carrier object passed to every callback, filter, and injector.

    Subclass this to attach domain-specific fields (e.g. authenticated user,
    request metadata). Pass the subclass as context_class to EventBus.
    """
    event: EventType
    timestamp: float = field(default_factory=time)  # Unix timestamp set at emit time
    args: list = field(default_factory=list)
    kwargs: dict = field(default_factory=dict)
