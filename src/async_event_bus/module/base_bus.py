from abc import ABC, abstractmethod
from asyncio import Semaphore, gather, get_event_loop, new_event_loop, run_coroutine_threadsafe, set_event_loop
from typing import Any, Awaitable, Callable, Type, Union

from loguru import logger

from .module_exceptions import MultipleError
from ..event import EventType, EventCallbackContainer

SubScriberCallback: Type = Callable[..., Union[Any, Awaitable[Any]]]


class BaseBus(ABC):
    """
    Event base class, which provides the most basic event subscription and triggering services.
    :param max_concurrent_tasks: The maximum number of tasks for an asynchronous task
    """

    def __init__(self, max_concurrent_tasks: int = 10):
        self._subscribers: dict[str, EventCallbackContainer] = {}
        self._semaphore = Semaphore(max_concurrent_tasks)
        self._raise_exception = False

    def on(self, event: EventType, *, weight: int = 1) -> Callable[[SubScriberCallback], SubScriberCallback]:
        """
        Subscribe to the event bus by decorator\n
        Use decorator to register an event handler to the event bus, which can be asynchronous or synchronous.\n
        The event type can be a string, representing a custom type,
        or you can write an enum class that inherits the EnumEvent class,
        or write a class that inherits the AbstractEvent class for more customization. \n
        Example:
            @event_bus.on('message_create')
            def message_logger(message, *_, **__):
                print(message)
            # Asynchronous functions also accepted
            @event_bus.on('message_create')
            async def message_recoder(message, *_, **__):
                await ...

        :param event: Event to subscribe to
        :param weight: The selection weight of the event handler
        :return: The decorator function
        """

        def decorator(func: SubScriberCallback):
            self.subscribe(event, func, weight=weight)
            logger.debug(f"{func.__name__} has subscribed to {event}, weight={weight}")
            return func

        return decorator

    def subscribe(self, event: EventType, callback: SubScriberCallback, *, weight: int = 1) -> None:
        """
        Subscribe to the event bus\n
        Functions used to subscribe to functions inside, or can be used separately\n
        Please check **BaseBus.on** for details\n
        Example:
            def message_logger(message, *_, **__):
                print(message)
            event_bus.subscribe('message_create', message_logger)
            # Asynchronous functions also accepted
            async def message_recoder(message, *_, **__):
                await ...
            event_bus.subscribe('message_create', message_recoder)

        :param event: Event to subscribe to
        :param callback: Event callback function
        :param weight: The selection weight of the event handler
        """
        if event not in self._subscribers:
            self._subscribers[event] = EventCallbackContainer()
        self._subscribers[event].add_callback(callback, weight)

    def unsubscribe(self, event: EventType, callback: SubScriberCallback) -> None:
        """
        Unsubscribe from the event\n
        Example:
            def message_logger(message, *_, **__):
                print(message)
            event_bus.unsubscribe('message_create', message_logger)

        :param event: Event to subscribe to
        :param callback: Event callback function
        """
        if event in self._subscribers:
            self._subscribers[event].remove_callback(callback)

    def emit_sync(self, event: EventType, *args, **kwargs) -> None:
        """
        Trigger events in a blocking manner\n
        Example:
            emit_sync('message_create', "This is a message", user="Half")

        :param event: Event to be triggered
        """
        try:
            loop = get_event_loop()
            if loop and loop.is_running():
                future = run_coroutine_threadsafe(
                    self.emit(event, *args, **kwargs),
                    loop
                )
                future.result()
        except RuntimeError:
            loop = new_event_loop()
            set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self.emit(event, *args, **kwargs)
                )
            finally:
                loop.close()
                set_event_loop(None)

    async def _run_with_semaphore(self, coroutine: Callable, *args, **kwargs):
        """
        Asynchronous function executor with limiter
        :param coroutine: Original asynchronous function
        """
        async with self._semaphore:
            return await coroutine(*args, **kwargs)

    @abstractmethod
    async def before_emit(self, event: EventType, *args, **kwargs) -> tuple[bool, dict]:
        return False, {}

    async def emit(self, event: EventType, *args, **kwargs) -> None:
        """
        Asynchronous trigger event\n
        Execution order:
            The greater the weight of the function, the more it is executed first,
            and the synchronous function takes precedence over the asynchronous function execution.\n
            Among them, the last asynchronous event handling function weight has no effect,
            because **asyncio.gather** will be used for concurrent execution,
            and the order of execution will be meaningless\n
        Example:
            await emit('message_create', "This is a message", user="Half")

        :param event: Event to be triggered
        """
        skip, extra_kwargs = await self.before_emit(event, *args, **kwargs)
        if skip:
            return
        kwargs.update(extra_kwargs)
        if event in self._subscribers:
            exceptions = []

            for callback in self._subscribers[event].sync_callback:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    if self._raise_exception:
                        raise e
                    exceptions.append(e)

            async_handlers = [self._run_with_semaphore(callback, *args, **kwargs) for callback in
                              self._subscribers[event].async_callback]

            if self._raise_exception:
                await gather(*async_handlers, return_exceptions=False)
            else:
                results = await gather(*async_handlers, return_exceptions=True)
                if not (len(results) == 1 and results[0] is None):
                    exceptions.extend(results)

            if (exception_size := len(exceptions)) != 0:
                if exception_size == 1:
                    raise exceptions[0]
                else:
                    raise MultipleError(exceptions)

    def clear(self):
        self._subscribers.clear()

    @property
    def raise_exception_immediately(self) -> bool:
        return self._raise_exception

    @raise_exception_immediately.setter
    def raise_exception_immediately(self, value: bool) -> None:
        self._raise_exception = value
