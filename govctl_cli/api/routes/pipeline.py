"""
Pipeline Routes — Status and History

Exposes project pipeline state from Central Bus state system,
with queue depth information and event history.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ...api.models import (
    PipelineStatus, PipelineEvent, PipelineHistory, to_dict,
)

log = logging.getLogger("govctl.api.pipeline")

router = APIRouter(prefix="/api/v1/pipeline", tags=["Pipeline"])


# ═══════════════════════════════════════════════════════════════════════
# Pipeline status
# ═══════════════════════════════════════════════════════════════════════


@router.get("/status")
async def get_pipeline_status(project_id: Optional[str] = None):
    """Get pipeline status for one or all projects.

    If project_id is provided, returns a single PipelineStatus object.
    Otherwise, returns a list of PipelineStatus for all active projects.
    """
    try:
        from central_bus.state import get as state_get, PROJECTS_DIR
        from central_bus.dashboard import summary as dash_summary
    except ImportError:
        raise HTTPException(status_code=503, detail="Central Bus not available")

    if project_id:
        try:
            state = state_get(project_id)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Project '{project_id}' not found",
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        pipeline = _build_pipeline_status(project_id, state)
        pipeline.queue_depth = _count_queue_depth(project_id)
        return pipeline

    # Return all projects
    if not PROJECTS_DIR.exists():
        return []

    projects = []
    for p_dir in sorted(PROJECTS_DIR.iterdir()):
        if not p_dir.is_dir():
            continue
        try:
            state = json.loads((p_dir / "state.json").read_text())
            pipeline = _build_pipeline_status(p_dir.name, state)
            pipeline.queue_depth = _count_queue_depth(p_dir.name)
            projects.append(pipeline)
        except (json.JSONDecodeError, OSError):
            continue

    return projects


# ═══════════════════════════════════════════════════════════════════════
# Pipeline history
# ═══════════════════════════════════════════════════════════════════════


@router.get("/history")
async def get_pipeline_history(
    project_id: str,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 50,
):
    """Get pipeline event history for a project.

    Reads from the Central Bus audit log (immutable JSONL).
    Events include phase transitions, guard events, and agent executions.
    """
    try:
        from central_bus.audit import read as audit_read
        from central_bus.state import GOV_LOG_DIR
    except ImportError:
        raise HTTPException(status_code=503, detail="Central Bus not available")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = since or today
    end_date = until or today

    events: list[dict] = []

    # 1. Read audit log for the date range
    try:
        from central_bus.audit import read as audit_read
        # Single date for now (date-range extension is trivial)
        audit_entries = audit_read(project_id, start_date)
        for entry in audit_entries:
            event = _bus_message_to_event(entry)
            if event:
                events.append(event)
    except Exception as exc:
        log.warning("Failed to read audit log: %s", exc)

    # 2. Read guard events
    guard_log = GOV_LOG_DIR / project_id / "guard_events.jsonl"
    if guard_log.exists():
        try:
            for line in guard_log.read_text().splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                events.append(PipelineEvent(
                    id=data.get("ts", ""),
                    type="governance",
                    status="success" if data.get("event") != "guard_failed" else "failed",
                    source="architect",
                    timestamp=data.get("ts", ""),
                    detail=data,
                ))
        except (json.JSONDecodeError, OSError):
            pass

    # Sort by timestamp descending, take latest
    events.sort(key=lambda e: e.timestamp, reverse=True)
    events = events[:limit]

    return PipelineHistory(
        items=events,
        total=len(events),
        project_id=project_id,
    )


# ═══════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════


def _build_pipeline_status(project_id: str, state: dict) -> PipelineStatus:
    """Build a PipelineStatus from raw state dict."""
    phases = state.get("phases", {})
    blockers = state.get("blockers", [])
    gov = state.get("governance", {})

    total = len(phases)
    done = sum(1 for p in phases.values() if p.get("status") == "done") if phases else 0
    progress = round(done / total * 100) if total else 0

    return PipelineStatus(
        project_id=project_id,
        name=state.get("name", ""),
        status=state.get("status", "in_progress"),
        phase=state.get("phase", "spec"),
        progress_pct=progress,
        phases=phases,
        blockers=blockers,
        guard_status=gov.get("guard_status", "pending"),
        updated_at=state.get("updated_at", ""),
    )


def _count_queue_depth(project_id: str) -> int:
    """Count pending messages for a project in the queue.

    Scans queue files for matching project_id. This is O(n) but
    acceptable for Phase 3-4 scale (few hundred messages).
    """
    from central_bus.queue import QUEUE_DIR

    count = 0
    if not QUEUE_DIR.exists():
        return 0

    for priority_file in QUEUE_DIR.glob("*.jsonl"):
        try:
            for line in priority_file.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if data.get("project_id") == project_id:
                        count += 1
                except json.JSONDecodeError:
                    continue
        except OSError:
            continue

    return count


def _bus_message_to_event(entry: dict) -> Optional[PipelineEvent]:
    """Convert a BusMessage dict to a PipelineEvent."""
    msg_type = entry.get("type", "")
    payload = entry.get("payload", {})
    ts = entry.get("ts", entry.get("timestamp", ""))

    if msg_type == "AO_REQUEST":
        return PipelineEvent(
            id=entry.get("id", ""),
            type="agent",
            status="running",
            source=entry.get("from_dept", ""),
            timestamp=ts,
            detail={
                "agent_id": payload.get("agent_id", ""),
                "trace_id": entry.get("trace_id", ""),
                "project_id": entry.get("project_id", ""),
            },
        )
    elif msg_type == "AO_RESPONSE":
        result = payload.get("result", {})
        return PipelineEvent(
            id=entry.get("id", ""),
            type="agent",
            status="success" if result.get("success", False) else "failed",
            source=entry.get("from_dept", ""),
            timestamp=ts,
            duration_ms=int(result.get("elapsed", 0) * 1000),
            detail={
                "agent_id": payload.get("agent_id", ""),
                "trace_id": entry.get("trace_id", ""),
            },
        )
    elif msg_type in ("ARTIFACT", "GOVERNANCE"):
        gov_event = payload.get("gov_event", "governance_event")
        return PipelineEvent(
            id=entry.get("id", ""),
            type="governance",
            status="success",
            source=entry.get("from_dept", ""),
            timestamp=ts,
            detail=payload,
        )

    return None
