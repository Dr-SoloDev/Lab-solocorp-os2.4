"""💰 Token / Quota Accounting — วัดว่า LLM call หนึ่งกินอะไรจริง

ทำไมต้องมี (incident 2026-10-25)
────────────────────────────────
โควตาฟรีของ workspace หมดกลางวันโดยไม่มีใครรู้ล่วงหน้า:
  · 297 requests สำเร็จ → แล้วทุก request หลังจากนั้นถูกปฏิเสธ 429
  · อีก 186 requests ถูกยิงเข้ากำแพงเปล่า ๆ (retry ทั้ง chain × 3 ครั้ง)
  · ไม่มีใครรู้ว่า "โควตาตายแล้ว" จน Owner ส่ง dashboard มาให้ดู
ต้นเหตุคือไม่มีตัววัดต่อ call และไม่มีความจำว่า "โควตาหมดแล้ว"

แหล่งข้อมูลจริง (ไม่ใช่การประมาณ)
────────────────────────────────
`opencode.db` → ตาราง `session_message` (type='assistant') มีคอลัมน์ data JSON:
    {"tokens":{"input":140,"output":471,"reasoning":814,
               "cache":{"read":60784,"write":0}}, "cost":0}
ตรวจกับ `request-logs-2026-10-25.json` (488 records จาก console gateway) แล้ว
ตรงกันทุกช่อง → ใช้ DB เป็นแหล่งความจริงได้ ไม่ต้อง parse stdout

⚠️ บทเรียนจากตัวเลขจริง: "15.2M tokens" ของ deepseek ใน dashboard คือ
   **cache_read** (15,431,680) ไม่ใช่ output (188,132)
   → cache read ถูกมาก ($0.006/M) อย่าตกใจตัวเลขนี้ ให้ดู output/cost

3 ชั้นป้องกัน
─────────────
1. `record()`          — ทุก call เขียน ledger JSONL → รู้ทีละ call ไม่ใช่รู้ทีหลัง
2. `check_budget()`    — เพดานรายวัน (requests / output / cost) → หยุดก่อนเผางบ
3. quota lock          — เจอ 429/402 → จำจนถึงเวลา reset → call ถัดไป fail fast
                          (ไม่ต้องเสียเวลาไล่ 5 โมเดล × 3 retry เข้ากำแพง)

หลักการ: accounting ต้อง **ไม่มีทางทำให้ LLM call พัง**
ทุกฟังก์ชันกลืน error ของตัวเอง คืนค่าที่ปลอดภัย (zeros) พร้อม `error` ให้ log
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

# ── Paths (override ได้ด้วย env เพื่อให้เทสต์ไม่แตะของจริง) ────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BUS_SYSTEM = _REPO_ROOT / "bus" / "system"

DB_PATH = Path(os.environ.get(
    "OPENCODE_DB",
    str(Path.home() / ".local" / "share" / "opencode" / "opencode.db"),
))
LEDGER_PATH = Path(os.environ.get(
    "SOLOCORP_TOKEN_LEDGER", str(_BUS_SYSTEM / "token-ledger.jsonl"),
))
QUOTA_PATH = Path(os.environ.get(
    "SOLOCORP_LLM_QUOTA", str(_BUS_SYSTEM / "llm_quota.json"),
))

# ── เพดานรายวัน (ค่าเริ่มต้นอิงของจริง 2026-10-25) ────────────────────
# requests: free tier ตายที่ ~297 สำเร็จ/วัน → 400 = กัน runaway loop
#           (ไม่ใช่กัน free limit — อันนั้น 429 lock จัดการ)
# cost:     $1/วัน — โมเดลฟรี = $0, ถ้า Owner เติมเงินนี่คือเบรกแรก
DEFAULT_LIMITS = {
    "requests": 400,
    "warn_requests": 200,
    "output_tokens": 2_000_000,
    "cost_usd": 1.0,
}

_NUM_FIELDS = ("requests", "input", "output", "reasoning", "cache_read", "cache_write")
_USAGE_KEYS = (*_NUM_FIELDS, "failed", "cost")


# ══════════════════════════════════════════════════════════════════════
# Usage containers
# ══════════════════════════════════════════════════════════════════════


def zero_usage(error: str = "") -> dict[str, Any]:
    """usage ว่าง — รูปเดียวกันตลอดเพื่อให้ sum/format ง่าย"""
    u: dict[str, Any] = {k: 0 for k in _NUM_FIELDS}
    u["failed"] = 0
    u["cost"] = 0.0
    u["error"] = error
    return u


def _add(target: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for k in _USAGE_KEYS:
        target[k] = target.get(k, 0) + (src.get(k) or 0)
    return target


def format_usage(u: dict[str, Any]) -> str:
    """สรุปบรรทัดเดียวสำหรับ log"""
    def k(n: float) -> str:
        n = float(n or 0)
        return f"{n/1000:.1f}k" if abs(n) >= 1000 else f"{int(n)}"

    return (
        f"req={u.get('requests', 0)} in={k(u.get('input', 0))} "
        f"out={k(u.get('output', 0))} reason={k(u.get('reasoning', 0))} "
        f"cache={k(u.get('cache_read', 0))} ${float(u.get('cost') or 0):.4f}"
    )


def new_session_id() -> str:
    """session id ที่เราสร้างเอง → ตามรอยได้ทั้งใน DB และ console request logs

    `opencode run --session <id>` สร้าง session ใหม่ถ้ายังไม่มี
    (ยืนยัน 2026-10-25: id ที่ส่งไปปรากฏใน session_v2.directory = repo)
    """
    return "ses_llm" + uuid.uuid4().hex[:20]


# ══════════════════════════════════════════════════════════════════════
# 1. อ่าน usage จริงจาก opencode.db
# ══════════════════════════════════════════════════════════════════════


def _connect_ro(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)


def _usage_from_message(data: dict[str, Any]) -> dict[str, Any]:
    """แปลง `session_message.data` (assistant) → usage dict

    แถวที่ไม่มี token เลย = request ที่ล้ม (429/402) → นับเป็น `failed` ไม่ใช่ `requests`
    """
    tokens = data.get("tokens") or {}
    if not isinstance(tokens, dict):
        return zero_usage()
    cache = tokens.get("cache") or {}
    if not isinstance(cache, dict):
        cache = {}

    got = {
        "input": int(tokens.get("input") or 0),
        "output": int(tokens.get("output") or 0),
        "reasoning": int(tokens.get("reasoning") or 0),
        "cache_read": int(cache.get("read") or 0),
        "cache_write": int(cache.get("write") or 0),
        "cost": float(data.get("cost") or 0),
    }
    if any(got[k] for k in ("input", "output", "cache_read", "cache_write")):
        got["requests"] = 1
    else:
        got["failed"] = 1
    return got


def read_session_usage(
    session_id: str,
    *,
    db_path: Optional[Path] = None,
    retries: int = 3,
    delay: float = 0.05,
) -> dict[str, Any]:
    """รวม token/cost ของทุก assistant message ใน session นี้

    Args:
        session_id: id ที่เราส่งให้ `opencode run --session`
        db_path: override (เทสต์ใช้ temp DB)
        retries: อ่านซ้ำกี่ครั้งถ้ายังไม่เจอแถว (DB อาจ flush ช้ากว่า process exit)
        delay: หน่วงระหว่างครั้ง (วินาที)

    Returns:
        dict: {"requests","input","output","reasoning","cache_read","cache_write",
               "failed","cost","error"} — ไม่ raise ทุกกรณี
    """
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return zero_usage(f"ไม่พบ opencode.db: {path}")

    last_err = ""
    for attempt in range(max(1, retries)):
        try:
            with _connect_ro(path) as conn:
                rows = conn.execute(
                    "SELECT data FROM session_message "
                    "WHERE session_id = ? AND type = 'assistant'",
                    (session_id,),
                ).fetchall()
        except sqlite3.Error as e:  # schema เปลี่ยน / ถูกล็อก / ไฟล์เสีย
            return zero_usage(f"sqlite: {e}")

        usage = zero_usage()
        for (raw,) in rows:
            try:
                data = json.loads(raw)
            except (TypeError, ValueError):
                continue
            _add(usage, _usage_from_message(data))

        if usage["requests"] or usage["failed"] or attempt == retries - 1:
            return usage
        last_err = "ยังไม่พบแถวของ session นี้ใน DB"
        time.sleep(delay)

    return zero_usage(last_err)


async def read_session_usage_async(session_id: str, **kw: Any) -> dict[str, Any]:
    """เวอร์ชันไม่บล็อก event loop (sqlite + retry sleep รันใน thread)"""
    import asyncio

    return await asyncio.to_thread(read_session_usage, session_id, **kw)


def read_db_usage(
    start_ms: int,
    end_ms: Optional[int] = None,
    *,
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """usage ของ **ทุก session** ในช่วงเวลา (รวม desktop/CLI ที่ไม่ได้ผ่าน llm_provider)

    ใช้ตอบคำถาม "วันนี้ทั้ง org กินเท่าไร" — ledger เก็บเฉพาะ call ที่เรายิง
    แต่ session ของ CEO/ผู้ช่วยก็กินโควตาเดียวกัน (2026-10-25: 188 requests
    มาจาก session เดียวที่ไม่ได้อยู่ใน ledger)

    Args:
        start_ms / end_ms: epoch ms (end = None → ถึงตอนนี้)
    """
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return zero_usage(f"ไม่พบ opencode.db: {path}")

    end = end_ms if end_ms is not None else int(time.time() * 1000)
    try:
        with _connect_ro(path) as conn:
            rows = conn.execute(
                "SELECT data FROM session_message "
                "WHERE type = 'assistant' AND time_created >= ? AND time_created <= ?",
                (int(start_ms), int(end)),
            ).fetchall()
    except sqlite3.Error as e:
        return zero_usage(f"sqlite: {e}")

    usage = zero_usage()
    for (raw,) in rows:
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            continue
        _add(usage, _usage_from_message(data))
    return usage


def read_db_usage_by_session(
    start_ms: int,
    end_ms: Optional[int] = None,
    *,
    limit: int = 10,
    db_path: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """เหมือน `read_db_usage` แต่แยกตาม session → ตอบว่า "ใครกินโควตา"

    Returns:
        list[dict]: [{"session_id","requests","input","output","reasoning",
                      "cache_read","cache_write","cost"}] เรียงจาก output มากไปน้อย
    """
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return []

    end = end_ms if end_ms is not None else int(time.time() * 1000)
    try:
        with _connect_ro(path) as conn:
            rows = conn.execute(
                "SELECT session_id, data FROM session_message "
                "WHERE type = 'assistant' AND time_created >= ? AND time_created <= ?",
                (int(start_ms), int(end)),
            ).fetchall()
    except sqlite3.Error:
        return []

    per: dict[str, dict[str, Any]] = {}
    for session_id, raw in rows:
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            continue
        bucket = per.setdefault(session_id, {"session_id": session_id, **zero_usage()})
        _add(bucket, _usage_from_message(data))

    ordered = sorted(per.values(), key=lambda u: u["output"], reverse=True)
    return ordered[:limit]


# ══════════════════════════════════════════════════════════════════════
# 2. Ledger — ทุก call เขียนบรรทัดของตัวเอง (append-only)
# ══════════════════════════════════════════════════════════════════════

def record(entry: dict[str, Any], *, path: Optional[Path] = None) -> bool:
    """ต่อท้าย ledger 1 บรรทัด (JSONL) — คืน False ถ้าเขียนไม่ได้ (ไม่ raise)

    entry ควรมี: ts, agent, session_id, model, ok, usage...
    เราเติม `ts` ให้ถ้าไม่มี (เวลา local + offset → today_totals เทียบง่าย)
    """
    p = Path(path) if path else LEDGER_PATH
    row = dict(entry)
    row.setdefault("ts", datetime.now().astimezone().isoformat(timespec="seconds"))
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return True
    except OSError as e:
        log.warning(f"token ledger เขียนไม่ได้ ({p}): {e}")
        return False


def today_totals(
    *, path: Optional[Path] = None, date: Optional[str] = None
) -> dict[str, Any]:
    """รวมยอดของวัน (local date, รูปแบบ YYYY-MM-DD)

    นับเฉพาะ entry ที่ `ok` ไม่ใช่ False — request ที่ล้มไม่ควรกินงบ
    (แต่ยังอยู่ใน ledger เพื่อการตรวจย้อนหลัง)
    """
    p = Path(path) if path else LEDGER_PATH
    day = date or datetime.now().astimezone().date().isoformat()
    totals = zero_usage()
    if not p.exists():
        return totals

    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        return zero_usage(f"อ่าน ledger ไม่ได้: {e}")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            totals["corrupt"] = totals.get("corrupt", 0) + 1
            continue  # บรรทัดเสีย (เขียนค้าง) — ข้าม ไม่ล้มทั้งรายงาน
        ts = str(e.get("ts", ""))
        if not ts:
            # ไม่มีเวลา = ใส่เข้า day ไหนไม่ได้ (ไม่งั้นจะถูกนับซ้ำทุกวัน) → รายงานแยก
            totals["undated"] = totals.get("undated", 0) + 1
            continue
        if ts[:10] != day:
            continue
        if e.get("ok") is False:
            continue
        _add(totals, e)
    return totals


def today_attempts(
    *, path: Optional[Path] = None, date: Optional[str] = None
) -> dict[str, int]:
    """นับจำนวนครั้งที่ **พยายาม** ยิง (รวมที่ล้ม) — ต่างจาก today_totals ที่นับแค่สำเร็จ

    ใช้ดูว่าเรายิงเข้ากำแพงกี่ครั้ง (2026-10-25: 186 ครั้ง)
    """
    p = Path(path) if path else LEDGER_PATH
    day = date or datetime.now().astimezone().date().isoformat()
    counts = {"ok": 0, "failed": 0, "corrupt": 0}
    if not p.exists():
        return counts
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return counts
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            counts["corrupt"] += 1
            continue
        ts = str(e.get("ts", ""))
        if not ts or ts[:10] != day:
            continue
        counts["failed" if e.get("ok") is False else "ok"] += 1
    return counts


# ══════════════════════════════════════════════════════════════════════
# 3. Budget — หยุดก่อนเผา ไม่ใช่รู้ทีหลัง
# ══════════════════════════════════════════════════════════════════════


def budget_limits() -> dict[str, Any]:
    """เพดานรายวันจาก env (มี default ที่อิงข้อมูลจริง)"""
    def num(key: str, default, cast=float):
        raw = os.environ.get(key)
        if raw is None or raw == "":
            return default
        try:
            return cast(raw)
        except ValueError:
            return default

    return {
        "requests": num("SOLOCORP_LLM_DAILY_REQUESTS", DEFAULT_LIMITS["requests"], int),
        "warn_requests": num(
            "SOLOCORP_LLM_WARN_REQUESTS", DEFAULT_LIMITS["warn_requests"], int
        ),
        "output_tokens": num(
            "SOLOCORP_LLM_DAILY_OUTPUT_TOKENS", DEFAULT_LIMITS["output_tokens"], int
        ),
        "cost_usd": num("SOLOCORP_LLM_DAILY_COST_USD", DEFAULT_LIMITS["cost_usd"], float),
    }


def check_budget(
    totals: Optional[dict[str, Any]] = None,
    limits: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """เทียบยอดวันนี้กับเพดาน

    Returns:
        dict: {"ok": bool, "warn": bool, "reason": str, "totals": {...}, "limits": {...}}
        ok=False → caller ต้องไม่ยิง LLM
    """
    t = totals if totals is not None else today_totals()
    lim = limits if limits is not None else budget_limits()

    reasons: list[str] = []
    if t.get("requests", 0) >= lim["requests"]:
        reasons.append(f"requests {t['requests']}/{lim['requests']}")
    if t.get("output", 0) >= lim["output_tokens"]:
        reasons.append(f"output {t['output']}/{lim['output_tokens']} tokens")
    if float(t.get("cost") or 0) >= lim["cost_usd"]:
        reasons.append(f"cost ${float(t['cost']):.4f}/${lim['cost_usd']:.2f}")

    warn = (
        t.get("requests", 0) >= lim["warn_requests"]
        or float(t.get("cost") or 0) >= lim["cost_usd"] * 0.8
    )
    return {
        "ok": not reasons,
        "warn": warn and not reasons,
        "reason": "; ".join(reasons),
        "totals": t,
        "limits": lim,
    }


# ══════════════════════════════════════════════════════════════════════
# 4. Quota lock — จำว่า "โควตาตายแล้ว" จนถึงเวลา reset
# ══════════════════════════════════════════════════════════════════════


def quota_status(
    *, path: Optional[Path] = None, now_ms: Optional[int] = None
) -> dict[str, Any]:
    """สถานะการล็อกโควตา (หมดอายุเองเมื่อเลยเวลา — ไม่ต้องมีใครมาปลด)"""
    p = Path(path) if path else QUOTA_PATH
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    empty = {
        "locked": False, "until_ms": 0, "until": "", "remaining_s": 0,
        "reason": "", "model": "",
    }
    if not p.exists():
        return empty

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        until = int(data.get("locked_until_ms") or 0)
    except (OSError, ValueError, TypeError):
        return empty

    if until <= now:
        return empty

    return {
        "locked": True,
        "until_ms": until,
        "until": datetime.fromtimestamp(until / 1000).astimezone().isoformat(
            timespec="seconds"
        ),
        "remaining_s": int((until - now) / 1000),
        "reason": str(data.get("reason") or "quota"),
        "model": str(data.get("model") or ""),
    }


def lock_quota(
    until_ms: int,
    reason: str = "quota",
    *,
    model: str = "",
    path: Optional[Path] = None,
) -> bool:
    """จำการล็อกไว้ (เขียนทับของเดิมถ้ามี) — คืน False ถ้าเขียนไม่ได้"""
    p = Path(path) if path else QUOTA_PATH
    payload = {
        "locked_until_ms": int(until_ms),
        "reason": reason,
        "model": model,
        "set_at_ms": int(time.time() * 1000),
        "set_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError as e:
        log.warning(f"เขียน quota lock ไม่ได้ ({p}): {e}")
        return False


def clear_quota(*, path: Optional[Path] = None) -> bool:
    """ปลดล็อกด้วยมือ (เช่น Owner เติมเงินแล้ว)"""
    p = Path(path) if path else QUOTA_PATH
    try:
        p.unlink(missing_ok=True)
        return True
    except OSError as e:
        log.warning(f"ลบ quota lock ไม่ได้ ({p}): {e}")
        return False


# ══════════════════════════════════════════════════════════════════════
# 5. แกะ error จาก opencode → รู้ว่าต้องรออีกนานแค่ไหน
# ══════════════════════════════════════════════════════════════════════

_RETRY_AFTER_MS_RE = re.compile(r'"retryAfterMs"\s*:\s*(\d+)')
_RETRY_AFTER_S_RE = re.compile(r"retry[- ]after[\"'\s:]+(\d+)", re.IGNORECASE)

# ข้อความที่แปลว่า "ไม่ใช่ปัญหาของโมเดลตัวนี้ — ทั้ง workspace ตัน"
_QUOTA_MARKERS = (
    "freeusagelimiterror",
    "free usage limit",
    "free-tier",
    "free tier",
    "insufficient account funds",
    "insufficient_quota",
    "quota exceeded",
)


def is_quota_error(text: str) -> bool:
    """error นี้คือ 'โควตา/เงินตัน' (ไม่ใช่โมเดลตาย) → หยุดทั้ง chain"""
    low = str(text).lower()
    return any(m in low for m in _QUOTA_MARKERS)


def is_funds_error(text: str) -> bool:
    """กระเป๋าเงินว่าง (402) — retry ไม่ช่วยจนกว่า Owner เติมเงิน"""
    low = str(text).lower()
    return "insufficient account funds" in low or "402" in low


def parse_retry_after_ms(text: str) -> Optional[int]:
    """ดึงเวลารอจาก error — รองรับ `"retryAfterMs":63736000` และ `Retry-After: 3600`

    Returns:
        int | None: มิลลิวินาทีที่ต้องรอ (None = ไม่รู้)
    """
    s = str(text)
    m = _RETRY_AFTER_MS_RE.search(s)
    if m:
        return int(m.group(1))
    m = _RETRY_AFTER_S_RE.search(s)
    if m:
        return int(m.group(1)) * 1000
    return None


def lock_from_error(text: str, *, model: str = "", default_s: int = 0) -> dict[str, Any]:
    """แปลง error → quota lock (ถ้าเข้าเงื่อนไข) แล้วคืนสถานะที่บันทึก

    default_s: ใช้เมื่อ error ไม่บอกเวลา — 0 = อ่านจาก env
      SOLOCORP_LLM_LOCK_DEFAULT_S (default 3600 = 1 ชม.)
      เหตุผล: error แบบ plain text ของ `opencode run` **ไม่มี** retryAfterMs
      (มีเฉพาะตอน `--format json`) → ต้องมีค่าสมมติฐานที่ปลอดภัย
    """
    wait_ms = parse_retry_after_ms(text)
    if wait_ms is None:
        if not default_s:
            try:
                default_s = int(os.environ.get("SOLOCORP_LLM_LOCK_DEFAULT_S", "3600"))
            except ValueError:
                default_s = 3600
        wait_ms = default_s * 1000
    until = int(time.time() * 1000) + int(wait_ms)
    reason = "funds" if is_funds_error(text) else "free-limit"
    lock_quota(until, reason, model=model)
    return quota_status()
