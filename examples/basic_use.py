import asyncio
import sys

from loguru import logger

from py_event_bus import EventBus

bus = EventBus()
logger.remove()
logger.add(sys.stdout, level="TRACE")


@bus.on("message")
async def message_handler(message: str, *args, **kwargs) -> None:
    logger.info(f"message received: {message}")


async def main():
    await asyncio.gather(
        bus.publish("message", "Hello"),
        bus.publish("message", "This is a test message"),
        bus.publish("message", "Send from python"),
        bus.publish("message", "This is also a test message")
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
