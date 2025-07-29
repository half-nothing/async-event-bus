# 自定义事件总线
# Custom event bus
import asyncio
import sys
from datetime import datetime
from enum import auto
from typing import Union

from loguru import logger

from async_event_bus import BaseBus, Event


# 你可以选择继承EventBus这个类，这样基础功能、注入器和过滤器都是默认存在的
# 如果你想更进一步自定义事件总线，请继承BaseBus类
# BaseBus 这个类只实现了最基础的时间订阅和发布功能
# You can choose to inherit the EventBus class
# so that the underlying features, injectors, and filters are all present by default
# If you want to customize the event bus a step further, inherit the BaseBus class
# BaseBus class implements only the most basic time subscription and publishing functions
class CustomEventBus(BaseBus):

    # 这个函数会在事件开始传播之前调用，可以通过返回True来终止这次事件传播
    # 还有一个返回值是返回要添加的属性值，用于注入器实现
    # This function is called before the event starts propagating, and can be terminated by returning True
    # There is also a return value that returns the attribute value to be added for the injector implementation
    async def before_emit(self, event: Union[Event, str], *args, **kwargs) -> tuple[bool, dict]:
        if event == MessageEvent.MESSAGE_DELETE:
            logger.info(f"Reject delete message: {event}")
            return True, {}
        return False, {"timestamp": datetime.now()}


# 创建自定义事件总线实例
# Create an event bus instance
bus = CustomEventBus()

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
    logger.info(f"Kwargs: {kwargs}")


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
    # 2025-07-29 19:16:50.703 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function async_message_create at 0x000001742C0914E0>, weight=1, async=True)
    # 2025-07-29 19:16:50.703 | DEBUG    | async_event_bus.module.base_bus:decorator:45 - async_message_create has subscribed to MessageEvent.MESSAGE_CREATE, weight=1
    # 2025-07-29 19:16:50.703 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function async_message_delete at 0x000001742C09B880>, weight=1, async=True)
    # 2025-07-29 19:16:50.703 | DEBUG    | async_event_bus.module.base_bus:decorator:45 - async_message_delete has subscribed to MessageEvent.MESSAGE_DELETE, weight=1
    # 2025-07-29 19:16:50.704 | INFO     | __main__:before_emit:27 - Reject delete message: MessageEvent.MESSAGE_DELETE
    # 2025-07-29 19:16:50.704 | INFO     | __main__:async_message_create:53 - Async message creating: Hello
    # 2025-07-29 19:16:50.704 | INFO     | __main__:async_message_create:54 - Kwargs: {'timestamp': datetime.datetime(2025, 7, 29, 19, 16, 50, 703811)}
    # 2025-07-29 19:16:50.704 | INFO     | __main__:async_message_create:53 - Async message creating: This is a test message
    # 2025-07-29 19:16:50.704 | INFO     | __main__:async_message_create:54 - Kwargs: {'timestamp': datetime.datetime(2025, 7, 29, 19, 16, 50, 704647)}
    # 2025-07-29 19:16:50.704 | INFO     | __main__:async_message_create:53 - Async message creating: Send from python
    # 2025-07-29 19:16:50.704 | INFO     | __main__:async_message_create:54 - Kwargs: {'timestamp': datetime.datetime(2025, 7, 29, 19, 16, 50, 704647)}
    # 2025-07-29 19:16:50.704 | INFO     | __main__:async_message_create:53 - Async message creating: This is also a test message
    # 2025-07-29 19:16:50.704 | INFO     | __main__:async_message_create:54 - Kwargs: {'timestamp': datetime.datetime(2025, 7, 29, 19, 16, 50, 704647)}


# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
