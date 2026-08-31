# 事件注入器
# Event injector
import asyncio
import sys
from datetime import datetime
from enum import auto

from loguru import logger

from async_event_bus import EnumEvent, EventBus, EventContext

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


# 通过添加全局注入器来为事件注入参数
# 注入器原地修改 ctx（例如写入 ctx.kwargs），返回值会被忽略
# Inject parameters into events by adding a global injector
# Injectors mutate ctx in-place (e.g. write into ctx.kwargs); return values are discarded
@bus.global_event_inject()
async def global_inject(ctx: EventContext) -> None:
    logger.info("Global inject called")
    ctx.kwargs["time"] = datetime.now().timestamp()


# 通过添加事件注入器来为某个事件注入参数
# 事件注入器在全局注入器之后执行
# Inject parameters into an event by adding an event injector
# Event injectors run after global injectors
@bus.event_inject(MessageEvent.MESSAGE_CREATE)
async def message_inject(ctx: EventContext) -> None:
    logger.info("Message inject called")
    ctx.kwargs["message_len"] = len(ctx.args[0])


# 为自定义事件注册回调函数
# Register a callback function for custom events
@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(ctx: EventContext) -> None:
    message = ctx.args[0]
    logger.info(f"Async message creating: {message}")
    logger.info(f"Message create time: {ctx.kwargs.get('time')}")
    logger.info(f"Message len: {ctx.kwargs.get('message_len')}")
    assert ctx.kwargs.get('time') is not None
    assert ctx.kwargs.get('message_len') == 22


async def main():
    # 触发事件
    # Trigger an event
    await bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message")


# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
