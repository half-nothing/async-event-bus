# 自定义事件总线
# Custom event bus
import asyncio
import sys
from datetime import datetime
from enum import auto

from loguru import logger

from async_event_bus import CoreModule, EnumEvent, EventContext, EventType

# 你可以选择继承EventBus这个类，这样基础功能、注入器和过滤器都是默认存在的
# 如果你想更进一步自定义事件总线，请继承CoreModule类
# CoreModule 这个类只实现了最基础的事件订阅和发布功能
# You can choose to inherit the EventBus class
# so that the underlying features, injectors, and filters are all present by default
# If you want to customize the event bus a step further, inherit the CoreModule class
# CoreModule implements only the most basic subscription and publishing functions
class CustomEventBus(CoreModule):
    # 这个函数会在事件开始传播之前调用，返回 False 可以终止这次事件传播
    # 也可以在这里直接修改 ctx（例如向 ctx.kwargs 注入数据）
    # This function is called before the event starts propagating
    # Returning False terminates the propagation
    # You can also mutate ctx directly here (e.g. inject data into ctx.kwargs)
    async def before_emit(self, event: EventType, ctx: EventContext) -> bool:
        if event == MessageEvent.MESSAGE_DELETE:
            logger.info(f"Reject delete message: {event}")
            return False
        ctx.kwargs["timestamp"] = datetime.now()
        return await super().before_emit(event, ctx)


# 创建自定义事件总线实例
# Create a custom event bus instance
bus: CustomEventBus = CustomEventBus()

# 设置日志级别
# Set log level
logger.remove()
logger.add(sys.stdout, level="TRACE")


# 通过继承EnumEvent类创建自定义事件
# Create custom events by inheriting the EnumEvent class
class MessageEvent(EnumEvent):
    MESSAGE_CREATE = auto()
    MESSAGE_DELETE = auto()


# 然后可以为自定义事件注册回调函数
# You can then register a callback function for custom events
@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(ctx: EventContext) -> None:
    message = ctx.args[0]
    logger.info(f"Async message creating: {message}")
    logger.info(f"Kwargs: {ctx.kwargs}")


@bus.on(MessageEvent.MESSAGE_DELETE)
async def async_message_delete(ctx: EventContext) -> None:
    message = ctx.args[0]
    logger.info(f"Async message deleting: {message}")


async def main():
    # 通过 asyncio.gather 同时触发多个事件
    # 删除事件会被 before_emit 拒绝，因此 async_message_delete 不会被执行
    # Trigger multiple events at the same time via asyncio.gather
    # Delete events are rejected by before_emit, so async_message_delete never runs
    await asyncio.gather(
        bus.emit(MessageEvent.MESSAGE_CREATE, "Hello"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "Send from python"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is also a test message"),
        bus.emit(MessageEvent.MESSAGE_DELETE, "Delete some message")
    )


# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
