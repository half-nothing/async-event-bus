import asyncio
import sys
from enum import auto
from typing import Any

import pytest
from loguru import logger

from async_event_bus import EnumEvent, EventBus

bus = EventBus()
logger.remove()
logger.add(sys.stdout, level="TRACE")


class MessageEvent(EnumEvent):
    MESSAGE_CREATE = auto()
    MESSAGE_DELETE = auto()


@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(message: str, *args: list[Any], **kwargs: dict[str, Any]) -> None:
    assert message in ("This is a test message", "This is also a test message")
    logger.info(f"Async message creating: {message}")
    await asyncio.sleep(1)
    logger.info(f"Async message created: {message}")


@bus.on(MessageEvent.MESSAGE_DELETE)
async def async_message_delete(message: str, *args: list[Any], **kwargs: dict[str, Any]) -> None:
    assert message in ("This is a test delete message", "This is also a test delete message")
    logger.info(f"Async message deleting: {message}")
    await asyncio.sleep(0.5)
    logger.info(f"Async message deleted: {message}")


@pytest.mark.asyncio
async def test_async_subscribe():
    await asyncio.gather(
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is also a test message"),
        bus.emit(MessageEvent.MESSAGE_DELETE, "This is a test delete message"),
        bus.emit(MessageEvent.MESSAGE_DELETE, "This is also a test delete message")
    )
    bus.unsubscribe(MessageEvent.MESSAGE_CREATE, async_message_create)
    bus.unsubscribe(MessageEvent.MESSAGE_DELETE, async_message_delete)


@bus.on(MessageEvent.MESSAGE_CREATE)
def message_create(message: str, *args: list[Any], **kwargs: dict[str, Any]) -> None:
    assert message in ("This is a test message", "This is also a test message")
    logger.info(f"Sync message created: {message}")


@bus.on(MessageEvent.MESSAGE_DELETE)
def message_delete(message: str, *args: list[Any], **kwargs: dict[str, Any]) -> None:
    assert message in ("This is a test delete message", "This is also a test delete message")
    logger.info(f"Message deleted: {message}")


def test_sync_subscribe() -> None:
    bus.emit_sync(MessageEvent.MESSAGE_CREATE, "This is a test message")
    bus.emit_sync(MessageEvent.MESSAGE_CREATE, "This is also a test message")
    bus.emit_sync(MessageEvent.MESSAGE_DELETE, "This is a test delete message")
    bus.emit_sync(MessageEvent.MESSAGE_DELETE, "This is also a test delete message")
    bus.unsubscribe(MessageEvent.MESSAGE_CREATE, message_create)
    bus.unsubscribe(MessageEvent.MESSAGE_DELETE, message_delete)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_async_subscribe())
    test_sync_subscribe()
