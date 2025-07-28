import asyncio
import sys
from datetime import datetime
from enum import auto
from typing import Any

from loguru import logger

from py_event_bus import Event, EventBus

bus = EventBus()
logger.remove()
logger.add(sys.stdout, level="TRACE")


class MessageEvent(Event):
    MESSAGE_CREATE = auto()


@bus.global_event_inject()
async def global_inject(*args, **kwargs) -> dict[str, Any]:
    logger.info(f"Global inject called")
    return {
        "time": datetime.now().timestamp()
    }


@bus.event_inject(MessageEvent.MESSAGE_CREATE)
async def message_inject(message: str, *args, **kwargs) -> dict[str, Any]:
    logger.info(f"Message inject called")
    return {
        "message_len": len(message)
    }


@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(message: str, *args, **kwargs) -> None:
    logger.info(f"Async message creating: {message}")
    logger.info(f"Message create time: {kwargs.get('time')}")
    logger.info(f"Message len: {kwargs.get('message_len')}")
    assert kwargs.get('time') is not None
    assert kwargs.get('message_len') == 22


async def main():
    await bus.publish(MessageEvent.MESSAGE_CREATE, "This is a test message")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
