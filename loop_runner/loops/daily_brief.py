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

        prompt = (
            f"คุณคือ CFO ของ SoloCorp OS\n\n"
            f"นี่คือข้อมูลสถานะปัจจุบันขององค์กร:\n{facts_text}\n\n"
            f"กรุณาสรุปรายงานตอนเช้าสำหรับ CEO (เทอโบ) ในรูปแบบ:\n"
            f"1. สถานะการเงินโดยรวม\n"
            f"2. สิ่งที่ต้องจับตามองวันนี้\n"
            f"3. คำแนะนำสำหรับ CEO\n"
            f"ใช้ภาษาไทย สั้น กระชับ ไม่เกิน 10 บรรทัด"
        )

        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                think(prompt, system_prompt="คุณคือ CFO meetoo ของ SoloCorp OS")
            )
            loop.close()
            return result
        except Exception as e:
            return f"⚠️ daily_brief: LLM ไม่พร้อม — {e}"
