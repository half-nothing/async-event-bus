import asyncio
import sys
from dataclasses import dataclass

import pytest
from loguru import logger

from async_event_bus import AbstractEvent, EventBus, EventContext

bus: EventBus = EventBus()
logger.remove()
logger.add(sys.stdout, level="TRACE")


@dataclass(frozen=True)
class MessageDeleteEvent(AbstractEvent):
    message_id: str


@dataclass(frozen=True)
class MessageCreateEvent(AbstractEvent):
    message: str
    message_id: str


@bus.on(MessageCreateEvent)
async def async_message_create(ctx: EventContext[MessageCreateEvent]) -> None:
    assert ctx.event.message in ("This is a test message", "This is also a test message")
    logger.info(f"Async message creating: {ctx.event.message}, id: {ctx.event.message_id}")
    await asyncio.sleep(1)
    logger.info(f"Async message created: {ctx.event.message}, id: {ctx.event.message_id}")


@bus.on(MessageDeleteEvent)
async def async_message_delete(ctx: EventContext[MessageDeleteEvent]) -> None:
    logger.info(f"Async message deleting: {ctx.event.message_id}")
    await asyncio.sleep(0.5)
    logger.info(f"Async message deleted: {ctx.event.message_id}")


@pytest.mark.asyncio
async def test_async_subscribe():
    await asyncio.gather(
        bus.emit(MessageCreateEvent("This is a test message", "1")),
        bus.emit(MessageCreateEvent("This is also a test message", "2")),
        bus.emit(MessageDeleteEvent("1")),
        bus.emit(MessageDeleteEvent("2"))
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_async_subscribe())
