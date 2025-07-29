from asyncio import iscoroutinefunction

from .async_event_callback import AsyncEventCallback
from .event_callback import EventCallback, T
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
