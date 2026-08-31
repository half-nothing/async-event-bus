# 事件总线的基础用法
# Basic usage of event bus
import asyncio
import sys

from loguru import logger

from async_event_bus import EventBus, EventContext

# 创建事件总线实例
# Create an event bus instance
bus: EventBus = EventBus()

# 设置日志级别
# Set log level
logger.remove()
logger.add(sys.stdout, level="TRACE")


# 为事件注册回调函数
# 回调统一接收 EventContext，可通过 ctx.args / ctx.kwargs 访问 emit 传入的参数
# 如果希望回调直接接收参数而非 EventContext，可在 emit 时传入 expand_args=True
# Register a callback function for the event
# Callbacks receive an EventContext; access emit args via ctx.args / ctx.kwargs
# Pass expand_args=True to emit() if you want args passed directly instead
@bus.on("message")
async def message_handler(ctx: EventContext) -> None:
    message = ctx.args[0]
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


# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
