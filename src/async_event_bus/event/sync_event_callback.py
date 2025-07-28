from typing import Any

from .event_callback import EventCallback, T


class SyncEventCallback(EventCallback):
    def __init__(self, callback: T, weight: int = 1):
        super().__init__(callback, weight)
        self._async = False

    def __call__(self, *args, **kwargs) -> Any:
        return self.callback(*args, **kwargs)

