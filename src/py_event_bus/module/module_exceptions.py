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
