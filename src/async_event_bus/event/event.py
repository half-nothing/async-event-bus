from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Generic, TypeVar


class EnumEvent(Enum):
    """Base class for enum-style events. Inherit and define members with auto()."""
    pass


class AbstractEvent(ABC):
    """Base class for class-style events with custom fields and logic."""
    pass


# EventType covers all supported event key forms, including AbstractEvent instances
EventType = EnumEvent | type[AbstractEvent] | str
EventInstance = EnumEvent | AbstractEvent | str

E = TypeVar("E", bound=EventInstance)


@dataclass
class EventContext(Generic[E]):
    """
    Carrier object passed to every callback, filter, and injector.

    E is the event type, allowing callbacks to access ctx.event with the correct type:
        async def handler(ctx: EventContext[MessageCreateEvent]) -> None:
            print(ctx.event.message)  # typed as MessageCreateEvent

    Subclass this to attach domain-specific fields (e.g. authenticated user, request metadata).
    Pass the subclass as context_class to EventBus.
    """
    event: E
    timestamp: float = field(default_factory=time)  # Unix timestamp set at emit time
    args: list = field(default_factory=list)
    kwargs: dict = field(default_factory=dict)
    # Scheduling options set by emit(); they tell filters/injectors/subscribers
    # whether ctx.args / ctx.kwargs should be unpacked when invoking callbacks.
    # init=False keeps the constructor signature stable for EventContext subclasses.
    expand_args: bool = field(default=False, init=False)
    expand_kwargs: bool = field(default=False, init=False)
