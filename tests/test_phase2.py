import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from central_bus.state import init_project, get, update_phase
from central_bus.audit import log, read
from central_bus.models import BusMessage


def make_msg(project_id="proj_p2") -> BusMessage:
    return BusMessage(
        from_dept="engineering", to_dept="qa", type="HANDOFF",
        project_id=project_id, phase="dev",
        payload={"text": "done"}, trace_id="trace_p2"
    )


# ── State Store tests ────────────────────────────────────────────────────────

def test_init_project(tmp_path, monkeypatch):
    import central_bus.state as s
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    state = init_project("proj_001", name="Test Project")
    assert state["project_id"] == "proj_001"
    assert state["phase"] == "spec"
    assert state["status"] == "in_progress"
    assert all(p["status"] == "pending" for p in state["phases"].values())

def test_get_project(tmp_path, monkeypatch):
    import central_bus.state as s
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    init_project("proj_002")
    state = get("proj_002")
    assert state["project_id"] == "proj_002"

def test_get_missing_raises(tmp_path, monkeypatch):
    import central_bus.state as s
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        get("nonexistent")

def test_update_phase(tmp_path, monkeypatch):
    import central_bus.state as s
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    init_project("proj_003")
    state = update_phase("proj_003", "spec", "done", owner="product")
    assert state["phases"]["spec"]["status"] == "done"
    assert state["phases"]["spec"]["owner"] == "product"

def test_phase_advances_after_done(tmp_path, monkeypatch):
    import central_bus.state as s
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    init_project("proj_004")
    update_phase("proj_004", "spec", "done")
    state = get("proj_004")
    assert state["phase"] == "design"

def test_project_status_done_when_all_phases_done(tmp_path, monkeypatch):
    import central_bus.state as s
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    init_project("proj_005")
    for phase in ["spec", "design", "arch", "dev", "qa", "deploy"]:
        update_phase("proj_005", phase, "done")
    state = get("proj_005")
    assert state["status"] == "done"

def test_project_status_failed(tmp_path, monkeypatch):
    import central_bus.state as s
    monkeypatch.setattr(s, "PROJECTS_DIR", tmp_path)
    init_project("proj_006")
    update_phase("proj_006", "dev", "failed")
    state = get("proj_006")
    assert state["status"] == "failed"


# ── Audit Logger tests ───────────────────────────────────────────────────────

def test_audit_log_and_read(tmp_path, monkeypatch):
    import central_bus.audit as a
    monkeypatch.setattr(a, "PROJECTS_DIR", tmp_path)
    msg = make_msg()
    log(msg)
    entries = read("proj_p2")
    assert len(entries) == 1
    assert entries[0]["id"] == msg.id

def test_audit_append_only(tmp_path, monkeypatch):
    import central_bus.audit as a
    monkeypatch.setattr(a, "PROJECTS_DIR", tmp_path)
    for _ in range(3):
        log(make_msg())
    assert len(read("proj_p2")) == 3

def test_audit_read_empty(tmp_path, monkeypatch):
    import central_bus.audit as a
    monkeypatch.setattr(a, "PROJECTS_DIR", tmp_path)
    assert read("no_project") == []

def test_audit_trace_id_preserved(tmp_path, monkeypatch):
    import central_bus.audit as a
    monkeypatch.setattr(a, "PROJECTS_DIR", tmp_path)
    msg = make_msg()
    log(msg)
    assert read("proj_p2")[0]["trace_id"] == "trace_p2"
