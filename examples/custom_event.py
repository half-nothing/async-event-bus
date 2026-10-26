# 自定义事件
# Custom events
import asyncio
import sys
from enum import auto

from loguru import logger

from async_event_bus import AbstractEvent, EnumEvent, EventBus, EventContext

# 创建事件总线实例
# Create an event bus instance
bus: EventBus = EventBus()

# 设置日志级别
# Set log level
logger.remove()
logger.add(sys.stdout, level="TRACE")


# 通过继承EnumEvent类创建自定义事件
# Create custom events by inheriting the EnumEvent class
class MessageEvent(EnumEvent):
    MESSAGE_CREATE = auto()
    MESSAGE_DELETE = auto()


# 你也可以通过继承AbstractEvent类创建自定义事件
# You can also create custom events by inheriting the AbstractEvent class
class LifeCycleEvent(AbstractEvent):
    def __init__(self, online: bool, status: bool) -> None:
        self.online = online
        self.status = status


# 然后可以为自定义事件注册回调函数
# You can then register a callback function for custom events
@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(ctx: EventContext) -> None:
    message = ctx.args[0]
    logger.info(f"Async message creating: {message}")


@bus.on(MessageEvent.MESSAGE_DELETE)
async def async_message_delete(ctx: EventContext) -> None:
    message = ctx.args[0]
    logger.info(f"Async message deleting: {message}")


@bus.on(LifeCycleEvent)
async def async_life_cycle(ctx: EventContext[LifeCycleEvent]) -> None:
    # emit 时直接传入 AbstractEvent 实例，实例可通过 ctx.event 访问
    # Pass an AbstractEvent instance directly to emit;
    # the instance is then available via ctx.event
    event = ctx.event
    logger.info(f"Async life_cycle: {event.online}, {event.status}")


async def main() -> None:
    # 通过 asyncio.gather 同时触发多个事件
    # Trigger multiple events at the same time via asyncio.gather
    await asyncio.gather(
        bus.emit(LifeCycleEvent(True, True)),
        bus.emit(MessageEvent.MESSAGE_CREATE, "Hello"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "Send from python"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is also a test message"),
        bus.emit(MessageEvent.MESSAGE_DELETE, "Delete some message"),
        bus.emit(LifeCycleEvent(False, False)),
    )


# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
