# 事件过滤器
# Event filters
import asyncio
import sys
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


# 通过添加全局过滤器来过滤事件
# 过滤器返回 True 放行，返回 False 终止传播
# Filter events by adding global filters
# Return True to allow propagation, False to stop the event
@bus.global_event_filter()
async def global_filter(ctx: EventContext) -> bool:
    logger.info(f"Global filter called, event: {ctx.event}")
    return True


# 通过添加事件过滤器来对指定事件进行过滤
# 事件过滤器在全局过滤器通过后执行
# Filter specified events by adding event filters
# Event filters run after global filters have passed
@bus.event_filter(MessageEvent.MESSAGE_CREATE)
async def message_filter(ctx: EventContext) -> bool:
    logger.info("Message filter called")
    message = ctx.args[0]
    if message.find("forbidden") != -1:
        logger.info(f"Forbidden message found: {message}")
        return False
    return True


# 为自定义事件注册回调函数
# Register a callback function for custom events
@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(ctx: EventContext) -> None:
    message = ctx.args[0]
    assert message.find("forbidden") == -1
    logger.info(f"Async message creating: {message}")


async def main():
    # 第二条消息包含 forbidden，会被过滤器拦截，回调不会执行
    # The second message contains "forbidden", so it is blocked by the filter
    # and the callback never runs
    await asyncio.gather(
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a forbidden test message")
    )


# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
