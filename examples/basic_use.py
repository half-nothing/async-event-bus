import asyncio
import sys

from loguru import logger

from async_event_bus import EventBus

bus = EventBus()
logger.remove()
logger.add(sys.stdout, level="TRACE")


@bus.on("message")
async def message_handler(message: str, *args, **kwargs) -> None:
    logger.info(f"message received: {message}")


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
