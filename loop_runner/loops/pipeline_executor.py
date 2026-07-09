"""Pipeline Executor — ดึง task จาก queue แล้วมอบหมายให้ LLM Agent ดำเนินการ"""

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

AGENT_PERSONA = {
    "engineering": "คุณคือ ช่างฟูล (Head of Engineering) ของ SoloCorp — full-stack developer ตอบเป็นภาษาไทย",
    "ui_designer": "คุณคือ UI Designer ของ SoloCorp — สร้าง component และ wireframe ตอบเป็นภาษาไทย",
    "qa": "คุณคือ QA ทีม ของ SoloCorp — ทดสอบและรายงาน bug ตอบเป็นภาษาไทย",
    "design": "คุณคือ ครีเอท (Creative Director) ของ SoloCorp — ออกแบบ UI/UX ตอบเป็นภาษาไทย",
    "product": "คุณคือ โปรดัค (Product Manager) ของ SoloCorp — เขียน PRD และ spec ตอบเป็นภาษาไทย",
    "architect": "คุณคือ พี่ทรงศักดิ์ (Architect) ของ SoloCorp — ออกแบบระบบ ตอบเป็นภาษาไทย",
    "cfo": "คุณคือ meetoo (CFO) ของ SoloCorp — ดูแลการเงิน ตอบเป็นภาษาไทย",
    "cmo": "คุณคือ มาร์ค (CMO) ของ SoloCorp — ดูแลการตลาด ตอบเป็นภาษาไทย",
    "orchestrator": "คุณคือ พี่วุฒิ (Orchestrator) ของ SoloCorp — ดูแล pipeline ตอบเป็นภาษาไทย",
}

MAX_TASKS_PER_RUN = 2


def _fetch_queue() -> list[dict]:
    """ดึง tasks ที่รอจาก Central Bus"""
    try:
        req = urllib.request.Request(
            f"{BUS_URL}/v1/context",
            headers={"Authorization": f"Bearer {API_KEY}"},
            method="POST",
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        return resp.get("queue", [])
    except Exception:
        return []


def _update_task_status(task_id: str, status: str, result: str = "") -> bool:
    """อัปเดตสถานะ task กลับไปที่ Central Bus"""
    try:
        payload = json.dumps({
            "task_id": task_id,
            "status": status,
            "result": result[:500],
        }).encode()
        req = urllib.request.Request(
            f"{BUS_URL}/v1/update",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            },
            method="POST",
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        return resp.get("success", False)
    except Exception:
        return False


class PipelineExecutorLoop(Loop):
    loop_id = "pipeline_executor"
    interval = timedelta(minutes=30)
    trust_level = 4  # L4 — auto-execute
    model_hint = "opencode/deepseek-v4-flash-free"

    def run(self) -> str:
        queue = _fetch_queue()
        if not queue:
            return "⏭ pipeline_executor: queue empty — nothing to run"

        executed = []
        for task in queue[:MAX_TASKS_PER_RUN]:
            task_id = task.get("task_id", "?")
            target = task.get("target_agent", task.get("to_dept", "general"))
            desc = task.get("payload", {}).get("description", task.get("description", ""))

            persona = AGENT_PERSONA.get(target.split("-")[0], f"คุณคือ {target} ของ SoloCorp")
            prompt = (
                f"{persona}\n\n"
                f"Task ID: {task_id}\n"
                f"คำสั่ง: {desc}\n\n"
                f"ทำงานนี้ให้เสร็จสมบูรณ์ รายงานผลลัพธ์โดยย่อ"
            )

            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    think(prompt, max_tokens=800)
                )
                loop.close()
            except Exception as e:
                result = f"⚠️ Error: {e}"

            # อัปเดตสถานะกลับ
            success = _update_task_status(task_id, "completed" if result else "failed", result)
            executed.append(f"[{task_id}] → {target}: {'✅' if success else '❌'} {result[:100]}...")

        return "✅ pipeline_executor ran " + str(len(executed)) + " tasks:\n" + "\n".join(executed)
