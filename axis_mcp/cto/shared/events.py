"""Intra-process event bus for CTO MCP Server."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Callable


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._lock: asyncio.Lock | None = None

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            handlers = list(self._subscribers.get(event_type, []))
        if not handlers:
            return
        await asyncio.gather(
            *(handler(payload) for handler in handlers), return_exceptions=True
        )


event_bus = EventBus()
