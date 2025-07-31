# 自定义事件
# Custom events
import asyncio
import sys
from enum import Enum, auto

from loguru import logger

from async_event_bus import AbstractEvent, EnumEvent, EventBus

# 创建事件总线实例
# Create an event bus instance
bus = EventBus()

# 设置日志级别
# Set log level
logger.remove()
logger.add(sys.stdout, level="TRACE")


# 通过继承EnumEvent类创建自定义事件
# Create custom events by inheriting the Event class
class MessageEvent(EnumEvent):
    MESSAGE_CREATE = auto()
    MESSAGE_DELETE = auto()


# 你也可以通过继承AbstractEvent类创建自定义事件
# You can also create custom events by inheriting the AbstractEvent class
class LifeCycleEvent(AbstractEvent):
    def __init__(self, online: bool, status: bool):
        self.online = online
        self.status = status


# 然后可以为自定义事件注册回调函数
# You can then register a callback function for custom events
@bus.on(MessageEvent.MESSAGE_CREATE)
async def async_message_create(message: str, *args, **kwargs) -> None:
    logger.info(f"Async message creating: {message}")


@bus.on(MessageEvent.MESSAGE_DELETE)
async def async_message_delete(message: str, *args, **kwargs) -> None:
    logger.info(f"Async message deleting: {message}")


@bus.on(LifeCycleEvent)
async def async_life_cycle(event: LifeCycleEvent, *args, **kwargs) -> None:
    logger.info(f"Async life_cycle: {event.online}, {event.status}")


async def main():
    # 通过 asyncio.gather 同时触发多个事件
    # Trigger multiple events at the same time via asyncio.gather
    await asyncio.gather(
        bus.emit(LifeCycleEvent, LifeCycleEvent(True, True)),
        bus.emit(MessageEvent.MESSAGE_CREATE, "Hello"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is a test message"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "Send from python"),
        bus.emit(MessageEvent.MESSAGE_CREATE, "This is also a test message"),
        bus.emit(MessageEvent.MESSAGE_DELETE, "Delete some message"),
        bus.emit(LifeCycleEvent, LifeCycleEvent(False, False)),
    )
    # 输出示例
    # Output example
    # 2025-07-31 15:56:49.565 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function async_message_create at 0x0000020C21BF7740>, weight=1, async=True)
    # 2025-07-31 15:56:49.565 | DEBUG    | async_event_bus.module.base_bus:decorator:45 - async_message_create has subscribed to MessageEvent.MESSAGE_CREATE, weight=1
    # 2025-07-31 15:56:49.565 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function async_message_delete at 0x0000020C21BF7880>, weight=1, async=True)
    # 2025-07-31 15:56:49.565 | DEBUG    | async_event_bus.module.base_bus:decorator:45 - async_message_delete has subscribed to MessageEvent.MESSAGE_DELETE, weight=1
    # 2025-07-31 15:56:49.565 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function async_life_cycle at 0x0000020C21BF7920>, weight=1, async=True)
    # 2025-07-31 15:56:49.565 | DEBUG    | async_event_bus.module.base_bus:decorator:45 - async_life_cycle has subscribed to <class '__main__.LifeCycleEvent'>, weight=1
    # 2025-07-31 15:56:49.567 | INFO     | __main__:async_life_cycle:50 - Async life_cycle: True, True
    # 2025-07-31 15:56:49.567 | INFO     | __main__:async_message_create:40 - Async message creating: Hello
    # 2025-07-31 15:56:49.567 | INFO     | __main__:async_message_create:40 - Async message creating: This is a test message
    # 2025-07-31 15:56:49.567 | INFO     | __main__:async_message_create:40 - Async message creating: Send from python
    # 2025-07-31 15:56:49.567 | INFO     | __main__:async_message_create:40 - Async message creating: This is also a test message
    # 2025-07-31 15:56:49.567 | INFO     | __main__:async_message_delete:45 - Async message deleting: Delete some message
    # 2025-07-31 15:56:49.567 | INFO     | __main__:async_life_cycle:50 - Async life_cycle: False, False


# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
