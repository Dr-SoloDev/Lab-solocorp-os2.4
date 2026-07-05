"""Guard Runner — automated guard execution for pipeline state machine.

This is the pure execution layer: load the spec, load artifacts, run checkers.
It does NOT touch project state files — that's state.py's job via run_pipeline_guards().
"""
from __future__ import annotations

import logging
from pathlib import Path

import tomllib

from govctl_cli.guard import GUARD_CHECKERS

log = logging.getLogger(__name__)

GOV_DIR = Path(__file__).resolve().parent.parent / "gov"
GUARD_SPEC_DIR = GOV_DIR / "guards"


def load_guard_spec(profile: str = "default", spec_dir: Path | None = None) -> dict:
    """Load a guard spec TOML file.

    Args:
        profile: Guard profile name (maps to gov/guards/<profile>.toml).
        spec_dir: Override the directory to search in. Defaults to GUARD_SPEC_DIR.

    Returns:
        Parsed TOML content as a dict.

    Raises:
        FileNotFoundError: If the profile file does not exist.
    """
    directory = spec_dir if spec_dir is not None else GUARD_SPEC_DIR
    path = directory / f"{profile}.toml"
    if not path.exists():
        raise FileNotFoundError(f"Guard profile '{profile}' not found at {path}")
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_project_artifacts(project_state: dict) -> dict[str, dict]:
    """Load all governance artifacts (ADRs, RFCs) referenced by a project.

    Args:
        project_state: The full project state dict (from state.get()).

    Returns:
        Dict mapping artifact ID (e.g. "ADR-001") -> parsed TOML content.
    """
    gov = project_state.get("governance", {})
    artifacts: dict[str, dict] = {}

    for adr_id in gov.get("adrs", []):
        path = GOV_DIR / "adr" / f"{adr_id}.toml"
        if path.exists():
            with open(path, "rb") as f:
                artifacts[adr_id] = tomllib.load(f)
        else:
            log.warning("ADR artifact not found: %s", path)

    for rfc_id in gov.get("rfcs", []):
        path = GOV_DIR / "rfc" / f"{rfc_id}.toml"
        if path.exists():
            with open(path, "rb") as f:
                artifacts[rfc_id] = tomllib.load(f)
        else:
            log.warning("RFC artifact not found: %s", path)

    return artifacts


def _check_single_guard(
    guard_def: dict,
    artifact_data: dict[str, dict],
) -> tuple[list[dict], bool, bool]:
    """Run a single automated or manual guard against all artifacts.

    Args:
        guard_def: Guard definition from the spec.
        artifact_data: Loaded artifact content keyed by ID.

    Returns:
        Tuple of (issues, passed, blocking).
    """
    gtype = guard_def.get("type", "automated")
    severity = guard_def.get("severity", "warning")
    gid = guard_def["id"]

    if gtype == "manual":
        return (
            [{"status": "PENDING", "detail": "Manual guard — requires human approval"}],
            False,
            severity == "blocking",
        )

    # Automated guard
    checker = GUARD_CHECKERS.get(gid)
    if not checker:
        log.warning("No checker implemented for %s — treating as warning", gid)
        return (
            [{"status": "WARN", "detail": "No checker implemented for this guard"}],
            True,
            False,
        )

    all_issues: list[dict] = []
    if not artifact_data:
        # No artifacts to check — guard passes (nothing to validate)
        return ([], True, False)

    for artifact_id, artifact in artifact_data.items():
        issues = checker(artifact)
        for issue in issues:
            issue["artifact"] = artifact_id
        all_issues.extend(issues)

    passed = not any(i["status"] == "FAIL" for i in all_issues)
    blocking = severity == "blocking" and not passed
    return (all_issues, passed, blocking)


def run_guards_for_phase(
    phase: str,
    active_guards: list[dict],
    artifact_data: dict[str, dict],
    guard_spec: dict | None = None,
) -> list[dict]:
    """Run guards for a phase transition against project artifacts.

    Only processes guards that are in ``active_guards``.  Guards whose ID does
    not appear in ``active_guards`` are skipped entirely.

    Args:
        phase: Target phase name (used for result metadata).
        active_guards: List of active guard entries from project state
            (each must have a ``"name"`` key matching a guard spec ``"id"``).
        artifact_data: Parsed TOML content for each artifact keyed by ID.
        guard_spec: Pre-loaded spec (auto-loaded if ``None``).

    Returns:
        List of result dicts, one per active guard processed:
        ``guard_id``, ``name``, ``type``, ``severity``, ``issues``,
        ``passed``, ``blocking``.
    """
    if guard_spec is None:
        guard_spec = load_guard_spec()

    guard_defs = {g["id"]: g for g in guard_spec.get("guards", [])}
    exec_order = guard_spec.get("execution", {}).get("order", [])

    # Fast lookup of active guard names
    active_names = {g["name"] for g in active_guards}

    results: list[dict] = []
    for gid in exec_order:
        if gid not in active_names:
            continue

        guard_def = guard_defs.get(gid)
        if not guard_def:
            log.warning("Guard %s in exec order but missing from spec", gid)
            continue

        issues, passed, blocking = _check_single_guard(guard_def, artifact_data)

        results.append({
            "guard_id": gid,
            "name": guard_def.get("name", gid),
            "type": guard_def.get("type", "automated"),
            "severity": guard_def.get("severity", "warning"),
            "issues": issues,
            "passed": passed,
            "blocking": blocking,
        })

    return results
