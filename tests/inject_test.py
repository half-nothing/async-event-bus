import asyncio
import sys
from datetime import datetime
from enum import auto

import pytest
from loguru import logger

from async_event_bus import EnumEvent, EventBus, EventContext

bus = EventBus()
logger.remove()
logger.add(sys.stdout, level="TRACE")


class MessageEvent(EnumEvent):
    MESSAGE_CREATE = auto()


@bus.global_event_inject()
async def global_inject(ctx: EventContext) -> None:
    logger.info(f"Global inject called")
    ctx.kwargs["time"] = datetime.now().timestamp()


@bus.event_inject(MessageEvent.MESSAGE_CREATE)
async def message_inject(ctx: EventContext) -> None:
    logger.info(f"Message inject called")
    ctx.kwargs["message_len"] = len(ctx.args[0])


@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(ctx: EventContext) -> None:
    message = ctx.args[0]
    logger.info(f"Async message creating: {message}")
    logger.info(f"Message create time: {ctx.kwargs.get('time')}")
    logger.info(f"Message len: {ctx.kwargs.get('message_len')}")
    assert ctx.kwargs.get('time') is not None
    assert ctx.kwargs.get('message_len') == 22


@pytest.mark.asyncio
async def test_inject():
    await bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_inject())
