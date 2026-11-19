"""In-memory TTL cache shared across modules (asyncio-safe)."""

from __future__ import annotations

import asyncio
import time
from typing import Any


class TTLCache:
    def __init__(self, default_ttl: float = 300.0) -> None:
        self._data: dict[str, tuple[Any, float]] = {}
        self._lock: asyncio.Lock | None = None
        self._default_ttl = default_ttl
        self._cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._lock is None:
            self._lock = asyncio.Lock()
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if time.monotonic() > expiry:
                del self._data[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        ttl = ttl or self._default_ttl
        async with self._lock:
            self._data[key] = (value, time.monotonic() + ttl)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            now = time.monotonic()
            async with self._lock:
                for k in [k for k, (_, e) in self._data.items() if e < now]:
                    del self._data[k]


cache = TTLCache()
