"""Watchdog auto-triage — routed ค้างเกินกำหนด → alert / fail (Wave 3 · Runtime Visibility)

ปัญหา
─────
worker poll เฉพาะ `status='routed'` (workers/agent_worker_service.py) และไม่มี
กลไกปิดสถานะข้อความที่ไม่มีใครหยิบ → ข้อความค้างเงียบ ๆ ได้เป็นสัปดาห์
(เคสจริง: task `watchdog-model-health-1793325601` สร้าง 2026-10-30 ค้าง routed
14 วัน กว่าจะถูก mark failed ด้วยมือ στις 2026-11-13)

`check_orphaned_messages` (central_bus/monitor_watchdog.py) ตรวจได้แค่ว่า
"ไม่มีใครจะมารับ" (target ไม่มีใน AGENT_IDS / ค้าง >15 นาที) แต่ **ไม่เคย**
ตัดสินใจอะไรกับข้อความนั้น — ค้างต่อไปเรื่อย ๆ

Policy (ค่าเริ่มต้น = report-only / dry-run)
──────────────────────────────────────────
  age > 24h  → ALERT   บันทึก ceo_alerts (id deterministic → idempotent)
  age > 7d   → FAIL    mark failed + error_log `AUTO-TRIAGE: routed stale >7d ...`
  completed / failed / dead → **ไม่แตะเด็ดขาด**

Idempotency
───────────
  · error_log มี entry AUTO-TRIAGE ที่ยังไม่ resolved → ไม่ append ซ้ำ
  · error_log มี entry AUTO-TRIAGE ที่ `resolved: true` → ไม่แตะ (คนแก้แล้ว)
  · alert id = `triage-<message_id>-24h` → `INSERT OR IGNORE` (รอบถัดไปไม่สร้างซ้ำ)
  · UPDATE ... WHERE error_log = <ค่าที่อ่านมา> → ถ้ามีคนแก้ระหว่างทาง จะไม่ทับ

Safety
──────
  · default = dry-run: อ่านเท่านั้น ไม่เขียนอะไรเลย
  · `--apply` เท่านั้นที่เขียนจริง
  · ไม่ย้าย dead_letter_queue — คงรูปเดียวกับ precedent (status='failed' + error_log)
    เพื่อให้ CEO เห็นใน queue failed และ ack/แก้ได้จากที่เดียว
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATUSES = ("routed",)
ALERT_AFTER_HOURS = 24
FAIL_AFTER_HOURS = 24 * 7  # 7 วัน
MARKER = "AUTO-TRIAGE"
SOURCE = "watchdog-triage"

Tier = Literal["none", "alert", "fail"]


# ── helpers ─────────────────────────────────────────────────────────────
def resolve_db_path(db_path: str | Path | None = None) -> Path:
    """path ของ bus.db — ค่า default มาจาก settings แบบเดียวกับ scripts/purge-stale-queue.py"""
    if db_path:
        path = Path(db_path)
    else:
        from central_bus.config import settings

        path = Path(settings.db_path)
    if not path.is_absolute():
        path = ROOT / path
    return path


def parse_ts(value: str | None) -> datetime | None:
    """รับได้ทั้ง ISO มี tz และ sqlite 'YYYY-MM-DD HH:MM:SS' (ถือเป็น UTC)"""
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def auto_triage_state(error_log_raw: str | None) -> tuple[bool, bool]:
    """คืน (has_marker, resolved) จาก error_log

    has_marker = มี entry ที่เป็น AUTO-TRIAGE มาก่อนแล้ว
    resolved   = entry นั้นถูกทำเครื่องหมายว่าแก้แล้ว (`resolved: true`)
    """
    if not error_log_raw:
        return (False, False)
    try:
        entries = json.loads(error_log_raw)
    except (TypeError, ValueError):
        return (False, False)
    if not isinstance(entries, list):
        return (False, False)

    marked = [
        entry
        for entry in entries
        if isinstance(entry, dict)
        and (entry.get("auto_triage") is True or MARKER in str(entry.get("error", "")))
    ]
    if not marked:
        return (False, False)
    return (True, any(entry.get("resolved") for entry in marked))


def triage_entry(
    *,
    age_hours: float,
    previous_status: str,
    threshold_hours: float,
    now: datetime,
) -> dict:
    days = age_hours / 24
    return {
        "attempt": 0,  # 0 = ไม่ใช่ retry ของ agent (ระบบเป็นคนตัดสิน ไม่ใช่ worker)
        "error": (
            f"{MARKER}: routed stale >{threshold_hours / 24:g}d "
            f"(age {days:.1f}d, status {previous_status}) — "
            "no worker pickup, auto-failed by watchdog-triage"
        ),
        "timestamp": now.isoformat(),
        "auto_triage": True,
        "marker": MARKER,
        "threshold_days": threshold_hours / 24,
        "previous_status": previous_status,
        "resolved": False,
    }


@dataclass
class TriageItem:
    message_id: str
    task_id: str
    agent_id: str
    target_agent: str | None
    status: str
    created_at: str | None
    age_hours: float
    tier: Tier
    reason: str
    applied: list[str] = field(default_factory=list)
    skipped: str | None = None

    @property
    def age_days(self) -> float:
        return round(self.age_hours / 24, 2)

    def as_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "target_agent": self.target_agent,
            "status": self.status,
            "created_at": self.created_at,
            "age_hours": round(self.age_hours, 2),
            "age_days": self.age_days,
            "tier": self.tier,
            "reason": self.reason,
            "applied": self.applied,
            "skipped": self.skipped,
        }


@dataclass
class TriageReport:
    db_path: str
    applied: bool
    alert_after_hours: float
    fail_after_hours: float
    statuses: tuple[str, ...] = DEFAULT_STATUSES
    checked: int = 0
    alert_count: int = 0
    fail_count: int = 0
    changed: int = 0
    alerts_written: int = 0
    items: list[TriageItem] = field(default_factory=list)
    error: str | None = None
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def has_candidates(self) -> bool:
        return bool(self.alert_count or self.fail_count)

    def as_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "db_path": self.db_path,
            "mode": "apply" if self.applied else "dry-run",
            "policy": {
                "alert_after_hours": self.alert_after_hours,
                "fail_after_hours": self.fail_after_hours,
                "statuses": list(self.statuses),
            },
            "checked": self.checked,
            "alert_count": self.alert_count,
            "fail_count": self.fail_count,
            "changed": self.changed,
            "alerts_written": self.alerts_written,
            "items": [item.as_dict() for item in self.items],
            "error": self.error,
        }


# ── core ────────────────────────────────────────────────────────────────
def _load_candidates(conn: sqlite3.Connection, statuses: tuple[str, ...]) -> list[dict]:
    placeholders = ",".join("?" for _ in statuses)
    rows = conn.execute(
        f"SELECT id, task_id, agent_id, target_agent, status, created_at, error_log "
        f"FROM queue WHERE status IN ({placeholders}) ORDER BY created_at ASC",
        statuses,
    )
    return [dict(row) for row in rows]


def _classify(
    row: dict,
    now: datetime,
    alert_after_hours: float,
    fail_after_hours: float,
) -> TriageItem:
    created = parse_ts(row.get("created_at"))
    age_hours = (now - created).total_seconds() / 3600 if created else 0.0
    has_marker, resolved = auto_triage_state(row.get("error_log"))

    # _load_candidates กรอง status มาแล้ว — ที่นี่ตัดสินด้วยอายุเท่านั้น
    if age_hours > fail_after_hours:
        tier = "fail"
        reason = (
            f"routed ค้าง {age_hours / 24:.1f} วัน (เกิน {fail_after_hours / 24:g} วัน) "
            "และไม่มี worker หยิบ"
        )
    elif age_hours > alert_after_hours:
        tier = "alert"
        reason = (
            f"routed ค้าง {age_hours:.1f} ชั่วโมง (เกิน {alert_after_hours:g} ชั่วโมง) "
            "และไม่มี worker หยิบ"
        )
    else:
        tier = "none"
        reason = f"ยังไม่เกินเกณฑ์ ({age_hours:.1f} ชั่วโมง)"

    item = TriageItem(
        message_id=row["id"],
        task_id=row.get("task_id") or "",
        agent_id=row.get("agent_id") or "",
        target_agent=row.get("target_agent"),
        status=row["status"],
        created_at=row.get("created_at"),
        age_hours=age_hours,
        tier=tier,
        reason=reason,
    )
    if tier != "none" and has_marker:
        item.skipped = (
            "auto-triage resolved แล้ว — ไม่แตะซ้ำ"
            if resolved
            else "มี AUTO-TRIAGE entry อยู่แล้ว — ไม่ append ซ้ำ (idempotent)"
        )
    return item


def _write_alert(
    conn: sqlite3.Connection, item: TriageItem, now: datetime, alert_after_hours: float
) -> bool:
    """INSERT OR IGNORE alert record — id deterministic → รอบถัดไปไม่สร้างซ้ำ"""
    alert_id = f"triage-{item.message_id}-{alert_after_hours:g}h"
    cursor = conn.execute(
        "INSERT OR IGNORE INTO ceo_alerts "
        "(id, alert_type, severity, source, title, detail, acknowledged, "
        " acknowledged_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 0, NULL, ?)",
        (
            alert_id,
            "queue_stale_routed",
            "HIGH",
            SOURCE,
            f"routed ค้าง {item.age_hours:.1f} ชั่วโมง: {item.task_id}"[:200],
            json.dumps(
                {
                    "message_id": item.message_id,
                    "task_id": item.task_id,
                    "agent_id": item.agent_id,
                    "target_agent": item.target_agent,
                    "status": item.status,
                    "created_at": item.created_at,
                    "age_hours": round(item.age_hours, 2),
                    "policy": f"alert after {alert_after_hours:g}h",
                    "hint": "ดู scripts/purge-stale-queue.py หรือตั้ง target_agent ให้ worker รับได้",
                },
                ensure_ascii=False,
            )[:2000],
            now.isoformat(),
        ),
    )
    return cursor.rowcount > 0


def _write_fail(
    conn: sqlite3.Connection,
    item: TriageItem,
    original_error_log: str | None,
    now: datetime,
    fail_after_hours: float,
) -> bool:
    """mark failed แบบ optimistic — ไม่ทับถ้ามีคนแก้ error_log/status ระหว่างทาง"""
    try:
        entries = json.loads(original_error_log or "[]")
        if not isinstance(entries, list):
            entries = []
    except (TypeError, ValueError):
        entries = []

    entries.append(
        triage_entry(
            age_hours=item.age_hours,
            previous_status=item.status,
            threshold_hours=fail_after_hours,
            now=now,
        )
    )
    cursor = conn.execute(
        "UPDATE queue SET status = 'failed', updated_at = ?, error_log = ? "
        "WHERE id = ? AND status IN ('routed','pending') "
        "AND IFNULL(error_log, '') = IFNULL(?, '')",
        (
            now.isoformat(),
            json.dumps(entries, ensure_ascii=False),
            item.message_id,
            original_error_log,
        ),
    )
    return cursor.rowcount > 0


def run_triage(
    db_path: str | Path | None = None,
    *,
    apply: bool = False,
    now: datetime | None = None,
    alert_after_hours: float = ALERT_AFTER_HOURS,
    fail_after_hours: float = FAIL_AFTER_HOURS,
    statuses: tuple[str, ...] = DEFAULT_STATUSES,
) -> TriageReport:
    """ตรวจ (และถ้า apply=True ก็จัดการ) ข้อความ routed ที่ค้างเกินกำหนด"""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    path = resolve_db_path(db_path)
    report = TriageReport(
        db_path=str(path),
        applied=apply,
        alert_after_hours=alert_after_hours,
        fail_after_hours=fail_after_hours,
        statuses=tuple(statuses),
    )

    if not path.exists():
        report.error = f"ไม่พบ DB: {path}"
        return report

    # ── อ่าน (read-only เสมอ) ──
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = _load_candidates(conn, statuses)
        conn.close()
    except sqlite3.Error as exc:
        report.error = f"อ่าน DB ไม่ได้: {exc}"
        return report

    report.checked = len(rows)
    items = [_classify(row, now, alert_after_hours, fail_after_hours) for row in rows]
    report.items = items
    report.alert_count = sum(1 for item in items if item.tier in ("alert", "fail"))
    report.fail_count = sum(1 for item in items if item.tier == "fail")

    if not apply or not report.has_candidates:
        return report

    # ── เขียน (เฉพาะ --apply) ──
    originals = {row["id"]: row.get("error_log") for row in rows}
    try:
        conn = sqlite3.connect(str(path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            for item in items:
                if item.tier == "none" or item.skipped:
                    continue
                if _write_alert(conn, item, now, alert_after_hours):
                    item.applied.append("alert")
                    report.alerts_written += 1
                if item.tier == "fail" and _write_fail(
                    conn, item, originals.get(item.message_id), now, fail_after_hours
                ):
                    item.applied.append("fail")
                    report.changed += 1
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except sqlite3.Error as exc:
        report.error = f"เขียน DB ไม่ได้: {exc}"

    return report


def format_report(report: TriageReport) -> str:
    mode = "APPLY" if report.applied else "DRY-RUN (report only)"
    lines = [
        f"watchdog-triage [{mode}] — {report.generated_at}",
        f"DB: {report.db_path}",
        f"Policy: routed > {report.alert_after_hours:g}h → alert · "
        f"> {report.fail_after_hours / 24:g}d → fail · "
        f"statuses={','.join(report.statuses)}",
    ]
    if report.error:
        lines.append(f"ERROR: {report.error}")
        return "\n".join(lines)
    lines.append(
        f"ตรวจ {report.checked} แถว · alert {report.alert_count} · "
        f"fail {report.fail_count} · เปลี่ยนสถานะ {report.changed} · "
        f"เขียน alert {report.alerts_written}"
    )
    for item in report.items:
        if item.tier == "none":
            continue
        tag = "FAIL" if item.tier == "fail" else "ALERT"
        extra = f" [{item.skipped}]" if item.skipped else ""
        applied = f" → applied={','.join(item.applied)}" if item.applied else ""
        lines.append(
            f"  {tag:5} {item.message_id[:8]} {item.task_id[:40]:42} "
            f"{item.status:8} age={item.age_days}d{extra}{applied}"
        )
    if not report.has_candidates:
        lines.append("  ✅ ไม่มีข้อความ routed ค้างเกินเกณฑ์")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Auto-triage routed ที่ค้างเกินกำหนด (default = report only)"
    )
    parser.add_argument(
        "--db", default=None, help="path ของ bus.db (default: settings)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="เขียนจริง (alert record + mark failed) — ไม่ใส่ = dry-run",
    )
    parser.add_argument("--json", action="store_true", help="พิมพ์ผลเป็น JSON")
    parser.add_argument(
        "--alert-after",
        type=float,
        default=ALERT_AFTER_HOURS,
        help="เกณฑ์ alert (ชั่วโมง, default 24)",
    )
    parser.add_argument(
        "--fail-after",
        type=float,
        default=FAIL_AFTER_HOURS,
        help="เกณฑ์ mark failed (ชั่วโมง, default 168 = 7 วัน)",
    )
    args = parser.parse_args(argv)

    report = run_triage(
        args.db,
        apply=args.apply,
        alert_after_hours=args.alert_after,
        fail_after_hours=args.fail_after,
    )

    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_report(report))

    if report.error:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
