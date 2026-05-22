from abc import ABC
from asyncio import Semaphore, gather
from typing import Callable, TypeVar, Generic, Awaitable, Hashable

from .module_exceptions import MultipleError
from ..event import EventCallbackContainer, EventContext, EventInstance,EventType

C = TypeVar("C", bound=EventContext)
R = TypeVar("R")


class BaseModule(ABC, Generic[C, R]):
    """Abstract base for all bus modules."""

    def __init__(
        self,
        max_concurrent_tasks: int = 16,
        raise_exception: bool = False,
        context_class: type[C] = EventContext,
    ) -> None:
        """Initialize the base module.

        Args:
            max_concurrent_tasks:   Maximum number of async callbacks that may execute simultaneously.
                                    Used to prevent resource exhaustion when many events fire at once.
            raise_exception:        If ``True``, the first exception encountered inside a callback will be re‑raised immediately.
                                    If ``False``, exceptions are collected and raised as a single ``MultipleError`` after all callbacks have run.
            context_class:          The event‑context type to instantiate when emitting events.
                                    Must be a subclass of ``EventContext``.
        """
        # A semaphore caps concurrent async executions to prevent resource exhaustion when many events fire simultaneously.
        # Without it, a burst of events could spawn thousands of coroutines that overwhelm the event loop or external services.
        self._semaphore = Semaphore(max_concurrent_tasks)
        # raise_exception is stored as a flag so that the error‑handling
        # strategy can be switched at runtime, e.g. during debugging vs production.
        self._raise_exception = raise_exception
        self._context_class = context_class

    @property
    def raise_exception_immediately(self) -> bool:
        """Whether exceptions are re‑raised immediately.

        Returns:
            ``True`` if the module is in fail‑fast mode,
            ``False`` if exceptions are collected.
        """
        return self._raise_exception

    @raise_exception_immediately.setter
    def raise_exception_immediately(self, value: bool) -> None:
        """Switch error‑handling strategy at runtime.

        Args:
            value:  ``True`` to enable fail‑fast mode.
                    ``False`` to collect exceptions.
        """
        self._raise_exception = value

    async def before_emit(self, event: EventType, ctx: EventContext) -> bool:
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
        self, coroutine: Callable[[C], Awaitable[R]], ctx: C
    ) -> R:
        """Wrap a single async callback with the concurrency semaphore.

        Guarantees that at most ``max_concurrent_tasks`` coroutines are active at any time.
        The ``async with`` block releases the slot as soon as the callback completes
        so that waiting tasks can proceed promptly.

        Args:
            coroutine:  An async callable that accepts an event context and returns ``R``.
            ctx:        The event context to pass to the callable.

        Returns:
            The return value of ``coroutine(ctx)``.
        """
        async with self._semaphore:
            return await coroutine(ctx)

    async def _execute_callback(
        self,
        container: EventCallbackContainer[C, R],
        ctx: C,
        handler: Callable[[R], bool] | None = None,
    ) -> bool:
        """Run all callbacks stored in *container* against *ctx*.

        Execution order:

        - Synchronous callbacks are invoked sequentially in descending weight order so that side‑effects are deterministic.
        - Asynchronous callbacks are scheduled concurrently via ``asyncio.gather``.

        Weight ordering among asynchronous callbacks is intentionally irrelevant.

        Args:
            container:  The callback container holding all registered handlers for a specific event.
            ctx:        The event context to pass to each callback.
            handler:    Optional short‑circuit predicate.
                        If provided, it is called with each callback return value;
                        returning ``False`` halts further execution and return ``False`` immediately.

        Returns:
            ``True`` if all callbacks executed without interruption,
            ``False`` if a ``handler`` predicate returned ``False``.

        Raises:
            MultipleError:  When ``raise_exception_immediately`` is ``False`` and one or more callbacks raise an exception.
                            The exception bundles all caught exceptions.
            Exception:      Any callback exception re‑raised directly when ``raise_exception_immediately`` is ``True``.
        """
        exceptions: list[Exception] = []

        # Synchronous callbacks are executed sequentially and in weight order.
        # This allows them to have deterministic side‑effects and respects the
        # weight‑based priority that users explicitly set.
        for callback in container.sync_callback:
            try:
                result = callback(ctx)
                if handler and not handler(result):
                    # A filter returned False.
                    # Before stopping we raise any already‑collected exceptions
                    # so that they are not silently lost.
                    if exceptions:
                        raise MultipleError(exceptions)
                    return False
            except Exception as e:
                if self._raise_exception:
                    # Fail‑fast mode: stop immediately so that the error can
                    # be debugged with its original traceback.
                    raise e
                # Otherwise accumulate the exception and continue so that
                # other handlers still get a chance to run.
                exceptions.append(e)

        # Prepare async callbacks, each wrapped with the semaphore.
        # They are gathered together for concurrent execution.
        # Weight ordering among async handlers is intentionally meaningless.
        # They all run concurrently anyway.
        async_handlers = [
            self._run_with_semaphore(callback, ctx)
            for callback in container.async_callback
        ]

        results: tuple[R] = tuple()
        if self._raise_exception:
            # In fail‑fast mode, gather will propagate the first exception immediately, aborting the remaining async tasks.
            await gather(*async_handlers, return_exceptions=False)
        else:
            # return_exceptions=True is critical: without it, one failing async callback would cancel all others.
            # By collecting results as exceptions we can separate successes from failures.
            results = await gather(*async_handlers, return_exceptions=True)
            exceptions.extend([r for r in results if isinstance(r, Exception)])

        if exceptions:
            # All collected exceptions are bundled into a single MultipleError
            # so that the caller can inspect every failure instead of just the  first one.
            raise MultipleError(exceptions)

        if not handler:
            # No short‑circuit logic requested; execution succeeded.
            return True

        # After async execution, apply the handler to each result.
        # If any returns False, stop further processing.
        # Though at this point all callbacks have already executed.
        # This is useful for consistency with filter semantics.
        for r in results:
            if not handler(r):
                return False

        return True
