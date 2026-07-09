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

        prompt = (
            f"คุณคือ CFO (meetoo) ของ SoloCorp OS\n\n"
            f"ข้อมูลองค์กรปัจจุบัน:\n"
            f"- จำนวน departments: 19\n"
            f"- จำนวน queue tasks: {queue_depth}\n"
            f"- facts ในระบบ: {len(facts)} รายการ\n\n"
            f"กรุณาตรวจสอบค่าใช้จ่ายที่อาจซ้ำซ้อนหรือไม่จำเป็น:\n"
            f"1. มี subscription/บริการใดที่อาจซ้ำซ้อน?\n"
            f"2. มีค่าใช้จ่ายรายเดือนอะไรบ้าง?\n"
            f"3. แนะนำการลดค่าใช้จ่าย\n\n"
            f"ตอบสั้น ๆ ไม่เกิน 8 บรรทัด"
        )

        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                think(prompt, system_prompt="คุณคือ CFO meetoo ของ SoloCorp OS")
            )
            loop.close()
            return f"## CFO Subscription Audit\n\n{result}"
        except Exception as e:
            return f"⚠️ subscription_audit: LLM ไม่พร้อม — {e}"
