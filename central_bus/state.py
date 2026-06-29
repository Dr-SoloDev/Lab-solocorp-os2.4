import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

PROJECTS_DIR = Path(__file__).parent.parent / "bus" / "projects"

PhaseStatus = Literal["pending", "in_progress", "done", "failed"]

PHASES = ["spec", "design", "arch", "dev", "qa", "deploy"]


def _state_path(project_id: str) -> Path:
    path = PROJECTS_DIR / project_id / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write(project_id: str, state: dict) -> None:
    path = _state_path(project_id)
    with open(path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(state, f, indent=2)
        fcntl.flock(f, fcntl.LOCK_UN)


def init_project(project_id: str, name: str = "") -> dict:
    """Create initial state.json for a new project."""
    state = {
        "project_id": project_id,
        "name": name,
        "status": "in_progress",
        "phase": "spec",
        "phases": {p: {"status": "pending", "owner": ""} for p in PHASES},
        "blockers": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write(project_id, state)
    return state


def get(project_id: str) -> dict:
    path = _state_path(project_id)
    if not path.exists():
        raise FileNotFoundError(f"Project {project_id} not found")
    return json.loads(path.read_text())


def update_phase(project_id: str, phase: str, status: PhaseStatus, owner: str = "") -> dict:
    """Update a phase status with sequence validation and optimistic locking."""
    if phase not in PHASES:
        raise ValueError(f"Invalid phase '{phase}'. Valid phases: {', '.join(PHASES)}")
    path = _state_path(project_id)
    with open(path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        state = json.load(f)
        if status != "failed":
            _validate_phase_transition(state["phases"], phase, status)
        state["phases"][phase]["status"] = status
        if owner:
            state["phases"][phase]["owner"] = owner
        state["phase"] = _current_phase(state["phases"])
        state["status"] = _project_status(state["phases"])
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        f.seek(0)
        json.dump(state, f, indent=2)
        f.truncate()
        fcntl.flock(f, fcntl.LOCK_UN)
    return state


VALID_PHASE_ORDER = {p: i for i, p in enumerate(PHASES)}


def _validate_phase_transition(phases: dict, target_phase: str, target_status: PhaseStatus) -> None:
    if target_status == "pending":
        return
    target_idx = VALID_PHASE_ORDER.get(target_phase)
    if target_idx is None:
        raise ValueError(f"Invalid phase: {target_phase}")
    if target_status in ("in_progress", "done"):
        for prev_phase in PHASES[:target_idx]:
            if phases[prev_phase]["status"] == "pending":
                raise ValueError(
                    f"Cannot set '{target_phase}' to '{target_status}': "
                    f"previous phase '{prev_phase}' is still pending"
                )


def _current_phase(phases: dict) -> str:
    for p in PHASES:
        if phases[p]["status"] in ("pending", "in_progress"):
            return p
    return "deploy"


def _project_status(phases: dict) -> str:
    statuses = [phases[p]["status"] for p in PHASES]
    if "failed" in statuses:
        return "failed"
    if all(s == "done" for s in statuses):
        return "done"
    return "in_progress"
