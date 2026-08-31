# async-event-bus

A simple event bus for python3

English | [简体中文](README_zh.md)

---
[![ReleaseCard]][Release]![ReleaseDataCard]  
![LastCommitCard]![ProjectLanguageCard]![ProjectLicense]
---

## Features

- **Multiple event types** — subscribe to plain strings, `EnumEvent` members or `AbstractEvent` classes
- **Sync & async callbacks** — sync callbacks run sequentially in weight order, async ones run concurrently
- **Typed `EventContext`** — a carrier object passed to every callback; subclass it to attach domain data
- **Filters** — global and per-event filters that stop propagation by returning `False`
- **Injectors** — global and per-event injectors that mutate the context before subscribers run
- **Weight ordering** — higher weight runs first (sync callbacks)
- **Concurrency control** — a semaphore caps the number of concurrent async callbacks
- **Configurable error handling** — fail-fast mode or collect all exceptions into `MultipleError`
- **`emit_sync`** — a blocking convenience wrapper around `emit` for synchronous code
- **Modular design** — `EventBus` is composed from `CoreModule`, `InjectModule` and `FilterModule` via MRO; build your own modules by inheriting `BaseModule`

## Installation

```shell
pip install async-event-bus
```

Requires Python 3.12+.

## Quick Start

```python
import asyncio

from loguru import logger

from async_event_bus import EventBus, EventContext

bus = EventBus()


@bus.on("message")
async def message_handler(ctx: EventContext) -> None:
    logger.info(f"message received: {ctx.args[0]}")


async def main():
    await asyncio.gather(
        bus.emit("message", "Hello"),
        bus.emit("message", "This is a test message"),
        bus.emit("message", "Send from python"),
        bus.emit("message", "This is also a test message")
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
```

