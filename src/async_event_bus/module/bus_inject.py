from typing import Any, Awaitable, Callable, Type, Union

from loguru import logger

from .base_module import BaseModule
from ..event import Event, EventCallbackContainer

InjectCallback: Type = Callable[..., Union[dict[str, Any], Awaitable[dict[str, Any]]]]


class BusInject(BaseModule):
    """
    事件总线注入器模块, 负责对事件进行参数注入, 以实现一些特殊操作, 比如：用户鉴权
    """

    def __init__(self):
        self._injects: dict[str, EventCallbackContainer] = {}
        self._global_injects: EventCallbackContainer = EventCallbackContainer()

    def clear(self) -> None:
        self._injects.clear()
        self._global_injects.clear()

    async def resolve(self, event: Union[Event, str], args: tuple, kwargs: dict[str, Any]) -> bool:
        kwargs.update(await self._apply_global_injects(*args, **kwargs))
        kwargs.update(await self._apply_event_injects(event, *args, **kwargs))
        return True

    async def _apply_event_injects(self, event: Union[Event, str], *args, **kwargs) -> dict[str, Any]:
        add_kwargs = {}
        if event in self._injects:
            for callback in self._injects[event].sync_callback:
                add_kwargs.update(callback(*args, **kwargs))
            for callback in self._injects[event].async_callback:
                add_kwargs.update(await callback(*args, **kwargs))
        return add_kwargs

    async def _apply_global_injects(self, *args, **kwargs) -> dict[str, Any]:
        add_kwargs = {}
        for callback in self._global_injects.sync_callback:
            add_kwargs.update(callback(*args, **kwargs))
        for callback in self._global_injects.async_callback:
            add_kwargs.update(await callback(*args, **kwargs))
        return add_kwargs

    def global_event_inject(self, weight: int = 1) -> Callable[[InjectCallback], InjectCallback]:
        def decorator(func: InjectCallback):
            self.add_global_inject(func, weight)
            return func

        return decorator

    def add_global_inject(self, callback: InjectCallback, weight: int = 1) -> None:
        self._global_injects.add_callback(callback, weight)
        logger.debug(f"Global inject {callback.__name__} has been added, weight={weight}")

    def remove_global_inject(self, callback: InjectCallback) -> None:
        self._global_injects.remove_callback(callback)

    def event_inject(self, event: Union[Event, str], weight: int = 1) -> Callable[[InjectCallback], InjectCallback]:
        def decorator(func: InjectCallback):
            self.add_inject(event, func, weight)
            return func

        return decorator

    def add_inject(self, event: Union[Event, str], callback: InjectCallback, weight: int = 1) -> None:
        if event not in self._injects:
            self._injects[event] = EventCallbackContainer()
        self._injects[event].add_callback(callback, weight)
        logger.debug(f"Event inject {callback.__name__} has been added to event {event}, weight={weight}")

    def remove_inject(self, event: Union[Event, str], callback: InjectCallback) -> None:
        if event in self._injects:
            self._injects[event].remove_callback(callback)
