from typing import Awaitable, Callable, Optional, Type, Union

from loguru import logger

from .base_module import BaseModule
from ..event import Event, EventCallbackContainer

FilterCallback: Type = Callable[..., Union[bool, Awaitable[bool]]]


class BusFilter(BaseModule):
    """
    事件总线过滤器模块, 负责对事件进行过滤, 同时判断是否继续传播该事件
    """

    def __init__(self):
        self._filters: dict[str, EventCallbackContainer] = {}
        self._global_filters: EventCallbackContainer = EventCallbackContainer()

    def clear(self):
        self._filters.clear()
        self._global_filters.clear()

    async def resolve(self, event: Union[Event, str], args, kwargs) -> bool:
        if await self._apply_global_filter(event, *args, **kwargs):
            return True
        if await self._apply_filter(event, *args, **kwargs):
            return True
        return False

    async def _apply_filter(self, event: Union[Event, str], *args, **kwargs) -> bool:
        if event in self._filters:
            for callback in self._filters[event].sync_callback:
                if callback(*args, **kwargs):
                    return True
            for callback in self._filters[event].async_callback:
                if await callback(*args, **kwargs):
                    return True
        return False

    async def _apply_global_filter(self, event: Union[Event, str], *args, **kwargs) -> bool:
        for callback in self._global_filters.sync_callback:
            if callback(event, *args, **kwargs):
                return True
        for callback in self._global_filters.async_callback:
            if await callback(event, *args, **kwargs):
                return True
        return False

    def global_event_filter(self, weight: int = 1) -> Callable[[FilterCallback], FilterCallback]:
        """
        全局过滤器修饰器\n
        使用修饰器来向事件总线注册一个全局事件过滤器函数，这个过滤器函数可以是异步函数，也可以是同步函数。\n
        传递函数的时候可以同时传递权重，权重大的过滤器会被优先调用\n
        过滤器返回值:\n
        如果返回True，则代表此事件被截断，不再向下传播。\n
        如果返回False，则此事件继续传播\n
        示例::\n
            @event_bus.on_global_event_filter()
            def message_logger(message, *_, **__):
                print(message)
            # 异步函数也可以
            @event_bus.on_global_event_filter()
            async def message_recoder(message, *_, **__):
                await ...
            # 可以同时传递权重
            @event_bus.on_global_event_filter(10)
            async def message_filter(message, *_, **__):
                await ...

        :param weight: 事件的选择权重
        """

        def decorator(func: FilterCallback):
            self.add_global_filter(func, weight)
            return func

        return decorator

    def add_global_filter(self, callback: FilterCallback, weight: int = 1) -> None:
        """
        注册全局过滤器\n
        用于注册全局过滤器的函数，也可以单独使用\n
        示例::\n
            def message_logger(message, *_, **__):
                print(message)
            async def message_recoder(message, *_, **__):
                await ...
            async def message_filter(message, *_, **__):
                await ...
            event_bus.add_global_filter(message_logger)
            event_bus.add_global_filter(message_recoder)
            event_bus.add_global_filter(message_filter, 10)

        :param callback: 事件回调函数
        :param weight: 事件的选择权重
        """
        self._global_filters.add_callback(callback, weight)
        logger.debug(f"Global filter {callback.__name__} has been added, weight={weight}")

    def remove_global_filter(self, callback: FilterCallback) -> None:
        """
        移除全局过滤器\n
        示例::\n
            def message_logger(message, *_, **__):
                print(message)
            event_bus.remove_global_filter(message_logger)

        :param callback: 事件回调函数
        """
        self._global_filters.remove_callback(callback)

    def event_filter(self, event: Union[Event, str], weight: int = 1) -> Callable[[FilterCallback], FilterCallback]:
        """
        事件过滤器修饰器\n
        使用修饰器来向事件总线注册一个事件过滤器函数，这个过滤器函数可以是异步函数，也可以是同步函数。\n
        事件类型可以是字符串，表示自定义类型，也可以写一个继承Event类的枚举类来管理事件。\n
        示例::\n
            @event_bus.event_filter('message_create')
            def message_logger(message, *_, **__):
                print(message)
            # 异步函数也可以
            @event_bus.event_filter('message_create')
            async def message_recoder(message, *_, **__):
                await ...
            # 可以同时传递权重
            @event_bus.event_filter('message_create', 10)
            async def message_filter(message, *_, **__):
                await ...

        :param event: 要订阅的事件
        :param weight: 事件的选择权重
        """

        def decorator(func: FilterCallback):
            self.add_filter(event, func, weight)
            return func

        return decorator

    def add_filter(self, event: Union[Event, str], callback: FilterCallback, weight: int = 1) -> None:
        """
        注册事件过滤器\n
        用于注册事件过滤器的函数，也可以单独使用\n
        示例::\n
            def message_logger(message, *_, **__):
                print(message)
            async def message_recoder(message, *_, **__):
                await ...
            async def message_filter(message, *_, **__):
                await ...
            event_bus.add_filter('message_create', message_logger)
            event_bus.add_filter('message_create', message_recoder)
            event_bus.add_filter('message_create', message_filter, 10)

        :param event: 要订阅的事件
        :param callback: 事件回调函数
        :param weight: 事件的选择权重
        """
        if event not in self._filters:
            self._filters[event] = EventCallbackContainer()
        self._filters[event].add_callback(callback, weight)
        logger.debug(f"Event filter {callback.__name__} has been added to event {event}, weight={weight}")

    def remove_filter(self, event: Union[Event, str], callback: FilterCallback) -> None:
        """
        移除事件过滤器

        示例::

            def message_logger(message, *_, **__):
                print(message)
            event_bus.remove_filter('message_create', message_logger)

        :param event: 要订阅的事件
        :param callback: 事件回调函数
        """
        if event in self._filters:
            self._filters[event].remove_callback(callback)
