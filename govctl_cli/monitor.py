"""
govctl monitor — collects metrics from Central Bus and gov/ for dashboard/API.

Reads project states from bus/projects/, queue messages from bus/queue/,
and governance artifact counts from gov/.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
BUS_DIR = PROJECT_ROOT / "bus"
QUEUE_DIR = BUS_DIR / "queue"
PROJECTS_DIR = BUS_DIR / "projects"
GOV_DIR = PROJECT_ROOT / "gov"
GOV_LOG_DIR = BUS_DIR / "governance"

QUEUE_PRIORITIES = ["critical", "high", "normal", "low"]


def count_toml(dir_path: Path) -> int:
    """Count .toml files in *dir_path* (return 0 if missing)."""
    if not dir_path.exists():
        return 0
    return len(list(dir_path.glob("*.toml")))


def count_queued_messages() -> dict[str, int]:
    """Return {priority: count} for each queue priority level."""
    counts: dict[str, int] = {p: 0 for p in QUEUE_PRIORITIES}
    if not QUEUE_DIR.exists():
        return counts

    for p in QUEUE_PRIORITIES:
        qfile = QUEUE_DIR / f"{p}.jsonl"
        if qfile.exists():
            with open(qfile) as f:
                counts[p] = sum(1 for line in f if line.strip())

    return counts


def collect_recent_events(limit: int = 20) -> list[dict]:
    """Collect recent governance events from bus/governance/*/guard_events.jsonl.

    Returns *limit* newest events, each with ts, event, guard, detail, and
    project_id.
    """
    events: list[dict] = []

    if not GOV_LOG_DIR.exists():
        return events

    for project_dir in sorted(GOV_LOG_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        evt_file = project_dir / "guard_events.jsonl"
        if not evt_file.exists():
            continue

        with open(evt_file) as f:
            for line in f:
                if line.strip():
                    try:
                        evt = json.loads(line)
                        evt["project_id"] = project_dir.name
                        events.append(evt)
                    except json.JSONDecodeError:
                        continue

    # Sort newest-first by ts
    events.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return events[:limit]


def collect_recent_bus_events(limit: int = 10) -> list[dict]:
    """Collect recent messages from the normal-priority queue as events."""
    events: list[dict] = []
    qfile = QUEUE_DIR / "normal.jsonl"
    if not qfile.exists():
        return events

    lines = []
    with open(qfile) as f:
        for line in f:
            if line.strip():
                lines.append(line)

    # Last N lines (newest at end → reverse)
    for line in reversed(lines[-limit:]):
        try:
            msg = json.loads(line)
            payload = msg.get("payload", {})
            events.append({
                "ts": msg.get("ts", ""),
                "event": payload.get("gov_event", msg.get("type", "unknown")),
                "project_id": msg.get("project_id", ""),
                "artifact_id": payload.get("artifact_id", ""),
                "title": payload.get("title", ""),
                "detail": payload.get("gov_detail", payload.get("title", "")),
            })
        except json.JSONDecodeError:
            continue

    return events


def count_active_projects() -> int:
    """Count projects with status != 'done'."""
    if not PROJECTS_DIR.exists():
        return 0

    active = 0
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        state_file = project_dir / "state.json"
        if not state_file.exists():
            continue
        try:
            state = json.loads(state_file.read_text())
            if state.get("status") != "done":
                active += 1
        except (json.JSONDecodeError, OSError):
            continue

    return active


def list_projects() -> list[dict]:
    """Return summary of all projects."""
    projects: list[dict] = []
    if not PROJECTS_DIR.exists():
        return projects

    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        state_file = project_dir / "state.json"
        if not state_file.exists():
            continue
        try:
            state = json.loads(state_file.read_text())
            phases = state.get("phases", {})
            done = sum(1 for p in phases.values() if p.get("status") == "done")
            total = len(phases) or 1
            projects.append({
                "project_id": state.get("project_id", project_dir.name),
                "name": state.get("name", ""),
                "status": state.get("status", "unknown"),
                "phase": state.get("phase", "unknown"),
                "progress_pct": round(done / total * 100),
                "phases": {k: v["status"] for k, v in phases.items()},
                "blockers": state.get("blockers", []),
                "updated_at": state.get("updated_at", ""),
            })
        except (json.JSONDecodeError, OSError):
            continue

    return projects


def collect_metrics() -> dict[str, Any]:
    """Collect and return system-wide metrics.

    Returns:
        {
            "timestamp": "...",
            "active_projects": 3,
            "queued_messages": {"critical": 0, "high": 2, "normal": 5, "low": 0},
            "adr_count": 6,
            "rfc_count": 1,
            "guard_count": 1,
            "agent_count": 5,
            "recent_events": [...]
        }
    """
    queued = count_queued_messages()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_projects": count_active_projects(),
        "queued_messages": queued,
        "total_queued": sum(queued.values()),
        "adr_count": count_toml(GOV_DIR / "adr"),
        "rfc_count": count_toml(GOV_DIR / "rfc"),
        "guard_count": count_toml(GOV_DIR / "guards"),
        "agent_count": 5,  # CEO, Orchestrator, Architect, Engineering, QA
        "recent_events": collect_recent_bus_events(limit=20),
    }
