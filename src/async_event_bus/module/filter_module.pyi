from typing import Awaitable, Callable, TypeAlias, TypeVar

from .base_module import BaseModule
from .module_exceptions import ExceptionStrategy
from ..event import EventContext, EventType

C = TypeVar("C", bound=EventContext)
Callback: TypeAlias = Callable[[C], bool | Awaitable[bool]]


class FilterModule(BaseModule[C, bool]):
    """Middleware module that gates event propagation.

    Filter callbacks return ``bool``: ``True`` continues propagation,
    ``False`` stops the event immediately.
    """

    def __init__(
            self,
            max_concurrent_tasks: int = 16,
            exception_strategy: ExceptionStrategy = ExceptionStrategy.COLLECT,
            context_class: type[C] = ...,
    ) -> None: ...

    def clear(self) -> None:
        """Remove all filters, both global and per-event."""
        ...

    async def before_emit(self, event: EventType, ctx: C) -> bool:
        """Run global filters first, then event-specific filters."""
        ...

    def global_event_filter(self, weight: int = 1) -> Callable[[Callback[C]], Callback[C]]:
        """Decorator that registers a global filter."""
        ...

    def add_global_filter(self, callback: Callback[C], weight: int = 1) -> None:
        """Programmatically register a global filter."""
        ...

    def remove_global_filter(self, callback: Callback[C]) -> None:
        """Remove a previously registered global filter."""
        ...

    def event_filter(self, event: EventType, weight: int = 1) -> Callable[[Callback[C]], Callback[C]]:
        """Decorator that registers a filter for a specific *event*."""
        ...

    def add_filter(self, event: EventType, callback: Callback[C], weight: int = 1) -> None:
        """Programmatically register a per-event filter."""
        ...

    def remove_filter(self, event: EventType, callback: Callback[C]) -> None:
        """Remove a previously registered per-event filter."""
        ...
