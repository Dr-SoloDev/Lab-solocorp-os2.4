import asyncio
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


# ── Audit Logger tests (async SQLite) ───────────────────────────────────────

def _run(coro):
    """Run a coroutine in an isolated event loop (no pytest-asyncio required)."""
    return asyncio.run(coro)


def _reset_db(db_path: str) -> None:
    """Reset the global DbManager singleton to force re-init with given path."""
    import central_bus.db as _db
    _db.reset_db_for_testing()
    import central_bus.config as _cfg
    _cfg.settings.db_path = db_path


def test_audit_log_and_read(tmp_path):
    _reset_db(str(tmp_path / "test.db"))
    msg = make_msg()

    async def _run_test():
        await log(msg)
        return await read("proj_p2")

    entries = _run(_run_test())
    assert len(entries) == 1
    assert entries[0]["entity_id"] == msg.id


def test_audit_append_only(tmp_path):
    _reset_db(str(tmp_path / "test.db"))

    async def _run_test():
        for _ in range(3):
            await log(make_msg())
        return await read("proj_p2")

    assert len(_run(_run_test())) == 3


def test_audit_read_empty(tmp_path):
    _reset_db(str(tmp_path / "test.db"))

    async def _run_test():
        return await read("no_project")

    assert _run(_run_test()) == []


def test_audit_trace_id_preserved(tmp_path):
    _reset_db(str(tmp_path / "test.db"))
    msg = make_msg()

    async def _run_test():
        await log(msg)
        return await read("proj_p2")

    entries = _run(_run_test())
    assert entries[0]["trace_id"] == "trace_p2"
