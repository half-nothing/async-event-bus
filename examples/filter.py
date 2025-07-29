import asyncio
import sys
from enum import auto

from loguru import logger

from async_event_bus import Event, EventBus

bus = EventBus()
logger.remove()
logger.add(sys.stdout, level="TRACE")


class MessageEvent(Event):
    MESSAGE_CREATE = auto()


@bus.global_event_filter()
async def global_filter(*args, **kwargs) -> bool:
    logger.info(f"Global filter called")
    return False


@bus.event_filter(MessageEvent.MESSAGE_CREATE)
async def message_filter(message: str, *args, **kwargs) -> bool:
    logger.info(f"Message filter called")
    if message.find("forbidden") != -1:
        logger.info(f"Forbidden message found: {message}")
        return True
    return False


@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(message: str, *args, **kwargs) -> None:
    assert message.find("forbidden") == -1
    logger.info(f"Async message creating: {message}")


async def main():
    await asyncio.gather(
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a forbidden test message")
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
