"""🤖 SoloCorp OS — LLM Provider

เชื่อมต่อ Agent กับ LLM (OpenCode cloud ผ่าน CLI หรือ API)

รองรับ:
- `opencode run` CLI (backup)
- OpenAI-compatible API (เมื่อ ACP server พร้อม)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from typing import Optional

log = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────

# OpenCode API Key จาก Owner
_OPENCODE_API_KEY = os.environ.get(
    "OPENCODE_API_KEY",
    "sk-gDFLCDp1p10Gg0aygn9HUw1we5hogFUfOqkssrCxqG3TxvhAcDVG2etcT1t4mIeD"
)

# Model ที่ใช้ — ตรงกับที่ opencode models มี
DEFAULT_MODEL = "opencode/deepseek-v4-flash-free"

# ACP endpoint (ถ้าเปิด)
_ACP_URL = os.environ.get("ACP_URL", "http://127.0.0.1:5200/v1/chat/completions")

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
        temperature: ความคิดสร้างสรรค์ (0.0 = ตายตัว, 1.0 = สร้างสรรค์)

    Returns:
        str: ข้อความตอบกลับจาก LLM
    """
    # ลองใช้ ACP API ก่อน
    try:
        return await _call_acp(prompt, system_prompt, model, max_tokens, temperature)
    except Exception as e:
        log.debug(f"ACP ไม่พร้อม ({e}), ใช้ opencode run แทน")

    # Fallback: opencode run CLI
    try:
        return await _call_opencode_run(prompt, system_prompt, model, max_tokens)
    except Exception as e:
        log.error(f"LLM ทั้งสองช่องทางล้มเหลว: {e}")
        return f"⚠️ LLM ไม่พร้อม: {e}"


async def _call_acp(
    prompt: str, system_prompt: str, model: str,
    max_tokens: int, temperature: float,
) -> str:
    """เรียก LLM ผ่าน ACP (OpenAI-compatible API)"""
    import urllib.request

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode()

    req = urllib.request.Request(
        _ACP_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_OPENCODE_API_KEY}",
        },
        method="POST",
    )

    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(
        None, lambda: json.loads(
            urllib.request.urlopen(req, timeout=30).read()
        )
    )

    return resp["choices"][0]["message"]["content"]


async def _call_opencode_run(
    prompt: str, system_prompt: str, model: str, max_tokens: int,
) -> str:
    """เรียก LLM ผ่าน opencode run CLI (fallback)"""
    full_prompt = system_prompt + "\n\n" + prompt if system_prompt else prompt

    cmd = [
        "/usr/local/bin/opencode", "run",
        "--model", model,
        "--", full_prompt,
    ]

    loop = asyncio.get_event_loop()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/workspace/repos/Lab-solocorp-os2.4",
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=45
        )
    except asyncio.TimeoutError:
        proc.kill()
        return "⚠️ LLM timeout (45s)"

    result = stdout.decode("utf-8", errors="replace").strip()
    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace")[:200]
        log.warning(f"opencode run exit {proc.returncode}: {err}")

    # opencode run output format:
    #   > assistant · model-name
    #   <actual response>
    # ตัดเฉพาะส่วนที่ LLM ตอบ (หลังบรรทัด >)
    lines = result.split("\n")
    response_lines = []
    capture = False
    for line in lines:
        if line.startswith(">"):
            capture = True  # เริ่ม capture หลังจากบรรทัด >
            continue
        if capture and line.strip():
            response_lines.append(line)

    response = "\n".join(response_lines).strip()
    # ถ้าไม่เจอ pattern > ให้ใช้ result ทั้งหมด
    if not response:
        response = result
    return response[:max_tokens]


# ── Utility ────────────────────────────────────────────────────────────

def count_tokens(text: str) -> int:
    """นับจำนวน token โดยประมาณ (ไทย + อังกฤษ)"""
    import re
    # นับคำไทย (1 คำ ≈ 2 tokens)
    thai_chars = len(re.findall(r'[\u0E00-\u0E7F]', text))
    # นับคำอังกฤษ (5 ตัวอักษร ≈ 1 token)
    eng_words = len(re.findall(r'[a-zA-Z]+', text))
    return thai_chars + eng_words + len(text.split())
