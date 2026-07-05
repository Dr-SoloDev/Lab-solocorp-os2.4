"""Tests for guard_runner.py and the pipeline guard integration in state.py.

Test pyramid:
  1. Pure function tests for ``run_guards_for_phase`` — no I/O.
  2. ``load_guard_spec`` / ``load_project_artifacts`` — real filesystem.
  3. State integration (``run_pipeline_guards`` + ``update_phase`` hook) —
     tmp_path + monkeypatch for isolated file I/O.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from central_bus.guard_runner import (
    load_guard_spec,
    load_project_artifacts,
    run_guards_for_phase,
)
from central_bus.state import (
    add_guard,
    get,
    init_project,
    run_pipeline_guards,
    update_phase,
)

# ===========================================================================
# Test data — pure dicts, no filesystem needed
# ===========================================================================

MIN_SPEC = {
    "guards": [
        {"id": "GUARD-001", "name": "Schema Compliance", "type": "automated", "severity": "blocking"},
        {"id": "GUARD-002", "name": "Bilingual Completeness", "type": "automated", "severity": "blocking"},
        {"id": "GUARD-005", "name": "Review Date Compliance", "type": "automated", "severity": "warning"},
        {"id": "GUARD-007", "name": "Stakeholder Sign-off", "type": "manual", "severity": "blocking"},
    ],
    "execution": {
        "order": ["GUARD-001", "GUARD-002", "GUARD-005", "GUARD-007"],
    },
}

VALID_ARTIFACT = {
    "metadata": {
        "id": "ADR-001",
        "title": "Test ADR",
        "status": "accepted",
        "author": "Tester",
        "date": "2026-07-05",
    },
    "classification": {
        "domain": "governance",
        "impact": "low",
        "complexity": "low",
        "scope": "team",
    },
    "body": {
        "en": {"summary": "x", "context": "x", "decision": "x", "consequences": "x"},
        "th": {"summary": "x", "context": "x", "decision": "x", "consequences": "x"},
    },
    "footer": {"references": [], "review_date": "2026-10-05"},
}

EMPTY_ARTIFACT: dict = {}

# ===========================================================================
# Pure function tests for run_guards_for_phase
# ===========================================================================


class TestRunGuardsForPhase:
    """Pure execution layer — no state file I/O, all data passed as params."""

    def test_empty_active_guards_returns_empty(self):
        results = run_guards_for_phase(
            phase="spec",
            active_guards=[],
            artifact_data={},
            guard_spec=MIN_SPEC,
        )
        assert results == []

    def test_automated_guard_passes_with_valid_artifact(self):
        active = [{"name": "GUARD-001", "status": "pending"}]
        results = run_guards_for_phase(
            phase="spec",
            active_guards=active,
            artifact_data={"ADR-001": VALID_ARTIFACT},
            guard_spec=MIN_SPEC,
        )
        assert len(results) == 1
        r = results[0]
        assert r["guard_id"] == "GUARD-001"
        assert r["passed"] is True
        assert r["blocking"] is False

    def test_automated_guard_fails_with_empty_artifact(self):
        active = [{"name": "GUARD-001", "status": "pending"}]
        results = run_guards_for_phase(
            phase="spec",
            active_guards=active,
            artifact_data={"ADR-001": EMPTY_ARTIFACT},
            guard_spec=MIN_SPEC,
        )
        assert len(results) == 1
        r = results[0]
        assert r["guard_id"] == "GUARD-001"
        assert r["passed"] is False
        assert r["blocking"] is True  # severity=blocking + failed

    def test_warning_severity_guard_is_not_blocking(self):
        active = [{"name": "GUARD-005", "status": "pending"}]
        results = run_guards_for_phase(
            phase="spec",
            active_guards=active,
            artifact_data={"ADR-001": EMPTY_ARTIFACT},
            guard_spec=MIN_SPEC,
        )
        assert len(results) == 1
        r = results[0]
        assert r["passed"] is False
        assert r["blocking"] is False  # severity=warning → not blocking

    def test_manual_guard_returns_pending(self):
        active = [{"name": "GUARD-007", "status": "pending"}]
        results = run_guards_for_phase(
            phase="spec",
            active_guards=active,
            artifact_data={},
            guard_spec=MIN_SPEC,
        )
        assert len(results) == 1
        r = results[0]
        assert r["guard_id"] == "GUARD-007"
        assert r["passed"] is False
        assert r["type"] == "manual"
        assert any(i["status"] == "PENDING" for i in r["issues"])

    def test_skips_guards_not_in_active_set(self):
        active = [{"name": "GUARD-002", "status": "pending"}]
        results = run_guards_for_phase(
            phase="spec",
            active_guards=active,
            artifact_data={"ADR-001": VALID_ARTIFACT},
            guard_spec=MIN_SPEC,
        )
        ids = [r["guard_id"] for r in results]
        assert "GUARD-001" not in ids
        assert "GUARD-002" in ids

    def test_multiple_guards_all_pass(self):
        active = [
            {"name": "GUARD-001", "status": "pending"},
            {"name": "GUARD-002", "status": "pending"},
        ]
        results = run_guards_for_phase(
            phase="spec",
            active_guards=active,
            artifact_data={"ADR-001": VALID_ARTIFACT},
            guard_spec=MIN_SPEC,
        )
        assert len(results) == 2
        assert all(r["passed"] for r in results)

    def test_multiple_guards_some_fail(self):
        active = [
            {"name": "GUARD-001", "status": "pending"},
            {"name": "GUARD-002", "status": "pending"},
        ]
        results = run_guards_for_phase(
            phase="spec",
            active_guards=active,
            artifact_data={"ADR-001": EMPTY_ARTIFACT},
            guard_spec=MIN_SPEC,
        )
        assert len(results) == 2
        assert all(not r["passed"] for r in results)

    def test_no_artifacts_returns_passed(self):
        """Zero artifacts means nothing to validate — guard passes."""
        active = [{"name": "GUARD-001", "status": "pending"}]
        results = run_guards_for_phase(
            phase="spec",
            active_guards=active,
            artifact_data={},
            guard_spec=MIN_SPEC,
        )
        assert len(results) == 1
        assert results[0]["passed"] is True

    def test_guard_not_in_spec_is_skipped(self):
        active = [{"name": "GUARD-999", "status": "pending"}]
        results = run_guards_for_phase(
            phase="spec",
            active_guards=active,
            artifact_data={"ADR-001": VALID_ARTIFACT},
            guard_spec=MIN_SPEC,
        )
        assert results == []

    def test_result_includes_issues_from_all_artifacts(self):
        active = [{"name": "GUARD-001", "status": "pending"}]
        results = run_guards_for_phase(
            phase="spec",
            active_guards=active,
            artifact_data={
                "ADR-001": VALID_ARTIFACT,
                "ADR-002": EMPTY_ARTIFACT,
            },
            guard_spec=MIN_SPEC,
        )
        assert len(results) == 1
        r = results[0]
        assert r["passed"] is False  # ADR-002 is empty → fails
        # Issues should reference the failing artifact
        assert any(i.get("artifact") == "ADR-002" for i in r["issues"])


# ===========================================================================
# load_guard_spec / load_project_artifacts (real filesystem)
# ===========================================================================


class TestLoadGuardSpec:
    def test_loads_default_profile(self):
        spec = load_guard_spec()
        assert "guards" in spec
        assert "execution" in spec
        assert len(spec["guards"]) == 9

    def test_unknown_profile_raises(self):
        with pytest.raises(FileNotFoundError):
            load_guard_spec("nonexistent_profile")

    def test_execution_order_matches_guard_ids(self):
        spec = load_guard_spec()
        order = spec["execution"]["order"]
        guard_ids = {g["id"] for g in spec["guards"]}
        assert set(order) == guard_ids


class TestLoadProjectArtifacts:
    def test_no_artifacts_returns_empty(self):
        state = {"governance": {"adrs": [], "rfcs": []}}
        assert load_project_artifacts(state) == {}

    def test_loads_real_adr001(self):
        state = {"governance": {"adrs": ["ADR-001"], "rfcs": []}}
        artifacts = load_project_artifacts(state)
        assert "ADR-001" in artifacts
        assert artifacts["ADR-001"]["metadata"]["id"] == "ADR-001"

    def test_loads_real_rfc001(self):
        state = {"governance": {"adrs": [], "rfcs": ["RFC-001"]}}
        artifacts = load_project_artifacts(state)
        assert "RFC-001" in artifacts
        assert artifacts["RFC-001"]["metadata"]["id"] == "RFC-001"


# ===========================================================================
# State integration: run_pipeline_guards + update_phase hook
# ===========================================================================

SAMPLE_GUARD_SPEC = """\
[metadata]
id = "GUARD-SPEC-TEST"
title = "Test Spec"
version = "1.0.0"
status = "active"
author = "Tester"
created = "2026-07-05"

