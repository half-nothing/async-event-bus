import asyncio
import sys

from loguru import logger

from async_event_bus import EventBus

# 创建事件总线实例
# Create an event bus instance
bus = EventBus()

# 设置日志级别
# Set log level
logger.remove()
logger.add(sys.stdout, level="TRACE")


# 为事件注册回调函数
# Register a callback function for the event
@bus.on("message")
async def message_handler(message: str, *args, **kwargs) -> None:
    logger.info(f"message received: {message}")


async def main():
    # 通过 asyncio.gather 同时触发多个事件
    # Trigger multiple events at the same time via asyncio.gather
    await asyncio.gather(
        bus.emit("message", "Hello"),
        bus.emit("message", "This is a test message"),
        bus.emit("message", "Send from python"),
        bus.emit("message", "This is also a test message")
    )
    # 输出示例
    # Output example
    # 2025-07-29 18:19:28.729 | TRACE    | async_event_bus.event.event_callback_container:add_async_callback:31 - Adding async callback: EventCallback(callback=<function message_handler at 0x000002162793B420>, weight=1, async=True)
    # 2025-07-29 18:19:28.729 | DEBUG    | async_event_bus.module.base_bus:decorator:45 - message_handler has subscribed to message, weight=1
    # 2025-07-29 18:19:28.730 | INFO     | __main__:message_handler:22 - message received: Hello
    # 2025-07-29 18:19:28.730 | INFO     | __main__:message_handler:22 - message received: This is a test message
    # 2025-07-29 18:19:28.730 | INFO     | __main__:message_handler:22 - message received: Send from python
    # 2025-07-29 18:19:28.730 | INFO     | __main__:message_handler:22 - message received: This is also a test message

# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
