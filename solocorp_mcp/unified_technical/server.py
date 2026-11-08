"""Unified Technical MCP Server entry point.

Run with: python3 -m solocorp_mcp.unified_technical.server
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent.parent

sys.path.insert(0, str(ROOT))

from solocorp_mcp.unified_technical.modules.architect_module import (  # noqa: E402
    ArchitectModule,
)
from solocorp_mcp.unified_technical.modules.engineering_module import (  # noqa: E402
    EngineeringModule,
)
from solocorp_mcp.unified_technical.modules.qa_module import QAModule  # noqa: E402
from solocorp_mcp.unified_technical.shared.cache import cache  # noqa: E402
from solocorp_mcp.unified_technical.shared.db import db_manager  # noqa: E402
from solocorp_mcp.unified_technical.shared.lock import lock_manager  # noqa: E402
from solocorp_mcp.unified_technical.tools.unified_tools import (  # noqa: E402
    unified_health_check,
    unified_list_tools,
    unified_pipeline_status,
)

_architect: ArchitectModule | None = None
_engineering: EngineeringModule | None = None
_qa: QAModule | None = None


async def _startup() -> None:
    global _architect, _engineering, _qa
    await db_manager.init()
    await cache.start()
    await lock_manager.init()
    _architect = ArchitectModule()
    _engineering = EngineeringModule()
    _qa = QAModule()
    await _architect.startup()
    await _engineering.startup()
    await _qa.startup()


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    await _startup()
    yield
    # Graceful shutdown: stop cache cleanup task and close SQLite connection.
    # LockManager is stateless (locks only) — no close needed.
    # Modules have no shutdown hook (startup only in BaseModule).
    await cache.stop()
    await db_manager.close()


mcp = FastMCP(
    "unified-technical",
    instructions="""\
Unified Technical MCP Server — SoloCorp OS.
Combines Architect, Engineering (backend/frontend), and QA into one process
per Two-Tier Architecture (Control Layer = agents, Data Layer = this server).

Tool namespaces:
- architect_* -> routing, pipeline definition, bus topology
- engineering_* -> backend/frontend implementation, code review
- qa_* -> test execution, evidence recording
- unified_* -> health check, pipeline status, tool discovery
""",
    lifespan=lifespan,
)


@mcp.tool()
async def unified_technical_health() -> dict:
    """Health check — verify server, database, cache, all modules."""
    return await unified_health_check(_architect, _engineering, _qa)


@mcp.tool()
async def architect_route(topic: str, trace_id: str | None = None) -> dict:
    """Route technical topic to Architect specialist."""
    return await _architect.route(topic, trace_id)


@mcp.tool()
async def architect_pipeline_define(
    pipeline_id: str, phase_sequence: list[str]
) -> dict:
    """Define pipeline phase sequence."""
    return await _architect.pipeline_define(pipeline_id, phase_sequence)


@mcp.tool()
async def engineering_build_backend(
    spec: str, project_id: str, trace_id: str | None = None
) -> dict:
    """Build backend feature — API, database, business logic."""
    return await _engineering.build_backend(spec, project_id, trace_id)


@mcp.tool()
async def engineering_build_frontend(
    spec: str, project_id: str, trace_id: str | None = None
) -> dict:
    """Build frontend feature — React/Next.js UI, components, styling."""
    return await _engineering.build_frontend(spec, project_id, trace_id)


@mcp.tool()
async def engineering_code_review(build_artifact_ref: str, pr_description: str) -> dict:
    """Code review before sending to QA."""
    return await _engineering.code_review(build_artifact_ref, pr_description)


@mcp.tool()
async def qa_run_test(
    suite_id: str, project_id: str, trace_id: str | None = None
) -> dict:
    """Run QA test suite — pytest execution, result collection."""
    return await _qa.run_test(suite_id, project_id, trace_id)


@mcp.tool()
async def qa_record_evidence(
    task_id: str,
    suite_id: str,
    status: str,
    note: str = "",
    trace_id: str | None = None,
) -> dict:
    """Record QA evidence — store test result to disk + bus."""
    return await _qa.record_evidence(task_id, suite_id, status, note, trace_id)


@mcp.tool()
async def unified_pipeline_status(project_id: str) -> dict:
    """Get combined pipeline status."""
    return await unified_pipeline_status(project_id)


@mcp.tool()
async def unified_list_tools_tool(namespace: str | None = None) -> dict:
    """List tools by namespace."""
    return await unified_list_tools(namespace)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
