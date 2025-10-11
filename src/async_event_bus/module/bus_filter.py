from typing import Awaitable, Callable, Type, Union

from loguru import logger

from .base_module import BaseModule
from ..event import EventType, EventCallbackContainer

FilterCallback: Type = Callable[..., Union[bool, Awaitable[bool]]]


class BusFilter(BaseModule):
    """
    The event bus filter module is responsible for filtering the event
    and determining whether to continue to propagate the event
    """

    def __init__(self):
        self._filters: dict[str, EventCallbackContainer] = {}
        self._global_filters: EventCallbackContainer = EventCallbackContainer()

    def clear(self):
        self._filters.clear()
        self._global_filters.clear()

    async def resolve(self, event: EventType, args, kwargs) -> bool:
        if await self._apply_global_filter(event, *args, **kwargs):
            return True
        if await self._apply_filter(event, *args, **kwargs):
            return True
        return False

    async def _apply_filter(self, event: EventType, *args, **kwargs) -> bool:
        if event in self._filters:
            for callback in self._filters[event].sync_callback:
                if callback(*args, **kwargs):
                    return True
            for callback in self._filters[event].async_callback:
                if await callback(*args, **kwargs):
                    return True
        return False

    async def _apply_global_filter(self, event: EventType, *args, **kwargs) -> bool:
        for callback in self._global_filters.sync_callback:
            if callback(event, *args, **kwargs):
                return True
        for callback in self._global_filters.async_callback:
            if await callback(event, *args, **kwargs):
                return True
        return False

    def global_event_filter(self, weight: int = 1) -> Callable[[FilterCallback], FilterCallback]:
        """
        Register to global filters by decorator\n
        Use decorator to register a global event filter function to the event bus,
        which can be asynchronous or synchronous.\n
        When passing a function, you can pass the weight at the same time,
        and the filter with the weight will be called first\n
        The filter return value:
            If it returns `True`, it means that this event is truncated and no longer propagates down.\n
            If it returns `False`, this event continues to propagate\n
        Example:
            @event_bus.on_global_event_filter()
            def message_logger(message, *_, **__):
                print(message)
            # Asynchronous functions also accepted
            @event_bus.on_global_event_filter()
            async def message_recoder(message, *_, **__):
                await ...
            # Weights can be passed simultaneously
            @event_bus.on_global_event_filter(10)
            async def message_filter(message, *_, **__):
                await ...

        :param weight: The selection weight of the filter
        :return: The decorator function
        """

        def decorator(func: FilterCallback):
            self.add_global_filter(func, weight)
            return func

        return decorator

    def add_global_filter(self, callback: FilterCallback, weight: int = 1) -> None:
        """
        Register for global filters\n
        Functions used to register to global filters inside, or can be used separately\n
        Please check **BusFilter.global_event_filter** for details\n
        Example:
            def message_logger(message, *_, **__):
                print(message)
            event_bus.add_global_filter(message_logger)
            # Asynchronous functions also accepted
            async def message_recoder(message, *_, **__):
                await ...
            event_bus.add_global_filter(message_recoder)
            # Weights can be passed simultaneously
            async def message_filter(message, *_, **__):
                await ...
            event_bus.add_global_filter(message_filter, 10)

        :param callback: Event filter function
        :param weight: The selection weight of the filter
        """
        self._global_filters.add_callback(callback, weight)
        logger.debug(f"Global filter {callback.__name__} has been added, weight={weight}")

    def remove_global_filter(self, callback: FilterCallback) -> None:
        """
        Remove the global filter\n
        Example:
            def message_logger(message, *_, **__):
                print(message)
            event_bus.remove_global_filter(message_logger)

        :param callback: Event filter function
        """
        self._global_filters.remove_callback(callback)

    def event_filter(self, event: EventType, weight: int = 1) -> Callable[[FilterCallback], FilterCallback]:
        """
        Register to event filters by decorator\n
        Use decorator to register an event filter function to the event bus,
        which can be asynchronous or synchronous.\n
        The event type can be a string, representing a custom type,
        or you can write an enum class that inherits the EnumEvent class,
        or write a class that inherits the AbstractEvent class for more customization. \n
        Please check **BusFilter.global_event_filter** for filter returns\n
        Example:
            @event_bus.event_filter('message_create')
            def message_logger(message, *_, **__):
                print(message)
            # Asynchronous functions also accepted
            @event_bus.event_filter('message_create')
            async def message_recoder(message, *_, **__):
                await ...
            # Weights can be passed simultaneously
            @event_bus.event_filter('message_create', 10)
            async def message_filter(message, *_, **__):
                await ...

        :param event: Event to filter to
        :param weight: The selection weight of the filter
        """

        def decorator(func: FilterCallback):
            self.add_filter(event, func, weight)
            return func

        return decorator

    def add_filter(self, event: EventType, callback: FilterCallback, weight: int = 1) -> None:
        """
        Register for event filters\n
        Functions used to register to event filters inside, or can be used separately\n
        Please check **BusFilter.event_filter** for details\n
        Example:
            def message_logger(message, *_, **__):
                print(message)
            event_bus.add_filter('message_create', message_logger)
            @event_bus.event_filter('message_create')
            async def message_recoder(message, *_, **__):
                await ...
            event_bus.add_filter('message_create', message_recoder)
            # Weights can be passed simultaneously
            async def message_filter(message, *_, **__):
                await ...
            event_bus.add_filter('message_create', message_filter, 10)

        :param event: Event to filter to
        :param callback: Event filter function
        :param weight: The selection weight of the filter
        """
        if event not in self._filters:
            self._filters[event] = EventCallbackContainer()
        self._filters[event].add_callback(callback, weight)
        logger.debug(f"Event filter {callback.__name__} has been added to event {event}, weight={weight}")

    def remove_filter(self, event: EventType, callback: FilterCallback) -> None:
        """
        Remove the event filter\n
        Example:
            def message_logger(message, *_, **__):
                print(message)
            event_bus.remove_filter('message_create', message_logger)

        :param event: Event to filter to
        :param callback: Event filter function
        """
        if event in self._filters:
            self._filters[event].remove_callback(callback)
