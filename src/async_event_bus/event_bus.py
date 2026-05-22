from typing import TypeVar

from .event import EventContext
from .module import CoreModule, FilterModule, InjectModule

C = TypeVar("C", bound=EventContext)
R = TypeVar("R")


class EventBus(CoreModule[C, R], InjectModule[C], FilterModule[C]):
    """
    Full-featured event bus combining subscription, injection, and filtering.

    Example:
        bus = EventBus()

        @bus.on(MyEvent.FOO)
        async def handler(ctx: EventContext) -> None: ...

        @bus.event_inject(MyEvent.FOO)
        async def injector(ctx: EventContext) -> None:
            ctx.kwargs["user"] = await get_user()

        @bus.event_filter(MyEvent.FOO)
        async def guard(ctx: EventContext) -> bool:
            return ctx.kwargs.get("user") is not None

        await bus.emit(MyEvent.FOO, payload)
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 10,
        raise_exception: bool = False,
        context_class: type[C] = EventContext
    ):
        super().__init__(max_concurrent_tasks, raise_exception, context_class)

    def clear(self):
        super().clear()
