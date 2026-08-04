"""Daily Brief — CEO Morning Briefing via LLM Provider + Central Bus"""

import asyncio
import json
import os
import urllib.request
from datetime import timedelta
from pathlib import Path

from ..runner import Loop

# LLM Provider
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from workers.llm_provider import think

BUS_URL = os.environ.get("SOLOCORP_BUS_URL", "http://127.0.0.1:8099")
API_KEY = os.environ.get("SOLOCORP_API_KEY", "sk-solocorp-admin-local-dev-001")


def _fetch_facts() -> list[dict]:
    """ดึง facts จาก Central Bus เพื่อให้ LLM ใช้เป็นข้อมูล"""
    try:
        req = urllib.request.Request(
            f"{BUS_URL}/v1/context",
            headers={"Authorization": f"Bearer {API_KEY}"},
            method="POST",
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        return resp.get("facts", [])
    except Exception as e:
        return [{"id": "error", "content": f"ไม่สามารถเชื่อมต่อ Central Bus: {e}"}]


class DailyBriefLoop(Loop):
    loop_id = "daily_brief"
    interval = timedelta(hours=20)
    trust_level = 1  # L1 report only

    def run(self) -> str:
        facts = _fetch_facts()
        facts_text = "\n".join(
            f"- [{f.get('id','?')}] {f.get('content','')[:200]}"
            for f in facts[:20]
        )

        # NOTE: deepseek-v4-flash-free returns EMPTY on long Thai prompts (verified 2026-08-04).
        # Prompt uses EN structure + TH output instruction — stable. Fallback retries EN-only.
        prompt = (
            f"You are CFO of SoloCorp OS. Org status:\n{facts_text}\n\n"
            f"Morning report for CEO (เทอโบ). Respond in Thai, max 10 lines:\n"
            f"1. Finance overview\n2. Watch items today\n3. CEO recommendations"
        )

        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                think(prompt, system_prompt="You are CFO meetoo of SoloCorp OS. Output in Thai.")
            )
            loop.close()

            # Fallback: EN-only short prompt if model returned empty (LLM ไม่พร้อม)
            if result.startswith("⚠️ LLM ไม่พร้อม"):
                result = self._fallback_en(facts_text)
            return result
        except Exception as e:
            return f"⚠️ daily_brief: LLM ไม่พร้อม — {e}"

    @staticmethod
    def _fallback_en(facts_text: str) -> str:
        """Retry with short EN-only prompt (verified working for long input)."""
        prompt = (
            f"SoloCorp OS morning brief. Status:\n{facts_text[:500]}\n\n"
            f"Summarize finance status, today watch items, CEO recommendations. Max 10 lines."
        )
        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                think(prompt, system_prompt="You are SoloCorp CFO. Be concise.", max_tokens=300)
            )
            loop.close()
            return result
        except Exception as e:
            return f"⚠️ daily_brief: fallback failed — {e}"
