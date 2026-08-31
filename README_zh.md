# async-event-bus

一个简单易用的 Python3 异步事件总线

[English](README.md) | 简体中文

---
[![ReleaseCard]][Release]![ReleaseDataCard]  
![LastCommitCard]![ProjectLanguageCard]![ProjectLicense]
---

## 特性

- **多种事件类型** — 支持字符串、`EnumEvent` 枚举成员、`AbstractEvent` 类
- **同步与异步回调** — 同步回调按权重顺序依次执行，异步回调并发执行
- **类型化的 `EventContext`** — 每个回调都会收到的事件载体，可继承以附加业务字段
- **过滤器（Filters）** — 全局与事件级过滤器，返回 `False` 即可终止事件传播
- **注入器（Injectors）** — 全局与事件级注入器，在订阅者执行前原地修改上下文
- **权重排序** — 权重越高越先执行（同步回调）
- **并发控制** — 信号量限制异步回调的并发数
- **可配置的异常处理** — 快速失败模式，或收集所有异常为 `MultipleError`
- **`emit_sync`** — 供同步代码使用的阻塞式触发
- **模块化设计** — `EventBus` 由 `CoreModule`、`InjectModule`、`FilterModule` 通过 MRO 组合而成；也可继承 `BaseModule`
  编写自己的模块

## 安装

```shell
pip install async-event-bus
```

需要 Python 3.12 及以上版本。

## 快速开始

```python
import asyncio

from loguru import logger

from async_event_bus import EventBus, EventContext

bus = EventBus()


@bus.on("message")
async def message_handler(ctx: EventContext) -> None:
    logger.info(f"message received: {ctx.args[0]}")


async def main():
    await asyncio.gather(
        bus.emit("message", "Hello"),
        bus.emit("message", "This is a test message"),
        bus.emit("message", "Send from python"),
        bus.emit("message", "This is also a test message")
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
```

