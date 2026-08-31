from inspect import iscoroutinefunction
from typing import Any, Callable, Generic, TypeVar, TypeAlias, Awaitable, cast

from loguru import logger

from .event import EventContext

# Generic type variables allow modules to enforce type-safe event contexts and
# return values without binding to concrete implementations.
C = TypeVar("C", bound=EventContext)
R = TypeVar("R")

# Separate type aliases for sync and async callbacks make the constructor
# signatures of SyncEventCallback/AsyncEventCallback self-documenting and
# help static type checkers distinguish the two variants.
SyncCallback: TypeAlias = Callable[[C], R]
AsyncCallback: TypeAlias = Callable[[C], Awaitable[R]]
Callback: TypeAlias = Callable[[C], R | Awaitable[R]]


class EventCallback(Generic[C, R]):
    """Wraps a raw callable so that scheduler‑relevant metadata can be stored alongside it."""

    def __init__(self, callback: Callback[C, R], weight: int = 1) -> None:
        """Initialize the wrapper.

        Args:
            callback:   Any sync or async callable that accepts an event context.
            weight:     Priority; higher weights execute first.
        """
        # Weight is stored *on* the callback object,
        # so that containers can sort handlers without additional lookups or decorator‑side data structures.
        self._callback = callback
        self._weight = weight
        # Subclasses set the _async flag explicitly;
        # the base class defaults to False so that legacy code that constructs EventCallback directly
        # still behaves like a synchronous wrapper.
        self._async = False

    @property
    def weight(self) -> int:
        """Execution priority.

        Returns:
            The current weight.
        """
        return self._weight

    @weight.setter
    def weight(self, weight: int) -> None:
        """Change the weight at runtime.

        Args:
            weight: New priority value.
        """
        self._weight = weight

    @property
    def callback(self) -> Callback[C, R]:
        """The original callable.

        Returns:
            The wrapped function.
        """
        return self._callback

    @property
    def is_async(self) -> bool:
        """Whether the callable is asynchronous.

        Returns:
            ``True`` if the callable must be awaited, ``False`` otherwise.

        Exposing async‑ness allows the executor to branch between
        sequential synchronous execution and concurrent asynchronous execution.
        """
        return self._async

    def __eq__(self, __value: Any) -> bool:
        """Compare by both callback identity and weight.

        Equality is deliberately based on the *combination* of callback and weight.
        This ensures that registering the same function with a different weight creates a distinct entry,
        which is useful for scenarios where a single function plays multiple roles.
        """
        if isinstance(__value, self.__class__):
            return self._callback == __value._callback and self._weight == __value._weight
        # Also allow comparison against raw callables,
        # so that removal APIs can accept either form without extra conversion.
        return self._callback == __value

    def __str__(self) -> str:
        return f"EventCallback(callback={self._callback}, weight={self.weight}, async={self.is_async})"

    def __repr__(self) -> str:
        return str(self)

    @staticmethod
    def create(callback: Callback[C, R], weight: int = 1) -> "EventCallback[C, R]":
        """Factory that returns the correct subclass for *callback*.

        Args:
            callback:   Any sync or async callable accepting an event context.
            weight:     Execution priority.

        Returns:
            An ``AsyncEventCallback`` if *callback* is a coroutine function,
            otherwise a ``SyncEventCallback``.
        """
        if iscoroutinefunction(callback):
            return AsyncEventCallback(cast(AsyncCallback[C, R], callback), weight)
        return SyncEventCallback(cast(SyncCallback[C, R], callback), weight)


class SyncEventCallback(EventCallback[C, R]):
    """Enforces synchronous invocation.

    The event bus can call this directly without an event loop.
    """

    # Re-declared with the narrower type so that the executor and type checkers
    # know this wrapper's callback is always synchronous.
    _callback: SyncCallback[C, R]

    def __init__(self, callback: SyncCallback[C, R], weight: int = 1) -> None:
        """Wrap a synchronous callback.

        Args:
            callback:   A synchronous callable ``(EventContext) -> R``.
            weight:     Execution priority.
        """
        super().__init__(callback, weight)
        self._async = False

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Invoke the wrapped synchronous callback.

        Returns:
            Whatever the original callback returns.
        """
        # Delegates directly – the base class guarantees this is synchronous.
        return self._callback(*args, **kwargs)


class AsyncEventCallback(EventCallback[C, R]):
    """Enforces ``await``‑based invocation.

    Wrapping async callables prevents accidental synchronous calls that
    would return a coroutine object instead of the expected result.
    """

    # Re-declared with the narrower type so that ``await self._callback(...)``
    # type-checks and the executor knows this wrapper is always asynchronous.
    _callback: AsyncCallback[C, R]

    def __init__(self, callback: AsyncCallback[C, R], weight: int = 1) -> None:
        """Wrap an asynchronous callback.

        Args:
            callback:   An async callable ``(EventContext) -> Awaitable[R]``.
            weight:     Execution priority.
        """
        super().__init__(callback, weight)
        self._async = True

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Await the wrapped asynchronous callback.

        Returns:
            The result of the coroutine.
        """
        return await self._callback(*args, **kwargs)


