from asyncio import iscoroutinefunction
from typing import Callable, Union

from loguru import logger

from .async_event_callback import AsyncEventCallback
from .event_callback import EventCallback
from .event_callback_factory import EventCallbackFactory
from .sync_event_callback import SyncEventCallback


class EventCallbackContainer:
    """
    A container class that stores callback functions
    """

    def __init__(self):
        self._sync_callback: list[SyncEventCallback] = []
        self._async_callback: list[AsyncEventCallback] = []

    def add_sync_callback(self, callback: SyncEventCallback) -> None:
        if callback not in self._sync_callback:
            logger.trace(f"Adding sync callback: {callback}")
            self._sync_callback.append(callback)
            self._sync_callback.sort(key=lambda item: item.weight, reverse=True)
        else:
            logger.trace(f"Callback already exists: {callback}")

    def add_async_callback(self, callback: AsyncEventCallback) -> None:
        if callback not in self._async_callback:
            logger.trace(f"Adding async callback: {callback}")
            self._async_callback.append(callback)
            self._async_callback.sort(key=lambda item: item.weight, reverse=True)
        else:
            logger.trace(f"Callback already exists: {callback}")

    def add_callback(self, callback: Union[EventCallback, Callable], weight: int = 1) -> None:
        if not isinstance(callback, EventCallback):
            callback = EventCallbackFactory.create(callback, weight)
        if isinstance(callback, AsyncEventCallback):
            self.add_async_callback(callback)
        elif isinstance(callback, SyncEventCallback):
            self.add_sync_callback(callback)
        else:
            raise TypeError(f'Callback type {type(callback)} not supported')

    def remove_sync_callback(self, callback: Union[SyncEventCallback, Callable]) -> None:
        if callback in self._sync_callback:
            logger.trace(f"Removing sync callback: {callback}")
            self._sync_callback.remove(callback)

    def remove_async_callback(self, callback: Union[AsyncEventCallback, Callable]) -> None:
        if callback in self._async_callback:
            logger.trace(f"Removing async callback: {callback}")
            self._async_callback.remove(callback)

    def remove_callback(self, callback: Union[EventCallback, Callable]) -> None:
        if not isinstance(callback, EventCallback):
            if iscoroutinefunction(callback):
                self.remove_async_callback(callback)
            else:
                self.remove_sync_callback(callback)
            return
        if isinstance(callback, AsyncEventCallback):
            self.remove_async_callback(callback)
        elif isinstance(callback, SyncEventCallback):
            self.remove_sync_callback(callback)
        else:
            raise TypeError(f'Callback type {type(callback)} not supported')

    def clear(self) -> None:
        self._sync_callback.clear()
        self._async_callback.clear()

    @property
    def sync_callback(self) -> list[SyncEventCallback]:
        return self._sync_callback

    @property
    def async_callback(self) -> list[AsyncEventCallback]:
        return self._async_callback
