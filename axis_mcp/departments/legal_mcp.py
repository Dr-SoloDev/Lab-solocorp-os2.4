"""Legal department MCP server (FR-07 standalone). Records review requests;
never gives legal advice, never approves — every output requires human review."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..runtime_freshness import freshness

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEWS_ROOT = ROOT / "legal_vault" / "reviews"
REVIEWS_ROOT.mkdir(parents=True, exist_ok=True)
_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

mcp = FastMCP(
    "legal",
    instructions="SoloCorp Legal department. Head coordinates compliance, contracts, governance. Tools record review requests without approving.",
)


@mcp.tool()
def legal_department_info() -> str:
    """Return the head, specialists, scope, and data root for Legal."""
    from ..bus_store import as_json

    return as_json(
        {
            "status": "ok",
            "department": "legal",
            "runtime": freshness(),
            "head": {"id": "legal-tulya", "name": "ตุลย์ (Tulya)", "role": "Head of Legal", "profile": "profiles/13-legal/SOUL.md"},
            "specialists": [{"id": "compliance-auditor", "name": "Compliance Auditor", "role": "SOC 2, ISO 27001, HIPAA, PCI-DSS"},
                {"id": "legal-document-review", "name": "Legal Document Review", "role": "Contract review, risk assessment"},
                {"id": "legal-client-intake", "name": "Legal Client Intake", "role": "Screening, conflict check"}],
            "control_rule": "Client sends work via head; specialists are internal; no output approves anything",
            "data_root": "legal_vault/reviews/",
            "requires_human_review": True,
        }
    )


@mcp.tool()
def legal_list_matters(limit: int = 10) -> str:
    """List legal matters with status summary (records only, not advice)."""
    from ..bus_store import as_json

    matters = [{"matter_id": "legal-001", "name": "AXIS trademark clearance", "status": "open"},
        {"matter_id": "legal-002", "name": "FLUX Kommunity license review", "status": "open"},
        {"matter_id": "legal-003", "name": "Publish gate policy", "status": "monitoring"}][:limit]
    return as_json(
        {
            "status": "ok",
            "department": "legal",
            "matters": matters,
            "count": len(matters),
            "requires_human_review": True,
        }
    )


@mcp.tool()
def legal_create_review(title: str, brief: str = "") -> str:
    """Create a review request file (template only; never approves)."""
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
    path = (REVIEWS_ROOT / f"REVIEW-{slug}.md").resolve()
    if not path.is_relative_to(REVIEWS_ROOT.resolve()):
        return as_json(
            {
                "status": "error",
                "error": "write_out_of_bounds",
                "message": "outside reviews root",
            }
        )
    body = (
        f"# Legal Review Request: {title.strip()}\n\n**Status:** AWAITING HUMAN REVIEW (this tool never approves)\n\n"
        f"## Matter\n{brief.strip() or '(todo)'}\n\n## Checklist for human reviewer\n- [ ] Scope confirmed\n- [ ] Risk assessed\n- [ ] Decision recorded by human\n"
    )
    path.write_text(body, encoding="utf-8")
    rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    return as_json(
        {
            "status": "ok",
            "department": "legal",
            "path": rel,
            "sha256": hashlib.sha256(body.encode()).hexdigest(),
            "requires_human_review": True,
        }
    )


@mcp.tool()
def legal_check_compliance(items_csv: str) -> str:
    """Record a compliance checklist; every item requires human review."""
    from ..bus_store import as_json

    items = [s.strip() for s in (items_csv or "").split(",") if s.strip()]
    if not items:
        return as_json(
            {"status": "error", "error": "empty_items", "message": "items_csv is empty"}
        )
    return as_json(
        {
            "status": "ok",
            "department": "legal",
            "checklist": [
                {"item": n, "verdict": "requires_human_review"} for n in items
            ],
            "count": len(items),
            "requires_human_review": True,
        }
    )


if __name__ == "__main__":
    mcp.run()
