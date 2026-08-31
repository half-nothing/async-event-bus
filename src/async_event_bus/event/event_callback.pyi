from typing import Any, Awaitable, Callable, Generic, TypeAlias, TypeVar

from .event import EventContext

C = TypeVar("C", bound=EventContext)
R = TypeVar("R")

# Separate type aliases for sync and async callbacks make the constructor
# signatures of SyncEventCallback/AsyncEventCallback self-documenting and
# help static type checkers distinguish the two variants.
SyncCallback: TypeAlias = Callable[[C], R]
AsyncCallback: TypeAlias = Callable[[C], Awaitable[R]]
Callback: TypeAlias = Callable[[C], R | Awaitable[R]]


class EventCallback(Generic[C, R]):
    """Wraps a raw callable so that scheduler-related metadata can be stored alongside it."""

    def __init__(self, callback: Callback[C, R], weight: int = 1) -> None: ...

    @property
    def weight(self) -> int:
        """Execution priority; higher weights execute first."""
        ...

    @weight.setter
    def weight(self, weight: int) -> None: ...

    @property
    def callback(self) -> Callback[C, R]:
        """The original callable."""
        ...

    @property
    def is_async(self) -> bool:
        """Whether the callable is asynchronous."""
        ...

    def __eq__(self, __value: Any) -> bool: ...

    def __str__(self) -> str: ...

    def __repr__(self) -> str: ...

    @staticmethod
    def create(callback: Callback[C, R], weight: int = 1) -> EventCallback[C, R]:
        """Factory that returns the correct subclass for *callback*."""
        ...


class SyncEventCallback(EventCallback[C, R]):
    """Enforces synchronous invocation; the bus can call this without an event loop."""

    def __init__(self, callback: SyncCallback[C, R], weight: int = 1) -> None: ...

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


class AsyncEventCallback(EventCallback[C, R]):
    """Enforces await-based invocation."""

    def __init__(self, callback: AsyncCallback[C, R], weight: int = 1) -> None: ...

    async def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


class EventCallbackContainer(Generic[C, R]):
    """Holds registered callbacks for a single event type.

    Synchronous and asynchronous callbacks are stored in separate ordered lists
    because their execution models differ.
    """

    def __init__(self) -> None: ...

    def add_sync_callback(self, callback: SyncEventCallback[C, R]) -> None: ...

    def add_async_callback(self, callback: AsyncEventCallback[C, R]) -> None: ...

    def add_callback(self, callback: EventCallback[C, R] | Callback[C, R], weight: int = 1) -> None: ...

    def remove_sync_callback(self, callback: SyncEventCallback[C, R] | Callback[C, R]) -> None: ...

    def remove_async_callback(self, callback: AsyncEventCallback[C, R] | Callback[C, R]) -> None: ...

    def remove_callback(self, callback: EventCallback[C, R] | Callback[C, R]) -> None: ...

    def clear(self) -> None: ...

    @property
    def sync_callback(self) -> list[SyncEventCallback[C, R]]:
        """The ordered (weight-descending) list of synchronous callbacks."""
        ...

    @property
    def async_callback(self) -> list[AsyncEventCallback[C, R]]:
        """The ordered list of asynchronous callbacks."""
        ...
