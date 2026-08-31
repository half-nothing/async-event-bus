# 异常处理策略
# Exception strategies
import asyncio
import sys

from loguru import logger

from async_event_bus import EventBus, EventContext, ExceptionStrategy, MultipleError

# 设置日志级别
# Set log level
logger.remove()
logger.add(sys.stdout, level="TRACE")


def success(ctx: EventContext) -> str:
    """正常的同步回调，返回一个结果"""
    # A normal sync callback that returns a result
    logger.info(f"success callback ran: {ctx.args[0]}")
    return f"success: {ctx.args[0]}"


def another_success(ctx: EventContext) -> str:
    """另一个正常的同步回调"""
    # Another normal sync callback
    logger.info(f"another_success callback ran: {ctx.args[0]}")
    return f"another: {ctx.args[0]}"


def failure(ctx: EventContext) -> None:
    """会抛异常的回调"""
    # A callback that raises an exception
    logger.info(f"failure callback ran: {ctx.args[0]}")
    raise ValueError(f"failure: {ctx.args[0]}")


async def demo_collect() -> None:
    # 策略一：COLLECT（默认）——所有回调都会执行，异常统一以 MultipleError 抛出
    # Strategy 1: COLLECT (default) — all callbacks run, then exceptions are
    # raised together as a single MultipleError
    bus: EventBus = EventBus(exception_strategy=ExceptionStrategy.COLLECT)
    bus.subscribe("event", success)
    bus.subscribe("event", failure)
    try:
        await bus.emit("event", "collect")
    except MultipleError as e:
        logger.info(f"[COLLECT] collected {len(e.exceptions)} exception(s)")
        for exc in e.exceptions:
            logger.info(f"[COLLECT]   - {exc}")


async def demo_raise() -> None:
    # 策略二：RAISE——遇到第一个异常立即抛出，中止剩余回调
    # Strategy 2: RAISE — the first exception is re-raised immediately,
    # aborting the remaining callbacks
    bus: EventBus = EventBus(exception_strategy=ExceptionStrategy.RAISE)
    bus.subscribe("event", failure)
    bus.subscribe("event", success)   # 不会被执行 / never runs
    try:
        await bus.emit("event", "raise")
    except ValueError as e:
        logger.info(f"[RAISE] re-raised immediately: {e}")


async def demo_ignore() -> None:
    # 策略三：IGNORE——异常被记录并跳过，emit 返回 None
    # Strategy 3: IGNORE — exceptions are logged and skipped, emit returns None
    bus: EventBus = EventBus(exception_strategy=ExceptionStrategy.IGNORE)
    bus.subscribe("event", failure)
    bus.subscribe("event", success)
    result = await bus.emit("event", "ignore")
    logger.info(f"[IGNORE] emit returned: {result}")


async def demo_return() -> None:
    # 策略四：RETURN——不抛异常，emit 返回 EmitResult，成功结果与异常分开存放
    # Strategy 4: RETURN — nothing is raised; emit returns an EmitResult with
    # successful outcomes and exceptions kept in separate lists
    bus: EventBus = EventBus(exception_strategy=ExceptionStrategy.RETURN)
    bus.subscribe("event", success)
    bus.subscribe("event", failure)
    bus.subscribe("event", another_success)
    result = await bus.emit("event", "return")
    assert result is not None
    logger.info(f"[RETURN] {len(result.results)} result(s), {len(result.exceptions)} exception(s)")
    for r in result.results:
        logger.info(f"[RETURN]   - result: {r}")
    for exc in result.exceptions:
        logger.info(f"[RETURN]   - exception: {exc}")


async def main() -> None:
    await demo_collect()
    await demo_raise()
    await demo_ignore()
    await demo_return()


# 程序入口
# Program entry point
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
