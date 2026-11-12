"""Live dashboard data sources (Phase A — 3s polling).

Owner อยากเห็นทุกห้องแบบสดโดยไม่ต้องพิมพ์ ``opencode session list`` เอง
ไฟล์นี้รวมแหล่งข้อมูล 3 อย่างไว้ที่เดียว — sessions, queue depth, สถานะรวม:

* :func:`list_sessions` — พยายามอ่าน sessions แบบ headless ก่อน
  (``opencode session list --format json``) ถ้า CLI ใช้ไม่ได้ค่อย fallback
  ไปอ่าน ``opencode.db`` แบบ read-only ถ้าทั้งคู่ล้มเหลวคืน ``[]`` พร้อม
  ``error`` — หน้า /live ต้อง render ได้เสมอ ห้าม 500 (PRD §9)
  Beta: production path มี sessions cache TTL 10s — poll 3s ไม่ spawn CLI
  ทุก poll (ADR-034 risk #1)
* :func:`queue_depths` — นับบรรทัด JSONL ใน ``bus/queue/`` แบบ fail-open
* :func:`live_status` — รวม sessions + queue + modules + provider เป็นก้อนเดียว
  ให้ ``GET /api/live/status`` และหน้า ``/live`` ใช้ร่วมกัน

Fail-open ทุกฟังก์ชัน: ไม่มี exception หลุดออกไปเด็ดขาด
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE_DIR = (
    Path(os.environ.get("SOLOCORP_BUS_DIR", str(REPO_ROOT / "bus"))) / "queue"
)
DEFAULT_OPENCODE_DB = Path(
    os.environ.get(
        "OPENCODE_DB",
        str(Path.home() / ".local" / "share" / "opencode" / "opencode.db"),
    )
)

SESSION_LIMIT = 30
CLI_TIMEOUT_S = 4.0

# ADR-034 Beta hardening: หน้า /live poll `/api/live/status` ทุก 3s แต่ห้าม
# spawn `opencode` CLI ทุก poll (risk #1) — cache envelope ของ sessions ไว้
# 10s ต่อ limit หนึ่งค่า เกิน TTL ค่อยเรียก source ใหม่ ระหว่างนั้นตอบ cache
# (updated_at คือเวลาของ cache — UI โชว์ความ stale ตรงไปตรงมา ไม่หลอกว่าสด)
SESSION_CACHE_TTL_S = 10.0
_SESSIONS_CACHE: dict[int, tuple[float, dict[str, Any]]] = {}
_SESSIONS_CACHE_LOCK = threading.Lock()


def clear_sessions_cache() -> None:
    """ล้าง sessions cache — ใช้ใน test เท่านั้น (production ไม่เรียก)."""

    with _SESSIONS_CACHE_LOCK:
        _SESSIONS_CACHE.clear()


# ชื่อไฟล์ queue ที่นับ — high/normal คือสัญญาใน task, ที่เหลือคือของจริงใน repo
# (critical/high/normal/low ตาม monitor.py + dead_letter ตาม solocorp_skills).
QUEUE_FILES: dict[str, list[str]] = {
    "critical": ["critical.jsonl"],
    "high": ["high.jsonl"],
    "normal": ["normal.jsonl"],
    "low": ["low.jsonl"],
    "dead": ["dead.jsonl", "dead_letter.jsonl"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_iso_time(value: Any) -> str | None:
    """แปลง epoch (s/ms) หรือ ISO string เป็น ISO string แบบสั้น."""

    if value is None:
        return None
    if isinstance(value, (int, float)) and value > 0:
        # opencode.db เก็บ ms; epoch s อยู่แถว 1e9, ms อยู่แถว 1e12
        seconds = float(value) / 1000.0 if value > 1e11 else float(value)
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat(
                timespec="seconds"
            )
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _as_int(value: Any) -> int | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        number = int(value)
        return number if number >= 0 else None
    except (TypeError, ValueError):
        return None


def normalize_session(raw: Any) -> dict[str, Any]:
    """บีบ session 1 แถว (จาก CLI หรือ DB — shape ไม่แน่นอน) ให้เป็น envelope เดียว.

    Contract หน้า /live: ``id, title, agent, model, tokens, outcome, time``.
    ฟิลด์ไหนไม่มีคือ ``None`` — ห้ามทิ้งแถว ห้าม raise.
    """

    if not isinstance(raw, dict):
        return {
            "id": str(raw)[:64] if raw else "—",
            "title": "—",
            "agent": None,
            "model": None,
            "tokens": None,
            "outcome": None,
            "time": None,
        }
    get = raw.get
    session_id = get("id") or get("session_id") or get("sessionID") or get("key") or "—"
    title = get("title") or get("name") or get("summary") or get("brief") or "—"
    agent = get("agent") or get("agent_id") or get("agentId") or None
    model = (
        get("model") or get("model_id") or get("modelId") or get("model_name") or None
    )
    tokens = None
    for key in ("tokens", "total_tokens", "token_count", "usage"):
        candidate = get(key)
        if isinstance(candidate, dict):
            candidate = (candidate.get("total") or candidate.get("input", 0) or 0) + (
                candidate.get("output") or 0
            )
        tokens = _as_int(candidate)
        if tokens is not None:
            break
    if tokens is None:
        usage = get("tokens_in"), get("tokens_out")
        if any(isinstance(v, (int, float)) for v in usage):
            tokens = int(sum(v or 0 for v in usage if isinstance(v, (int, float))))
    outcome = (
        get("outcome")
        or get("status")
        or get("result")
        or get("state")
        or get("conclusion")
        or None
    )
    time_value = _to_iso_time(
        get("time")
        or get("updated_at")
        or get("updatedAt")
        or get("time_created")
        or get("timeCreated")
        or get("created_at")
        or get("createdAt")
        or get("timestamp")
    )
    return {
        "id": str(session_id),
        "title": str(title),
        "agent": str(agent) if agent else None,
        "model": str(model) if model else None,
        "tokens": tokens,
        "outcome": str(outcome) if outcome else None,
        "time": time_value,
    }


def _sessions_from_cli(
    limit: int, *, command: list[str] | None = None
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """เรียก ``opencode session list --format json`` แบบ headless.

    คืน ``(sessions, None)`` เมื่อสำเร็จ หรือ ``(None, reason)`` เมื่อ CLI
    ใช้ไม่ได้ — caller เป็นคนตัดสินใจ fallback ต่อ.
    """

    cmd = command or ["opencode", "session", "list", "--format", "json"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_S,
            check=False,
        )
    except FileNotFoundError:
        return None, "opencode CLI not found"
    except subprocess.TimeoutExpired:
        return None, f"opencode CLI timed out after {CLI_TIMEOUT_S:g}s"
    except OSError as exc:
        return None, f"opencode CLI cannot start: {exc}"
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:200]
        return None, f"opencode CLI exited {proc.returncode}: {detail or 'no output'}"
    try:
        payload: Any = json.loads(proc.stdout or "null")
    except json.JSONDecodeError as exc:
        return None, f"opencode CLI returned non-JSON: {exc}"
    if isinstance(payload, dict):
        for key in ("sessions", "items", "data"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        return None, "opencode CLI JSON is not a list"
    return [normalize_session(item) for item in payload[:limit]], None


def _sessions_from_db(
    limit: int, *, db_path: Path | None = None
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Fallback: อ่านตาราง session จาก ``opencode.db`` แบบ read-only.

    Schema ของ opencode เปลี่ยนได้ — เลยไม่ hardcode column: ดูชื่อตาราง
    จาก ``sqlite_master`` แล้ว map ตามชื่อคอลัมน์จริงที่มีอยู่.
    """

    path = Path(db_path) if db_path else DEFAULT_OPENCODE_DB
    if not path.exists():
        return None, f"opencode.db not found: {path}"
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2.0)
    except sqlite3.Error as exc:
        return None, f"sqlite open failed: {exc}"
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        table = next(
            (name for name in ("session", "sessions", "session_v2") if name in tables),
            None,
        )
        if table is None:
            return None, f"no session table in {path.name} (has: {sorted(tables)[:8]})"
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        order_col = next(
            (
                col
                for col in (
                    "time_updated",
                    "time_created",
                    "updated_at",
                    "created_at",
                    "timestamp",
                    "time",
                )
                if col in columns
            ),
            columns[0] if columns else "rowid",
        )
        rows = conn.execute(
            f"SELECT * FROM {table} ORDER BY {order_col} DESC LIMIT ?",
            (max(1, limit),),
        ).fetchall()
        names = [
            desc[0]
            for desc in conn.execute(f"SELECT * FROM {table} LIMIT 0").description or []
        ]
        sessions = [normalize_session(dict(zip(names, row))) for row in rows]
        return sessions, None
    except sqlite3.Error as exc:
        return None, f"sqlite read failed: {exc}"
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def list_sessions(
    limit: int = SESSION_LIMIT,
    *,
    queue_cli: list[str] | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """คืน envelope ``{sessions, count, source, error, updated_at}`` — ไม่ raise.

    Beta cache (ADR-034): production path (ไม่ส่ง override ใด ๆ) อ่านจาก cache
    10s — poll 3s จึง spawn CLI อย่างมากทุก 10s ไม่ใช่ทุก 3s; test path ที่ส่ง
    ``queue_cli`` / ``db_path`` มาชัดเจน bypass cache เสมอเพื่อ determinism.
    """

    use_cache = queue_cli is None and db_path is None
    now = time.monotonic()
    if use_cache:
        with _SESSIONS_CACHE_LOCK:
            cached = _SESSIONS_CACHE.get(limit)
            if cached is not None:
                cached_at, envelope = cached
                if now - cached_at < SESSION_CACHE_TTL_S:
                    return envelope
    try:
        sessions, cli_error = _sessions_from_cli(limit, command=queue_cli)
        if sessions is not None:
            envelope = {
                "sessions": sessions,
                "count": len(sessions),
                "source": "cli",
                "error": None,
                "updated_at": _now_iso(),
            }
            if use_cache:
                with _SESSIONS_CACHE_LOCK:
                    _SESSIONS_CACHE[limit] = (now, envelope)
            return envelope
        db_sessions, db_error = _sessions_from_db(limit, db_path=db_path)
        if db_sessions is not None:
            envelope = {
                "sessions": db_sessions,
                "count": len(db_sessions),
                "source": "db",
                "error": None,
                "updated_at": _now_iso(),
            }
            if use_cache:
                with _SESSIONS_CACHE_LOCK:
                    _SESSIONS_CACHE[limit] = (now, envelope)
            return envelope
        envelope = {
            "sessions": [],
            "count": 0,
            "source": "none",
            "error": "; ".join(part for part in (cli_error, db_error) if part)
            or "no session source available",
            "updated_at": _now_iso(),
        }
        # อย่า cache path ที่ล้ม — poll รอบหน้าจะได้ลอง source ใหม่ทันที
        # แทนที่จะเสิร์ฟความว่างเปล่าค้าง 10s
        return envelope
    except Exception as exc:  # noqa: BLE001 - dashboard ต้อง render ได้เสมอ
        return {
            "sessions": [],
            "count": 0,
            "source": "none",
            "error": f"{type(exc).__name__}: {exc}"[:200],
            "updated_at": _now_iso(),
        }


def queue_depths(*, queue_dir: Path | None = None) -> dict[str, Any]:
    """นับบรรทัด JSONL ต่อ priority — ไฟล์หาย = 0, อ่านไม่ได้ = fail-open."""

    base = Path(queue_dir) if queue_dir else DEFAULT_QUEUE_DIR
    queues: dict[str, int] = {}
    try:
        for logical, files in QUEUE_FILES.items():
            total = 0
            for name in files:
                path = base / name
                if not path.exists():
                    continue
                try:
                    with open(path, encoding="utf-8") as handle:
                        total += sum(1 for line in handle if line.strip())
                except OSError:
                    continue
            queues[logical] = total
        # alias ที่ task สั่ง: dead = dead.jsonl + dead_letter.jsonl
        queues.setdefault("dead", queues.pop("dead", 0))
        total = sum(queues.values())
        return {"queues": queues, "total": total, "updated_at": _now_iso()}
    except Exception as exc:  # noqa: BLE001 - dashboard ต้อง render ได้เสมอ
        return {
            "queues": {key: 0 for key in QUEUE_FILES},
            "total": 0,
            "updated_at": _now_iso(),
            "error": f"{type(exc).__name__}: {exc}"[:200],
        }


def live_status(
    runtime: Any,
    *,
    session_limit: int = SESSION_LIMIT,
    queue_dir: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """รวมทุกอย่างที่หน้า /live ต้อง polling — ไม่ raise เด็ดขาด."""

    try:
        sessions_envelope = list_sessions(session_limit, db_path=db_path)
    except Exception as exc:  # noqa: BLE001
        sessions_envelope = {
            "sessions": [],
            "count": 0,
            "source": "none",
            "error": f"{type(exc).__name__}: {exc}"[:200],
            "updated_at": _now_iso(),
        }
    try:
        queue_envelope = queue_depths(queue_dir=queue_dir)
    except Exception as exc:  # noqa: BLE001
        queue_envelope = {
            "queues": {key: 0 for key in QUEUE_FILES},
            "total": 0,
            "updated_at": _now_iso(),
            "error": f"{type(exc).__name__}: {exc}"[:200],
        }
    try:
        counts = runtime.counts()
        provider_state = runtime.provider.status().get("state")
        registry_valid = bool(runtime.registry_health().get("valid"))
        try:
            module_states = [
                {"id": module["id"], "status_text": module["status_text"]}
                for module in runtime.modules()
            ]
        except Exception:  # noqa: BLE001
            module_states = []
    except Exception as exc:  # noqa: BLE001 - runtime พังก็ยังต้องตอบ JSON
        return {
            "sessions": sessions_envelope["sessions"],
            "session_count": sessions_envelope["count"],
            "session_source": sessions_envelope["source"],
            "session_error": sessions_envelope.get("error"),
            "queues": queue_envelope["queues"],
            "queue_total": queue_envelope["total"],
            "modules": {"total": 0, "enabled": 0, "connected": 0, "error": 0},
            "module_states": [],
            "provider_state": "unknown",
            "registry_valid": False,
            "error": f"runtime read failed: {exc}"[:200],
            "updated_at": _now_iso(),
        }
    return {
        "sessions": sessions_envelope["sessions"],
        "session_count": sessions_envelope["count"],
        "session_source": sessions_envelope["source"],
        "session_error": sessions_envelope.get("error"),
        "queues": queue_envelope["queues"],
        "queue_total": queue_envelope["total"],
        "modules": counts,
        "module_states": module_states,
        "provider_state": provider_state,
        "registry_valid": registry_valid,
        "error": None,
        "updated_at": _now_iso(),
    }
