from typing import Awaitable, Callable, TypeAlias, TypeVar

from .base_module import BaseModule
from .module_exceptions import ExceptionStrategy
from ..event import EventContext, EventType

C = TypeVar("C", bound=EventContext)
Callback: TypeAlias = Callable[[C], None | Awaitable[None]]


class InjectModule(BaseModule[C, None]):
    """Middleware module that mutates ``EventContext`` before subscribers run.

    Injectors receive *ctx* and modify it in-place; return values are discarded.
    """

    def __init__(
            self,
            max_concurrent_tasks: int = 16,
            exception_strategy: ExceptionStrategy = ExceptionStrategy.COLLECT,
            context_class: type[C] = ...,
    ) -> None: ...

    def clear(self) -> None:
        """Remove all injectors, both global and per-event."""
        ...

    async def before_emit(self, event: EventType, ctx: C) -> bool:
        """Apply global injectors first, then event-specific ones."""
        ...

    def global_event_inject(self, weight: int = 1) -> Callable[[Callback[C]], Callback[C]]:
        """Decorator that registers a global injector."""
        ...

    def add_global_inject(self, callback: Callback[C], weight: int = 1) -> None:
        """Programmatically register a global injector."""
        ...

    def remove_global_inject(self, callback: Callback[C]) -> None:
        """Remove a previously registered global injector."""
        ...

    def event_inject(self, event: EventType, weight: int = 1) -> Callable[[Callback[C]], Callback[C]]:
        """Decorator that registers an injector for a specific *event*."""
        ...

    def add_inject(self, event: EventType, callback: Callback[C], weight: int = 1) -> None:
        """Programmatically register a per-event injector."""
        ...

    def remove_inject(self, event: EventType, callback: Callback[C]) -> None:
        """Remove a previously registered per-event injector."""
        ...
