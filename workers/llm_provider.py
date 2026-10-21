"""🤖 SoloCorp OS — LLM Provider

เชื่อมต่อ Agent กับ LLM (OpenCode ผ่าน opencode run CLI)

ใช้ opencode run CLI โดยตรง — stable, official, tested.
- ส่ง prompt ผ่าน stdin ป้องกัน shell injection
- --pure ลด overhead plugins
- --agent <judgment agent> กันโมเดลพยายามใช้เครื่องมือ (permission auto-reject → stdout ว่าง)
- retry + timeout + semaphore concurrency control
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────

# Fallback chain (2026-10-20 — ทดสอบจาก repo root จริงทุกตัว):
# 1. Minimax M3.1 Flash Free   — ตัวหลัก (~12s)
# 2. DeepSeek V4.1 Flash Free  — สำรอง 1
# 3. Nemotron 3.5 Lightning    — สำรอง 2
# 4. Longcat 2.5 Preview Free  — สำรอง 3 (~46s ช้า)
# 5. Mimo 2.6 Flash Free       — สำรอง 4
#
# ⚠️ โมเดลที่ถูกลบออก (ไม่มีใน opencode models แล้ว → "Model not found"):
#    muse-spark-1.3-contributor-free, space-bunny-free
# ⚠️ โมเดลที่มีอยู่แต่ใช้ไม่ได้จาก repo root:
#    beam-free (gateway ปฏิเสธ agents_md), glm-5.3-flash-free (unknown_parameter)
DEFAULT_MODEL = "opencode/minimax-m3.1-flash-free"
# ยืนยันแล้วว่าใช้ได้จริงจาก repo root (2026-10-20) — ทดสอบทีละตัว
# ดูวิธีทดสอบ: python scripts/check-model-health.py --verify <model>
MODEL_FALLBACKS = [
    "opencode/minimax-m3.1-flash-free",        # ~12s · เร็วสุดในชุดที่ใช้ได้
    "opencode/deepseek-v4.1-flash-free",
    "opencode/nemotron-3.5-lightning-free",
    "opencode/nemotron-3-ultra-free",          # + เพิ่ม 2026-10-20
    "opencode/big-pickle",                     # + เพิ่ม 2026-10-20
    "opencode/longcat-2.5-preview-free",       # ~46s · ช้า
    "opencode/mimo-v2.6-flash-free",
]
# Dead models — ถ้ามี caller ส่งชื่อเก่ามา ให้ map เข้า fallback chain ทันที
DEAD_MODELS = {
    # ยังไม่มีใน opencode models (Model not found)
    "opencode/x-preview-f-free",
    "opencode/muse-spark-1.3-contributor-free",
    "opencode/space-bunny-free",
    "opencode/deepseek-v4-flash-free",
    "stealth/ox-alpha",
    # มีอยู่แต่ gateway free-tier ปฏิเสธ agents_md / unknown_parameter
    "opencode/beam-free",
    "opencode/glm-5.3-flash-free",
}

# ── Model health check (กันโมเดลตายเงียบ) ────────────────────────────
# โมเดลฟรีของ opencode ถูกเปลี่ยนชื่อ/ลบไปเรื่อย ๆ → chain นี้จะตาย
# โดยไม่มี error ชัดเจน (ทุกโมเดลคืน "empty response")
# → ต้องตรวจชื่อเป็นระยะ แล้วเตือนก่อนที่ agent ทั้ง 19 ตัวจะ "ตาบอด"

_MODEL_CACHE_PATH = Path(
    os.environ.get(
        "SOLOCORP_MODEL_HEALTH_CACHE",
        str(Path(__file__).parent.parent / "bus" / "system" / "model_health.json"),
    )
)
_MODEL_CACHE_TTL_HOURS = 6
_MODELS_TIMEOUT = 30


def list_available_models(prefix: str = "opencode/") -> list[str]:
    """รายชื่อโมเดลที่ opencode มีจริง ณ ตอนนี้ (เรียก CLI)

    Returns:
        list[str]: เช่น ["opencode/minimax-m3.1-flash-free", ...]
        คืน [] ถ้าเรียกไม่ได้ (ไม่มี opencode / timeout)
    """
    import subprocess

    try:
        r = subprocess.run(
            [_CMD, "models"], capture_output=True, text=True,
            timeout=_MODELS_TIMEOUT,
        )
    except Exception:
        return []

    out = []
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if line.startswith(prefix):
            out.append(line)
    return out


def _read_model_cache() -> dict:
    try:
        if not _MODEL_CACHE_PATH.exists():
            return {}
        data = json.loads(_MODEL_CACHE_PATH.read_text(encoding="utf-8"))
        checked = data.get("checked_at")
        if not checked:
            return {}
        age_h = (datetime.now(timezone.utc)
                 - datetime.fromisoformat(checked)).total_seconds() / 3600
        if age_h > _MODEL_CACHE_TTL_HOURS:
            return {}
        return data
    except Exception:
        return {}


def _write_model_cache(models: list[str]) -> None:
    try:
        _MODEL_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _MODEL_CACHE_PATH.write_text(json.dumps({
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "available": models,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def audit_models(use_cache: bool = True) -> dict:
    """เทียบ MODEL_FALLBACKS กับโมเดลที่มีจริง → รายงานสุขภาพ chain

    Returns:
        dict: {
            ok: bool,             # ไม่มีโมเดลใน chain หาย
            chain: [...],         # chain ปัจจุบัน
            available: [...],     # โมเดล opencode/ ที่มีจริง (ทั้งหมด)
            missing: [...],       # ใน chain แต่ไม่มีจริง  ← ต้องแก้
            usable: [...],        # ใน chain ที่มีจริง
            candidates: [...],    # มีจริงแต่ยังไม่อยู่ใน chain (ข้อเสนอ)
            checked_at: str,
            stale: bool,          # ใช้ข้อมูล cache
            error: str | None,
        }
    """
    cached = _read_model_cache() if use_cache else {}
    if cached.get("available"):
        available = list(cached["available"])
        stale = True
        checked_at = cached.get("checked_at", "")
    else:
        available = list_available_models()
        stale = False
        checked_at = datetime.now(timezone.utc).isoformat()
        if available:
            _write_model_cache(available)

    chain = list(MODEL_FALLBACKS)
    if not available:
        return {
            "ok": True, "chain": chain, "available": [], "missing": [],
            "usable": chain, "candidates": [], "checked_at": checked_at,
            "stale": stale, "error": "อ่านรายชื่อโมเดลไม่ได้ (ข้ามการตรวจ)",
        }

    avail_set = set(available)
    missing = [m for m in chain if m not in avail_set]
    usable = [m for m in chain if m in avail_set]
    candidates = [m for m in available if m not in chain]

    return {
        "ok": not missing,
        "chain": chain,
        "available": available,
        "missing": missing,
        "usable": usable,
        "candidates": candidates,
        "checked_at": checked_at,
        "stale": stale,
        "error": None,
    }
_CMD = os.environ.get("OPENCODE_BIN", os.path.expanduser("~/.opencode/bin/opencode"))
_MAX_CONCURRENT = 3
_LLM_TIMEOUT = 60
_MAX_RETRIES = 3
_CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# จะได้ reuse context ทุกครั้ง (ไม่ต้อง search path ใหม่)
_CMD_WITH_FLAGS = [_CMD, "run", "--pure"]

# Concurrency control
_semaphore = asyncio.Semaphore(_MAX_CONCURRENT)


# ── Judgment agent (LLM ต้อง "ตอบ" ไม่ใช่ "ลงมือทำ") ───────────────────
# Defect (2026-10-21): `opencode run` ที่รันใน repo จะโหลด agent config ของโปรเจกต์
# → persona หลัก (ceo-turbo) → โมเดลพยายามใช้เครื่องมือ (bash/git/read)
# → permission ถูก auto-reject → run จบ exit 0 แต่ stdout ว่าง
# → provider เห็น "ค่าว่าง" → เปลี่ยนโมเดลไปตัวถัดไปจนหมด → "⚠️ LLM ไม่พร้อม"
# Fix: เรียกด้วย `--agent llm-judge` (agent ที่ปิดสิทธิ์เครื่องมือทั้งหมด)
# Fallback: agent ไม่มี/ไม่รู้จัก → retry โดยไม่ใส่ --agent (ไม่ให้ระบบล้มทั้งหมด)

_LLM_AGENT_ENV = "SOLOCORP_LLM_AGENT"
_DEFAULT_LLM_AGENT = "llm-judge"
# agent ต้องอ่านได้จาก .opencode/agents/ ของ repo (cwd = repo root) หรือ global config
_AGENT_SEARCH_DIRS = (
    Path(_CWD) / ".opencode" / "agents",
    Path(_CWD) / ".opencode" / "agent",
    Path(os.path.expanduser("~")) / ".config" / "opencode" / "agent",
    Path(os.path.expanduser("~")) / ".config" / "opencode" / "agents",
)
# คำที่บ่งบอกว่า error เกี่ยวกับ agent (ไม่มี / ไม่รู้จัก / flag ผิด)
_AGENT_FAIL_WORDS = (
    "not found", "unknown", "invalid", "no such", "does not exist",
    "not exist", "missing", "unrecognized", "no agent",
)


def _agent_name() -> str:
    """ชื่อ judgment agent — override ได้ด้วย env SOLOCORP_LLM_AGENT"""
    return (os.environ.get(_LLM_AGENT_ENV) or "").strip() or _DEFAULT_LLM_AGENT


def _agent_available(name: str) -> bool:
    """agent ต้องมีไฟล์จริง ถึงจะส่ง --agent ไปได้"""
    return any((d / f"{name}.md").is_file() for d in _AGENT_SEARCH_DIRS)


def _resolve_agent() -> Optional[str]:
    """คืนชื่อ agent ที่ใช้ได้จริง — None = เรียกโดยไม่ใส่ --agent"""
    name = _agent_name()
    if not _agent_available(name):
        log.warning(
            f"LLM agent '{name}' ไม่พบใน .opencode/agents/ "
            f"→ เรียก opencode โดยไม่ใส่ --agent"
        )
        return None
    return name


def _looks_like_agent_error(message: str) -> bool:
    """error เกี่ยวกับ agent? (ไม่มี / ไม่รู้จัก / flag ผิด) → ต้อง retry โดยไม่ใส่ --agent"""
    low = (message or "").lower()
    if "model not found" in low:
        return False  # เป็นเรื่องโมเดล ไม่ใช่เรื่อง agent
    if "agent" not in low:
        return False
    return any(word in low for word in _AGENT_FAIL_WORDS)


# ── Provider Functions ─────────────────────────────────────────────────


async def think(
    prompt: str,
    system_prompt: str = "",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 500,
    temperature: float = 0.7,
    timeout: Optional[int] = None,
) -> str:
    """ให้ LLM คิดและตอบกลับ — ใช้ได้จากทุก Agent

    Args:
        prompt: คำถาม/คำสั่งถึง LLM
        system_prompt: context/brief เพิ่มเติม (เช่น บทบาท agent)
        model: ชื่อ model (default: muse-spark-1.3, fallback → space-bunny → longcat → mimo)
        max_tokens: ความยาวสูงสุดของคำตอบ
        temperature: (reserved) ไม่ได้ส่งไป opencode run โดยตรง
        timeout: override timeout (วินาที) — prompt ยาว/ภาษาไทยต้องใช้เวลานาน

    Returns:
        str: ข้อความตอบกลับจาก LLM (ตัด max_tokens แล้ว)
    """
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    last_error = ""

    # Build try-list: requested model first, then fallbacks (skip duplicates).
    # Dead models map straight to full chain.
    if model in DEAD_MODELS or model == DEFAULT_MODEL or model in MODEL_FALLBACKS:
        try_list = list(MODEL_FALLBACKS)
        # ถ้า caller เจาะจงตัวใน chain ให้เริ่มจากตัวนั้นก่อน
        if model in MODEL_FALLBACKS:
            try_list.remove(model)
            try_list.insert(0, model)
    else:
        try_list = [model] + [m for m in MODEL_FALLBACKS if m != model]

    for model_name in try_list:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with _semaphore:
                    result = await _run_opencode(full_prompt, model_name, timeout=timeout)

                if not result:
                    log.warning(f"LLM เปล่า ({model_name} attempt {attempt})")
                    last_error = f"{model_name}: empty response"
                    break  # เปล่า = เปลี่ยนโมเดลเลย ไม่ retry ตัวเดิมซ้ำ

                if model_name != try_list[0]:
                    log.info(f"LLM fallback สำเร็จด้วย {model_name}")
                return result[:max_tokens]

            except asyncio.TimeoutError:
                log.warning(f"LLM timeout {model_name} attempt {attempt}/{_MAX_RETRIES}")
                last_error = f"{model_name}: timeout ({timeout or _LLM_TIMEOUT}s)"
                continue

            except Exception as e:
                log.warning(f"LLM error {model_name} attempt {attempt}/{_MAX_RETRIES}: {e}")
                last_error = f"{model_name}: {e}"
                # Model not found = ข้ามไปตัวถัดไปทันที ไม่ต้อง retry ซ้ำ
                if "Model not found" in str(e) or "model not found" in str(e).lower():
                    break
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(attempt)
                continue

    log.error(f"LLM หมดโอกาส (ลอง {len(try_list)} โมเดล): {last_error}")
    return f"⚠️ LLM ไม่พร้อม: {last_error}"


async def _run_opencode(full_prompt: str, model: str, *, timeout: Optional[int] = None) -> str:
    """เรียก LLM ผ่าน opencode run CLI (core)

    spawn subprocess → ส่ง prompt ผ่าน stdin → อ่าน stdout
    ใช้ --model + --pure เพื่อลด overhead
    ใช้ --agent <judgment agent> ด้วย เพื่อกันโมเดลพยายามใช้เครื่องมือ
    (permission auto-reject → stdout ว่าง → provider คืน "LLM ไม่พร้อม")
    ถ้า agent ไม่มี/ไม่รู้จัก → retry โดยไม่ใส่ --agent (ไม่ให้ระบบล้มทั้งหมด)
    """
    agent = _resolve_agent()
    try:
        return await _exec_opencode(full_prompt, model, agent=agent, timeout=timeout)
    except Exception as exc:
        if agent and _looks_like_agent_error(str(exc)):
            log.warning(
                f"opencode agent '{agent}' ใช้ไม่ได้ ({exc}) "
                f"→ retry โดยไม่ใส่ --agent"
            )
            return await _exec_opencode(full_prompt, model, agent=None, timeout=timeout)
        raise


async def _exec_opencode(
    full_prompt: str,
    model: str,
    *,
    agent: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """รัน opencode run 1 ครั้ง (ไม่มี fallback — ใช้จาก _run_opencode)"""
    cmd = [*_CMD_WITH_FLAGS, "--model", model]
    if agent:
        cmd += ["--agent", agent]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=_CWD,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=full_prompt.encode("utf-8")),
            timeout=timeout or _LLM_TIMEOUT,
        )
    except asyncio.TimeoutError:
        _safe_kill(proc)
        raise

    exit_code = await _safe_wait(proc)
    result = stdout.decode("utf-8", errors="replace").strip()

    if exit_code and exit_code != 0:
        err = stderr.decode("utf-8", errors="replace")[:200]
        raise RuntimeError(f"opencode run exit {exit_code}: {err}")

    return result


def _safe_kill(proc: asyncio.subprocess.Process) -> None:
    """ฆ่า process + ป้องกัน ProcessLookupError"""
    try:
        proc.kill()
    except ProcessLookupError:
        pass
    except OSError:
        pass


async def _safe_wait(proc: asyncio.subprocess.Process) -> int:
    """รอเก็บ zombie + คืน returncode"""
    try:
        return await proc.wait()
    except ProcessLookupError:
        return proc.returncode or -1
    except OSError:
        return proc.returncode or -1


# ── Utility ────────────────────────────────────────────────────────────

def count_tokens(text: str) -> int:
    """นับจำนวน token โดยประมาณ (ไทย + อังกฤษ)"""
    import re
    thai_chars = len(re.findall(r'[\u0E00-\u0E7F]', text))
    eng_words = len(re.findall(r'[a-zA-Z]+', text))
    return thai_chars + eng_words + len(text.split())
