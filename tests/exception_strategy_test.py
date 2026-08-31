import asyncio
from enum import auto

import pytest

from async_event_bus import EnumEvent, EventBus, EventContext, ExceptionStrategy, MultipleError


class MessageEvent(EnumEvent):
    MESSAGE_CREATE = auto()


def sync_ok(ctx: EventContext) -> str:
    return "ok"


def sync_fail(ctx: EventContext) -> None:
    raise ValueError("sync fail")


async def async_ok(ctx: EventContext) -> str:
    return "async-ok"


async def async_fail(ctx: EventContext) -> None:
    raise RuntimeError("async fail")


@pytest.mark.asyncio
async def test_collect_default():
    """COLLECT (default): all callbacks run, exceptions bundled into MultipleError."""
    bus: EventBus = EventBus()
    bus.subscribe(MessageEvent.MESSAGE_CREATE, sync_fail)
    bus.subscribe(MessageEvent.MESSAGE_CREATE, async_fail)
    with pytest.raises(MultipleError) as exc_info:
        await bus.emit(MessageEvent.MESSAGE_CREATE)
    assert len(exc_info.value.exceptions) == 2


@pytest.mark.asyncio
async def test_raise_fail_fast():
    """RAISE: the first exception is re-raised immediately."""
    bus = EventBus(exception_strategy=ExceptionStrategy.RAISE)
    bus.subscribe(MessageEvent.MESSAGE_CREATE, sync_fail)
    with pytest.raises(ValueError, match="sync fail"):
        await bus.emit(MessageEvent.MESSAGE_CREATE)


@pytest.mark.asyncio
async def test_ignore():
    """IGNORE: exceptions are swallowed (logged), emit returns None."""
    bus = EventBus(exception_strategy=ExceptionStrategy.IGNORE)
    bus.subscribe(MessageEvent.MESSAGE_CREATE, sync_fail)
    bus.subscribe(MessageEvent.MESSAGE_CREATE, async_fail)
    result = await bus.emit(MessageEvent.MESSAGE_CREATE)
    assert result is None


@pytest.mark.asyncio
async def test_return():
    """RETURN: results and exceptions are returned separately, never raised."""
    bus = EventBus(exception_strategy=ExceptionStrategy.RETURN)
    bus.subscribe(MessageEvent.MESSAGE_CREATE, sync_ok)
    bus.subscribe(MessageEvent.MESSAGE_CREATE, sync_fail)
    bus.subscribe(MessageEvent.MESSAGE_CREATE, async_ok)
    bus.subscribe(MessageEvent.MESSAGE_CREATE, async_fail)

    result = await bus.emit(MessageEvent.MESSAGE_CREATE)
    assert result is not None
    assert result.results == ["ok", "async-ok"]
    assert len(result.exceptions) == 2
    assert isinstance(result.exceptions[0], ValueError)
    assert isinstance(result.exceptions[1], RuntimeError)


def test_return_sync():
    """RETURN works with the blocking emit_sync wrapper."""
    bus = EventBus(exception_strategy=ExceptionStrategy.RETURN)
    bus.subscribe(MessageEvent.MESSAGE_CREATE, sync_ok)
    bus.subscribe(MessageEvent.MESSAGE_CREATE, sync_fail)

    result = bus.emit_sync(MessageEvent.MESSAGE_CREATE)
    assert result is not None
    assert result.results == ["ok"]
    assert len(result.exceptions) == 1
    assert isinstance(result.exceptions[0], ValueError)


@pytest.mark.asyncio
async def test_return_none_when_filtered():
    """RETURN: a filtered event has no callback outcomes, so emit returns None."""
    bus = EventBus(exception_strategy=ExceptionStrategy.RETURN)

    @bus.global_event_filter()
    def block(ctx: EventContext) -> bool:
        return False

    @bus.on(MessageEvent.MESSAGE_CREATE)
    async def never_runs(ctx: EventContext) -> str:
        return "unreachable"

    result = await bus.emit(MessageEvent.MESSAGE_CREATE)
    assert result is None


@pytest.mark.asyncio
async def test_strategy_switchable_at_runtime():
    """The strategy can be switched at runtime via the exception_strategy property."""
    bus: EventBus = EventBus()
    bus.subscribe(MessageEvent.MESSAGE_CREATE, sync_fail)

    bus.exception_strategy = ExceptionStrategy.RETURN
    result = await bus.emit(MessageEvent.MESSAGE_CREATE)
    assert result is not None and isinstance(result.exceptions[0], ValueError)

    bus.exception_strategy = ExceptionStrategy.IGNORE
    assert await bus.emit(MessageEvent.MESSAGE_CREATE) is None
