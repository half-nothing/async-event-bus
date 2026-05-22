from typing import TypeVar

from .event import EventContext
from .module import CoreModule, FilterModule, InjectModule

C = TypeVar("C", bound=EventContext)
R = TypeVar("R")


class EventBus(CoreModule[C, R], InjectModule[C], FilterModule[C]):
    """
    Full-featured event bus combining subscription, injection, and filtering.

    --- Basic usage ---

    from async_event_bus import EventBus, EnumEvent, EventContext
    from enum import auto

    class AppEvent(EnumEvent):
        MESSAGE_CREATE = auto()

    bus = EventBus()

    @bus.on(AppEvent.MESSAGE_CREATE)
    async def on_message(ctx: EventContext) -> None:
        print(ctx.args)

    await bus.emit(AppEvent.MESSAGE_CREATE, "hello")
    bus.emit_sync(AppEvent.MESSAGE_CREATE, "hello")   # blocking variant

    --- Custom EventContext ---

    from dataclasses import dataclass, field

    @dataclass
    class AppContext(EventContext):
        user: str = ""

    bus = EventBus(context_class=AppContext)

    @bus.global_event_inject()
    async def inject_user(ctx: AppContext) -> None:
        ctx.user = await fetch_user(ctx.kwargs.get("user_id"))

    @bus.on(AppEvent.MESSAGE_CREATE)
    async def on_message(ctx: AppContext) -> None:
        print(f"{ctx.user}: {ctx.args}")

    --- Filtering ---

    @bus.global_event_filter()
    async def auth_guard(ctx: AppContext) -> bool:
        return ctx.user is not None   # False stops propagation

    @bus.event_filter(AppEvent.MESSAGE_CREATE)
    def content_filter(ctx: EventContext) -> bool:
        return "forbidden" not in ctx.args[0]

    --- Weight-based ordering ---

    # Higher weight = called first. Sync callbacks always precede async ones.
    @bus.on(AppEvent.MESSAGE_CREATE, weight=10)
    def high_priority(ctx: EventContext) -> None: ...

    @bus.on(AppEvent.MESSAGE_CREATE, weight=1)
    def low_priority(ctx: EventContext) -> None: ...

    --- Exception handling ---

    bus = EventBus(raise_exception=True)   # first exception aborts immediately
    # default (False): all callbacks run, exceptions collected into MultipleError

    Args:
        max_concurrent_tasks:   Semaphore limit for concurrent async callbacks (default 10)
        raise_exception:        If True, first exception aborts execution immediately (default False)
        context_class:          EventContext subclass to instantiate on each emit (default EventContext)
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