Callbacks always receive an `EventContext` (or a subclass). Emit arguments are
available via `ctx.args` / `ctx.kwargs`; see [expand_args / expand_kwargs](#expand_args--expand_kwargs)
for the alternative unpacked calling convention.

## Custom Events

Three kinds of event keys are supported: strings, `EnumEvent` members, and
`AbstractEvent` classes.

```python
from enum import auto

from async_event_bus import AbstractEvent, EnumEvent, EventBus, EventContext

bus = EventBus()


# 1. Enum-style events
class MessageEvent(EnumEvent):
    MESSAGE_CREATE = auto()
    MESSAGE_DELETE = auto()


# 2. Class-style events
class LifeCycleEvent(AbstractEvent):
    def __init__(self, online: bool, status: bool):
        self.online = online
        self.status = status


@bus.on(MessageEvent.MESSAGE_CREATE)
async def on_create(ctx: EventContext) -> None:
    logger.info(f"creating: {ctx.args[0]}")


@bus.on(LifeCycleEvent)
async def on_life_cycle(ctx: EventContext) -> None:
    # Pass an AbstractEvent instance to emit; it is available as ctx.event
    event = ctx.event  # type: LifeCycleEvent
    logger.info(f"life cycle: {event.online}, {event.status}")


await bus.emit(MessageEvent.MESSAGE_CREATE, "hello")   # inside an async context
await bus.emit(LifeCycleEvent(True, True))
```

## Custom EventContext

Subclass `EventContext` to attach domain-specific fields, then pass the subclass
as `context_class` to `EventBus`. Injectors (see below) are the usual place to
fill these fields before subscribers run.

```python
from dataclasses import dataclass

from async_event_bus import EventBus, EventContext

@dataclass
class AppContext(EventContext):
    user: str = ""

bus = EventBus(context_class=AppContext)


@bus.global_event_inject()
async def inject_user(ctx: AppContext) -> None:
    ctx.user = await fetch_user(ctx.kwargs.get("user_id"))


@bus.on("message")
async def on_message(ctx: AppContext) -> None:
    print(f"{ctx.user}: {ctx.args}")
```

## Filters

Filters gate event propagation. Return `True` to continue, `False` to stop the
event immediately — remaining filters and all subscribers are skipped.

- Global filters run first, then per-event filters.
- Global filters always receive `ctx`; per-event filters honor
  `expand_args` / `expand_kwargs` like subscribers do.

```python
@bus.global_event_filter()
async def auth_guard(ctx: EventContext) -> bool:
    return ctx.kwargs.get("user") is not None   # False stops propagation


@bus.event_filter(MessageEvent.MESSAGE_CREATE)
def content_filter(ctx: EventContext) -> bool:
    return "forbidden" not in ctx.args[0]
```

Programmatic equivalents: `add_global_filter`, `add_filter`, and the matching
`remove_global_filter` / `remove_filter`.

## Injectors

Injectors mutate the context in-place before subscribers run. Return values are
discarded — side effects happen on `ctx`. If any injector raises, the event is
dropped so subscribers never see an incomplete context.

- Global injectors run first, then per-event injectors.
- Like filters, global injectors always receive `ctx`, while per-event
  injectors honor `expand_args` / `expand_kwargs`.

```python
import time

@bus.global_event_inject()
async def add_timestamp(ctx: EventContext) -> None:
    ctx.kwargs["timestamp"] = time.time()


@bus.event_inject(MessageEvent.MESSAGE_CREATE)
async def add_message_len(ctx: EventContext) -> None:
    ctx.kwargs["message_len"] = len(ctx.args[0])
```

Programmatic equivalents: `add_global_inject`, `add_inject`, and the matching
`remove_global_inject` / `remove_inject`.

## Weight & Execution Order

Higher weight runs first. Synchronous callbacks always execute before
asynchronous ones, sequentially and in descending weight order; asynchronous
callbacks run concurrently via `asyncio.gather`, so weight is irrelevant among
them.

```python
@bus.on("message", weight=10)
def high_priority(ctx: EventContext) -> None:
    ...

@bus.on("message", weight=1)
def low_priority(ctx: EventContext) -> None:
    ...
```

## expand_args / expand_kwargs

By default callbacks receive the `EventContext` object. With
`expand_args=True` / `expand_kwargs=True`, `ctx.args` / `ctx.kwargs` are unpacked
and passed directly, which gives cleaner signatures for per-event handlers,
filters and injectors.

```python
@bus.on("message")
async def handler(ctx: EventContext, message: str) -> None:
    print(message)

await bus.emit("message", "hello", expand_args=True)
```

## Exception Handling

Callback exceptions are handled according to the `ExceptionStrategy` chosen at
construction time. Four strategies are available:

| Strategy | Behaviour |
| --- | --- |
| `ExceptionStrategy.IGNORE` | Exceptions are logged and skipped; `emit` returns `None`. |
| `ExceptionStrategy.RAISE` | Fail fast: the first exception aborts execution immediately. |
| `ExceptionStrategy.COLLECT` (default) | All callbacks run; exceptions are raised together as a `MultipleError`. |
| `ExceptionStrategy.RETURN` | Exceptions are not raised — `emit` returns an `EmitResult` with results and exceptions kept separate. |

```python
from async_event_bus import EventBus, ExceptionStrategy, MultipleError

bus = EventBus(exception_strategy=ExceptionStrategy.COLLECT)   # default

try:
    await bus.emit("message", "hello")
except MultipleError as e:
    for exc in e.exceptions:
        print(exc)
```

With `RETURN`, `emit` (and `emit_sync`) returns an `EmitResult` instead of
raising — successful outcomes and exceptions are kept in separate lists:

```python
from async_event_bus import EmitResult, EventBus, EventContext, ExceptionStrategy

bus = EventBus(exception_strategy=ExceptionStrategy.RETURN)


@bus.on("message")
def ok(ctx: EventContext) -> str:
    return "hello"


@bus.on("message")
def boom(ctx: EventContext) -> None:
    raise ValueError("boom")


result: EmitResult | None = await bus.emit("message")
# result.results == ["hello"]                     -- successful outcomes
# result.exceptions == [ValueError("boom")]       -- exceptions, kept apart
```

The strategy can also be switched at runtime through the `exception_strategy`
property of the bus.

## Custom Event Bus & Modules

`EventBus` itself is just `CoreModule` (subscribe/emit) combined with
`InjectModule` and `FilterModule` via MRO. You can compose your own bus the same
way, or write a custom module by overriding `before_emit` on `BaseModule`.

### Custom event bus (inherit CoreModule)

```python
from async_event_bus import CoreModule, EnumEvent, EventContext, EventType

class CustomEventBus(CoreModule):
    # Returning False terminates propagation; you can also mutate ctx here.
    async def before_emit(self, event: EventType, ctx: EventContext) -> bool:
        if event == MessageEvent.MESSAGE_DELETE:
            return False
        ctx.kwargs["timestamp"] = time.time()
        return await super().before_emit(event, ctx)
```

### Custom module (inherit BaseModule)

```python
from async_event_bus import BaseModule, CoreModule, EventContext, EventType

class CustomModule(BaseModule[EventContext, bool]):
    async def before_emit(self, event: EventType, ctx: EventContext) -> bool:
        # inspect / mutate the event here, then continue the chain
        return await super().before_emit(event, ctx)

class CustomEventBus(CoreModule, CustomModule):
    pass
```

## Examples

Check the `examples/` folder for runnable, fully commented samples:

- `basic_use.py` — subscribe and emit with strings
- `custom_event.py` — `EnumEvent` and `AbstractEvent` events
- `custom_event_bus.py` — a custom bus inheriting `CoreModule`
- `custom_event_bus_module.py` — a custom module combined via MRO
- `filter.py` — global and per-event filters
- `inject.py` — global and per-event injectors
- `exception_strategy.py` — the four `ExceptionStrategy` modes (IGNORE / RAISE / COLLECT / RETURN)

## License

[MIT](LICENSE)

[ReleaseCard]: https://img.shields.io/github/v/release/half-nothing/async-event-bus?style=for-the-badge&logo=github

[ReleaseDataCard]: https://img.shields.io/github/release-date/half-nothing/async-event-bus?display_date=published_at&style=for-the-badge&logo=github

[LastCommitCard]: https://img.shields.io/github/last-commit/half-nothing/async-event-bus?display_timestamp=committer&style=for-the-badge&logo=github

[ProjectLanguageCard]: https://img.shields.io/github/languages/top/half-nothing/async-event-bus?style=for-the-badge&logo=github

[ProjectLicense]: https://img.shields.io/badge/License-MIT-blue?style=for-the-badge&logo=github

[Release]: https://www.github.com/half-nothing/async-event-bus/releases/latest
