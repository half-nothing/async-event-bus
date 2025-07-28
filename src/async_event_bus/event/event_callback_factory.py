from asyncio import iscoroutinefunction

from .event_callback import EventCallback, T
from .async_event_callback import AsyncEventCallback
from .sync_event_callback import SyncEventCallback


class EventCallbackFactory:
    """
    创建 EventCallback 实例的工厂
    """

    @staticmethod
    def create(callback: T, weight: int = 1) -> EventCallback:
        if iscoroutinefunction(callback):
            return AsyncEventCallback(callback, weight)
        else:
            return SyncEventCallback(callback, weight)
