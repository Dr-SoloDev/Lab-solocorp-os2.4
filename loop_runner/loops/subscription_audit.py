"""Subscription Audit — ตรวจสอบค่าใช้จ่ายรายเดือนซ้ำซ้อน"""

import asyncio
import json
import os
import urllib.request
from datetime import timedelta
from pathlib import Path

from ..runner import Loop

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from workers.llm_provider import think

BUS_URL = os.environ.get("SOLOCORP_BUS_URL", "http://127.0.0.1:8099")
API_KEY = os.environ.get("SOLOCORP_API_KEY", "sk-solocorp-admin-local-dev-001")


def _fetch_context() -> dict:
    """ดึง context จาก Central Bus"""
    try:
        req = urllib.request.Request(
            f"{BUS_URL}/v1/context",
            headers={"Authorization": f"Bearer {API_KEY}"},
            method="POST",
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        return resp
    except Exception as e:
        return {"facts": [], "queue": []}


class SubscriptionAuditLoop(Loop):
    loop_id = "subscription_audit"
    interval = timedelta(days=30)
    trust_level = 4  # L4 — auto-execute
    model_hint = "opencode/deepseek-v4-flash-free"

    def run(self) -> str:
        ctx = _fetch_context()
        facts = ctx.get("facts", [])
        queue = ctx.get("queue", [])
        queue_depth = len(queue)

        facts_text = "\n".join(
            f"- [{f.get('id','?')}] {f.get('content','')[:200]}"
            for f in facts[:20]
        )

        # NOTE: deepseek-v4-flash-free returns EMPTY on long Thai prompts
        # (same bug class as daily_brief — verified 2026-08-04).
        # Prompt uses EN structure + TH output instruction — stable. Fallback retries EN-only.
        prompt = (
            f"You are CFO of SoloCorp OS. Org status:\n{facts_text}\n\n"
            f"Audit subscriptions for duplicates or unnecessary costs. Respond in Thai, max 8 lines:\n"
            f"1. Duplicate subscriptions?\n2. Monthly recurring costs?\n3. Cost reduction recommendations"
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
            return f"## CFO Subscription Audit\n\n{result}"
        except Exception as e:
            return f"⚠️ subscription_audit: LLM ไม่พร้อม — {e}"

    @staticmethod
    def _fallback_en(facts_text: str) -> str:
        """Retry with short EN-only prompt (verified working for long input)."""
        prompt = (
            f"SoloCorp OS subscription audit. Status:\n{facts_text[:500]}\n\n"
            f"List duplicate subscriptions, monthly recurring costs, cost reduction ideas. Max 8 lines."
        )
        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                think(prompt, system_prompt="You are SoloCorp CFO. Be concise.", max_tokens=300)
            )
            loop.close()
            return result
        except Exception as e:
            return f"⚠️ subscription_audit: fallback failed — {e}"
