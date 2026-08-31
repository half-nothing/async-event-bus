from typing import Awaitable, Callable, TypeAlias, TypeVar, cast

from loguru import logger

from .base_module import BaseModule
from .module_exceptions import ExceptionStrategy
from ..event import AbstractEvent, EventType, EventCallbackContainer, EventContext

C = TypeVar("C", bound=EventContext)
Callback: TypeAlias = Callable[[C], None | Awaitable[None]]


class InjectModule(BaseModule[C, None]):
    """Middleware module that mutates ``EventContext`` before subscribers run.

    Injectors receive *ctx* and modify it in‑place (e.g. attach an authenticated user, add a database session, resolve dependencies).
    Global injectors run before event‑specific ones so that shared setup is always applied first.
    If any injector raises an exception, ``before_emit`` returns ``False`` and the event is dropped,
    which prevents handlers from operating on incomplete context.

    The return type ``None`` reflects that injectors are side‑effect‑only;
    their return values are discarded by the executor.
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 16,
        exception_strategy: ExceptionStrategy = ExceptionStrategy.COLLECT,
        context_class: type[C] = cast(type[C], EventContext),
    ) -> None:
        """Initialize the inject module.

        Args:
            max_concurrent_tasks:   Maximum number of async injectors that may run concurrently.
                                    Limits pressure on shared resources.
            exception_strategy:     How injector exceptions are handled
                                    (see :class:`ExceptionStrategy`).
            context_class:          ``EventContext`` subclass to use.
        """
        super().__init__(max_concurrent_tasks, exception_strategy, context_class)
        # Separate containers keep global injectors isolated from per‑event ones,
        # so that mandatory setup (e.g. authentication) cannot be accidentally
        # skipped by an event‑specific registration.
        self._injects: dict[EventType, EventCallbackContainer[C, None]] = {}
        self._global_injects = EventCallbackContainer[C, None]()

    def clear(self) -> None:
        """Remove all injectors, both global and per‑event."""
        self._injects.clear()
        self._global_injects.clear()

    async def before_emit(self, event: EventType, ctx: C) -> bool:
        """Apply global injectors first, then event‑specific ones.

        All injectors run within a try/except block because a failed injector leaves the context in an untrustworthy state;
        returning ``False`` safely aborts the event rather than forwarding potentially invalid data to subscribers.

        Args:
            event:  The event that is about to be emitted.
            ctx:    The event context that will be mutated in‑place.

        Returns:
            ``True`` if all injectors succeeded,
            ``False`` if any injector raised an exception.
        """
        try:
            await self._apply_global_injects(ctx)
            await self._apply_event_injects(event, ctx)
        except Exception as e:
            # A failed injector means the context is incomplete — the event
            # must not proceed to handlers.
            logger.error(f"Inject failed: {e}")
            return False
        return await super().before_emit(event, ctx)

    async def _apply_event_injects(self, event: EventType, ctx: C) -> None:
        """Execute injectors registered for *ctx.event*.

        Event‑specific injectors honor ``expand_args``/``expand_kwargs`` so that
        they can receive the event payload directly instead of ``ctx``.
        """
        if event not in self._injects:
            return
        await self._execute_callback(
            self._injects[event], ctx,
            expand_args=ctx.expand_args, expand_kwargs=ctx.expand_kwargs,
        )

    async def _apply_global_injects(self, ctx: C) -> None:
        """Execute all global injectors against *ctx*.

        Global injectors are cross‑cutting logic and always receive ``ctx``;
        they are intentionally not affected by ``expand_args``/``expand_kwargs``.
        """
        await self._execute_callback(self._global_injects, ctx)

    def global_event_inject(
        self, weight: int = 1
    ) -> Callable[[Callback[C]], Callback[C]]:
        """Decorator that registers a global injector.

        Global injectors apply to every event before per‑event injectors,
        so that shared setup is always applied first.

        Args:
            weight: Higher‑weight injectors execute earlier.

        Returns:
            A decorator that registers the function and returns it unchanged.
        """

        def decorator(func: Callback[C]) -> Callback[C]:
            self.add_global_inject(func, weight)
            return func

        return decorator

    def add_global_inject(self, callback: Callback[C], weight: int = 1) -> None:
        """Programmatically register a global injector.

        Args:
            callback:   A sync or async callable that accepts an ``EventContext`` and returns ``None``.
            weight:     Execution priority.
        """
        self._global_injects.add_callback(callback, weight)
        logger.debug(
            f"Global inject {callback.__name__} has been added, weight={weight}"
        )

    def remove_global_inject(self, callback: Callback[C]) -> None:
        """Remove a previously registered global injector."""
        self._global_injects.remove_callback(callback)

    def event_inject(
        self, event: EventType, weight: int = 1
    ) -> Callable[[Callback[C]], Callback[C]]:
        """Decorator that registers an injector for a specific *event*.

        Per‑event injectors run after global injectors have succeeded,
        so that they can enrich the context with data that is only relevant to a particular event type.

        Args:
            event:  The event type to inject into.
            weight: Higher‑weight injectors execute earlier.

        Returns:
            A decorator that registers the function and returns it unchanged.
        """

        def decorator(func: Callback[C]) -> Callback[C]:
            self.add_inject(event, func, weight)
            return func

        return decorator

    def add_inject(
        self, event: EventType, callback: Callback[C], weight: int = 1
    ) -> None:
        """Programmatically register a per‑event injector.

        Args:
            event:      The event type to inject into.
            callback:   A sync or async callable that accepts an ``EventContext`` and returns ``None``.
            weight:     Execution priority.
        """
        if isinstance(event, AbstractEvent):
            raise TypeError(
                f"Expected an event type, got an instance of {type(event).__name__}. "
                f"Use the event class, not an instance."
            )
        if event not in self._injects:
            self._injects[event] = EventCallbackContainer[C, None]()
        self._injects[event].add_callback(callback, weight)
        logger.debug(
            f"Event inject {callback.__name__} has been added to event {event}, weight={weight}"
        )

    def remove_inject(self, event: EventType, callback: Callback[C]) -> None:
        """Remove a previously registered per‑event injector."""
        if event in self._injects:
            self._injects[event].remove_callback(callback)
