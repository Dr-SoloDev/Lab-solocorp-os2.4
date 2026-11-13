"""Concurrency control — asyncio locks for shared resources."""

from __future__ import annotations

import asyncio


class LockManager:
    def __init__(self) -> None:
        self._db_lock: asyncio.Lock | None = None
        self._cache_lock: asyncio.Lock | None = None
        self._build_lock: asyncio.Lock | None = None
        self._qa_lock: asyncio.Lock | None = None

    async def init(self) -> None:
        self._db_lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()
        self._build_lock = asyncio.Lock()
        self._qa_lock = asyncio.Lock()

    @property
    def db_lock(self) -> asyncio.Lock:
        assert self._db_lock is not None, "LockManager not initialized"
        return self._db_lock

    @property
    def build_lock(self) -> asyncio.Lock:
        assert self._build_lock is not None, "LockManager not initialized"
        return self._build_lock

    @property
    def qa_lock(self) -> asyncio.Lock:
        assert self._qa_lock is not None, "LockManager not initialized"
        return self._qa_lock


lock_manager = LockManager()
