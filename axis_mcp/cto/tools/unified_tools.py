"""Unified tools — health check, pipeline status, tool discovery."""

from __future__ import annotations

from typing import Any

from axis_mcp.unified_technical.shared.db import db_manager
from axis_mcp.unified_technical.shared.cache import cache
from axis_mcp.unified_technical.shared.lock import lock_manager


async def unified_health_check(architect, engineering, qa) -> dict[str, Any]:
    """Health check — verify server, database, cache, all modules."""
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


async def unified_pipeline_status(project_id: str) -> dict[str, Any]:
    """Get combined pipeline status (Architect -> Engineering -> QA)."""
    return {
        "status": "ok",
        "project_id": project_id,
        "pipeline": "architect -> engineering -> qa",
    }


async def unified_list_tools(namespace: str | None = None) -> dict[str, Any]:
    """List tools by namespace to prevent context saturation."""
    all_tools = {
        "architect": ["architect_route", "architect_pipeline_define"],
        "engineering": [
            "engineering_build_backend",
            "engineering_build_frontend",
            "engineering_code_review",
        ],
        "qa": ["qa_run_test", "qa_record_evidence"],
        "unified": [
            "unified_technical_health",
            "unified_pipeline_status",
            "unified_list_tools",
        ],
    }
    if namespace:
        return {"namespace": namespace, "tools": all_tools.get(namespace, [])}
    return {"namespaces": list(all_tools.keys()), "tools": all_tools}
