"""🤖 SoloCorp OS — LLM Provider

เชื่อมต่อ Agent กับ LLM (OpenCode ผ่าน opencode run CLI)

ใช้ opencode run CLI โดยตรง — stable, official, tested.
- ส่ง prompt ผ่าน stdin ป้องกัน shell injection
- --pure ลด overhead plugins
- retry + timeout + semaphore concurrency control
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess

log = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────

# Owner-ordered fallback chain (2026-09-27, CMD-005 follow-up):
# 1. Space Bunny Free — text+image+video, ~80 tok/s (primary)
# 2. Muse Spark 1.3 Free — สำรอง 1
# 3. Longcat 2.5 Preview Free — สำรอง 2
# 4. Mimo-2.6-Flash Free — สำรอง 3
DEFAULT_MODEL = "opencode/space-bunny-free"
MODEL_FALLBACKS = [
    "opencode/space-bunny-free",
    "opencode/muse-spark-1.3-contributor-free",
    "opencode/longcat-2.5-preview-free",
    "opencode/mimo-v2.6-flash-free",
]
# Dead models — ถ้ามี caller ส่งชื่อเก่ามา ให้ map เข้า fallback chain ทันที
DEAD_MODELS = {
    "opencode/x-preview-f-free",
    "stealth/ox-alpha",
    "opencode/deepseek-v4-flash-free",
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


# ── Provider Functions ─────────────────────────────────────────────────


async def think(
    prompt: str,
    system_prompt: str = "",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 500,
    temperature: float = 0.7,
) -> str:
    """ให้ LLM คิดและตอบกลับ — ใช้ได้จากทุก Agent

    Args:
        prompt: คำถาม/คำสั่งถึง LLM
        system_prompt: context/brief เพิ่มเติม (เช่น บทบาท agent)
        model: ชื่อ model (default: space-bunny-free, fallback → muse-spark → longcat → mimo)
        max_tokens: ความยาวสูงสุดของคำตอบ
        temperature: (reserved) ไม่ได้ส่งไป opencode run โดยตรง

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
                    result = await _run_opencode(full_prompt, model_name)

                if not result:
                    log.warning(f"LLM เปล่า ({model_name} attempt {attempt})")
                    last_error = f"{model_name}: empty response"
                    break  # เปล่า = เปลี่ยนโมเดลเลย ไม่ retry ตัวเดิมซ้ำ

                if model_name != try_list[0]:
                    log.info(f"LLM fallback สำเร็จด้วย {model_name}")
                return result[:max_tokens]

            except asyncio.TimeoutError:
                log.warning(f"LLM timeout {model_name} attempt {attempt}/{_MAX_RETRIES}")
                last_error = f"{model_name}: timeout ({_LLM_TIMEOUT}s)"
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


async def _run_opencode(full_prompt: str, model: str) -> str:
    """เรียก LLM ผ่าน opencode run CLI (core)

    spawn subprocess → ส่ง prompt ผ่าน stdin → อ่าน stdout
    ใช้ --model + --pure เพื่อลด overhead
    """
    cmd = [*_CMD_WITH_FLAGS, "--model", model]

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
            timeout=_LLM_TIMEOUT,
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
