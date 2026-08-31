# 自定义事件总线模块
# Custom event bus modules
import asyncio
import sys
from datetime import datetime
from enum import auto

from loguru import logger

from async_event_bus import BaseModule, CoreModule, EnumEvent, EventContext, EventType


# 自定义事件总线模块，需要继承自BaseModule
# 通过覆写 before_emit 参与事件传播链：
#   返回 False 终止本次事件传播；返回 True 继续传播
# 也可以在这里修改 ctx（例如向 ctx.kwargs 注入数据）
# Custom event bus module, must inherit from BaseModule
# Override before_emit to take part in the propagation chain:
#   returning False stops the event; returning True continues
# You can also mutate ctx here (e.g. inject data into ctx.kwargs)
class CustomModule(BaseModule[EventContext, bool]):
    async def before_emit(self, event: EventType, ctx: EventContext) -> bool:
        logger.info(f"Resolve event: {event}, {ctx.args}, {ctx.kwargs}")
        if event == MessageEvent.MESSAGE_DELETE:
            logger.info(f"Reject delete message: {event}")
            return False
        ctx.kwargs["timestamp"] = datetime.now()
        return await super().before_emit(event, ctx)

    # 清理模块状态
    # Clean up the module
    def clear(self) -> None:
        pass


# 自定义事件总线：通过继承组合 CoreModule 与自定义模块
# EventBus 本身也是通过 MRO 组合 CoreModule、InjectModule、FilterModule 得到的，
# 因此自定义模块可以用同样的方式加入传播链
# Custom event bus: combine CoreModule with a custom module via inheritance (MRO)
# EventBus itself is built the same way (CoreModule + InjectModule + FilterModule),
# so custom modules can join the propagation chain the same way
class CustomEventBus(CoreModule, CustomModule):
    pass


# 创建自定义事件总线实例
# Create a custom event bus instance
bus = CustomEventBus()

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
    # 删除事件会被自定义模块的 before_emit 拒绝，因此 async_message_delete 不会被执行
    # Trigger multiple events at the same time via asyncio.gather
    # Delete events are rejected by the custom module's before_emit,
    # so async_message_delete never runs
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
