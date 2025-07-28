import asyncio
import sys
from enum import auto

from loguru import logger

from py_event_bus import Event, EventBus

bus = EventBus()
logger.remove()
logger.add(sys.stdout, level="TRACE")


class MessageEvent(Event):
    MESSAGE_CREATE = auto()
    MESSAGE_DELETE = auto()


@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(message: str, *args, **kwargs) -> None:
    logger.info(f"Async message creating: {message}")


@bus.on(MessageEvent.MESSAGE_DELETE)
async def async_message_delete(message: str, *args, **kwargs) -> None:
    logger.info(f"Async message deleting: {message}")


async def main():
    await asyncio.gather(
        bus.publish(MessageEvent.MESSAGE_CREATE, "Hello"),
        bus.publish(MessageEvent.MESSAGE_CREATE, "This is a test message"),
        bus.publish(MessageEvent.MESSAGE_CREATE, "Send from python"),
        bus.publish(MessageEvent.MESSAGE_CREATE, "This is also a test message"),
        bus.publish(MessageEvent.MESSAGE_DELETE, "Delete some message")
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
