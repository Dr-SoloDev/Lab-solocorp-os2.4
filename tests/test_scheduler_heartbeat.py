"""Scheduler heartbeat tests — loop_runner/main.py heartbeat() (CMD-001-F)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import loop_runner.state as state
from loop_runner.main import heartbeat


class TestSchedulerHeartbeat:
    def test_heartbeat_writes_state_record(self, monkeypatch, tmp_path):
        monkeypatch.setattr(state, "DB", tmp_path / "state.db")
        marker = heartbeat()
        assert marker.startswith("[scheduler]")
        assert marker.endswith("fired")
        last = state.last_run("__scheduler__")
        assert last is not None  # record ถูกเขียนจริง

    def test_heartbeat_survives_broken_db(self, monkeypatch, tmp_path):
        # DB path ที่ parent ไม่มีอยู่ → sqlite connect fail → ต้องไม่ raise
        monkeypatch.setattr(state, "DB", tmp_path / "missing" / "state.db")
        marker = heartbeat()
        assert marker.startswith("[scheduler]")

    def test_heartbeat_repeated_updates_last_run(self, monkeypatch, tmp_path):
        monkeypatch.setattr(state, "DB", tmp_path / "state.db")
        heartbeat()
        first = state.last_run("__scheduler__")
        assert first is not None
        heartbeat()
        second = state.last_run("__scheduler__")
        assert second >= first  # upsert ไม่งอก row ใหม่
