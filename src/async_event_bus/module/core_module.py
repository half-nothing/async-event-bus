from asyncio import get_event_loop, new_event_loop, run_coroutine_threadsafe, set_event_loop
from typing import Awaitable, Callable, TypeAlias, TypeVar

from loguru import logger

from .base_module import BaseModule
from .. import AbstractEvent
from ..event import EventType, EventInstance, EventCallbackContainer, EventContext

C = TypeVar("C", bound=EventContext)
R = TypeVar("R")
Callback: TypeAlias = Callable[[C], R | Awaitable[R]]


class CoreModule(BaseModule[C, R]):
    """Provides subscribe, unsubscribe, and emit operations for the event bus."""

    def __init__(
        self,
        max_concurrent_tasks: int = 16,
        raise_exception: bool = False,
        context_class: type[C] = EventContext,
    ) -> None:
        """Initialize the core module.

        Args:
            max_concurrent_tasks:   Semaphore limit for concurrent async callbacks.
                                    Higher values increase throughput but may overwhelm the event loop or external resources.
            raise_exception:        If ``True``, the first exception inside a callback is re‑raised immediately.
                                    If ``False``, exceptions are collected and raised together
                                    as a ``MultipleError`` after all callbacks have run.
            context_class:          Subclass of ``EventContext`` used to construct the context object on every emit.
                                    Allows applications to pass custom context fields.
        """
        super().__init__(max_concurrent_tasks, raise_exception, context_class)
        # Lazy dict avoids pre‑allocating containers for events that never get subscribers.
        self._subscribers: dict[EventType, EventCallbackContainer[C, R]] = {}

    def on(
        self, event: EventType, *, weight: int = 1
    ) -> Callable[[Callback[C, R]], Callback[C, R]]:
        """Decorator that registers a callback for *event*.

        The decorator pattern is used because it allows event handlers to be
        defined directly below the event type they react to,
        which makes the subscription relationship visible at a glance.

        Args:
            event:  The event to subscribe to. Can be a string, an ``EnumEvent`` member, or a subclass of ``AbstractEvent``.
            weight: Higher‑weight callbacks are executed earlier.

        Returns:
            A decorator that, when applied to a callable, registers it and returns the callable unchanged.
        """

        def decorator(func: Callback[C, R]) -> Callback[C, R]:
            self.subscribe(event, func, weight=weight)
            logger.debug(f"{func.__name__} has subscribed to {event}, weight={weight}")
            return func

        return decorator

    def subscribe(
        self, event: EventType, callback: Callback[C, R], *, weight: int = 1
    ) -> None:
        """Register *callback* to be invoked when *event* is emitted.

        This is the programmatic equivalent of the :meth:`on` decorator.

        Args:
            event:      The event to subscribe to.
            callback:   A synchronous or asynchronous callable that accepts an ``EventContext`` (or a subclass).
            weight:     Execution priority – higher weights run first among synchronous callbacks.
        """
        if event not in self._subscribers:
            self._subscribers[event] = EventCallbackContainer()
        self._subscribers[event].add_callback(callback, weight)

    def unsubscribe(self, event: EventType, callback: Callback[C, R]) -> None:
        """Remove a previously registered *callback* for *event*.

        Removal is idempotent; if the callback is not found, nothing happens.

        Args:
            event:      The event to unsubscribe from.
            callback:   The exact callable that was originally registered.
        """
        if event in self._subscribers:
            self._subscribers[event].remove_callback(callback)

    async def before_emit(self, ctx: C) -> bool:
        """Continue the cooperative before_emit chain.

        Delegates to the next module in the MRO
        so that filters and injectors have a chance to inspect
        or modify the context before handlers are called.

        Args:
            ctx: The event context about to be dispatched.

        Returns:
            ``True`` if the event should be propagated, ``False`` otherwise.
        """
        return await super().before_emit(ctx)

    async def emit(self, event: EventInstance, *args, **kwargs) -> None:
        """Emit an event asynchronously.

        Constructs a context, runs the ``before_emit``, and then executes all registered callbacks.

        Execution order among callbacks:

        - Synchronous callbacks run first, in descending weight order.
        - Asynchronous callbacks are then scheduled concurrently via ``asyncio.gather``;
          their relative weights are irrelevant at that point.

        Args:
            event: The event to emit.
        """
        ctx = self._context_class(event=event, args=list(args), kwargs=kwargs)
        if not await self.before_emit(ctx):
            return

        if isinstance(event, AbstractEvent):
            event = type(event)

        if event not in self._subscribers:
            return

        await self._execute_callback(self._subscribers[event], ctx)

    def emit_sync(self, event: EventInstance, *args, **kwargs) -> None:
        """Blocking convenience wrapper around `emit`.

        Handles three event‑loop scenarios so that synchronous code can safely trigger the asynchronous emit path:

        1. A running loop exists → schedule via ``run_coroutine_threadsafe`` and block on the future.
        2. A loop exists but is not running → run the coroutine on that loop.
        3. No loop exists → create a temporary loop, execute, and tear it down.

        Args:
            event: The event to emit.
        """
        try:
            loop = get_event_loop()
            if loop and loop.is_running():
                # Running loop — must not call run_until_complete;
                # schedule thread‑safely to avoid deadlocks.
                future = run_coroutine_threadsafe(
                    self.emit(event, *args, **kwargs), loop
                )
                future.result()
            else:
                # Loop exists but isn't running — safe to block.
                loop.run_until_complete(self.emit(event, *args, **kwargs))
        except RuntimeError:
            # No event loop in this thread — create a temporary one.
            loop = new_event_loop()
            set_event_loop(loop)
            try:
                loop.run_until_complete(self.emit(event, *args, **kwargs))
            finally:
                loop.close()
                set_event_loop(None)

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._subscribers.clear()
