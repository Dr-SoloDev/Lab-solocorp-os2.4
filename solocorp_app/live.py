"""Live dashboard data sources (PR2.1 hardening).

Owner อยากเห็นทุกห้องแบบสดโดยไม่ต้องพิมพ์ ``opencode session list`` เอง
ไฟล์นี้รวมแหล่งข้อมูล 3 อย่างไว้ที่เดียว — sessions, queue depth, สถานะรวม:

* :func:`list_sessions` — CLI อย่างเดียว
  (``opencode session list --format json``) ถ้า CLI ใช้ไม่ได้คืน ``[]``
  พร้อม ``error`` — หน้า /live ต้อง render ได้เสมอ ห้าม 500 (PRD §9)
  PR2.1: sessions cache TTL 15s + single-flight — poll 3s ไม่ spawn CLI
  ทุก poll (D1/D2)
* :func:`queue_depths` — นับบรรทัด JSONL ใน ``bus/queue/`` แบบ fail-open
  PR2.1: queue cache TTL 5s + cap 50k lines / 8MB ต่อไฟล์ +
  ข้าม ``*.offset`` + ``archive/`` (D5)
* :func:`live_status` — รวม sessions + queue + tasks_summary + modules +
  provider เป็นก้อนเดียวให้ ``GET /api/live/status`` และหน้า ``/live``
  ใช้ร่วมกัน (D4)

Fail-open ทุกฟังก์ชัน: ไม่มี exception หลุดออกไปเด็ดขาด
ห้าม import content_service / Concat / DB ใด ๆ เข้าไฟล์นี้ (R2/R3)
"""

from __future__ import annotations

import json
import os
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

SESSION_LIMIT = 30
# D2: สั้นกว่า poll 3s เสมอ — กัน request ซ้อนกัน
CLI_TIMEOUT_S = 1.5

# D1: in-process TTL cache แยก sessions / queue
TTL_SESSIONS_S = 15.0
TTL_QUEUE_S = 5.0
_CACHE: dict[str, dict[str, Any]] = {
    "sessions": {"value": None, "expires_at": 0.0},
    "queue": {"value": None, "expires_at": 0.0},
}
_CACHE_LOCK = threading.Lock()

# D2: single-flight — กัน spawn CLI ซ้อนเมื่อ poll ตรงกัน
_CLI_LOCK = threading.Lock()

# D5: กันไฟล์บวมค้าง poll
MAX_LINES_PER_FILE = 50_000
MAX_BYTES_PER_FILE = 8_000_000


def clear_live_cache() -> None:
    """ล้าง live cache ทั้ง sessions + queue — ใช้ใน test เท่านั้น."""

    with _CACHE_LOCK:
        _CACHE["sessions"] = {"value": None, "expires_at": 0.0}
        _CACHE["queue"] = {"value": None, "expires_at": 0.0}


def clear_sessions_cache() -> None:
    """ล้าง sessions cache — ใช้ใน test เท่านั้น (คงชื่อเดิมไว้ compat)."""

    with _CACHE_LOCK:
        _CACHE["sessions"] = {"value": None, "expires_at": 0.0}


