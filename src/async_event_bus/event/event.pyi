from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Generic, TypeAlias, TypeVar

E = TypeVar("E", bound="EventInstance")


class EnumEvent(Enum):  # type: ignore[misc]  # user-defined base; members are added by subclasses
    """Base class for enum-style events. Inherit and define members with auto()."""
    pass


class AbstractEvent(ABC):
    """Base class for class-style events with custom fields and logic."""
    pass


# EventType covers all supported event key forms, including AbstractEvent instances
EventType: TypeAlias = EnumEvent | type[AbstractEvent] | str
EventInstance: TypeAlias = EnumEvent | AbstractEvent | str


@dataclass
class EventContext(Generic[E]):
    """Carrier object passed to every callback, filter, and injector.

    Subclass this to attach domain-specific fields (e.g. authenticated user,
    request metadata) and pass the subclass as ``context_class`` to EventBus.
    """
    event: E
    timestamp: float = field(default_factory=time)  # Unix timestamp set at emit time
    args: list = field(default_factory=list)
    kwargs: dict = field(default_factory=dict)
    # Scheduling options set by emit(); init=False keeps the constructor
    # signature stable for EventContext subclasses.
    expand_args: bool = field(default=False, init=False)
    expand_kwargs: bool = field(default=False, init=False)
