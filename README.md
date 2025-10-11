# async-event-bus

A simple event bus for python3

---
[![ReleaseCard]][Release]![ReleaseDataCard]  
![LastCommitCard]![ProjectLanguageCard]![ProjectLicense]
---

## Quick Start

1. install package with pip or any tools you like

```shell
pip install async-event-bus
```

2. use example code under

```python
import asyncio
import sys

from loguru import logger

from async_event_bus import EventBus

bus = EventBus()
logger.remove()
logger.add(sys.stdout, level="TRACE")


@bus.on("message")
async def message_handler(message: str, *args, **kwargs) -> None:
    logger.info(f"message received: {message}")


async def main():
    await asyncio.gather(
        bus.emit("message", "Hello"),
        bus.emit("message", "This is a test message"),
        bus.emit("message", "Send from python"),
        bus.emit("message", "This is also a test message")
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())

```

3. Check out the examples under the 'examples' folder for more help  

[ReleaseCard]: https://img.shields.io/github/v/release/half-nothing/async-event-bus?style=for-the-badge&logo=github

[ReleaseDataCard]: https://img.shields.io/github/release-date/half-nothing/async-event-bus?display_date=published_at&style=for-the-badge&logo=github

[LastCommitCard]: https://img.shields.io/github/last-commit/half-nothing/async-event-bus?display_timestamp=committer&style=for-the-badge&logo=github

[ProjectLanguageCard]: https://img.shields.io/github/languages/top/half-nothing/async-event-bus?style=for-the-badge&logo=github

[ProjectLicense]: https://img.shields.io/badge/License-MIT-blue?style=for-the-badge&logo=github

[Release]: https://www.github.com/half-nothing/async-event-bus/releases/latest
