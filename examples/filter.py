import asyncio
import sys
from enum import auto

from loguru import logger

from async_event_bus import Event, EventBus

# 创建事件总线实例
# Create an event bus instance
bus = EventBus()

# 设置日志级别
# Set log level
logger.remove()
logger.add(sys.stdout, level="TRACE")


# 通过继承Event类创建自定义事件
# Create custom events by inheriting the Event class
class MessageEvent(Event):
    MESSAGE_CREATE = auto()


# 通过添加全局过滤器来过滤事件
# Filter events by adding global filters
@bus.global_event_filter()
async def global_filter(event: Event, *args, **kwargs) -> bool:
    logger.info(f"Global filter called, event: {event}")
    return False


# 通过添加事件过滤器来对指定事件进行过滤
# Filter specified events by adding event filters
@bus.event_filter(MessageEvent.MESSAGE_CREATE)
async def message_filter(message: str, *args, **kwargs) -> bool:
    logger.info(f"Message filter called")
    if message.find("forbidden") != -1:
        logger.info(f"Forbidden message found: {message}")
        return True
    return False


# 为自定义事件注册回调函数
# Register a callback function for custom events
@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(message: str, *args, **kwargs) -> None:
    assert message.find("forbidden") == -1
    logger.info(f"Async message creating: {message}")


async def main():
    # 通过 asyncio.gather 同时触发多个事件
    # Trigger multiple events at the same time via asyncio.gather
    await asyncio.gather(
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a forbidden test message")
    )
    # 输出示例
    # Output example
    # 2025-07-29 19:02:38.659 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function global_filter at 0x000001D4A0E21DA0>, weight=1, async=True)
    # 2025-07-29 19:02:38.659 | DEBUG    | async_event_bus.module.bus_filter:add_global_filter:99 - Global filter global_filter has been added, weight=1
    # 2025-07-29 19:02:38.659 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function message_filter at 0x000001D4A0E214E0>, weight=1, async=True)
    # 2025-07-29 19:02:38.659 | DEBUG    | async_event_bus.module.bus_filter:add_filter:163 - Event filter message_filter has been added to event MessageEvent.MESSAGE_CREATE, weight=1
    # 2025-07-29 19:02:38.659 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function async_message_create at 0x000001D4A0E27A60>, weight=1, async=True)
    # 2025-07-29 19:02:38.659 | DEBUG    | async_event_bus.module.base_bus:decorator:45 - async_message_create has subscribed to MessageEvent.MESSAGE_CREATE, weight=1
    # 2025-07-29 19:02:38.660 | INFO     | __main__:global_filter:28 - Global filter called, event: MessageEvent.MESSAGE_CREATE
    # 2025-07-29 19:02:38.660 | INFO     | __main__:message_filter:35 - Message filter called
    # 2025-07-29 19:02:38.660 | INFO     | __main__:global_filter:28 - Global filter called, event: MessageEvent.MESSAGE_CREATE
    # 2025-07-29 19:02:38.660 | INFO     | __main__:message_filter:35 - Message filter called
    # 2025-07-29 19:02:38.660 | INFO     | __main__:message_filter:37 - Forbidden message found: This is a forbidden test message
    # 2025-07-29 19:02:38.660 | INFO     | __main__:async_message_create:47 - Async message creating: This is a test message


# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