[[guards]]
id = "GUARD-001"
name = "Schema Compliance"
type = "automated"
severity = "blocking"

[[guards]]
id = "GUARD-002"
name = "Bilingual Completeness"
type = "automated"
severity = "blocking"

[execution]
order = ["GUARD-001", "GUARD-002"]
"""

SAMPLE_VALID_ADR = """\
[metadata]
id = "ADR-001"
title = "Test ADR"
status = "accepted"
author = "Tester"
date = "2026-07-05"

[classification]
domain = "governance"
impact = "low"
complexity = "low"
scope = "team"

[body.en]
summary = "x"
context = "x"
decision = "x"
consequences = "x"

[body.th]
summary = "x"
context = "x"
decision = "x"
consequences = "x"

[footer]
references = []
review_date = "2026-10-05"
"""


class _IntegrationBase:
    """Sets up tmp_path with gov/ files and monkeypatches guard_runner paths."""

    @staticmethod
    def _setup_gov(tmp_path):
        """Create minimal gov/ directory structure in tmp_path."""
        gov_dir = tmp_path / "gov"
        guard_spec_dir = gov_dir / "guards"
        adr_dir = gov_dir / "adr"

        guard_spec_dir.mkdir(parents=True, exist_ok=True)
        adr_dir.mkdir(parents=True, exist_ok=True)

        (guard_spec_dir / "default.toml").write_text(SAMPLE_GUARD_SPEC)
        (adr_dir / "ADR-001.toml").write_text(SAMPLE_VALID_ADR)

        return gov_dir, guard_spec_dir

    @staticmethod
    def _patch_guard_runner(tmp_path, monkeypatch):
        """Point guard_runner.GOV_DIR / GUARD_SPEC_DIR to tmp_path."""
        import central_bus.guard_runner as gr

        gov_dir, guard_spec_dir = _IntegrationBase._setup_gov(tmp_path)
        monkeypatch.setattr(gr, "GOV_DIR", gov_dir)
        monkeypatch.setattr(gr, "GUARD_SPEC_DIR", guard_spec_dir)

    @staticmethod
    def _patch_state(tmp_path, monkeypatch):
        """Point state.PROJECTS_DIR to tmp_path."""
        projects_dir = tmp_path / "bus" / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("central_bus.state.PROJECTS_DIR", projects_dir)


class TestRunPipelineGuards(_IntegrationBase):
    """State-level run_pipeline_guards() that coordinates execution + resolution."""

    def test_no_active_guards_returns_empty(self, tmp_path, monkeypatch):
        self._patch_guard_runner(tmp_path, monkeypatch)
        self._patch_state(tmp_path, monkeypatch)
        init_project("p1")
        assert run_pipeline_guards("p1", "spec") == []

    def test_active_guards_pass_and_get_resolved(self, tmp_path, monkeypatch):
        self._patch_guard_runner(tmp_path, monkeypatch)
        self._patch_state(tmp_path, monkeypatch)
        init_project("p1")

        # Link the real ADR-001 artifact
        import central_bus.state as st
        st.update_governance("p1", {"adrs": ["ADR-001"]})

        add_guard("p1", "GUARD-001")
        add_guard("p1", "GUARD-002")
        assert len(get("p1")["governance"]["active_guards"]) == 2

        results = run_pipeline_guards("p1", "spec")

        assert len(results) == 2
        assert all(r["passed"] for r in results)

        # Guards should be resolved
        state = get("p1")
        assert state["governance"]["active_guards"] == []
        assert state["governance"]["guard_status"] == "passed"

    def test_blocking_guard_fails_raises_valueerror(self, tmp_path, monkeypatch):
        self._patch_guard_runner(tmp_path, monkeypatch)
        self._patch_state(tmp_path, monkeypatch)
        init_project("p1")
        add_guard("p1", "GUARD-001")
        # NOTE: no artifacts linked → guard will fail

        with pytest.raises(ValueError, match="blocking guard"):
            run_pipeline_guards("p1", "spec")

        # Guard should NOT be resolved
        assert len(get("p1")["governance"]["active_guards"]) == 1

    def test_missing_guard_spec_is_handled_gracefully(self, tmp_path, monkeypatch):
        self._patch_state(tmp_path, monkeypatch)
        init_project("p1")
        add_guard("p1", "GUARD-001")
        # No guard spec exists (GOV_DIR was not set up)
        results = run_pipeline_guards("p1", "spec")
        assert results == []


class TestUpdatePhaseGuardHook(_IntegrationBase):
    """The update_phase() integration: guards fire on in_progress transitions."""

    def test_in_progress_with_passing_guards(self, tmp_path, monkeypatch):
        self._patch_guard_runner(tmp_path, monkeypatch)
        self._patch_state(tmp_path, monkeypatch)
        init_project("p1")

        import central_bus.state as st
        st.update_governance("p1", {"adrs": ["ADR-001"]})
        add_guard("p1", "GUARD-001")
        add_guard("p1", "GUARD-002")

        state = update_phase("p1", "spec", "in_progress")

        assert state["phases"]["spec"]["status"] == "in_progress"
        assert state["governance"]["active_guards"] == []
        assert state["governance"]["guard_status"] == "passed"

    def test_in_progress_with_failing_guards(self, tmp_path, monkeypatch):
        self._patch_guard_runner(tmp_path, monkeypatch)
        self._patch_state(tmp_path, monkeypatch)
        init_project("p1")
        add_guard("p1", "GUARD-001")
        # No artifacts → guard fails

        with pytest.raises(ValueError, match="blocking guard"):
            update_phase("p1", "spec", "in_progress")

        # Phase must NOT have been updated
        assert get("p1")["phases"]["spec"]["status"] == "pending"

    def test_done_transition_does_not_trigger_guards(self, tmp_path, monkeypatch):
        """Guards only run on in_progress — done transitions are unaffected."""
        self._patch_guard_runner(tmp_path, monkeypatch)
        self._patch_state(tmp_path, monkeypatch)
        init_project("p1")
        add_guard("p1", "GUARD-001")

        # First set spec to in_progress (will fail due to guard)
        with pytest.raises(ValueError):
            update_phase("p1", "spec", "in_progress")

    def test_no_active_guards_transition_proceeds_normally(self, tmp_path, monkeypatch):
        self._patch_guard_runner(tmp_path, monkeypatch)
        self._patch_state(tmp_path, monkeypatch)
        init_project("p1")
        state = update_phase("p1", "spec", "in_progress")
        assert state["phases"]["spec"]["status"] == "in_progress"

    def test_subsequent_phases_also_trigger_guards(self, tmp_path, monkeypatch):
        self._patch_guard_runner(tmp_path, monkeypatch)
        self._patch_state(tmp_path, monkeypatch)
        init_project("p1")

        import central_bus.state as st
        st.update_governance("p1", {"adrs": ["ADR-001"]})

        # Advance through spec successfully
        add_guard("p1", "GUARD-001")
        update_phase("p1", "spec", "in_progress")
        update_phase("p1", "spec", "done")

        # Add a new guard for the design phase
        add_guard("p1", "GUARD-001")
        state = update_phase("p1", "design", "in_progress")
        assert state["phases"]["design"]["status"] == "in_progress"
        assert state["governance"]["active_guards"] == []
