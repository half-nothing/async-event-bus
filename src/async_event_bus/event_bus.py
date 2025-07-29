from typing import Union

from .module import BaseBus, BusFilter, BusInject
from .event import Event


class EventBus(BaseBus, BusFilter, BusInject):
    """
    事件总线
    """

    def __init__(self, max_concurrent_tasks: int = 10):
        BaseBus.__init__(self, max_concurrent_tasks)
        BusFilter.__init__(self)
        BusInject.__init__(self)

    async def before_emit(self, event: Union[Event, str], *args, **kwargs) -> tuple[bool, dict]:
        await BusInject.resolve(self, event, args, kwargs)
        return await BusFilter.resolve(self, event, args, kwargs), kwargs

    def clear(self):
        super().clear()
        BusFilter.clear(self)
        BusInject.clear(self)
