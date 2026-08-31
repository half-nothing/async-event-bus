from enum import Enum


class ExceptionStrategy(Enum):
    """Exception handling strategies for callbacks executed by the event bus.

    Choose one when constructing the bus; the strategy applies to all
    subscribers, filters and injectors of that bus.
    """

    # Ignore exceptions: they are logged but never raised nor returned.
    IGNORE = ...
    # Fail fast: the first exception is raised immediately, aborting the remaining callbacks.
    RAISE = ...
    # Collect all exceptions and raise a single MultipleError after all callbacks have run.
    COLLECT = ...
    # Do not raise: exceptions are returned as part of the emit return value.
    RETURN = ...


class MultipleError(Exception):
    def __init__(self, exceptions: list[Exception]) -> None: ...

    @property
    def exceptions(self) -> list[Exception]:
        """Every exception collected during execution."""
        ...

    def __str__(self) -> str: ...

    def __repr__(self) -> str: ...
