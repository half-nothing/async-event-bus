from typing import TypeVar

from .event import EventContext
from .module import CoreModule, ExceptionStrategy, FilterModule, InjectModule

C = TypeVar("C", bound=EventContext)
R = TypeVar("R")


class EventBus(CoreModule[C, R], InjectModule[C], FilterModule[C]):
    """Full-featured event bus combining subscription, injection, and filtering."""

    def __init__(
            self,
            max_concurrent_tasks: int = 10,
            exception_strategy: ExceptionStrategy = ExceptionStrategy.COLLECT,
            context_class: type[C] = ...,
    ) -> None: ...

    def clear(self) -> None: ...
