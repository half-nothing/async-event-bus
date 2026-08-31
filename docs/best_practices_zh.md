# 最佳实践

在真实应用中使用 `async-event-bus` 的实用建议。每节针对一个常见决策点给出推荐做法。

## 事件的组织

- **把某个模块的所有事件集中定义在一处。** 每个领域一个文件（如 `events.py`），
  事件面一目了然、便于发现。
- **可枚举的事件优先用 `EnumEvent`** —— 类型安全、可哈希、自文档化：
  ```python
  class OrderEvent(EnumEvent):
      CREATED = auto()
      CANCELLED = auto()
  ```
- **事件带数据时用 `AbstractEvent`**；把实例传给 `emit`，在回调里以
  `ctx.event` 读回：
  ```python
  @dataclass
  class OrderCreated(AbstractEvent):
      order_id: str
  ```
- **慎用纯字符串** —— 写脚本方便，但容易拼错、难以发现。

## 回调签名

- **默认接收 `EventContext`。** 回调可访问 `ctx.event`、`ctx.args`、
  `ctx.kwargs` 以及自定义上下文子类附加的字段：
  ```python
  @bus.on(OrderCreated)
  async def on_order_created(ctx: EventContext[OrderCreated]) -> None:
      print(ctx.event.order_id)
  ```
- **`expand_args` 只适合简单的纯位置参数**（如单个字符串消息）。它用更短的
  签名换来对上下文的访问受限——注意 *事件级* 过滤器与注入器也必须用同样的
  展开签名，而 *全局* 钩子仍然接收 `ctx`。
- **标注上下文类型**（`ctx: EventContext[MyEvent]`），让类型检查器正确推断
  `ctx.event`。

## 异常策略的选择

| 场景          | 推荐策略                                                |
|-------------|-----------------------------------------------------|
| 开发 / 调试     | `RAISE` —— 第一个失败立刻暴露                                |
| 生产、继续处理     | `COLLECT`（默认）—— 不丢业务，检查 `e.exceptions`              |
| 结果驱动型代码     | `RETURN` —— 检查 `EmitResult.results` / `.exceptions` |
| 非关键、尽力而为的路径 | `IGNORE` —— 记日志后继续                                  |

- 开发期用 `RAISE`，生产切 `COLLECT` —— 通过 `exception_strategy` 属性在
  启动时一行切换：
  ```python
  bus.exception_strategy = ExceptionStrategy.COLLECT if is_prod else ExceptionStrategy.RAISE
  ```
- 使用 `RETURN` 时务必处理 `None` 情况：事件被过滤器拦截或没有订阅者时，
  `emit` 返回 `None` 而非 `EmitResult`。
- **慎用 `IGNORE`** —— 被吞掉的异常只在日志里可见；请确保日志已配置。

## 过滤器与注入器

- **过滤器应当无副作用、保持纯粹** —— 只返回 `True`/`False`，不做别的事。
  把第一个 `False` 当作耗时工作的提前退出。
- **副作用交给注入器** —— 加载用户、会话、时间戳并写入 `ctx`：
  ```python
  @bus.global_event_inject()
  async def attach_user(ctx: EventContext) -> None:
      ctx.user = await load_user(ctx.kwargs["user_id"])
  ```
- **横切规则用全局钩子**（鉴权、租户隔离、限流），事件专属逻辑用事件级钩子。
- **顺序有讲究**：全局过滤器/注入器先于事件级执行；同一层级内需要特定顺序时
  用 `weight`。
- 注入器抛异常会丢弃事件（`COLLECT` 模式下以 `MultipleError` 浮出）——
  订阅者永远不会看到半成品上下文。

## 权重与执行顺序

- **`weight` 只对 *同步* 回调生效。** 异步回调并发执行，永远不要依赖它们的
  相对顺序。
- 需要确定性顺序？把回调写成同步的，或在单个处理器内显式串联工作。
- 权重相同的同步回调按注册顺序执行。

## 并发

- **按处理器依赖的资源调 `max_concurrent_tasks`**（数据库连接池大小、
  API 限流）。默认 10。
- **异步回调适合 IO 密集型工作**（网络、数据库）；CPU 密集型会阻塞事件循环
  —— 可在回调内用 `asyncio.to_thread` 或工作线程池。
- **回调保持短小。** 总线是协作式的：一个慢的同步回调会拖慢同一事件的所有
  其他同步回调。
- `emit` 只是调度异步回调；调用方会等待它们全部完成。

## 自定义上下文与模块

- **扩展 `EventContext`** 承载请求级数据（用户、请求 ID、数据库会话），由
  注入器填充 —— 处理器读取类型化字段，而不是在 `kwargs` 里翻找。
- **横切关注点写成自定义模块**（审计日志、指标、关联 ID）：继承
  `BaseModule` 覆写 `before_emit`，再通过 MRO 组合进自己的总线。
- **覆写结束时务必调用 `super().before_emit(event, ctx)`** —— 它延续协作链，
  最终放行事件。

## 测试

- **每个测试新建独立的 `EventBus`** —— 模块级总线会在测试间泄漏订阅。
- **用 `RETURN` 断言结果**，避免 try/except 噪音：
  ```python
  bus = EventBus(exception_strategy=ExceptionStrategy.RETURN)

  result = await bus.emit("message", "hello")
  assert result is not None
  assert result.results == ["handled"]
  assert not result.exceptions
  ```
- **用 `COLLECT` 断言异常聚合** —— 期待 `MultipleError` 并检查 `.exceptions`。
- 测试过滤器：发出应被拦截的事件，断言没有订阅者执行（或 `RETURN` 模式下
  `emit` 返回 `None`）。
- 异步测试用 `pytest-asyncio`；纯同步测试用 `emit_sync`。

## 常见陷阱

- **同一函数对同一事件重复注册会被去重**（身份 + 权重）。需要同样的逻辑跑
  两次时，注册不同函数或换不同权重。
- **异步回调的 `weight` 无效** —— 不要假设异步处理器之间的执行顺序。
- **全局过滤器/注入器始终接收 `ctx`** —— 它们不受 `expand_args` /
  `expand_kwargs` 影响；只有事件级钩子和订阅者使用展开签名。
- **`RETURN` 模式下事件被拦截或无订阅者时 `emit` 返回 `None`** —— 记得判空。
- **`IGNORE` 会吞掉异常** —— 不配置日志的话，失败将不可见。
- **`ctx.kwargs` 混用 emit 关键字参数与注入数据** —— 建议用带前缀的键名
  （命名空间）避免调用方与注入器冲突。
- 在运行中的事件循环里调用 `emit_sync` 会阻塞该循环所在线程 —— 异步代码里
  优先 `await emit(...)`。
