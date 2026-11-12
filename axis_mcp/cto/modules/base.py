"""Base class for pipeline modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from axis_mcp.unified_technical.shared.db import db_manager
from axis_mcp.unified_technical.shared.cache import cache
from axis_mcp.unified_technical.shared.lock import lock_manager


class BaseModule(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    async def startup(self) -> None:
        await db_manager.init()
        await lock_manager.init()

    @abstractmethod
    async def health_check(self) -> dict[str, Any]: ...
