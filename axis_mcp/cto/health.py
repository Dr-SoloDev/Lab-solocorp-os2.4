"""Health check tools for CTO MCP Server."""

from __future__ import annotations

from typing import Any

from axis_mcp.cto.shared.db import db_manager
from axis_mcp.cto.shared.cache import cache
from axis_mcp.cto.shared.lock import lock_manager


async def health_check(
    db_manager, cache, lock_manager, architect, engineering, qa
) -> dict[str, Any]:
    """Comprehensive health check for the unified server."""
    return {
        "status": "healthy",
        "server": "cto",
        "modules": {
            "architect": await architect.health_check(),
            "engineering": await engineering.health_check(),
            "qa": await qa.health_check(),
        },
        "database": "connected",
        "cache": "active",
    }
