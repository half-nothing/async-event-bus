from abc import ABC
from asyncio import Semaphore, gather
from dataclasses import dataclass
from typing import Callable, TypeVar, Generic, Awaitable, cast

from loguru import logger

from .module_exceptions import ExceptionStrategy, MultipleError
from ..event import EventCallbackContainer, EventContext, EventType

C = TypeVar("C", bound=EventContext)
R = TypeVar("R")


@dataclass
class EmitResult(Generic[R]):
    """Outcome of executing a callback container.

    Successful callback outcomes and exceptions are kept in separate lists,
    so callers never have to filter a mixed bag of results.

    Attributes:
        results:    Return values of the callbacks that completed successfully,
                    in execution order (sync callbacks first, then async ones).
        exceptions: Exceptions raised by the callbacks, in the order they
                    occurred. Only populated by the ``RETURN`` strategy
                    (``COLLECT`` raises them as ``MultipleError`` instead,
                    ``IGNORE`` drops them after logging).
    """

    results: list[R]
    exceptions: list[Exception]


class BaseModule(ABC, Generic[C, R]):
    """Abstract base for all bus modules."""

    def __init__(
            self,
            max_concurrent_tasks: int = 16,
            exception_strategy: ExceptionStrategy = ExceptionStrategy.COLLECT,
            context_class: type[C] = cast(type[C], EventContext),
    ) -> None:
        """Initialize the base module.

        Args:
            max_concurrent_tasks:   Maximum number of async callbacks that may execute simultaneously.
                                    Used to prevent resource exhaustion when many events fire at once.
            exception_strategy:     How callback exceptions are handled. One of
                                    ``ExceptionStrategy.IGNORE`` (log and continue),
                                    ``RAISE`` (fail fast), ``COLLECT`` (raise a single
                                    ``MultipleError`` after execution, default) or
                                    ``RETURN`` (returned by ``emit`` instead of raised).
            context_class:          The event‑context type to instantiate when emitting events.
                                    Must be a subclass of ``EventContext``.
        """
        # A semaphore caps concurrent async executions to prevent resource exhaustion when many events fire simultaneously.
        # Without it, a burst of events could spawn thousands of coroutines that overwhelm the event loop or external services.
        self._semaphore = Semaphore(max_concurrent_tasks)
        # The exception strategy can be switched at runtime,
        # e.g. while debugging (RAISE) vs production (COLLECT).
        self._exception_strategy = exception_strategy
        self._context_class = context_class

    @property
    def exception_strategy(self) -> ExceptionStrategy:
        """How callback exceptions are currently handled.

        Returns:
            The active :class:`ExceptionStrategy`.
        """
        return self._exception_strategy

    @exception_strategy.setter
    def exception_strategy(self, value: ExceptionStrategy) -> None:
        """Switch the exception handling strategy at runtime.

        Args:
            value: The new :class:`ExceptionStrategy`.
        """
        self._exception_strategy = value

    async def before_emit(self, event: EventType, ctx: C) -> bool:
        """Terminal node of the cooperative ``before_emit`` chain.

        Always returns ``True`` so that, if no other module interrupts,
        the event reaches the actual subscribers.

        Args:
            event:  The event that is about to be emitted.
            ctx:    The event context that is about to be dispatched.

        Returns:
            ``True`` to allow the event to propagate.
        """
        return True

    def clear(self) -> None:
        """Reset all state stored by the module.

        The base implementation does nothing.
        Subclasses that maintain registries override this method to
        provide a consistent interface for hot‑reloading or resetting the bus.
        """
        pass

    async def _run_with_semaphore(
            self,
            coroutine: Callable[[C], Awaitable[R]],
            ctx: C,
            expand_args: bool = False,
            expand_kwargs: bool = False,
    ) -> R:
        """Wrap a single async callback with the concurrency semaphore.

        Guarantees that at most ``max_concurrent_tasks`` coroutines are active at any time.
        The ``async with`` block releases the slot as soon as the callback completes
        so that waiting tasks can proceed promptly.

        Args:
            coroutine:      An async callable that accepts an event context and returns ``R``.
            ctx:            The event context to pass to the callable.
            expand_args:    If ``True``, unpack ``ctx.args`` as positional arguments instead of passing ``ctx``.
            expand_kwargs:  If ``True``, unpack ``ctx.kwargs`` as keyword arguments instead of passing ``ctx``.

        Returns:
            The return value of the coroutine.
        """
        async with self._semaphore:
            call_args = ctx.args if expand_args else []
            call_kwargs = ctx.kwargs if expand_kwargs else {}
            return await coroutine(ctx, *call_args, **call_kwargs)

    async def _execute_callback(
            self,
            container: EventCallbackContainer[C, R],
            ctx: C,
            handler: Callable[[R], bool] | None = None,
            expand_args: bool = False,
            expand_kwargs: bool = False,
    ) -> EmitResult[R]:
        """Run all callbacks stored in *container* against *ctx*.

        Execution order:

        - Synchronous callbacks are invoked sequentially in descending weight order so that side‑effects are deterministic.
        - Asynchronous callbacks are scheduled concurrently via ``asyncio.gather``.

        Exception behavior follows the configured :class:`ExceptionStrategy`:

        - ``IGNORE``:  exceptions are logged and execution continues.
        - ``RAISE``:   the first exception is re‑raised immediately, aborting the remaining callbacks.
        - ``COLLECT``: all exceptions are bundled into a single ``MultipleError`` raised after execution.
        - ``RETURN``:  exceptions are collected in ``EmitResult.exceptions`` and never raised.

        Args:
            container:      The callback container holding all registered handlers for a specific event.
            ctx:            The event context to pass to each callback.
            handler:        Optional short‑circuit predicate.
                            If provided, it is called with each callback return value;
                            returning ``False`` halts further execution.
            expand_args:    If ``True``, unpack ``ctx.args`` as positional arguments instead of passing ``ctx``.
            expand_kwargs:  If ``True``, unpack ``ctx.kwargs`` as keyword arguments instead of passing ``ctx``.

        Returns:
            An ``EmitResult`` with successful outcomes in ``results`` and
            (for the ``RETURN`` strategy) exceptions in ``exceptions``.

        Raises:
            MultipleError:  When the strategy is ``COLLECT`` and one or more callbacks raise an exception.
                            The exception bundles all caught exceptions.
            Exception:      Any callback exception re‑raised directly when the strategy is ``RAISE``.
        """
        strategy = self._exception_strategy
        results: list[R] = []
        exceptions: list[Exception] = []
        stopped = False

        # Synchronous callbacks are executed sequentially and in weight order.
        # This allows them to have deterministic side‑effects and respects the
        # weight‑based priority that users explicitly set.
        for callback in container.sync_callback:
            try:
                call_args = ctx.args if expand_args else []
                call_kwargs = ctx.kwargs if expand_kwargs else {}
                result = callback(ctx, *call_args, **call_kwargs)
                if handler and not handler(result):
                    # A filter returned False: stop the chain here,
                    # before the asynchronous callbacks are scheduled.
                    # The result is still recorded so that callers (e.g. the
                    # filter module) can see the blocking outcome.
                    stopped = True
                results.append(result)
                if stopped:
                    break
            except Exception as e:
                if strategy is ExceptionStrategy.RAISE:
                    # Fail‑fast mode: stop immediately so that the error can
                    # be debugged with its original traceback.
                    raise e
                if strategy is ExceptionStrategy.COLLECT:
                    # Accumulate the exception and continue so that
                    # other handlers still get a chance to run.
                    exceptions.append(e)
                elif strategy is ExceptionStrategy.IGNORE:
                    logger.warning(f"Exception ignored in callback: {e!r}")
                else:
                    # RETURN: keep the exception for the caller instead of raising it.
                    exceptions.append(e)

        if not stopped:
            # Prepare async callbacks, each wrapped with the semaphore.
            # They are gathered together for concurrent execution.
            # Weight ordering among async handlers is intentionally meaningless.
            async_handlers = [
                self._run_with_semaphore(callback, ctx, expand_args, expand_kwargs)
                for callback in container.async_callback
            ]
            if strategy is ExceptionStrategy.RAISE:
                # In fail‑fast mode, gather propagates the first exception
                # immediately, aborting the remaining async tasks.
                await gather(*async_handlers, return_exceptions=False)
            else:
                # return_exceptions=True is critical: without it, one failing
                # async callback would cancel all others.
                gathered = await gather(*async_handlers, return_exceptions=True)
                for item in gathered:
                    if isinstance(item, Exception):
                        if strategy is ExceptionStrategy.COLLECT:
                            exceptions.append(item)
                        elif strategy is ExceptionStrategy.IGNORE:
                            logger.warning(f"Exception ignored in callback: {item!r}")
                        else:
                            # RETURN: keep the exception for the caller.
                            exceptions.append(item)
                    elif isinstance(item, BaseException):
                        # gather(return_exceptions=True) only wraps Exception
                        # instances; any other BaseException propagates.
                        raise item
                    else:
                        results.append(item)

        if exceptions and strategy is ExceptionStrategy.COLLECT:
            # All collected exceptions are bundled into a single MultipleError
            # so that the caller can inspect every failure instead of just the  first one.
            raise MultipleError(exceptions)

        if handler:
            # After async execution, apply the handler to each result so that
            # filter semantics stay consistent for sync and async filters.
            for r in results:
                if not handler(r):
                    break

        return EmitResult(results=results, exceptions=exceptions)
