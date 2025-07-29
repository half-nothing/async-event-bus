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
    MESSAGE_DELETE = auto()


# 然后可以为自定义事件注册回调函数
# You can then register a callback function for custom events
@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(message: str, *args, **kwargs) -> None:
    logger.info(f"Async message creating: {message}")


@bus.on(MessageEvent.MESSAGE_DELETE)
async def async_message_delete(message: str, *args, **kwargs) -> None:
    logger.info(f"Async message deleting: {message}")


async def main():
    # 通过 asyncio.gather 同时触发多个事件
    # Trigger multiple events at the same time via asyncio.gather
    await asyncio.gather(
        bus.emit(MessageEvent.MESSAGE_CREATE, "Hello"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "Send from python"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is also a test message"),
        bus.emit(MessageEvent.MESSAGE_DELETE, "Delete some message")
    )
    # 输出示例
    # Output example
    # 2025-07-29 18:18:47.492 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function async_message_create at 0x0000021C8B32D440>, weight=1, async=True)
    # 2025-07-29 18:18:47.492 | DEBUG    | async_event_bus.module.base_bus:decorator:45 - async_message_create has subscribed to MessageEvent.MESSAGE_CREATE, weight=1
    # 2025-07-29 18:18:47.492 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function async_message_delete at 0x0000021C8B36F880>, weight=1, async=True)
    # 2025-07-29 18:18:47.492 | DEBUG    | async_event_bus.module.base_bus:decorator:45 - async_message_delete has subscribed to MessageEvent.MESSAGE_DELETE, weight=1
    # 2025-07-29 18:18:47.494 | INFO     | __main__:async_message_create:30 - Async message creating: Hello
    # 2025-07-29 18:18:47.494 | INFO     | __main__:async_message_create:30 - Async message creating: This is a test message
    # 2025-07-29 18:18:47.494 | INFO     | __main__:async_message_create:30 - Async message creating: Send from python
    # 2025-07-29 18:18:47.494 | INFO     | __main__:async_message_create:30 - Async message creating: This is also a test message
    # 2025-07-29 18:18:47.494 | INFO     | __main__:async_message_delete:35 - Async message deleting: Delete some message


# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
