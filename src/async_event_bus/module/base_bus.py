from abc import ABC, abstractmethod
from asyncio import Semaphore, gather, get_event_loop, new_event_loop, run_coroutine_threadsafe, set_event_loop
from typing import Any, Awaitable, Callable, Type, Union

from loguru import logger

from .module_exceptions import MultipleError
from ..event import Event, EventCallbackContainer

SubScriberCallback: Type = Callable[..., Union[Any, Awaitable[Any]]]


class BaseBus(ABC):
    """
    EventBus 事件基类，提供最基础的事件订阅和触发服务。
    :param max_concurrent_tasks: 异步任务的最大任务数
    """

    def __init__(self, max_concurrent_tasks: int = 10):
        self._subscribers: dict[str, EventCallbackContainer] = {}
        self._semaphore = Semaphore(max_concurrent_tasks)
        self._raise_exception = False

    def on(self, event: Union[Event, str], *, weight: int = 1) -> Callable:
        """
        订阅事件修饰器\n
        使用修饰器来向事件总线注册一个事件处理函数，这个事件处理函数可以是异步函数，也可以是同步函数。\n
        事件类型可以是字符串，表示自定义类型，也可以写一个继承Event类的枚举类来管理事件。\n
        示例::\n
            @event_bus.on('message_create')
            def message_logger(message, *_, **__):
                print(message)
            # 异步函数也可以
            @event_bus.on('message_create')
            async def message_recoder(message, *_, **__):
                await ...

        :param event: 要订阅的事件
        :param weight: 事件的选择权重
        :return: 实际上的修饰器
        """

        def decorator(func: SubScriberCallback):
            self.subscribe(event, func, weight=weight)
            logger.debug(f"{func.__name__} has subscribed to {event}, weight={weight}")
            return func

        return decorator

    def subscribe(self, event: Union[Event, str], callback: SubScriberCallback, *, weight: int = 1) -> None:
        """
        订阅事件\n
        用于订阅事件修饰器内部的函数，也可以单独使用\n
        详细信息请查看\n
        示例::\n
            def message_logger(message, *_, **__):
                print(message)
            async def message_recoder(message, *_, **__):
                await ...
            event_bus.subscribe('message_create', message_logger)
            event_bus.subscribe('message_create', message_recoder)

        :param event: 要订阅的事件
        :param callback: 事件回调函数
        :param weight: 事件的选择权重
        """
        if event not in self._subscribers:
            self._subscribers[event] = EventCallbackContainer()
        self._subscribers[event].add_callback(callback, weight)

    def unsubscribe(self, event: Union[Event, str], callback: SubScriberCallback) -> None:
        """
        取消订阅事件\n
        示例::\n
            def message_logger(message, *_, **__):
                print(message)
            event_bus.unsubscribe('message_create', message_logger)

        :param event: 要订阅的事件
        :param callback: 事件回调函数
        """
        if event in self._subscribers:
            self._subscribers[event].remove_callback(callback)

    def emit_sync(self, event: Union[Event, str], *args, **kwargs) -> None:
        """
        以同步方式触发事件（底层还是异步执行）\n
        示例:
            emit_sync('message_create', "This is a message", user="Half")

        :param event: 要触发的事件
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
        带有限制器的异步函数执行器
        :param coroutine: 原异步函数
        """
        async with self._semaphore:
            return await coroutine(*args, **kwargs)

    @abstractmethod
    async def before_emit(self, event: Union[Event, str], *args, **kwargs) -> tuple[bool, dict]:
        return False, {}

    async def emit(self, event: Union[Event, str], *args, **kwargs) -> None:
        """
        异步触发事件\n
        执行顺序:
            函数的权重越大，越先被执行，同步函数优先于异步函数执行。\n
            其中，最后的异步事件处理函数权重没有作用，因为会使用asyncio.gather并发执行，执行先后顺序也就失去了意义\n
        示例:
            await emit('message_create', "This is a message", user="Half")

        :param event: 要触发的事件
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
