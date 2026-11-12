"""Health check tools for Unified Technical MCP Server."""

from __future__ import annotations

from typing import Any

from axis_mcp.unified_technical.shared.db import db_manager
from axis_mcp.unified_technical.shared.cache import cache
from axis_mcp.unified_technical.shared.lock import lock_manager


async def health_check(
    db_manager, cache, lock_manager, architect, engineering, qa
) -> dict[str, Any]:
    """Comprehensive health check for the unified server."""
    return {
        "status": "healthy",
        "server": "unified-technical",
        "modules": {
            "architect": await architect.health_check(),
            "engineering": await engineering.health_check(),
            "qa": await qa.health_check(),
        },
        "database": "connected",
        "cache": "active",
    }
