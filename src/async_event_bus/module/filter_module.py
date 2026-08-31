from typing import Awaitable, Callable, TypeAlias, TypeVar

from loguru import logger

from .base_module import BaseModule
from ..event import AbstractEvent, EventType, EventCallbackContainer, EventContext

C = TypeVar("C", bound=EventContext)
Callback: TypeAlias = Callable[[C], bool | Awaitable[bool]]


class FilterModule(BaseModule[C, bool]):
    """Middleware module that gates event propagation.

    Filter callbacks return ``bool``: ``True`` continues propagation, ``False`` stops the event immediately.
    Global filters run before event‑specific ones.
    The first ``False`` short‑circuits the entire chain, so that remaining filters and all subscribers are skipped.
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 16,
        raise_exception: bool = False,
        context_class: type[C] = EventContext,
    ) -> None:
        """Initialize the filter module.

        Args:
            max_concurrent_tasks:   Maximum number of async filters that may run concurrently.
            raise_exception:        If ``True``, re‑raise filter exceptions immediately.
            context_class:          ``EventContext`` subclass to use.
        """
        super().__init__(max_concurrent_tasks, raise_exception, context_class)
        # Separate containers for global and per‑event filters keep the
        # execution paths independent,
        # so that global rules cannot be accidentally bypassed by event‑specific
        # registrations and vice‑versa.
        self._filters: dict[EventType, EventCallbackContainer[C, bool]] = {}
        self._global_filters = EventCallbackContainer[C, bool]()

    def clear(self) -> None:
        """Remove all filters, both global and per‑event."""
        self._filters.clear()
        self._global_filters.clear()

    async def before_emit(self, event: EventType, ctx: C) -> bool:
        """Run global filters first, then event‑specific filters.

        Short‑circuits on the first ``False``, so that later filters and subscribers are never called.
        Delegates to the next module in the MRO if all filters pass.

        Args:
            event:  The event that is about to be emitted.
            ctx:    The event context about to be dispatched.

        Returns:
            ``True`` if the event may proceed, ``False`` if propagation was stopped.
        """
        if not await self._apply_global_filter(ctx):
            return False
        if not await self._apply_filter(event, ctx):
            return False
        return await super().before_emit(event, ctx)

    async def _apply_filter(self, event: EventType, ctx: C) -> bool:
        """Execute event‑specific filters registered for *ctx.event*.

        Event‑specific filters honor ``expand_args``/``expand_kwargs`` so that
        they can receive the event payload directly instead of ``ctx``.
        """
        if event not in self._filters:
            return True
        return await self._execute_callback(
            self._filters[event], ctx, lambda x: x,
            expand_args=ctx.expand_args, expand_kwargs=ctx.expand_kwargs,
        )

    async def _apply_global_filter(self, ctx: C) -> bool:
        """Execute all global filters against *ctx*.

        Global filters are cross‑cutting logic and always receive ``ctx``;
        they are intentionally not affected by ``expand_args``/``expand_kwargs``.
        """
        return await self._execute_callback(self._global_filters, ctx, lambda x: x)

    def global_event_filter(
        self, weight: int = 1
    ) -> Callable[[Callback[C]], Callback[C]]:
        """Decorator that registers a global filter.

        Global filters apply to every event before per‑event filters,
        so that cross‑cutting concerns can be enforced uniformly.

        Args:
            weight: Higher‑weight filters execute first.

        Returns:
            A decorator that registers the function and returns it unchanged.
        """

        def decorator(func: Callback[C]) -> Callback[C]:
            self.add_global_filter(func, weight)
            return func

        return decorator

    def add_global_filter(self, callback: Callback[C], weight: int = 1) -> None:
        """Programmatically register a global filter.

        Args:
            callback:   A sync or async callable that accepts an event context and returns ``bool``.
            weight:     Execution priority.
        """
        self._global_filters.add_callback(callback, weight)
        logger.debug(f"Global filter {callback.__name__} has been added, weight={weight}")

    def remove_global_filter(self, callback: Callback[C]) -> None:
        """Remove a previously registered global filter. """
        self._global_filters.remove_callback(callback)

    def event_filter(
        self, event: EventType, weight: int = 1
    ) -> Callable[[Callback[C]], Callback[C]]:
        """Decorator that registers a filter for a specific *event*.

        Per‑event filters run after global filters have passed,
        so that they can add additional restrictions that only apply to a particular event type.

        Args:
            event:  The event type to filter.
            weight: Higher‑weight filters execute first.

        Returns:
            A decorator that registers the function and returns it unchanged.
        """

        def decorator(func: Callback[C]) -> Callback[C]:
            self.add_filter(event, func, weight)
            return func

        return decorator

    def add_filter(
        self, event: EventType, callback: Callback[C], weight: int = 1
    ) -> None:
        """Programmatically register a per‑event filter.

        Args:
            event:      The event type to filter.
            callback:   A sync or async callable that accepts an event context and returns ``bool``.
            weight:     Execution priority.
        """
        if isinstance(event, AbstractEvent):
            raise TypeError(
                f"Expected an event type, got an instance of {type(event).__name__}. "
                f"Use the event class, not an instance."
            )
        if event not in self._filters:
            self._filters[event] = EventCallbackContainer[C, bool]()
        self._filters[event].add_callback(callback, weight)
        logger.debug(
            f"Event filter {callback.__name__} has been added to event {event}, weight={weight}"
        )

    def remove_filter(self, event: EventType, callback: Callback[C]) -> None:
        """Remove a previously registered per‑event filter. """
        if event in self._filters:
            self._filters[event].remove_callback(callback)
