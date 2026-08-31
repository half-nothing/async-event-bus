from .event.event import AbstractEvent, EnumEvent, EventContext, EventInstance, EventType
from .event.event_callback import AsyncEventCallback, EventCallback, EventCallbackContainer, SyncEventCallback
from .module.base_module import BaseModule, EmitResult
from .module.core_module import CoreModule
from .module.filter_module import FilterModule
from .module.inject_module import InjectModule
from .module.module_exceptions import ExceptionStrategy, MultipleError
from .event_bus import EventBus

__version__: str
__author__: str

__all__ = [
    "EnumEvent",
    "AbstractEvent",
    "EventType",
    "EventInstance",
    "EventContext",
    "EventCallback",
    "SyncEventCallback",
    "AsyncEventCallback",
    "CoreModule",
    "BaseModule",
    "FilterModule",
    "InjectModule",
    "EmitResult",
    "ExceptionStrategy",
    "MultipleError",
    "EventBus",
]
