"""Product department MCP server (FR-07 standalone)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..runtime_freshness import freshness

ROOT = Path(__file__).resolve().parent.parent.parent
DRAFTS_ROOT = ROOT / "docs" / "prds" / "drafts"
DRAFTS_ROOT.mkdir(parents=True, exist_ok=True)
_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

mcp = FastMCP(
    "product",
    instructions="SoloCorp Product department. Head coordinates PRD, roadmap, prioritization. Tools store drafts without publishing.",
)


@mcp.tool()
def product_department_info() -> str:
    """Return the head, specialists, scope, and data root for Product."""
    from ..bus_store import as_json

    return as_json(
        {
            "status": "ok",
            "department": "product",
            "runtime": freshness(),
            "head": {
                "id": "product-produck",
                "name": "โปรดัค (Produck)",
                "role": "Head of Product",
                "profile": "profiles/06-product/SOUL.md",
            },
            "specialists": [
                {"id": "alex-pm", "name": "Alex PM", "role": "PRD and lifecycle"},
                {
                    "id": "feedback-synthesizer",
                    "name": "Feedback Synthesizer",
                    "role": "RICE/MoSCoW/Kano",
                },
                {
                    "id": "sprint-prioritizer",
                    "name": "Sprint Prioritizer",
                    "role": "Sprint planning",
                },
            ],
            "control_rule": "Client sends work via head; specialists are internal",
            "data_root": "docs/prds/drafts/",
        }
    )


@mcp.tool()
def product_list_features(limit: int = 10) -> str:
    """List roadmap features with status summary."""
    from ..bus_store import as_json

    feats = [
        {"feature_id": "prd-001", "name": "SoloCorp App shell", "status": "planned"},
        {"feature_id": "prd-002", "name": "Content Creator module", "status": "active"},
        {"feature_id": "prd-003", "name": "Module registry UI", "status": "planned"},
    ][:limit]
    return as_json(
        {
            "status": "ok",
            "department": "product",
            "features": feats,
            "count": len(feats),
        }
    )


@mcp.tool()
def product_create_prd(title: str, brief: str = "") -> str:
    """Create a PRD draft file from title and brief (no LLM, template only)."""
    from ..bus_store import as_json

    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", (title or "").strip().lower()).strip("-")[
        :64
    ]
    if not slug or not _SLUG_RE.fullmatch(slug):
        return as_json(
            {
                "status": "error",
                "error": "invalid_title",
                "message": "title must slug to 1-64 [A-Za-z0-9_-]",
            }
        )
    path = (DRAFTS_ROOT / f"PRD-{slug}.md").resolve()
    if not path.is_relative_to(DRAFTS_ROOT.resolve()):
        return as_json(
            {
                "status": "error",
                "error": "write_out_of_bounds",
                "message": "outside drafts root",
            }
        )
    body = (
        f"# PRD: {title.strip()}\n\n**Status:** Draft\n\n## Problem Statement\n{brief.strip() or '(todo)'}\n\n"
        "## Why Now\n(todo)\n\n## Success Metrics\n- Metric 1: (todo)\n\n## Requirements\n### Must Have (P0)\n- (todo)\n\n"
        "### Should Have (P1)\n- (todo)\n\n### Nice to Have (P2)\n- (todo)\n\n## In Scope\n- (todo)\n\n## Out of Scope\n- (todo)\n"
    )
    path.write_text(body, encoding="utf-8")
    return as_json(
        {
            "status": "ok",
            "department": "product",
            "path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(body.encode()).hexdigest(),
        }
    )


@mcp.tool()
def product_prioritize(items_csv: str) -> str:
    """Rank a comma-separated item list (deterministic, rank by input order)."""
    from ..bus_store import as_json

    items = [s.strip() for s in (items_csv or "").split(",") if s.strip()]
    if not items:
        return as_json(
            {"status": "error", "error": "empty_items", "message": "items_csv is empty"}
        )
    return as_json(
        {
            "status": "ok",
            "department": "product",
            "ranked": [{"item": n, "rank": i + 1} for i, n in enumerate(items)],
            "count": len(items),
        }
    )


if __name__ == "__main__":
    mcp.run()
