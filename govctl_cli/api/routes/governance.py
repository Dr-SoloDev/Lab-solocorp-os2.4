"""
Governance Routes — ADR / RFC / Guard CRUD

Each write operation creates a TOML artifact in the gov/ directory AND
publishes a BusMessage to Central Bus for audit trail.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from ...api.models import (
    ADRSummary, ADRDetail, ADRCreateRequest,
    RFCSummary, RFCDetail, RFCCreateRequest,
    GuardSummary, GuardDetail, GuardCreateRequest,
    to_dict, to_dict_skip_empty,
)

log = logging.getLogger("govctl.api.governance")

router = APIRouter(prefix="/api/v1/gov", tags=["Governance"])

# ── Paths ─────────────────────────────────────────────────────────────

GOV_DIR = Path("gov")
ADR_DIR = GOV_DIR / "adr"
RFC_DIR = GOV_DIR / "rfc"
GUARD_DIR = GOV_DIR / "guards"


# ═══════════════════════════════════════════════════════════════════════
# ADR
# ═══════════════════════════════════════════════════════════════════════


@router.get("/adrs")
async def list_adrs(
    status: Optional[str] = None,
    domain: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
):
    """List ADRs with optional filters."""
    items: list[dict] = []
    if not ADR_DIR.exists():
        return {"items": items, "total": 0}

    for path in sorted(ADR_DIR.glob("*.toml")):
        item = _read_adr_toml(path)
        if item is None:
            continue
        # Filters
        if status and item.get("status") != status:
            continue
        if domain and item.get("domain") != domain:
            continue
        if search:
            text = f"{item.get('title', '')} {item.get('context', '')}".lower()
            if search.lower() not in text:
                continue
        items.append(item)
        if len(items) >= limit:
            break

    return {"items": items, "total": len(items)}


@router.post("/adrs", status_code=201)
async def create_adr(req: ADRCreateRequest):
    """Create a new ADR."""
    adr_id = _next_id(ADR_DIR, "ADR")
    path = ADR_DIR / f"{adr_id}.toml"
    today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")

    data = {
        "metadata": {
            "id": adr_id,
            "title": req.title,
            "status": req.status or "proposed",
            "author": getattr(req, "author", "") or "",
            "date": today,
            "version": getattr(req, "version", "1.0.0") or "1.0.0",
        },
        "classification": {
            "domain": req.domain or "",
            "impact": req.impact or "",
            "complexity": getattr(req, "complexity", "") or "",
            "scope": getattr(req, "scope", "") or "",
        },
        "context": req.context or "",
        "decision": req.decision or "",
        "consequences": req.consequences or "",
        "options": getattr(req, "options", []) or [],
    }

    _write_toml(path, data)
    _publish_gov_event("adr_created", adr_id, data)

    detail = await _load_adr_detail(path)
    return detail


@router.get("/adrs/{id}")
async def get_adr(id: str):
    """Get ADR detail by ID."""
    path = ADR_DIR / f"{id}.toml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"ADR {id} not found")

    detail = await _load_adr_detail(path)
    return detail


# ═══════════════════════════════════════════════════════════════════════
# RFC
# ═══════════════════════════════════════════════════════════════════════


@router.get("/rfcs")
async def list_rfcs(
    status: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 20,
):
    """List RFCs with optional filters."""
    items: list[dict] = []
    if not RFC_DIR.exists():
        return {"items": items, "total": 0}

    for path in sorted(RFC_DIR.glob("*.toml")):
        item = _read_rfc_toml(path)
        if item is None:
            continue
        if status and item.get("status") != status:
            continue
        if domain and item.get("domain") != domain:
            continue
        items.append(item)
        if len(items) >= limit:
            break

    return {"items": items, "total": len(items)}


@router.post("/rfcs", status_code=201)
async def create_rfc(req: RFCCreateRequest):
    """Create a new RFC."""
    rfc_id = _next_id(RFC_DIR, "RFC")
    path = RFC_DIR / f"{rfc_id}.toml"
    today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")

    data = {
        "metadata": {
            "id": rfc_id,
            "title": req.title,
            "status": req.status or "draft",
            "author": getattr(req, "author", "") or "",
            "date": today,
            "complexity_score": getattr(req, "complexity_score", 0) or 0,
        },
        "classification": {
            "domain": getattr(req, "domain", "") or "",
        },
        "background": getattr(req, "background", "") or "",
        "proposal": getattr(req, "proposal", "") or "",
        "alternatives": getattr(req, "alternatives", []) or [],
        "implementation": getattr(req, "implementation", "") or "",
    }

    _write_toml(path, data)
    _publish_gov_event("rfc_created", rfc_id, data)

    detail = await _load_rfc_detail(path)
    return detail


@router.get("/rfcs/{id}")
async def get_rfc(id: str):
    """Get RFC detail by ID."""
    path = RFC_DIR / f"{id}.toml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"RFC {id} not found")

    detail = await _load_rfc_detail(path)
    return detail


# ═══════════════════════════════════════════════════════════════════════
# Guards
# ═══════════════════════════════════════════════════════════════════════


@router.get("/guards")
async def list_guards(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
):
    """List guards with optional filters.

    Guards are stored per-project in the state system, not as standalone
    TOML files. This endpoint reads from the central_bus state.
    """
    try:
        from central_bus.state import PROJECTS_DIR
    except ImportError:
        raise HTTPException(status_code=503, detail="Central Bus not available")

    items: list[dict] = []
    projects = [project_id] if project_id else _list_projects(PROJECTS_DIR)

    for pid in projects:
        project_state = _safe_read_state(PROJECTS_DIR, pid)
        if not project_state:
            continue
        gov = project_state.get("governance", {})
        guards = gov.get("active_guards", [])
        for g in guards:
            if status and g.get("status") != status:
                continue
            items.append({
                "name": g["name"],
                "status": g["status"],
                "project_id": pid,
                "added_at": g.get("added_at", ""),
            })

    return {"items": items, "total": len(items)}


@router.post("/guards", status_code=201)
async def create_guard(req: GuardCreateRequest):
    """Create a guard check for a project (adds to active_guards)."""
    try:
        from central_bus.state import add_guard
    except ImportError:
        raise HTTPException(status_code=503, detail="Central Bus not available")

    try:
        gov = add_guard(req.project_id, req.name)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Project {req.project_id} not found. Initialize it first.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _publish_gov_event("guard_run", req.name, {
        "project_id": req.project_id,
        "phase": req.phase,
    })

    return {
        "name": req.name,
        "status": "pending",
        "project_id": req.project_id,
        "added_at": gov.get("guard_status", "pending"),
    }


# ═══════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════


def _read_adr_toml(path: Path) -> Optional[dict]:
    """Parse an ADR TOML file and return summary fields."""
    try:
        import tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        log.warning("Failed to parse ADR: %s", path)
        return None

    meta = data.get("metadata", {})
    return {
        "id": meta.get("id", path.stem),
        "title": meta.get("title", ""),
        "status": meta.get("status", ""),
        "domain": data.get("classification", {}).get("domain", ""),
        "impact": data.get("classification", {}).get("impact", ""),
        "date": meta.get("date", ""),
        "author": meta.get("author", ""),
    }


def _read_rfc_toml(path: Path) -> Optional[dict]:
    """Parse an RFC TOML file and return summary fields."""
    try:
        import tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        log.warning("Failed to parse RFC: %s", path)
        return None

    meta = data.get("metadata", {})
    return {
        "id": meta.get("id", path.stem),
        "title": meta.get("title", ""),
        "status": meta.get("status", ""),
        "domain": data.get("classification", {}).get("domain", ""),
        "author": meta.get("author", ""),
        "date": meta.get("date", ""),
        "complexity_score": meta.get("complexity_score", 0),
    }


def _write_toml(path: Path, data: dict) -> None:
    """Write a governance artifact as TOML (or JSON fallback)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import tomli_w
        with open(path, "wb") as f:
            tomli_w.dump(data, f)
    except ImportError:
        # Fallback: write as JSON when tomli_w not available
        import json
        path = path.with_suffix(".json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


def _next_id(directory: Path, prefix: str) -> str:
    """Compute the next sequential ID (e.g. ADR-003) for a directory."""
    directory.mkdir(parents=True, exist_ok=True)
    max_num = 0
    for p in directory.glob(f"{prefix}-*.toml"):
        stem = p.stem
        try:
            num = int(stem.split("-")[-1])
            max_num = max(max_num, num)
        except (IndexError, ValueError):
            continue
    return f"{prefix}-{max_num + 1:03d}"


def _publish_gov_event(event: str, entity_id: str, data: dict) -> None:
    """Publish a governance event to Central Bus (best-effort)."""
    try:
        from central_bus.models import BusMessage
        from central_bus.queue import enqueue
        from datetime import datetime, timezone

        msg = BusMessage(
            from_dept="architect",
            to_dept="orchestrator",
            type="GOVERNANCE",
            project_id=data.get("project_id", "system"),
            phase="governance",
            payload={
                "gov_event": event,
                "gov_detail": f"{event}: {entity_id}",
                "gov_entity_id": entity_id,
                "gov_result": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            trace_id=__import__("uuid").uuid4().hex[:12],
            priority="normal",
        )
        enqueue(msg)
    except ImportError:
        log.debug("Central Bus not available — governance event not published")
    except Exception as exc:
        log.warning("Failed to publish governance event: %s", exc)


async def _load_adr_detail(path: Path) -> dict:
    """Load full ADR detail from a TOML file."""
    try:
        import tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail=f"Failed to parse {path}")

    meta = data.get("metadata", {})
    return {
        "id": meta.get("id", path.stem),
        "title": meta.get("title", ""),
        "status": meta.get("status", ""),
        "domain": data.get("classification", {}).get("domain", ""),
        "impact": data.get("classification", {}).get("impact", ""),
        "date": meta.get("date", ""),
        "author": meta.get("author", ""),
        "context": data.get("context", ""),
        "decision": data.get("decision", ""),
        "consequences": data.get("consequences", ""),
        "options": data.get("options", []),
        "path": str(path.resolve()),
    }


async def _load_rfc_detail(path: Path) -> dict:
    """Load full RFC detail from a TOML file."""
    try:
        import tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail=f"Failed to parse {path}")

    meta = data.get("metadata", {})
    return {
        "id": meta.get("id", path.stem),
        "title": meta.get("title", ""),
        "status": meta.get("status", ""),
        "domain": data.get("classification", {}).get("domain", ""),
        "author": meta.get("author", ""),
        "date": meta.get("date", ""),
        "complexity_score": meta.get("complexity_score", 0),
        "background": data.get("background", ""),
        "proposal": data.get("proposal", ""),
        "alternatives": data.get("alternatives", []),
        "implementation": data.get("implementation", ""),
        "path": str(path.resolve()),
    }


def _list_projects(projects_dir: Path) -> list[str]:
    """List project IDs from the state directory."""
    if not projects_dir.exists():
        return []
    return sorted(p.name for p in projects_dir.iterdir() if p.is_dir())


def _safe_read_state(projects_dir: Path, project_id: str) -> Optional[dict]:
    """Read project state.json safely."""
    import json
    path = projects_dir / project_id / "state.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
