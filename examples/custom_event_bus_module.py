# 自定义事件总线模块
# Custom event bus modules
import asyncio
import sys
from datetime import datetime
from enum import auto
from typing import Union

from loguru import logger

from async_event_bus import BaseBus, BaseModule, Event


# 自定义事件总线模块, 需要继承自BaseModule
class CustomModule(BaseModule):

    # 执行模块逻辑, 注意这里的args和kwargs是变量而不是可变变量，他们接受事件总线传递过来的参数，并可以对这些参数进行修改
    # 返回True会终止此次事件的传播
    # Executing the module logic, note that args and kwargs here are variables rather than variables,
    # and they accept the parameters passed by the event bus and can modify them
    # Returning to True will stop the propagation of the event
    async def resolve(self, event: Union[Event, str], args, kwargs) -> bool:
        logger.info(f"Resolve event: {event}, {args}, {kwargs}")
        return False

    # 清理模块
    # Clean up the module
    def clear(self) -> None:
        pass


# 自定义事件总线，可以通过继承或者组合来使用模块
# Custom event bus. modules can be used by inheritance or combination
class CustomEventBus(BaseBus, CustomModule):
    def __init__(self) -> None:
        super().__init__()
        self._module = CustomModule()

    async def before_emit(self, event: Union[Event, str], *args, **kwargs) -> tuple[bool, dict]:
        # 这种也可以，但是这样外部调用模块接口会比较麻烦
        # This is also possible, but it will be more troublesome to call the module interface externally
        # if await self._module.resolve(event, args, kwargs):
        #     return True
        if await CustomModule.resolve(self, event, args, kwargs):
            return True, {}
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
    # D:\WorkSpace\python\py-event-bus\.venv\Scripts\python.exe D:\WorkSpace\python\py-event-bus\examples\custom_event_bus_module.py
    # 2025-07-29 19:25:43.832 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function async_message_create at 0x000001F9F66B39C0>, weight=1, async=True)
    # 2025-07-29 19:25:43.832 | DEBUG    | async_event_bus.module.base_bus:decorator:45 - async_message_create has subscribed to MessageEvent.MESSAGE_CREATE, weight=1
    # 2025-07-29 19:25:43.832 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function async_message_delete at 0x000001F9F66B3B00>, weight=1, async=True)
    # 2025-07-29 19:25:43.832 | DEBUG    | async_event_bus.module.base_bus:decorator:45 - async_message_delete has subscribed to MessageEvent.MESSAGE_DELETE, weight=1
    # 2025-07-29 19:25:43.834 | INFO     | __main__:resolve:23 - Resolve event: MessageEvent.MESSAGE_CREATE, ('Hello',), {}
    # 2025-07-29 19:25:43.834 | INFO     | __main__:resolve:23 - Resolve event: MessageEvent.MESSAGE_CREATE, ('This is a test message',), {}
    # 2025-07-29 19:25:43.834 | INFO     | __main__:resolve:23 - Resolve event: MessageEvent.MESSAGE_CREATE, ('Send from python',), {}
    # 2025-07-29 19:25:43.834 | INFO     | __main__:resolve:23 - Resolve event: MessageEvent.MESSAGE_CREATE, ('This is also a test message',), {}
    # 2025-07-29 19:25:43.834 | INFO     | __main__:resolve:23 - Resolve event: MessageEvent.MESSAGE_DELETE, ('Delete some message',), {}
    # 2025-07-29 19:25:43.834 | INFO     | __main__:before_emit:39 - Reject delete message: MessageEvent.MESSAGE_DELETE
    # 2025-07-29 19:25:43.834 | INFO     | __main__:async_message_create:65 - Async message creating: Hello
    # 2025-07-29 19:25:43.834 | INFO     | __main__:async_message_create:66 - Kwargs: {'timestamp': datetime.datetime(2025, 7, 29, 19, 25, 43, 834489)}
    # 2025-07-29 19:25:43.834 | INFO     | __main__:async_message_create:65 - Async message creating: This is a test message
    # 2025-07-29 19:25:43.834 | INFO     | __main__:async_message_create:66 - Kwargs: {'timestamp': datetime.datetime(2025, 7, 29, 19, 25, 43, 834561)}
    # 2025-07-29 19:25:43.834 | INFO     | __main__:async_message_create:65 - Async message creating: Send from python
    # 2025-07-29 19:25:43.834 | INFO     | __main__:async_message_create:66 - Kwargs: {'timestamp': datetime.datetime(2025, 7, 29, 19, 25, 43, 834594)}
    # 2025-07-29 19:25:43.834 | INFO     | __main__:async_message_create:65 - Async message creating: This is also a test message
    # 2025-07-29 19:25:43.834 | INFO     | __main__:async_message_create:66 - Kwargs: {'timestamp': datetime.datetime(2025, 7, 29, 19, 25, 43, 834622)}


# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
