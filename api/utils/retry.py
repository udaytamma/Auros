from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Type


async def retry_async(
    func: Callable[[], Awaitable],
    exceptions: tuple[Type[BaseException], ...],
    attempts: int = 3,
    base_delay: float = 0.5,
) -> object:
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await func()
        except exceptions as exc:  # noqa: PERF203
            last_exc = exc
            if attempt == attempts:
                break
            await asyncio.sleep(base_delay * attempt)
    if last_exc:
        raise last_exc
    raise RuntimeError("retry_async failed without exception")
