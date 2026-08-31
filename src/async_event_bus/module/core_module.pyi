from typing import Any, Awaitable, Callable, TypeAlias, TypeVar

from .base_module import BaseModule, EmitResult
from .module_exceptions import ExceptionStrategy
from ..event import EventContext, EventInstance, EventType

C = TypeVar("C", bound=EventContext)
R = TypeVar("R")
Callback: TypeAlias = Callable[[C], R | Awaitable[R]]


class CoreModule(BaseModule[C, R]):
    """Provides subscribe, unsubscribe, and emit operations for the event bus."""

    def __init__(
            self,
            max_concurrent_tasks: int = 16,
            exception_strategy: ExceptionStrategy = ExceptionStrategy.COLLECT,
            context_class: type[C] = ...,
    ) -> None: ...

    def on(self, event: EventType, *, weight: int = 1) -> Callable[[Callback[C, R]], Callback[C, R]]:
        """Decorator that registers a callback for *event*."""
        ...

    def subscribe(self, event: EventType, callback: Callback[C, R], *, weight: int = 1) -> None:
        """Register *callback* to be invoked when *event* is emitted."""
        ...

    def unsubscribe(self, event: EventType, callback: Callback[C, R]) -> None:
        """Remove a previously registered *callback* for *event*."""
        ...

    async def before_emit(self, event: EventType, ctx: C) -> bool:
        """Continue the cooperative before_emit chain."""
        ...

    async def emit(
            self,
            event: EventInstance,
            *args: Any,
            expand_args: bool = False,
            expand_kwargs: bool = False,
            **kwargs: Any,
    ) -> EmitResult[R] | None:
        """Emit an event asynchronously.

        Returns an ``EmitResult`` under ``ExceptionStrategy.RETURN`` (or
        ``None`` when the event was filtered out or had no subscribers),
        otherwise ``None``.
        """
        ...

    def emit_sync(
            self,
            event: EventInstance,
            *args: Any,
            expand_args: bool = False,
            expand_kwargs: bool = False,
            **kwargs: Any,
    ) -> EmitResult[R] | None:
        """Blocking convenience wrapper around :meth:`emit`."""
        ...

    def clear(self) -> None:
        """Remove all subscriptions."""
        ...
