import asyncio
import sys
from typing import Any

import pytest
from loguru import logger

from async_event_bus import AbstractEvent, EventBus

bus = EventBus()
logger.remove()
logger.add(sys.stdout, level="TRACE")


class MessageDeleteEvent(AbstractEvent):
    def __init__(self, message_id: str):
        self.message_id = message_id


class MessageCreateEvent(AbstractEvent):
    def __init__(self, message: str, message_id: str):
        self.message = message
        self.message_id = message_id


@bus.on(MessageCreateEvent)
async def async_message_create(event: MessageCreateEvent, *args: list[Any], **kwargs: dict[str, Any]) -> None:
    assert event.message in ("This is a test message", "This is also a test message")
    logger.info(f"Async message creating: {event.message}, id: {event.message_id}")
    await asyncio.sleep(1)
    logger.info(f"Async message created: {event.message}, id: {event.message_id}")


@bus.on(MessageDeleteEvent)
async def async_message_delete(event: MessageDeleteEvent, *args: list[Any], **kwargs: dict[str, Any]) -> None:
    logger.info(f"Async message deleting: {event.message_id}")
    await asyncio.sleep(0.5)
    logger.info(f"Async message deleted: {event.message_id}")


@pytest.mark.asyncio
async def test_async_subscribe():
    await asyncio.gather(
        bus.emit(MessageCreateEvent, MessageCreateEvent("This is a test message", "1")),
        bus.emit(MessageCreateEvent, MessageCreateEvent("This is also a test message", "2")),
        bus.emit(MessageDeleteEvent, MessageDeleteEvent("1")),
        bus.emit(MessageDeleteEvent, MessageDeleteEvent("2"))
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_async_subscribe())
