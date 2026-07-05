import fcntl
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

log = logging.getLogger(__name__)

PROJECTS_DIR = Path(__file__).parent.parent / "bus" / "projects"
GOV_LOG_DIR = Path(__file__).parent.parent / "bus" / "governance"

PhaseStatus = Literal["pending", "in_progress", "done", "failed"]
GuardStatus = Literal["pending", "running", "passed", "failed"]

PHASES = ["spec", "design", "arch", "dev", "qa", "deploy"]

# ── Helper: guard event log ──────────────────────────────────────────


def _log_guard_event(project_id: str, event: dict) -> None:
    """Append a governance event to the project's guard log."""
    log_path = GOV_LOG_DIR / project_id / "guard_events.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(event) + "\n")
        fcntl.flock(f, fcntl.LOCK_UN)


# ── State file I/O ───────────────────────────────────────────────────


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


def init_project(project_id: str, name: str = "", threshold: str = "auto") -> dict:
    """Create initial state.json for a new project.

    Args:
        project_id: Unique project identifier.
        name: Human-readable project name.
        threshold: Governance threshold mode — "auto" | "manual".
                   auto = guard checks run automatically at phase gates.
                   manual = guards must be explicitly resolved before transition.
    """
    state = {
        "project_id": project_id,
        "name": name,
        "status": "in_progress",
        "phase": "spec",
        "phases": {p: {"status": "pending", "owner": ""} for p in PHASES},
        "blockers": [],
        "governance": {
            "rfcs": [],
            "adrs": [],
            "active_guards": [],
            "guard_status": "pending",
            "complexity_score": 0,
            "threshold": threshold,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _log_guard_event(project_id, {
        "ts": state["updated_at"],
        "event": "project_init",
        "detail": f"Project '{name}' initialized with {threshold} threshold",
    })
    _write(project_id, state)
    return state


def get(project_id: str) -> dict:
    path = _state_path(project_id)
    if not path.exists():
        raise FileNotFoundError(f"Project {project_id} not found")
    return json.loads(path.read_text())


def update_phase(project_id: str, phase: str, status: PhaseStatus, owner: str = "", evidence: dict | None = None) -> dict:
    """Update a phase status with sequence validation, optimistic locking, and governance guard check.

    Governance guard validation:
        - Before marking a phase as ``done``, if there are active guards and
          guard_status is not "passed", the transition is **blocked**.
        - Before marking a phase as ``in_progress``, if governance threshold is
          "manual" and guard_status is not "passed", the transition is blocked.

    QA gate validation:
        - When ``status == "done"`` and ``evidence`` is provided, the quality
          gate is checked via ``qa_gate.check()``. If missing conditions are
          found, the transition is **blocked** with a ``ValueError``.
        - When ``status == "done"`` and ``evidence`` is ``None``, the gate
          check is skipped and a warning is logged (backward compatibility).
    """
    if phase not in PHASES:
        raise ValueError(f"Invalid phase '{phase}'. Valid phases: {', '.join(PHASES)}")

    # Run pipeline guards BEFORE acquiring the file lock — guards manage
    # their own locking via resolve_guard().  If a blocking guard fails,
    # ValueError is raised and the phase transition is aborted.
    if status == "in_progress":
        run_pipeline_guards(project_id, phase)

    path = _state_path(project_id)
    with open(path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        state = json.load(f)
        if status != "failed":
            _validate_phase_transition(state["phases"], phase, status)
            _validate_governance_guard(state, phase, status)
            # QA gate check — block if evidence is provided and conditions are not met
            if status == "done":
                if evidence is not None:
                    from .qa_gate import check  # lazy import to avoid circular dependency

                    passed, missing = check(project_id, phase, evidence)
                    if not passed:
                        raise ValueError(
                            f"Cannot set '{phase}' to 'done': "
                            f"QA gate check failed. Missing conditions: {missing}"
                        )
                else:
                    import logging

                    logging.warning(
                        "No evidence provided for phase '%s' done transition — "
                        "QA gate check skipped for project '%s'",
                        phase,
                        project_id,
                    )
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


# ── Governance: guard validation hook ────────────────────────────────


def _validate_governance_guard(state: dict, target_phase: str, target_status: PhaseStatus) -> None:
    """Block phase transition if governance guard has not passed.

    Rules:
        - ``done`` transition: blocked if active_guards is non-empty AND guard_status != "passed".
        - ``in_progress`` transition (manual threshold only): blocked if guard_status != "passed".
    """
    gov = state.get("governance", {})
    active_guards = gov.get("active_guards", [])
    guard_status: str = gov.get("guard_status", "pending")
    threshold: str = gov.get("threshold", "auto")

    if target_status == "done" and active_guards and guard_status != "passed":
        raise ValueError(
            f"Cannot set '{target_phase}' to 'done': "
            f"governance guard status is '{guard_status}' (expected 'passed'). "
            f"Active guards: {active_guards}."
        )

    if target_status == "in_progress" and threshold == "manual" and guard_status != "passed":
        raise ValueError(
            f"Cannot set '{target_phase}' to 'in_progress' under manual threshold: "
            f"governance guard status is '{guard_status}' (expected 'passed')."
        )


# ── Governance: read / write helpers ────────────────────────────────


def get_governance(project_id: str) -> dict:
    """Return the governance sub-object for a project."""
    return get(project_id).get("governance", {})


def update_governance(project_id: str, updates: dict) -> dict:
    """Update governance fields atomically.

    Accepted keys: rfcs, adrs, active_guards, guard_status, complexity_score, threshold.
    """
    allowed = {"rfcs", "adrs", "active_guards", "guard_status", "complexity_score", "threshold"}
    path = _state_path(project_id)
    with open(path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        state = json.load(f)
        gov = state.setdefault("governance", {
            "rfcs": [], "adrs": [], "active_guards": [],
            "guard_status": "pending", "complexity_score": 0, "threshold": "auto",
        })
        for key in allowed:
            if key in updates:
                gov[key] = updates[key]
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        f.seek(0)
        json.dump(state, f, indent=2)
        f.truncate()
        fcntl.flock(f, fcntl.LOCK_UN)
    return state


def add_guard(project_id: str, guard_name: str) -> dict:
    """Add a named guard check to active_guards and set guard_status to 'pending'.

    Returns the updated governance sub-object.
    """
    guard_entry = {
        "name": guard_name,
        "status": "pending",
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    path = _state_path(project_id)
    with open(path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        state = json.load(f)
        gov = state.setdefault("governance", {
            "rfcs": [], "adrs": [], "active_guards": [],
            "guard_status": "pending", "complexity_score": 0, "threshold": "auto",
        })
        # deduplicate by name
        if guard_name not in [g["name"] for g in gov["active_guards"]]:
            gov["active_guards"].append(guard_entry)
        gov["guard_status"] = "pending"
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        f.seek(0)
        json.dump(state, f, indent=2)
        f.truncate()
        fcntl.flock(f, fcntl.LOCK_UN)

    _log_guard_event(project_id, {
        "ts": guard_entry["added_at"],
        "event": "guard_added",
        "guard": guard_name,
        "detail": f"Guard '{guard_name}' added to active_guards",
    })
    return state.get("governance", {})


def resolve_guard(project_id: str, guard_name: str, passed: bool) -> dict:
    """Resolve a named guard — remove from active_guards and update guard_status.

    When all active guards are resolved, guard_status becomes 'passed' (or 'failed').
    Returns the updated governance sub-object.
    """
    resolved_at = datetime.now(timezone.utc).isoformat()
    path = _state_path(project_id)
    with open(path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        state = json.load(f)
        gov = state.setdefault("governance", {
            "rfcs": [], "adrs": [], "active_guards": [],
            "guard_status": "pending", "complexity_score": 0, "threshold": "auto",
        })
        before = len(gov["active_guards"])
        gov["active_guards"] = [g for g in gov["active_guards"] if g["name"] != guard_name]
        removed = before - len(gov["active_guards"])

        # Determine overall status
        if passed and not gov["active_guards"]:
            gov["guard_status"] = "passed"
        elif not passed:
            gov["guard_status"] = "failed"
        # else: still pending (other guards remain)

        state["updated_at"] = resolved_at
        f.seek(0)
        json.dump(state, f, indent=2)
        f.truncate()
        fcntl.flock(f, fcntl.LOCK_UN)

    if removed:
        _log_guard_event(project_id, {
            "ts": resolved_at,
            "event": "guard_resolved" if passed else "guard_failed",
            "guard": guard_name,
            "detail": f"Guard '{guard_name}' {'passed' if passed else 'failed'} "
                      f"(remaining: {len(gov['active_guards'])})",
        })
    return state.get("governance", {})


def compute_complexity_score(project_id: str) -> int:
    """Compute a governance complexity score (0-3) for a project based on:

    - Number of RFCs linked (1+ → +1)
    - Number of ADRs linked (2+ → +1)
    - Whether threshold is manual (+1)
    - Any active guards (+1, but capped at 3)
    """
    state = get(project_id)
    gov = state.get("governance", {})
    score = 0
    if len(gov.get("rfcs", [])) > 0:
        score += 1
    if len(gov.get("adrs", [])) >= 2:
        score += 1
    if gov.get("threshold") == "manual":
        score += 1
    if gov.get("active_guards"):
        score = min(score + 1, 3)
    return min(score, 3)


# ── Pipeline guard runner ────────────────────────────────────────────


def run_pipeline_guards(project_id: str, phase: str) -> list[dict]:
    """Execute automated pipeline guards and resolve passed ones.

    Loads the project state, runs every active automated guard against the
    project's governance artifacts (ADRs, RFCs), resolves any that pass,
    and raises ``ValueError`` if a blocking guard fails.

    Manual guards (GUARD-007, GUARD-008, GUARD-009) are left pending —
    they require CLI approval via ``govctl guard approve``.

    This function acquires **its own** file locks (via ``resolve_guard``)
    and is safe to call *before* ``update_phase`` acquires its lock.

    Args:
        project_id: Project identifier.
        phase: Target phase name (used in error messaging).

    Returns:
        List of guard result dicts (same schema as
        :func:`guard_runner.run_guards_for_phase`).  Empty list when
        there are no active guards.

    Raises:
        ValueError: If any blocking guard produces FAIL issues.
        FileNotFoundError: If the project does not exist.
    """
    state = get(project_id)
    gov = state.get("governance", {})
    active_guards = gov.get("active_guards", [])

    if not active_guards:
        return []

    from .guard_runner import load_guard_spec, load_project_artifacts, run_guards_for_phase

    # Derive guard spec directory relative to PROJECTS_DIR so that patching
    # PROJECTS_DIR in tests automatically isolates guard spec lookups.
    # Layout: PROJECTS_DIR = <root>/bus/projects → <root>/gov/guards
    guard_spec_dir = PROJECTS_DIR.parent.parent / "gov" / "guards"

    try:
        guard_spec = load_guard_spec(spec_dir=guard_spec_dir)
    except FileNotFoundError:
        log.error("Guard spec not found — skipping pipeline guards for %s", project_id)
        return []

    artifact_data = load_project_artifacts(state)

    results = run_guards_for_phase(
        phase=phase,
        active_guards=active_guards,
        artifact_data=artifact_data,
        guard_spec=guard_spec,
    )

    # Resolve automated guards that passed; collect blocking failures.
    # A blocking guard that "passed" only because artifact_data was empty is
    # not a genuine pass — the project has no governance artifacts linked, so
    # the guard requirement cannot be verified. Treat it as a blocking failure.
    blocking_failures: list[dict] = []
    for result in results:
        if result["type"] == "automated" and result["passed"]:
            if not artifact_data and result["severity"] == "blocking":
                # Vacuous pass on a blocking guard — not acceptable
                blocking_failures.append({**result, "blocking": True})
            else:
                resolve_guard(project_id, result["guard_id"], passed=True)
        elif result.get("blocking"):
            blocking_failures.append(result)

    if blocking_failures:
        failed_names = sorted(r["guard_id"] for r in blocking_failures)
        raise ValueError(
            f"Cannot set '{phase}' to 'in_progress': "
            f"blocking guard(s) failed: {failed_names}. "
            f"Run 'govctl guard run --target <artifact>' for details."
        )

    return results


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
