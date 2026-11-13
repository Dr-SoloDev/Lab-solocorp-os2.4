"""CTO department MCP server.

C-Level Technical Command Layer (Phase 1: Bus-coordination / Build / QA).
Dual-run additive: delegates to Engineering (07) + QA (10) owners, never
implements directly. Reports to CEO directly.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..runtime_freshness import freshness

mcp = FastMCP(
    "cto",
    instructions=(
        "SoloCorp CTO department (C-Level, reports to CEO directly). "
        "Phase 1 scope: Bus-coordination / Build / QA only. "
        "CTO coordinates via Central Bus, delegates implementation to "
        "Engineering (07) and QA (10) owners, never implements directly."
    ),
)


def _error(exc: Exception) -> str:
    from ..bus_store import as_json

    return as_json(
        {"status": "error", "error": type(exc).__name__, "message": str(exc)}
    )


@mcp.tool()
def cto_department_info() -> str:
    """Return the head, scope, alias coverage, and data root for CTO."""

    from ..bus_store import as_json

    return as_json(
        {
            "status": "ok",
            "department": "cto",
            "runtime": freshness(),
            "head": {
                "id": "cto-vector",
                "name": "เวคเตอร์ (Vector Chaisriram)",
                "role": "Chief Technology Officer",
                "profile": "profiles/cto/cto.md",
                "reports_to": "CEO (เทอโบ) directly",
            },
            "phase1_scope": ["bus-coordination", "build", "qa"],
            "aliases": {
                "07-engineering": "Build owner: ช่างฟูล (Changful) — CTO coordinates, never implements",
                "10-qa": "QA owner: QA-ทีม — CTO respects verdict, never overrides FAIL",
            },
            "coordinated_owners": [
                {
                    "id": "architect-songsak",
                    "domain": "bus-coordination",
                    "role": "Central Bus + Routing Rules owner",
                },
                {
                    "id": "engineering-changful",
                    "domain": "build",
                    "role": "Code / PR / branch / deploy owner",
                },
                {
                    "id": "qa-team",
                    "domain": "qa",
                    "role": "Quality gate / test evidence owner",
                },
            ],
            "control_rule": "CTO delegates via Central Bus; specialists implement via owner Heads",
            "data_root": "central_bus/content/",
            "dual_run": {
                "mode": "shadow-additive",
                "engineering_preserved": True,
                "qa_preserved": True,
            },
        }
    )


@mcp.tool()
def cto_list_projects(limit: int = 10) -> str:
    """List recent CTO-coordinated projects with status summary."""
    from ..bus_store import as_json

    return as_json(
        {
            "status": "ok",
            "department": "cto",
            "projects": [
                {
                    "project_id": "cto-001",
                    "name": "CTO dual-run shadow (Phase 1)",
                    "status": "active",
                    "owner": "cto-vector",
                    "covers": ["07-engineering", "10-qa"],
                },
            ][:limit],
            "count": 1,
        }
    )


@mcp.tool()
def cto_route(topic: str) -> str:
    """Route a CTO topic to the real Phase 1 owner (architect/engineering/qa)."""
    from ..bus_store import as_json

    topic_lower = topic.lower()
    if any(k in topic_lower for k in ("bus", "routing", "central", "schema")):
        routed_to = "architect-songsak"
        domain = "bus-coordination"
    elif any(
        k in topic_lower
        for k in ("test", "qa", "quality", "regression", "smoke", "evidence")
    ):
        routed_to = "qa-team"
        domain = "qa"
    elif any(
        k in topic_lower
        for k in (
            "implement",
            "build",
            "deploy",
            "code",
            "backend",
            "frontend",
            "bug",
            "review",
        )
    ):
        routed_to = "engineering-changful"
        domain = "build"
    else:
        routed_to = "cto-vector"
        domain = "triage"

    return as_json(
        {
            "status": "ok",
            "department": "cto",
            "topic": topic,
            "domain": domain,
            "routed_to": routed_to,
            "reason": f"Phase 1 owner mapping for domain={domain}",
        }
    )


if __name__ == "__main__":
    mcp.run()
