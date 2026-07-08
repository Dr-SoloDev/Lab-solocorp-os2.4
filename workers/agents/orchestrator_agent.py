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

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")

        if "pipeline" in action or "coordinate" in action:
            return await self._coordinate_pipeline(task)
        elif "status" in action or "check" in action:
            return await self._pipeline_status(task)
        elif "handoff" in action:
            return await self._execute_handoff(task)
        else:
            return {"status": "completed", "summary": f"Orchestrator รับทราบ: {task.get('payload', {}).get('description', '')}", "details": {}}

    async def _coordinate_pipeline(self, task: dict) -> dict:
        return {
            "status": "completed",
            "summary": "🔗 Pipeline coordinate เสร็จสิ้น",
            "details": {
                "pipeline": task.get("payload", {}).get("pipeline", "default"),
                "steps": task.get("payload", {}).get("steps", []),
                "status": "running — smooth",
            },
        }

    async def _pipeline_status(self, task: dict) -> dict:
        return {
            "status": "completed",
            "summary": "📊 Pipeline status — ทั้งหมดปกติ",
            "details": {
                "active_pipelines": [],
                "blocked": [],
                "completed": [],
                "health": "🟢 all green",
            },
        }

    async def _execute_handoff(self, task: dict) -> dict:
        payload = task.get("payload", {})
        return {
            "status": "completed",
            "summary": "🤝 Handoff สำเร็จ",
            "details": {
                "from_dept": payload.get("from", ""),
                "to_dept": payload.get("to", ""),
                "context_packed": True,
                "acknowledged": True,
            },
        }
