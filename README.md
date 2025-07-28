# py-event-bus

A simple event bus for python3

[![GitHub release](https://img.shields.io/github/v/release/half-nothing/async-event-bus)](https://www.github.com/half-nothing/async-event-bus/releases/latest)
![GitHub commits since latest release](https://img.shields.io/github/commits-since/half-nothing/async-event-bus/latest/main)
![GitHub top language](https://img.shields.io/github/languages/top/half-nothing/async-event-bus)
![GPLv3](https://img.shields.io/badge/License-GPLv3-blue)

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
        bus.publish("message", "Hello"),
        bus.publish("message", "This is a test message"),
        bus.publish("message", "Send from python"),
        bus.publish("message", "This is also a test message")
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())

```

3. Check out the examples under the 'examples' folder for more help  