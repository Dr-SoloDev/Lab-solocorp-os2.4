"""🤖 SoloCorp OS — Maxplus AI LLM Provider

ใช้ Maxplus AI API โดยตรงผ่าน HTTP — เร็วและเสถียรกว่า CLI
Compatible กับ OpenAI API format
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import aiohttp

log = logging.getLogger(__name__)

# ── Load .env file ─────────────────────────────────────────────────────

def load_env():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

# ── Configuration ──────────────────────────────────────────────────────

DEFAULT_MODEL = os.environ.get("MAXPLUS_MODEL", "stealth/ox-alpha")
BASE_URL = os.environ.get("MAXPLUS_BASE_URL", "https://api.maxplus-ai.cc/ox-alpha/v1")
API_KEY = os.environ.get("MAXPLUS_API_KEY", "")

_MAX_CONCURRENT = 5
_LLM_TIMEOUT = 30
_MAX_RETRIES = 3

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
    """ให้ LLM คิดและตอบกลับ — ใช้ Maxplus AI API

    Args:
        prompt: คำถาม/คำสั่งถึง LLM
        system_prompt: context/brief เพิ่มเติม
        model: ชื่อ model (default: stealth/ox-alpha)
        max_tokens: ความยาวสูงสุดของคำตอบ
        temperature: ความสร้างสรรค์ (0.0-1.0)

    Returns:
        str: ข้อความตอบกลับจาก LLM
    """
    if not API_KEY:
        return "⚠️ LLM ไม่พร้อม: MAXPLUS_API_KEY ไม่ได้ตั้งค่า"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept-Encoding": "identity",  # Disable Brotli compression
    }

    last_error = ""

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            async with _semaphore:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{BASE_URL}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=_LLM_TIMEOUT),
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise RuntimeError(f"HTTP {response.status}: {error_text[:200]}")

                        data = await response.json()
                        message = data.get("choices", [{}])[0].get("message", {})
                        
                        # DeepSeek V4 reasoning models return reasoning_content
                        result = message.get("content", "").strip()
                        if not result:
                            result = message.get("reasoning_content", "").strip()

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


# ── Quick Test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    async def test():
        print("🤖 Testing Maxplus AI LLM Provider...")
        print("=" * 50)

        # Test 1: Simple question
        result = await think(
            prompt="Answer with just YES or NO: Is SoloCorp OS running?",
            max_tokens=10
        )
        print(f"✅ Test 1: {result}")

        # Test 2: With system prompt
        result = await think(
            system_prompt="You are a helpful assistant for SoloCorp OS.",
            prompt="What is your role?",
            max_tokens=100
        )
        print(f"✅ Test 2: {result}")

    asyncio.run(test())
