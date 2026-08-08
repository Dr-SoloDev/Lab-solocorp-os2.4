"""Dashboard loops section tests — central_bus/dashboard.py _loops() (CMD-001-F / ORD-001-C)."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import loop_runner.state as state
from central_bus.dashboard import _loops, owner_dashboard


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setattr(state, "DB", tmp_path / "state.db")
    yield state.DB


class TestDashboardLoops:
    def test_empty_state_db_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr(state, "DB", tmp_path / "nonexistent.db")
        data = _loops()
        assert data["loops"] == []
        assert data["heartbeat"] is None

    def test_loops_and_heartbeat_present(self, fresh_db):
        state.record("__scheduler__", "fired", success=True)
        state.record("daily_brief", "brief ok", success=True)
        data = _loops()
        ids = [l["loop_id"] for l in data["loops"]]
        assert "daily_brief" in ids
        assert data["heartbeat"] is not None
        assert data["heartbeat"]["status"] == "✅"

    def test_stale_loop_is_red(self, fresh_db):
        # __scheduler__ interval = 30 นาที → stale เมื่อ > 60 นาที
        old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        import sqlite3
        with sqlite3.connect(state.DB) as c:
            c.execute("CREATE TABLE IF NOT EXISTS loops (id TEXT PRIMARY KEY, last_run TEXT, last_result TEXT, failures INTEGER DEFAULT 0)")
            c.execute("INSERT INTO loops(id, last_run, last_result, failures) VALUES('daily_brief', ?, 'old', 0)", (old,))
            c.execute("INSERT INTO loops(id, last_run, last_result, failures) VALUES('__scheduler__', ?, 'fired', 0)", (old,))
        data = _loops()
        hb = data["heartbeat"]
        assert hb["status"] == "🔴"  # 180 นาที >> 2×interval (60 นาที)
        db = next(l for l in data["loops"] if l["loop_id"] == "daily_brief")
        assert db["status"] == "✅"  # 180 นาที ≤ 2×interval ของ 20 ชม. (2400 นาที)

    def test_owner_dashboard_json_contains_loops(self, fresh_db):
        state.record("__scheduler__", "fired", success=True)
        dash = owner_dashboard(format="json")
        assert "loops" in dash
        assert dash["loops"]["heartbeat"]["loop_id"] == "__scheduler__"

    def test_owner_dashboard_markdown_has_loops_table(self, fresh_db):
        state.record("__scheduler__", "fired", success=True)
        md = owner_dashboard(format="markdown")
        assert "## 🔁 Automation Loops" in md
        assert "__scheduler__" in md
