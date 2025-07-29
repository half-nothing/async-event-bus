import asyncio
import sys
from datetime import datetime
from enum import auto
from typing import Any

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


# 通过添加全局注入器来为事件注入参数
# Inject parameters into events by adding a global injector
@bus.global_event_inject()
async def global_inject(*args, **kwargs) -> dict[str, Any]:
    logger.info(f"Global inject called")
    return {
        "time": datetime.now().timestamp()
    }


# 通过添加事件注入器来为某个事件注入参数
# Inject parameters into an event by adding an event injector
@bus.event_inject(MessageEvent.MESSAGE_CREATE)
async def message_inject(message: str, *args, **kwargs) -> dict[str, Any]:
    logger.info(f"Message inject called")
    return {
        "message_len": len(message)
    }


# 为自定义事件注册回调函数
# Register a callback function for custom events
@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(message: str, *args, **kwargs) -> None:
    logger.info(f"Async message creating: {message}")
    logger.info(f"Message create time: {kwargs.get('time')}")
    logger.info(f"Message len: {kwargs.get('message_len')}")
    assert kwargs.get('time') is not None
    assert kwargs.get('message_len') == 22


async def main():
    # 触发事件
    await bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message")
    # 输出示例
    # Output example
    # 2025-07-29 19:04:10.228 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function global_inject at 0x0000017B931E13A0>, weight=1, async=True)
    # 2025-07-29 19:04:10.228 | DEBUG    | async_event_bus.module.bus_inject:add_global_inject:55 - Global inject global_inject has been added, weight=1
    # 2025-07-29 19:04:10.229 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function message_inject at 0x0000017B931E14E0>, weight=1, async=True)
    # 2025-07-29 19:04:10.229 | DEBUG    | async_event_bus.module.bus_inject:add_inject:71 - Event inject message_inject has been added to event MessageEvent.MESSAGE_CREATE, weight=1
    # 2025-07-29 19:04:10.229 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function async_message_create at 0x0000017B931E7880>, weight=1, async=True)
    # 2025-07-29 19:04:10.229 | DEBUG    | async_event_bus.module.base_bus:decorator:45 - async_message_create has subscribed to MessageEvent.MESSAGE_CREATE, weight=1
    # 2025-07-29 19:04:10.230 | INFO     | __main__:global_inject:30 - Global inject called
    # 2025-07-29 19:04:10.230 | INFO     | __main__:message_inject:39 - Message inject called
    # 2025-07-29 19:04:10.231 | INFO     | __main__:async_message_create:48 - Async message creating: This is a test message
    # 2025-07-29 19:04:10.231 | INFO     | __main__:async_message_create:49 - Message create time: 1753787050.23089
    # 2025-07-29 19:04:10.231 | INFO     | __main__:async_message_create:50 - Message len: 22


# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