回调统一接收 `EventContext`（或其子类），emit 传入的参数通过 `ctx.args` / `ctx.kwargs`
获取；如需直接展开传参，参见 [expand_args / expand_kwargs](#expand_args--expand_kwargs)。

## 自定义事件

支持三种事件键：字符串、`EnumEvent` 枚举成员、`AbstractEvent` 类。

```python
from enum import auto

from async_event_bus import AbstractEvent, EnumEvent, EventBus, EventContext

bus = EventBus()


# 1. 枚举风格事件
class MessageEvent(EnumEvent):
    MESSAGE_CREATE = auto()
    MESSAGE_DELETE = auto()


# 2. 类风格事件
class LifeCycleEvent(AbstractEvent):
    def __init__(self, online: bool, status: bool):
        self.online = online
        self.status = status


@bus.on(MessageEvent.MESSAGE_CREATE)
async def on_create(ctx: EventContext) -> None:
    logger.info(f"creating: {ctx.args[0]}")


@bus.on(LifeCycleEvent)
async def on_life_cycle(ctx: EventContext) -> None:
    # 将 AbstractEvent 实例直接传给 emit，可通过 ctx.event 访问该实例
    event = ctx.event  # type: LifeCycleEvent
    logger.info(f"life cycle: {event.online}, {event.status}")


await bus.emit(MessageEvent.MESSAGE_CREATE, "hello")  # 需在 async 上下文中调用
await bus.emit(LifeCycleEvent(True, True))
```

## 自定义 EventContext

继承 `EventContext` 以附加业务字段，再将子类作为 `context_class` 传给 `EventBus`。
注入器（见下文）通常负责在订阅者执行前填充这些字段。

```python
from dataclasses import dataclass

from async_event_bus import EventBus, EventContext


@dataclass
class AppContext(EventContext):
    user: str = ""


bus = EventBus(context_class=AppContext)


@bus.global_event_inject()
async def inject_user(ctx: AppContext) -> None:
    ctx.user = await fetch_user(ctx.kwargs.get("user_id"))


@bus.on("message")
async def on_message(ctx: AppContext) -> None:
    print(f"{ctx.user}: {ctx.args}")
```

## 过滤器

过滤器负责拦截事件传播。返回 `True` 放行，返回 `False` 立即终止本次事件——
剩余的过滤器和所有订阅者都会被跳过。

- 先执行全局过滤器，再执行事件级过滤器。
- 全局过滤器始终接收 `ctx`；事件级过滤器与订阅者一样支持
  `expand_args` / `expand_kwargs` 展开传参。

```python
@bus.global_event_filter()
async def auth_guard(ctx: EventContext) -> bool:
    return ctx.kwargs.get("user") is not None  # 返回 False 终止传播


@bus.event_filter(MessageEvent.MESSAGE_CREATE)
def content_filter(ctx: EventContext) -> bool:
    return "forbidden" not in ctx.args[0]
```

编程式等价方法：`add_global_filter`、`add_filter`，以及对应的
`remove_global_filter` / `remove_filter`。

## 注入器

注入器在订阅者执行前原地修改上下文。返回值会被忽略——副作用发生在 `ctx` 上。
若任意注入器抛异常，本次事件会被丢弃，订阅者不会拿到不完整的上下文。

- 先执行全局注入器，再执行事件级注入器。
- 与过滤器相同：全局注入器始终接收 `ctx`，事件级注入器支持
  `expand_args` / `expand_kwargs`。

```python
import time


@bus.global_event_inject()
async def add_timestamp(ctx: EventContext) -> None:
    ctx.kwargs["timestamp"] = time.time()


@bus.event_inject(MessageEvent.MESSAGE_CREATE)
async def add_message_len(ctx: EventContext) -> None:
    ctx.kwargs["message_len"] = len(ctx.args[0])
```

编程式等价方法：`add_global_inject`、`add_inject`，以及对应的
`remove_global_inject` / `remove_inject`。

## 权重与执行顺序

权重越高越先执行。同步回调总是先于异步回调执行：按权重降序依次运行；
异步回调通过 `asyncio.gather` 并发执行，因此权重对异步回调没有意义。

```python
@bus.on("message", weight=10)
def high_priority(ctx: EventContext) -> None:
    ...


@bus.on("message", weight=1)
def low_priority(ctx: EventContext) -> None:
    ...
```

## expand_args / expand_kwargs

默认情况下回调接收 `EventContext` 对象。设置 `expand_args=True` /
`expand_kwargs=True` 后，`ctx.args` / `ctx.kwargs` 会被解包直接传入，
事件级处理器、过滤器、注入器的签名可以更简洁。

```python
@bus.on("message")
async def handler(ctx: EventContext, message: str) -> None:
    print(message)


await bus.emit("message", "hello", expand_args=True)
```

## 异常处理

回调抛出的异常按照构造时选择的 `ExceptionStrategy` 策略处理，共有四种：

| 策略                              | 行为                                        |
|---------------------------------|-------------------------------------------|
| `ExceptionStrategy.IGNORE`      | 忽略异常：记录日志后继续执行，`emit` 返回 `None`。          |
| `ExceptionStrategy.RAISE`       | 快速失败：遇到第一个异常立即抛出，中止剩余回调。                  |
| `ExceptionStrategy.COLLECT`（默认） | 所有回调照常执行，异常统一以 `MultipleError` 抛出。        |
| `ExceptionStrategy.RETURN`      | 不抛异常——`emit` 返回 `EmitResult`，成功结果与异常分开存放。 |

```python
from async_event_bus import EventBus, ExceptionStrategy, MultipleError

bus = EventBus(exception_strategy=ExceptionStrategy.COLLECT)  # 默认

try:
    await bus.emit("message", "hello")
except MultipleError as e:
    for exc in e.exceptions:
        print(exc)
```

使用 `RETURN` 策略时，`emit`（以及 `emit_sync`）返回一个 `EmitResult` 而不是
抛出异常——成功结果与异常分别存放在两个列表中：

```python
from async_event_bus import EmitResult, EventBus, EventContext, ExceptionStrategy

bus = EventBus(exception_strategy=ExceptionStrategy.RETURN)


@bus.on("message")
def ok(ctx: EventContext) -> str:
    return "hello"


@bus.on("message")
def boom(ctx: EventContext) -> None:
    raise ValueError("boom")


result: EmitResult | None = await bus.emit("message")
# result.results == ["hello"]                     -- 成功结果
# result.exceptions == [ValueError("boom")]       -- 异常，与结果分开
```

策略也可以通过总线的 `exception_strategy` 属性在运行时切换。

## 自定义事件总线与模块

`EventBus` 本身只是 `CoreModule`（订阅/发布）与 `InjectModule`、`FilterModule`
通过 MRO 组合的结果。你可以用同样的方式组合自己的总线，也可以在 `BaseModule`
上覆写 `before_emit` 编写自定义模块。

### 自定义事件总线（继承 CoreModule）

```python
from async_event_bus import CoreModule, EnumEvent, EventContext, EventType


class CustomEventBus(CoreModule):
    # 返回 False 终止传播；也可以在这里修改 ctx
    async def before_emit(self, event: EventType, ctx: EventContext) -> bool:
        if event == MessageEvent.MESSAGE_DELETE:
            return False
        ctx.kwargs["timestamp"] = time.time()
        return await super().before_emit(event, ctx)
```

### 自定义模块（继承 BaseModule）

```python
from async_event_bus import BaseModule, CoreModule, EventContext, EventType


class CustomModule(BaseModule[EventContext, bool]):
    async def before_emit(self, event: EventType, ctx: EventContext) -> bool:
        # 在这里检查/修改事件，然后继续传播链
        return await super().before_emit(event, ctx)


class CustomEventBus(CoreModule, CustomModule):
    pass
```

## 示例

`examples/` 目录下有可直接运行、带完整注释的示例：

- `basic_use.py` — 字符串事件的订阅与发布
- `custom_event.py` — `EnumEvent` 与 `AbstractEvent` 事件
- `custom_event_bus.py` — 继承 `CoreModule` 的自定义总线
- `custom_event_bus_module.py` — 通过 MRO 组合的自定义模块
- `filter.py` — 全局与事件级过滤器
- `inject.py` — 全局与事件级注入器
- `exception_strategy.py` — `ExceptionStrategy` 四种异常处理模式（IGNORE / RAISE / COLLECT / RETURN）

## 许可证

[MIT](LICENSE)

[ReleaseCard]: https://img.shields.io/github/v/release/half-nothing/async-event-bus?style=for-the-badge&logo=github

[ReleaseDataCard]: https://img.shields.io/github/release-date/half-nothing/async-event-bus?display_date=published_at&style=for-the-badge&logo=github

[LastCommitCard]: https://img.shields.io/github/last-commit/half-nothing/async-event-bus?display_timestamp=committer&style=for-the-badge&logo=github

[ProjectLanguageCard]: https://img.shields.io/github/languages/top/half-nothing/async-event-bus?style=for-the-badge&logo=github

[ProjectLicense]: https://img.shields.io/badge/License-MIT-blue?style=for-the-badge&logo=github

[Release]: https://www.github.com/half-nothing/async-event-bus/releases/latest
