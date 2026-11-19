"""Engineering department MCP server.

Department boundary for Engineering. Exposes a small set of engineering-scoped
tools through the head, keeping specialist implementation details internal.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..runtime_freshness import freshness

mcp = FastMCP(
    "engineering",
    instructions=(
        "SoloCorp Engineering department. The head coordinates backend, frontend, "
        "architecture, and infrastructure specialists. Tools expose project status "
        "and routing without revealing internal specialist internals. "
        "DEPRECATED (Wave 2 CTO flip-default 20261113): primary is now CTO (@cto); "
        "this server is read-only redirect — forward new build/deploy work to CTO, "
        "trace cto-mig-W2-20261112T224226Z."
    ),
)


def _error(exc: Exception) -> str:
    from ..bus_store import as_json

    return as_json(
        {"status": "error", "error": type(exc).__name__, "message": str(exc)}
    )


@mcp.tool()
def engineering_department_info() -> str:
    """Return the head, specialists, scope, and data root for Engineering."""

    from ..bus_store import as_json

    return as_json(
        {
            "status": "ok",
            "department": "engineering",
            "runtime": freshness(),
            "head": {
                "id": "engineering-changful",
                "name": "ช่างฟูล (Changful)",
                "role": "Head of Engineering",
                "profile": "profiles/07-engineering/SOUL.md",
            },
            "specialists": [
                {
                    "id": "backend-architect",
                    "name": "สถาปนิกแบ็กเอนด์",
                    "role": "Scalable backend, database architecture, API design, cloud infra (<20ms)",
                },
                {
                    "id": "senior-developer",
                    "name": "นักพัฒนาอาวุโส",
                    "role": "Full-stack senior dev — Laravel, Livewire, FluxUI, Three.js, animations",
                },
                {
                    "id": "software-architect",
                    "name": "สถาปนิกซอฟต์แวร์",
                    "role": "Domain-driven design, microservices/modular monolith, event-driven, ADRs",
                },
            ],
            "control_rule": "Client ส่งงานผ่านหัวหน้า; specialist เป็น implementation ภายในแผนก",
            "data_root": "central_bus/content/",
            "deprecated": True,
            "primary": "cto",
            "forward_to": "cto (@axis/cto/deploy, @cto pipeline)",
            "trace_id": "cto-mig-W2-20261112T224226Z",
            "mode": "read-only redirect (1 release alias @changful preserved)",
        }
    )


@mcp.tool()
def engineering_list_projects(limit: int = 10) -> str:
    """List recent engineering projects with status summary."""
    from ..bus_store import as_json

    return as_json(
        {
            "status": "ok",
            "department": "engineering",
            "projects": [
                {
                    "project_id": "eng-001",
                    "name": "Core MCP Server",
                    "status": "active",
                    "owner": "backend-architect",
                },
                {
                    "project_id": "eng-002",
                    "name": "Content Creator Department MCP",
                    "status": "active",
                    "owner": "senior-developer",
                },
                {
                    "project_id": "eng-003",
                    "name": "Module Registry & Task Tracking",
                    "status": "active",
                    "owner": "software-architect",
                },
            ][:limit],
            "count": 3,
        }
    )


@mcp.tool()
def engineering_route_to_specialist(topic: str) -> str:
    """Route an engineering topic to the most suitable specialist."""
    from ..bus_store import as_json

    topic_lower = topic.lower()
    if any(k in topic_lower for k in ("backend", "api", "database", "cloud", "infra")):
        specialist = "backend-architect"
    elif any(
        k in topic_lower for k in ("frontend", "livewire", "fluxui", "three.js", "ui")
    ):
        specialist = "senior-developer"
    elif any(
        k in topic_lower for k in ("design", "ddd", "microservice", "adr", "event")
    ):
        specialist = "software-architect"
    else:
        specialist = "engineering-changful"

    return as_json(
        {
            "status": "ok",
            "department": "engineering",
            "topic": topic,
            "routed_to": specialist,
            "reason": f"Matched topic keywords to {specialist} role",
        }
    )


if __name__ == "__main__":
    mcp.run()
