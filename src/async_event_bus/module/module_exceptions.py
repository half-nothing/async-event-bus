from enum import Enum, auto


class ExceptionStrategy(Enum):
    """Exception handling strategies for callbacks executed by the event bus.

    Choose one when constructing the bus; the strategy applies to all
    subscribers, filters and injectors of that bus.
    """

    """Ignore exceptions: they are logged but never raised nor returned."""
    IGNORE = auto()

    """Fail fast: the first exception is raised immediately, aborting the remaining callbacks."""
    RAISE = auto()

    """Collect all exceptions and raise a single ``MultipleError`` after all callbacks have run."""
    COLLECT = auto()

    """Do not raise: exceptions are returned as part of the ``emit`` return value."""
    RETURN = auto()


class MultipleError(Exception):
    def __init__(self, exceptions: list[Exception]):
        self._exceptions = exceptions
        self._info = f"There are {len(self._exceptions)} exceptions occurred. Use exceptions property for more details."

    @property
    def exceptions(self) -> list[Exception]:
        return self._exceptions

    def __str__(self) -> str:
        return self._info

    def __repr__(self) -> str:
        return self._info
