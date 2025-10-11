from typing import Any

from .event_callback import EventCallback, T


class AsyncEventCallback(EventCallback):
    """
    A class that encapsulates an async callback function
    """

    def __init__(self, callback: T, weight: int = 1):
        super().__init__(callback, weight)
        self._async = True

    async def __call__(self, *args, **kwargs) -> Any:
        return await self._callback(*args, **kwargs)
