import asyncio
import sys
from datetime import datetime
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


@bus.global_event_inject()
async def global_inject(*args: list[Any], **kwargs: dict[str, Any]) -> dict[str, Any]:
    logger.info(f"Global inject called")
    return {
        "time": datetime.now().timestamp()
    }


@bus.event_inject(MessageEvent.MESSAGE_CREATE)
async def message_inject(message: str, *args: list[Any], **kwargs: dict[str, Any]) -> dict[str, Any]:
    logger.info(f"Message inject called")
    return {
        "message_len": len(message)
    }


@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(message: str, *args: list[Any], **kwargs: dict[str, Any]) -> None:
    logger.info(f"Async message creating: {message}")
    logger.info(f"Message create time: {kwargs.get('time')}")
    logger.info(f"Message len: {kwargs.get('message_len')}")
    assert kwargs.get('time') is not None
    assert kwargs.get('message_len') == 22


@pytest.mark.asyncio
async def test_inject():
    await bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_inject())