def clear_queue_cache() -> None:
    """ล้าง queue cache — ใช้ใน test เท่านั้น."""

    with _CACHE_LOCK:
        _CACHE["queue"] = {"value": None, "expires_at": 0.0}


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
        # epoch ms อยู่แถว 1e12, epoch s อยู่แถว 1e9
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
    """บีบ session 1 แถว (จาก CLI — shape ไม่แน่นอน) ให้เป็น envelope เดียว.

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
    ใช้ไม่ได้ — caller เป็นคนตัดสินใจ fail-open ต่อ.
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


def list_sessions(
    limit: int = SESSION_LIMIT,
    *,
    queue_cli: list[str] | None = None,
    command: list[str] | None = None,
) -> dict[str, Any]:
    """คืน envelope ``{sessions, count, source, error, updated_at, cache_hit}``.

    CLI อย่างเดียว (D3 — ไม่มี DB fallback) → fail-open ``source=none``.
    Production path (ไม่ส่ง override) อ่านจาก cache 15s + single-flight:
    ถ้ามี CLI รันอยู่คืน stale cache ทันที ไม่ spawn ซ้อน (D1/D2).
    Test path ที่ส่ง ``queue_cli`` / ``command`` มาชัดเจน bypass cache เสมอ.
    """

    override = queue_cli or command
    use_cache = override is None
    now = time.monotonic()
    if use_cache:
        with _CACHE_LOCK:
            entry = _CACHE["sessions"]
            if entry["value"] is not None and now < entry["expires_at"]:
                envelope = dict(entry["value"])
                envelope["cache_hit"] = True
                return envelope
    # D2 single-flight: non-blocking — มี CLI รันอยู่คืน stale ทันที
    if use_cache and not _CLI_LOCK.acquire(blocking=False):
        with _CACHE_LOCK:
            entry = _CACHE["sessions"]
            if entry["value"] is not None:
                envelope = dict(entry["value"])
                envelope["cache_hit"] = True
                return envelope
        return {
            "sessions": [],
            "count": 0,
            "source": "none",
            "error": "session lookup busy — retry next poll",
            "updated_at": _now_iso(),
            "cache_hit": False,
        }
    try:
        sessions, cli_error = _sessions_from_cli(limit, command=override)
        if sessions is not None:
            envelope = {
                "sessions": sessions,
                "count": len(sessions),
                "source": "cli",
                "error": None,
                "updated_at": _now_iso(),
                "cache_hit": False,
            }
            if use_cache:
                with _CACHE_LOCK:
                    _CACHE["sessions"] = {
                        "value": dict(envelope),
                        "expires_at": time.monotonic() + TTL_SESSIONS_S,
                    }
            return envelope
        envelope = {
            "sessions": [],
            "count": 0,
            "source": "none",
            "error": cli_error or "no session source available",
            "updated_at": _now_iso(),
            "cache_hit": False,
        }
        # อย่า cache path ที่ล้ม — poll รอบหน้าจะได้ลอง CLI ใหม่ทันที
        return envelope
    except Exception as exc:  # noqa: BLE001 - dashboard ต้อง render ได้เสมอ
        return {
            "sessions": [],
            "count": 0,
            "source": "none",
            "error": f"{type(exc).__name__}: {exc}"[:200],
            "updated_at": _now_iso(),
            "cache_hit": False,
        }
    finally:
        if use_cache and _CLI_LOCK.locked():
            try:
                _CLI_LOCK.release()
            except RuntimeError:
                pass


def _count_jsonl_file(path: Path) -> tuple[int, bool]:
    """นับบรรทัด non-empty ในไฟล์เดียวแบบมี cap กันบวม (D5).

    คืน ``(count, truncated)`` — truncated=True เมื่อหยุดก่อน EOF เพราะ
    เกิน cap (50k บรรทัด / 8MB) Product v1.0 §2.5.
    """

    total = 0
    seen_bytes = 0
    truncated = False
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                seen_bytes += len(line.encode("utf-8", errors="ignore"))
                if seen_bytes > MAX_BYTES_PER_FILE:
                    truncated = True
                    break
                if line.strip():
                    total += 1
                if total >= MAX_LINES_PER_FILE:
                    # อาจยังมีบรรทัดเหลือ — เช็คว่าถึง EOF จริงไหม
                    rest = handle.read(1)
                    if rest:
                        truncated = True
                    break
    except OSError:
        return 0, False
    return total, truncated


def queue_depths(*, queue_dir: Path | None = None) -> dict[str, Any]:
    """นับบรรทัด JSONL ต่อ priority — ไฟล์หาย = 0, อ่านไม่ได้ = fail-open.

    PR2.1 Product v1.0 §2.2 (แทน CHECKLIST "bus-queue"):
    ``queue_source`` คือป้ายฝั่ง queue คู่กับ ``session_source`` ฝั่ง session::

        files       — อ่านไฟล์จริง มีข้อมูล (total > 0)
        empty       — dir ว่าง/ไม่มีไฟล์/ทุกไฟล์ 0 บรรทัด (total == 0)
        truncated   — ไฟล์เกิน cap แล้วหยุดอ่าน (50k บรรทัด / 8MB)
        unavailable — อ่านไม่ได้เลย (exception ฝั่ง queue)

    ``queue_error`` (≤200 ตัวอักษร) คือเหตุผลฝั่ง queue เท่านั้น —
    คนละตัวกับ ``session_error`` และ ``error`` (runtime read fail).
    ข้าม ``*.offset`` + ``archive/`` เด็ดขาด (ห้าม ``rglob``),
    อ่านแค่ 6 ชื่อตายตัวใน :data:`QUEUE_FILES` + cap กันไฟล์บวม (D5).
    Production path มี cache 5s (D1); test path ที่ส่ง ``queue_dir`` มา
    bypass cache เสมอเพื่อ determinism.
    """

    use_cache = queue_dir is None
    now = time.monotonic()
    if use_cache:
        with _CACHE_LOCK:
            entry = _CACHE["queue"]
            if entry["value"] is not None and now < entry["expires_at"]:
                envelope = dict(entry["value"])
                envelope["cache_hit"] = True
                return envelope
    base = Path(queue_dir) if queue_dir else DEFAULT_QUEUE_DIR
    queues: dict[str, int] = {}
    truncated_any = False
    try:
        for logical, files in QUEUE_FILES.items():
            total = 0
            for name in files:
                # D5: ห้ามแตะ offset / archive — กันเดินผิดทางไปกวาด render หลาย GB (R2)
                if name.endswith(".offset") or name.startswith("archive"):
                    continue
                path = base / name
                if not path.exists() or not path.is_file():
                    continue
                try:
                    if path.stat().st_size > MAX_BYTES_PER_FILE * 2:
                        # ไฟล์ใหญ่ผิดปกติ — นับแบบ cap (ไม่ skip ทิ้ง)
                        pass
                except OSError:
                    continue
                count, was_truncated = _count_jsonl_file(path)
                total += count
                truncated_any = truncated_any or was_truncated
            queues[logical] = total
        queues.setdefault("dead", queues.pop("dead", 0))
        total = sum(queues.values())
        if truncated_any:
            queue_source = "truncated"
            queue_error: str | None = "queue cap exceeded (50k lines / 8MB)"
        elif total == 0:
            queue_source = "empty"
            queue_error = None
        else:
            queue_source = "files"
            queue_error = None
        envelope = {
            "queues": queues,
            "total": total,
            "queue_source": queue_source,
            "queue_error": queue_error,
            "updated_at": _now_iso(),
            "cache_hit": False,
        }
        if use_cache:
            with _CACHE_LOCK:
                _CACHE["queue"] = {
                    "value": dict(envelope),
                    "expires_at": time.monotonic() + TTL_QUEUE_S,
                }
        return envelope
    except Exception as exc:  # noqa: BLE001 - dashboard ต้อง render ได้เสมอ
        return {
            "queues": {key: 0 for key in QUEUE_FILES},
            "total": 0,
            "queue_source": "unavailable",
            "queue_error": f"{type(exc).__name__}: {exc}"[:200],
            "updated_at": _now_iso(),
            "cache_hit": False,
        }


def _tasks_summary(runtime: Any, *, cap: int = 200) -> dict[str, Any]:
    """นับ TaskTracker แบบ cap กันช้า — Product v1.0 §2.2 contract (D4).

    Shape ล็อก:: ``{"total": int, "by_status": {status: count}, "updated_at": iso}``
    Single source of truth = ``runtime.tasks()`` / ``runtime.tasks_summary()``
    (TaskTracker) เท่านั้น — ห้ามนับจาก ``bus/queue/*.jsonl``.
    fail-open เสมอ — tasks พังต้องไม่พา /live ล้ม.
    """

    try:
        if hasattr(runtime, "tasks_summary"):
            summary = runtime.tasks_summary(cap=cap)
            if isinstance(summary, dict) and "total" in summary:
                by_status = summary.get("by_status")
                if not isinstance(by_status, dict):
                    by_status = {}
                updated_at = summary.get("updated_at") or _now_iso()
                return {
                    "total": int(summary.get("total", 0)),
                    "by_status": {
                        str(key): int(value) for key, value in by_status.items()
                    },
                    "updated_at": str(updated_at),
                }
        tasks = runtime.tasks()
        if not isinstance(tasks, list):
            raise TypeError("tasks() did not return a list")
        by_status: dict[str, int] = {}
        for record in tasks[:cap]:
            status = record.get("status") if isinstance(record, dict) else None
            key = str(status) if status else "pending"
            by_status[key] = by_status.get(key, 0) + 1
        return {
            "total": len(tasks),
            "by_status": by_status,
            "updated_at": _now_iso(),
        }
    except Exception:  # noqa: BLE001 - tasks พังต้องไม่พา /live ล้ม
        return {"total": 0, "by_status": {}, "updated_at": _now_iso()}


def _degraded(
    *,
    session_source: str | None,
    queue_source: str | None,
    error: str | None,
    provider_state: str | None,
    registry_valid: bool,
) -> bool:
    """สูตร ``degraded`` ล็อก Product v1.0 §2.3 — ห้ามตีความหน้างาน.

    ``True`` เมื่อข้อใดข้อหนึ่งเป็นจริง: session none / queue
    truncated|unavailable / runtime error / provider unknown|failed /
    registry ไม่ valid — นอกนั้น ``False``. UI ใช้ฟิลด์นี้ฟิลด์เดียว
    ตัดสินป้ายเหลือง/แดง.
    """

    return (
        session_source == "none"
        or queue_source in ("truncated", "unavailable")
        or error is not None
        or provider_state in ("unknown", "failed")
        or not registry_valid
    )


def live_status(
    runtime: Any,
    *,
    session_limit: int = SESSION_LIMIT,
    queue_dir: Path | None = None,
) -> dict[str, Any]:
    """รวมทุกอย่างที่หน้า /live ต้อง polling — ไม่ raise เด็ดขาด.

    Contract Product v1.0 §2.2: ``sessions/session_count/session_source/
    session_error/queues/queue_total/queue_source/queue_error/cache_hit/
    degraded/tasks_summary/error/updated_at`` (+ modules/provider เดิม).
    ``tasks_summary`` มาจาก TaskTracker เท่านั้น — ห้ามนับจาก queue.
    """

    try:
        sessions_envelope = list_sessions(session_limit)
    except Exception as exc:  # noqa: BLE001
        sessions_envelope = {
            "sessions": [],
            "count": 0,
            "source": "none",
            "error": f"{type(exc).__name__}: {exc}"[:200],
            "updated_at": _now_iso(),
            "cache_hit": False,
        }
    # test path: ส่ง queue_dir มาให้ queue_depths โดยตรงเพื่อ determinism
    try:
        queue_envelope = queue_depths(queue_dir=queue_dir)
    except Exception as exc:  # noqa: BLE001
        queue_envelope = {
            "queues": {key: 0 for key in QUEUE_FILES},
            "total": 0,
            "queue_source": "unavailable",
            "queue_error": f"{type(exc).__name__}: {exc}"[:200],
            "updated_at": _now_iso(),
            "cache_hit": False,
        }
    queue_source = str(queue_envelope.get("queue_source") or "unavailable")
    if queue_source not in ("files", "empty", "truncated", "unavailable"):
        queue_source = "unavailable"
    queue_error = queue_envelope.get("queue_error", queue_envelope.get("error"))
    if queue_error is not None:
        queue_error = str(queue_error)[:200]
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
        tasks_summary = _tasks_summary(runtime)
    except Exception as exc:  # noqa: BLE001 - runtime พังก็ยังต้องตอบ JSON
        error: str | None = f"runtime read failed: {exc}"[:200]
        return {
            "sessions": sessions_envelope["sessions"],
            "session_count": sessions_envelope["count"],
            "session_source": sessions_envelope["source"],
            "session_error": sessions_envelope.get("error"),
            "queues": queue_envelope["queues"],
            "queue_total": queue_envelope["total"],
            "queue_source": queue_source,
            "queue_error": queue_error,
            "tasks_summary": {
                "total": 0,
                "by_status": {},
                "updated_at": _now_iso(),
            },
            "modules": {"total": 0, "enabled": 0, "connected": 0, "error": 0},
            "module_states": [],
            "provider_state": "unknown",
            "registry_valid": False,
            "cache_hit": bool(
                sessions_envelope.get("cache_hit") or queue_envelope.get("cache_hit")
            ),
            "degraded": True,
            "error": error,
            "updated_at": _now_iso(),
        }
    cache_hit = bool(
        sessions_envelope.get("cache_hit") or queue_envelope.get("cache_hit")
    )
    return {
        "sessions": sessions_envelope["sessions"],
        "session_count": sessions_envelope["count"],
        "session_source": sessions_envelope["source"],
        "session_error": sessions_envelope.get("error"),
        "queues": queue_envelope["queues"],
        "queue_total": queue_envelope["total"],
        "queue_source": queue_source,
        "queue_error": queue_error,
        "tasks_summary": tasks_summary,
        "modules": counts,
        "module_states": module_states,
        "provider_state": provider_state,
        "registry_valid": registry_valid,
        "cache_hit": cache_hit,
        "degraded": _degraded(
            session_source=sessions_envelope["source"],
            queue_source=queue_source,
            error=None,
            provider_state=provider_state,
            registry_valid=registry_valid,
        ),
        "error": None,
        "updated_at": _now_iso(),
    }
