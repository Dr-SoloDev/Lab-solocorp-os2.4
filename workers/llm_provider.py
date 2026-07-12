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

DEFAULT_MODEL = "opencode/deepseek-v4-flash-free"
_CMD = "/usr/local/bin/opencode"
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
        model: ชื่อ model (default: deepseek-v4-flash-free)
        max_tokens: ความยาวสูงสุดของคำตอบ
        temperature: (reserved) ไม่ได้ส่งไป opencode run โดยตรง

    Returns:
        str: ข้อความตอบกลับจาก LLM (ตัด max_tokens แล้ว)
    """
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    last_error = ""

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            async with _semaphore:
                result = await _run_opencode(full_prompt, model)

            if not result:
                log.warning(f"LLM เปล่า (attempt {attempt})")
                last_error = "empty response"
                continue

            return result[:max_tokens]

        except asyncio.TimeoutError:
            log.warning(f"LLM timeout attempt {attempt}/{_MAX_RETRIES}")
            last_error = f"timeout ({_LLM_TIMEOUT}s)"
            continue

        except Exception as e:
            log.warning(f"LLM error attempt {attempt}/{_MAX_RETRIES}: {e}")
            last_error = str(e)
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(attempt * 2)
            continue

    log.error(f"LLM หมดโอกาส ({_MAX_RETRIES} attempts): {last_error}")
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
