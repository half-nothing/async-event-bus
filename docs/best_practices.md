# Best Practices

Practical guidance for using `async-event-bus` in real applications. Each
section points out a common decision and the recommended approach.

## Organizing Events

- **Define all events of a module in one place.** A single file per domain
  (e.g. `events.py`) makes the event surface discoverable.
- **Prefer `EnumEvent` for enumerable events** — type-safe, hashable, and
  self-documenting:
  ```python
  class OrderEvent(EnumEvent):
      CREATED = auto()
      CANCELLED = auto()
  ```
- **Use `AbstractEvent` when the event carries a payload**; pass an instance to
  `emit` and read it back as `ctx.event`:
  ```python
  @dataclass
  class OrderCreated(AbstractEvent):
      order_id: str
  ```
- **Use plain strings sparingly** — convenient for quick scripts, but strings
  are easy to typo and hard to discover.

## Callback Signatures

- **Default to receiving `EventContext`.** It gives handlers access to
  `ctx.event`, `ctx.args`, `ctx.kwargs` and any fields your custom context
  subclass adds:
  ```python
  @bus.on(OrderCreated)
  async def on_order_created(ctx: EventContext[OrderCreated]) -> None:
      print(ctx.event.order_id)
  ```
- **Use `expand_args` only for simple, positional payloads** (e.g. one string
  message). It trades context access for a shorter signature — and remember
  that *per-event* filters and injectors must then use the same expanded
  signature, while *global* ones still receive `ctx`.
- **Annotate the context type** (`ctx: EventContext[MyEvent]`) so type checkers
  infer `ctx.event` correctly.

## Choosing an Exception Strategy

| Scenario                        | Recommended strategy                                          |
|---------------------------------|---------------------------------------------------------------|
| Development / debugging         | `RAISE` — surface the first failure immediately               |
| Production, keep processing     | `COLLECT` (default) — nothing is lost, inspect `e.exceptions` |
| Result-driven code              | `RETURN` — check `EmitResult.results` / `.exceptions`         |
| Non-critical, best-effort paths | `IGNORE` — log and continue                                   |

- Prefer `RAISE` while developing and switch to `COLLECT` in production — the
  `exception_strategy` property makes this a one-liner at startup:
  ```python
  bus.exception_strategy = ExceptionStrategy.COLLECT if is_prod else ExceptionStrategy.RAISE
  ```
- With `RETURN`, always handle the `None` case: a filtered-out event or an
  event with no subscribers yields `None`, not an `EmitResult`.
- **Be careful with `IGNORE`** — swallowed exceptions are only visible in logs;
  make sure logging is configured.

## Filters and Injectors

- **Filters should be pure and side-effect free** — return `True`/`False` and
  do nothing else. Use the first `False` as an early exit for expensive work.
- **Injectors own the side effects** — fetch users, sessions, timestamps and
  write them into `ctx`:
  ```python
  @bus.global_event_inject()
  async def attach_user(ctx: EventContext) -> None:
      ctx.user = await load_user(ctx.kwargs["user_id"])
  ```
- **Use global hooks for cross-cutting rules** (auth, tenant isolation,
  rate limiting), and per-event hooks for event-specific logic.
- **Order matters**: global filters/injectors run before per-event ones; use
  `weight` when you need a specific sequence inside one level.
- If an injector raises, the event is dropped (with `COLLECT` it surfaces as
  `MultipleError`) — subscribers never see a half-built context.

## Weights and Ordering

- **`weight` only orders *sync* callbacks.** Async callbacks run concurrently,
  so never rely on their relative order.
- Need deterministic ordering? Make the callback synchronous, or chain the work
  explicitly inside one handler.
- Registration order breaks ties between sync callbacks with equal weight.

## Concurrency

- **Tune `max_concurrent_tasks`** to the resources your handlers touch (DB
  pool size, API rate limits). Default is 10.
- **Async callbacks suit I/O-bound work** (network, DB); CPU-bound work blocks
  the event loop — consider `asyncio.to_thread` or a worker pool inside the
  callback.
- **Keep callbacks short.** The bus is cooperative: one slow sync callback
  delays every other sync callback for the same event.
- `emit` only schedules the async callbacks; the caller waits for all of them.

## Custom Context and Modules

- **Extend `EventContext`** for request-scoped data (user, request id, DB
  session) and let injectors fill it — handlers then read typed fields instead
  of digging through `kwargs`.
- **Write custom modules for cross-cutting concerns** (audit logging, metrics,
  correlation ids) by inheriting `BaseModule` and overriding `before_emit`;
  compose them into your own bus via MRO.
- **Always call `super().before_emit(event, ctx)`** at the end of an override —
  it continues the cooperative chain and eventually allows the event through.

## Testing

- **Create a fresh `EventBus` per test** — module-level buses leak
  subscriptions between tests.
- **Use `RETURN` to assert outcomes** without try/except noise:
  ```python
  bus = EventBus(exception_strategy=ExceptionStrategy.RETURN)

  result = await bus.emit("message", "hello")
  assert result is not None
  assert result.results == ["handled"]
  assert not result.exceptions
  ```
- **Use `COLLECT` to assert failure aggregation** — expect `MultipleError` and
  inspect `.exceptions`.
- Test filters by emitting an event that must be blocked, and assert that no
  subscriber ran (or that `emit` returned `None` in `RETURN` mode).
- Use `pytest-asyncio` for async tests; `emit_sync` covers plain sync tests.

## Common Pitfalls

- **Re-registering the same function for the same event is deduplicated**
  (identity + weight). Register different functions or use a different weight
  if you need the same logic twice.
- **Async callback `weight` is meaningless** — do not assume execution order
  among async handlers.
- **Global filters/injectors always receive `ctx`** — they ignore
  `expand_args`/`expand_kwargs`; only per-event hooks and subscribers use the
  expanded signature.
- **`emit` returns `None` in `RETURN` mode** when the event was filtered out or
  had no subscribers — guard against it.
- **`IGNORE` swallows exceptions** — without logging configured, failures
  become invisible.
- **`ctx.kwargs` mixes emit keyword arguments with injected data** — prefer
  distinct keys (e.g. namespaced prefixes) to avoid collisions between callers
  and injectors.
- `emit_sync` from inside a running loop blocks that loop's thread — prefer
  `await emit(...)` in async code.
