"""Tests — watchdog auto-triage (Wave 3 · Runtime Visibility)

ขอบเขต: central_bus/watchdog_triage.py
  · routed >24h → alert record
  · routed >7d  → mark failed + structured AUTO-TRIAGE error_log
  · idempotent (รันซ้ำไม่สร้าง alert/entry ซ้ำ)
  · completed / failed / resolved แล้ว = ไม่แตะ
  · default = dry-run (ไม่เขียนอะไรเลย)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from central_bus.db import SCHEMA_SQL
from central_bus.watchdog_triage import (
    MARKER,
    auto_triage_state,
    parse_ts,
    run_triage,
)

NOW = datetime(2026, 11, 23, 12, 0, 0, tzinfo=timezone.utc)


# ── fixtures / helpers ──────────────────────────────────────────────────
@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "bus.db"
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
    return path


def _insert(
    db_path,
    message_id: str,
    *,
    status: str = "routed",
    age_hours: float = 1.0,
    error_log: str | None = None,
    task_id: str = "task-1",
    agent_id: str = "watchdog",
    target_agent: str | None = "ceo-turbo",
    created_at: str | None = None,
) -> None:
    created = created_at or (NOW - timedelta(hours=age_hours)).isoformat()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT INTO queue "
            "(id, trace_id, task_id, agent_id, target_agent, priority, status, "
            " payload, error_log, retry_count, max_retries, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'normal', ?, '{}', ?, 0, 3, ?, ?)",
            (
                message_id,
                "trace-1",
                task_id,
                agent_id,
                target_agent,
                status,
                error_log,
                created,
                created,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _row(db_path, message_id: str) -> dict:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        return dict(
            conn.execute("SELECT * FROM queue WHERE id = ?", (message_id,)).fetchone()
        )
    finally:
        conn.close()


def _alerts(db_path) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM ceo_alerts")]
    finally:
        conn.close()


# ── policy: 24h alert ───────────────────────────────────────────────────
def test_routed_25h_alerts_in_apply_mode(db_path):
    _insert(db_path, "m-25h", age_hours=25)

    report = run_triage(db_path, apply=True, now=NOW)

    assert report.checked == 1
    assert report.alert_count == 1
    assert report.fail_count == 0
    assert report.alerts_written == 1

    alerts = _alerts(db_path)
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "queue_stale_routed"
    assert alerts[0]["source"] == "watchdog-triage"
    assert alerts[0]["id"] == "triage-m-25h-24h"  # deterministic
    detail = json.loads(alerts[0]["detail"])
    assert detail["message_id"] == "m-25h"

    # ยังไม่ถึง 7 วัน → status ต้องไม่เปลี่ยน
    assert _row(db_path, "m-25h")["status"] == "routed"


def test_dry_run_writes_nothing(db_path):
    _insert(db_path, "m-25h", age_hours=25)
    _insert(db_path, "m-8d", age_hours=24 * 8)

    report = run_triage(db_path, apply=False, now=NOW)

    assert report.applied is False
    assert report.checked == 2
    assert report.alert_count == 2
    assert report.fail_count == 1
    assert report.changed == 0
    assert report.alerts_written == 0
    assert _alerts(db_path) == []
    assert _row(db_path, "m-8d")["status"] == "routed"
    assert _row(db_path, "m-8d")["error_log"] is None


def test_fresh_routed_is_ignored(db_path):
    _insert(db_path, "m-2h", age_hours=2)

    report = run_triage(db_path, apply=True, now=NOW)

    assert report.checked == 1
    assert report.alert_count == 0
    assert report.fail_count == 0
    assert report.items[0].tier == "none"
    assert _alerts(db_path) == []
    assert _row(db_path, "m-2h")["status"] == "routed"


# ── policy: 7d fail ─────────────────────────────────────────────────────
def test_routed_8d_is_marked_failed_with_structured_error(db_path):
    _insert(db_path, "m-8d", age_hours=24 * 8, task_id="watchdog-model-health-1")

    report = run_triage(db_path, apply=True, now=NOW)

    assert report.fail_count == 1
    assert report.changed == 1
    assert "fail" in report.items[0].applied

    row = _row(db_path, "m-8d")
    assert row["status"] == "failed"

    entries = json.loads(row["error_log"])
    triage_entries = [e for e in entries if e.get("auto_triage")]
    assert len(triage_entries) == 1
    entry = triage_entries[0]
    assert entry["error"].startswith(f"{MARKER}: routed stale >7d")
    assert entry["threshold_days"] == 7
    assert entry["previous_status"] == "routed"
    assert entry["resolved"] is False

    # >24h ด้วย → ต้องมี alert record ด้วย
    assert len(_alerts(db_path)) == 1

    # ไม่ถูกย้ายเข้า dead_letter_queue (คงรูปเดียวกับ precedent W1)
    conn = sqlite3.connect(str(db_path))
    try:
        assert conn.execute("SELECT COUNT(*) FROM dead_letter_queue").fetchone()[0] == 0
    finally:
        conn.close()


def test_existing_error_log_is_preserved(db_path):
    previous = json.dumps([{"attempt": 1, "error": "boom", "timestamp": "x"}])
    _insert(db_path, "m-8d", age_hours=24 * 8, error_log=previous)

    run_triage(db_path, apply=True, now=NOW)

    entries = json.loads(_row(db_path, "m-8d")["error_log"])
    assert entries[0] == {"attempt": 1, "error": "boom", "timestamp": "x"}
    assert len([e for e in entries if e.get("auto_triage")]) == 1


def test_boundary_just_under_7d_only_alerts(db_path):
    _insert(db_path, "m-6d23h", age_hours=24 * 7 - 1)

    report = run_triage(db_path, apply=True, now=NOW)

    assert report.fail_count == 0
    assert report.alert_count == 1
    assert _row(db_path, "m-6d23h")["status"] == "routed"


# ── idempotency ─────────────────────────────────────────────────────────
def test_apply_twice_is_idempotent(db_path):
    _insert(db_path, "m-8d", age_hours=24 * 8)

    first = run_triage(db_path, apply=True, now=NOW)
    second = run_triage(db_path, apply=True, now=NOW)

    assert first.changed == 1 and first.alerts_written == 1
    # รอบสอง: แถวถูก failed ไปแล้ว → ไม่ถูกเลือกมาอีก
    assert second.checked == 0
    assert second.changed == 0
    assert second.alerts_written == 0

    assert len(_alerts(db_path)) == 1
    entries = json.loads(_row(db_path, "m-8d")["error_log"])
    assert len([e for e in entries if e.get("auto_triage")]) == 1


def test_rerun_on_still_routed_with_marker_does_not_duplicate(db_path):
    """ถ้ามี AUTO-TRIAGE entry อยู่แล้ว (แต่ยัง routed) → ไม่ append ซ้ำ"""
    existing = json.dumps(
        [
            {
                "attempt": 0,
                "error": f"{MARKER}: routed stale >7d (age 8.0d)",
                "auto_triage": True,
            }
        ]
    )
    _insert(db_path, "m-8d", age_hours=24 * 8, error_log=existing)

    report = run_triage(db_path, apply=True, now=NOW)

    assert report.fail_count == 1
    assert report.items[0].skipped is not None
    assert report.changed == 0
    entries = json.loads(_row(db_path, "m-8d")["error_log"])
    assert len(entries) == 1
    assert _row(db_path, "m-8d")["status"] == "routed"


def test_resolved_marker_is_never_touched_again(db_path):
    resolved = json.dumps(
        [
            {
                "attempt": 0,
                "error": f"{MARKER}: routed stale >7d",
                "auto_triage": True,
                "resolved": True,
            }
        ]
    )
    _insert(db_path, "m-8d", age_hours=24 * 8, error_log=resolved)

    report = run_triage(db_path, apply=True, now=NOW)

    assert report.items[0].skipped is not None
    assert "resolved" in report.items[0].skipped
    assert report.changed == 0
    assert report.alerts_written == 0
    assert _row(db_path, "m-8d")["status"] == "routed"
    assert json.loads(_row(db_path, "m-8d")["error_log"]) == json.loads(resolved)


# ── never touch completed / failed ──────────────────────────────────────
@pytest.mark.parametrize("status", ["completed", "failed", "dead"])
def test_terminal_statuses_are_untouched(db_path, status):
    _insert(db_path, f"m-{status}", status=status, age_hours=24 * 30)

    report = run_triage(db_path, apply=True, now=NOW)

    assert report.checked == 0
    row = _row(db_path, f"m-{status}")
    assert row["status"] == status
    assert row["error_log"] is None
    assert _alerts(db_path) == []


def test_pending_is_out_of_scope_by_default(db_path):
    _insert(db_path, "m-pending", status="pending", age_hours=24 * 30)

    report = run_triage(db_path, apply=True, now=NOW)

    assert report.checked == 0
    assert _row(db_path, "m-pending")["status"] == "pending"


# ── helpers / edge cases ────────────────────────────────────────────────
def test_naive_sqlite_timestamp_is_treated_as_utc(db_path):
    created = (NOW - timedelta(hours=24 * 8)).strftime("%Y-%m-%d %H:%M:%S")
    _insert(db_path, "m-naive", age_hours=0, created_at=created)

    report = run_triage(db_path, apply=True, now=NOW)

    assert report.fail_count == 1
    assert _row(db_path, "m-naive")["status"] == "failed"


def test_missing_db_returns_error_not_exception(tmp_path):
    report = run_triage(tmp_path / "nope.db", apply=True, now=NOW)

    assert report.error is not None
    assert "ไม่พบ DB" in report.error
    assert report.checked == 0


def test_parse_ts_variants():
    assert parse_ts("2026-11-23T12:00:00+00:00") == NOW
    assert parse_ts("2026-11-23 12:00:00") == NOW
    assert parse_ts("2026-11-23T12:00:00Z") == NOW
    assert parse_ts(None) is None
    assert parse_ts("not-a-date") is None


def test_auto_triage_state_variants():
    assert auto_triage_state(None) == (False, False)
    assert auto_triage_state("[]") == (False, False)
    assert auto_triage_state("ไม่ใช่ json") == (False, False)
    assert auto_triage_state(json.dumps([{"error": "other"}])) == (False, False)
    assert auto_triage_state(json.dumps([{"error": f"{MARKER}: x"}])) == (True, False)
    assert auto_triage_state(json.dumps([{"auto_triage": True, "resolved": True}])) == (
        True,
        True,
    )
