import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from central_bus.state import init_project, update_phase, PROJECTS_DIR
from central_bus.dashboard import summary, render, all_projects
from central_bus.qa_gate import check, advance, GATE_RULES


# ── Dashboard tests ──────────────────────────────────────────────────────────

def test_summary_initial(tmp_path, monkeypatch):
    import central_bus.state as s
    import central_bus.dashboard as d
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(d, "PROJECTS_DIR", tmp_path)
    init_project("p1", name="Test")
    r = summary("p1")
    assert r["progress_pct"] == 0
    assert r["phase"] == "spec"
    assert r["status"] == "in_progress"

def test_summary_progress(tmp_path, monkeypatch):
    import central_bus.state as s
    import central_bus.dashboard as d
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(d, "PROJECTS_DIR", tmp_path)
    init_project("p2")
    update_phase("p2", "spec", "done")
    update_phase("p2", "design", "done")
    update_phase("p2", "arch", "done")
    r = summary("p2")
    assert r["progress_pct"] == 50  # 3/6

def test_render_contains_phases(tmp_path, monkeypatch):
    import central_bus.state as s
    import central_bus.dashboard as d
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(d, "PROJECTS_DIR", tmp_path)
    init_project("p3", name="MyProj")
    out = render("p3")
    assert "MyProj" in out
    assert "spec" in out

def test_all_projects(tmp_path, monkeypatch):
    import central_bus.state as s
    import central_bus.dashboard as d
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(d, "PROJECTS_DIR", tmp_path)
    init_project("pa")
    init_project("pb")
    projects = all_projects()
    ids = [p["project_id"] for p in projects]
    assert "pa" in ids and "pb" in ids


# ── QA Gate tests ────────────────────────────────────────────────────────────

def test_gate_pass_all_evidence():
    evidence = {c: True for c in GATE_RULES["dev"]}
    passed, missing = check("proj", "dev", evidence)
    assert passed is True
    assert missing == []

def test_gate_fail_missing_condition():
    passed, missing = check("proj", "dev", {"code_review_passed": True})
    assert passed is False
    assert "unit_tests_passed" in missing

def test_gate_unknown_phase_passes():
    passed, missing = check("proj", "nonexistent", {})
    assert passed is True

def test_advance_passes_gate(tmp_path, monkeypatch):
    import central_bus.state as s
    import central_bus.dashboard as d
    import central_bus.qa_gate as qg
    import central_bus.exceptions as ex
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(d, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(ex, "ESCALATION_LOG", tmp_path / "esc.jsonl")
    init_project("pg1")
    evidence = {c: True for c in GATE_RULES["spec"]}
    result = advance("pg1", "spec", evidence)
    assert result is True
    assert s.get("pg1")["phases"]["spec"]["status"] == "done"

def test_advance_blocks_and_escalates(tmp_path, monkeypatch):
    import central_bus.state as s
    import central_bus.exceptions as ex
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(ex, "ESCALATION_LOG", tmp_path / "esc.jsonl")
    init_project("pg2")
    result = advance("pg2", "dev", evidence={})
    assert result is False
    assert (tmp_path / "esc.jsonl").exists()


# ── update_phase QA gate integration tests ─────────────────────────────

def test_update_phase_with_evidence_passes_gate(tmp_path, monkeypatch):
    """update_phase() with valid evidence should pass the gate and mark phase done."""
    import central_bus.state as s
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    init_project("proj_wire1")
    # Advance prior phases so "dev" can be set to done
    update_phase("proj_wire1", "spec", "done")
    update_phase("proj_wire1", "design", "done")
    update_phase("proj_wire1", "arch", "done")
    # Mark dev done with all required evidence
    evidence = {c: True for c in GATE_RULES["dev"]}
    state = update_phase("proj_wire1", "dev", "done", evidence=evidence)
    assert state["phases"]["dev"]["status"] == "done"


def test_update_phase_with_missing_evidence_raises(tmp_path, monkeypatch):
    """update_phase() with incomplete evidence should raise ValueError."""
    import central_bus.state as s
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    init_project("proj_wire2")
    update_phase("proj_wire2", "spec", "done")
    update_phase("proj_wire2", "design", "done")
    update_phase("proj_wire2", "arch", "done")
    # Only provide one of the two required conditions
    evidence = {"code_review_passed": True}  # missing unit_tests_passed
    with pytest.raises(ValueError, match="QA gate check failed"):
        update_phase("proj_wire2", "dev", "done", evidence=evidence)


def test_update_phase_skips_gate_without_evidence(tmp_path, monkeypatch):
    """update_phase() without evidence should skip gate check (backward compat) and succeed."""
    import central_bus.state as s
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    init_project("proj_wire3")
    update_phase("proj_wire3", "spec", "done")
    update_phase("proj_wire3", "design", "done")
    update_phase("proj_wire3", "arch", "done")
    # No evidence — should skip QA gate, log warning, and still succeed
    state = update_phase("proj_wire3", "dev", "done")
    assert state["phases"]["dev"]["status"] == "done"
