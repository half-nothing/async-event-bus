import asyncio
import sys
from enum import auto

import pytest
from loguru import logger

from async_event_bus import EnumEvent, EventBus, EventContext

bus: EventBus = EventBus()
logger.remove()
logger.add(sys.stdout, level="TRACE")


class MessageEvent(EnumEvent):
    MESSAGE_CREATE = auto()


@bus.global_event_filter()
async def global_filter(ctx: EventContext) -> bool:
    logger.info(f"Global filter called, event: {ctx.event}")
    return True


# NOTE: expand_args=True passes the payload as extra positional args, which the
# library types as Callable[[C], ...] and cannot express, hence the ignore below.
@bus.event_filter(MessageEvent.MESSAGE_CREATE)  # type: ignore[arg-type]
async def message_filter(ctx: EventContext, message: str) -> bool:
    logger.info(f"Message filter called")
    if message.find("forbidden") != -1:
        logger.info(f"Forbidden message found: {message}")
        return False
    return True


@bus.on(MessageEvent.MESSAGE_CREATE)  # type: ignore[arg-type]
async def async_message_create(ctx: EventContext, message: str) -> None:
    assert message.find("forbidden") == -1
    logger.info(f"Async message creating: {message}")


@pytest.mark.asyncio
async def test_filter():
    await asyncio.gather(
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message", expand_args=True),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a forbidden test message", expand_args=True)
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_filter())