class EventCallbackContainer(Generic[C, R]):
    """Holds registered callbacks for a single event type.

    Synchronous and asynchronous callbacks are stored in separate ordered
    lists because their execution models differ:

    - Synchronous handlers are called sequentially in weight order.
    - Asynchronous handlers are scheduled concurrently via ``asyncio.gather``
      so weight ordering among them is intentionally irrelevant at runtime.
    """

    def __init__(self) -> None:
        self._sync_callback: list[SyncEventCallback[C, R]] = []
        self._async_callback: list[AsyncEventCallback[C, R]] = []

    def add_sync_callback(self, callback: SyncEventCallback[C, R]) -> None:
        """Add a synchronous callback, avoiding duplicates.

        Duplicate detection uses the ``__eq__`` semantics (callback identity + weight).
        This prevents the same handler from being executed multiple times for one event,
        which would be surprising and potentially expensive.

        Sorting is performed eagerly here because callbacks are typically registered at import/startup time;
        the occasional *O(n log n)* cost is negligible and guarantees that
        the list is always ready for fast sequential iteration during event emission.
        """
        if callback not in self._sync_callback:
            logger.trace(f"Adding sync callback: {callback}")
            self._sync_callback.append(callback)
            self._sync_callback.sort(key=lambda item: item.weight, reverse=True)
        else:
            logger.trace(f"Callback already exists: {callback}")

    def add_async_callback(self, callback: AsyncEventCallback[C, R]) -> None:
        """Add an asynchronous callback, avoiding duplicates.

        See `add_sync_callback` for the rationale behind duplicate detection and eager sorting.
        """
        if callback not in self._async_callback:
            logger.trace(f"Adding async callback: {callback}")
            self._async_callback.append(callback)
            self._async_callback.sort(key=lambda item: item.weight, reverse=True)
        else:
            logger.trace(f"Callback already exists: {callback}")

    def add_callback(
        self, callback: EventCallback[C, R] | Callback[C, R], weight: int = 1
    ) -> None:
        """Normalize and add any callback to the appropriate internal list.

        Normalizing everything to ``EventCallback`` instances keeps the rest of the container logic simple:
        it only ever deals with typed ``EventCallback`` objects.

        Args:
            callback:   An ``EventCallback`` wrapper or a raw callable.
            weight:     Execution priority (used only when a raw callable is passed;
                        ignored for ``EventCallback`` instances).

        Raises:
            TypeError: If *callback* is neither a recognized ``EventCallback`` subclass nor a callable.
        """
        if not isinstance(callback, EventCallback) and callable(callback):
            callback = EventCallback.create(callback, weight)
        if isinstance(callback, AsyncEventCallback):
            self.add_async_callback(callback)
        elif isinstance(callback, SyncEventCallback):
            self.add_sync_callback(callback)
        else:
            raise TypeError(f"Callback type {type(callback)} not supported")

    def remove_sync_callback(
        self, callback: SyncEventCallback[C, R] | Callback[C, R]
    ) -> None:
        """Remove a synchronous callback.

        The ``in`` check mirrors the ``__eq__`` logic:
        it allows removal by passing either the ``EventCallback`` wrapper or the original function,
        so that callers don't have to remember which form they used during registration.
        """
        if callback in self._sync_callback:
            logger.trace(f"Removing sync callback: {callback}")
            # ``in`` relies on __eq__ semantics which accept both wrappers and
            # raw callables; narrow the union for the list remove() call.
            self._sync_callback.remove(cast(SyncEventCallback[C, R], callback))

    def remove_async_callback(
        self, callback: AsyncEventCallback[C, R] | Callback[C, R]
    ) -> None:
        """Remove an asynchronous callback.

        See `remove_sync_callback` for the rationale behind accepting both wrappers and raw callables.
        """
        if callback in self._async_callback:
            logger.trace(f"Removing async callback: {callback}")
            # See `remove_sync_callback` for the rationale behind the cast.
            self._async_callback.remove(cast(AsyncEventCallback[C, R], callback))

    def remove_callback(
        self, callback: EventCallback[C, R] | Callback[C, R]
    ) -> None:
        """Remove any callback, automatically detecting its type.

        When given a raw callable we must still determine whether it is sync
        or async so that removal targets the correct list.
        This avoids the need for the caller to remember that distinction.

        Args:
            callback: An ``EventCallback`` wrapper or the original function.

        Raises:
            TypeError: If *callback* is neither a recognized ``EventCallback`` subclass nor a callable.
        """
        if not isinstance(callback, EventCallback) and callable(callback):
            if iscoroutinefunction(callback):
                self.remove_async_callback(callback)
            else:
                self.remove_sync_callback(callback)
            return
        if isinstance(callback, AsyncEventCallback):
            self.remove_async_callback(callback)
        elif isinstance(callback, SyncEventCallback):
            self.remove_sync_callback(callback)
        else:
            raise TypeError(f"Callback type {type(callback)} not supported")

    def clear(self) -> None:
        """Remove all registered callbacks.

        Necessary when hot‑reloading modules or resetting bus state.
        """
        self._sync_callback.clear()
        self._async_callback.clear()

    @property
    def sync_callback(self) -> list[SyncEventCallback[C, R]]:
        """The ordered list of synchronous callbacks.

        Returns:
            A reference to the internal (already sorted) list,
            so that the executor can iterate without copying.
        """
        return self._sync_callback

    @property
    def async_callback(self) -> list[AsyncEventCallback[C, R]]:
        """The ordered list of asynchronous callbacks.

        Returns:
            A reference to the internal (already sorted) list.
        """
        return self._async_callback
