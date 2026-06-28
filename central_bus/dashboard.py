import json
from pathlib import Path
from .state import get, PROJECTS_DIR

STATUS_ICON = {"pending": "⏳", "in_progress": "🔄", "done": "✅", "failed": "❌"}


def summary(project_id: str) -> dict:
    state = get(project_id)
    phases = state["phases"]
    done = sum(1 for p in phases.values() if p["status"] == "done")
    total = len(phases)
    return {
        "project_id": project_id,
        "name": state.get("name", ""),
        "status": state["status"],
        "phase": state["phase"],
        "progress_pct": round(done / total * 100),
        "phases": {k: v["status"] for k, v in phases.items()},
        "blockers": state.get("blockers", []),
    }


def all_projects() -> list[dict]:
    if not PROJECTS_DIR.exists():
        return []
    return [summary(p.name) for p in sorted(PROJECTS_DIR.iterdir()) if p.is_dir()]


def render(project_id: str) -> str:
    s = summary(project_id)
    lines = [
        f"## Pipeline: {s['name'] or project_id}",
        f"Status: {s['status']} | Phase: {s['phase']} | Progress: {s['progress_pct']}%",
        "",
        "### Phases",
    ]
    for phase, status in s["phases"].items():
        lines.append(f"  {STATUS_ICON.get(status,'?')} {phase}: {status}")
    if s["blockers"]:
        lines.append("\n### Blockers")
        lines.extend(f"  - {b}" for b in s["blockers"])
    return "\n".join(lines)
