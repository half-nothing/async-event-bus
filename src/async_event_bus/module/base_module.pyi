from abc import ABC
from dataclasses import dataclass
from typing import Generic, TypeVar

from .module_exceptions import ExceptionStrategy
from ..event import EventContext, EventType

C = TypeVar("C", bound=EventContext)
R = TypeVar("R")


@dataclass
class EmitResult(Generic[R]):
    """Outcome of executing a callback container.

    Successful callback outcomes and exceptions are kept in separate lists.

    Attributes:
        results:    Return values of the callbacks that completed successfully,
                    in execution order (sync callbacks first, then async ones).
        exceptions: Exceptions raised by the callbacks, in the order they
                    occurred. Only populated by the ``RETURN`` strategy.
    """

    results: list[R]
    exceptions: list[Exception]


class BaseModule(ABC, Generic[C, R]):
    """Abstract base for all bus modules."""

    def __init__(
            self,
            max_concurrent_tasks: int = 16,
            exception_strategy: ExceptionStrategy = ExceptionStrategy.COLLECT,
            context_class: type[C] = ...,
    ) -> None: ...

    @property
    def exception_strategy(self) -> ExceptionStrategy:
        """How callback exceptions are currently handled."""
        ...

    @exception_strategy.setter
    def exception_strategy(self, value: ExceptionStrategy) -> None: ...

    async def before_emit(self, event: EventType, ctx: C) -> bool:
        """Cooperative pre-emit hook; return ``False`` to stop propagation."""
        ...

    def clear(self) -> None:
        """Reset all state stored by the module."""
        ...
