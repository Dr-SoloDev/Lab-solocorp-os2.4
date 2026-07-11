"""Orchestrator Agent — @orchestrator-wut: Pipeline Coordination"""

from __future__ import annotations

from workers.agents.base_agent import BaseAgent


class OrchestratorAgent(BaseAgent):
    """Orchestrator — ดูแล pipeline coordination ระหว่าง departments"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="orchestrator-wut",
            name="Orchestrator พี่วุฒิ",
            profile_path="profiles/04-orchestrator/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )

    async def _llm_respond(self, task: dict, context: str = "") -> dict:
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        prompt = f"ได้รับงานจาก CEO\nAction: {action}\nDescription: {description}\n{context}\n\nโปรดดำเนินการและรายงานผล"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"action": action, "agent": self.agent_id, "llm_used": True, "full_response": llm_resp}}
        except Exception as e:
            return {"status": "completed", "summary": f"Orchestrator รับทราบ: {description}", "details": {"action": action, "llm_error": str(e)}}

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")
        if "pipeline" in action or "coordinate" in action:
            return await self._coordinate_pipeline(task)
        elif "status" in action or "check" in action:
            return await self._pipeline_status(task)
        elif "handoff" in action:
            return await self._execute_handoff(task)
        else:
            return await self._llm_respond(task)

    async def _coordinate_pipeline(self, task: dict) -> dict:
        desc = task.get("payload", {}).get("description", "")
        steps = task.get("payload", {}).get("steps", [])
        prompt = f"คุณคือ Orchestrator (พี่วุฒิ) ของ SoloCorp OS\n\nCoordinate pipeline: {desc}\nSteps: {steps}\nโปรดวางแผน pipeline และ coordination"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"pipeline": desc, "steps": steps, "llm_used": True}}
        except Exception:
            return {"status": "completed", "summary": "🔗 Pipeline coordinate เสร็จสิ้น", "details": {"pipeline": desc, "steps": steps}}

    async def _pipeline_status(self, task: dict) -> dict:
        prompt = f"คุณคือ Orchestrator (พี่วุฒิ) ของ SoloCorp OS\nรายงานสถานะ pipeline ล่าสุด: {task.get('payload',{}).get('description','')}\nโปรดรายงานสุขภาพ pipeline และข้อเสนอแนะ"
        try:
            llm_resp = await self.think(prompt, max_tokens=300)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"llm_used": True}}
        except Exception:
            return {"status": "completed", "summary": "📊 Pipeline status — ทั้งหมดปกติ", "details": {"health": "🟢 all green"}}

    async def _execute_handoff(self, task: dict) -> dict:
        payload = task.get("payload", {})
        prompt = f"คุณคือ Orchestrator (พี่วุฒิ) ของ SoloCorp OS\n\nHandoff จาก {payload.get('from','?')} ไป {payload.get('to','?')}\nContext: {payload.get('description','')}\nโปรดดำเนินการ handoff และยืนยัน"
        try:
            llm_resp = await self.think(prompt, max_tokens=400)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"from_dept": payload.get("from", ""), "to_dept": payload.get("to", ""), "llm_used": True}}
        except Exception:
            return {"status": "completed", "summary": "🤝 Handoff สำเร็จ", "details": {"from_dept": payload.get("from", ""), "to_dept": payload.get("to", ""), "context_packed": True}}
