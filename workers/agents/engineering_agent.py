"""Engineering Agent — @changful: Backend, Frontend, Architecture"""

from __future__ import annotations

from workers.agents.base_agent import BaseAgent


class EngineeringAgent(BaseAgent):
    """Engineering — ดูแล implementation โค้ดทั้ง backend/frontend"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="changful",
            name="Engineering ช่างฟูล",
            profile_path="profiles/07-engineering/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")

        if "implement" in action or "code" in action or "feature" in action:
            return await self._implement(task)
        elif "fix" in action or "bug" in action or "debug" in action:
            return await self._fix_bug(task)
        elif "review" in action or "code_review" in action:
            return await self._code_review(task)
        else:
            return {"status": "completed", "summary": f"Engineering รับทราบ: {task.get('payload', {}).get('description', '')}", "details": {}}

    async def _implement(self, task: dict) -> dict:
        payload = task.get("payload", {})
        return {
            "status": "completed",
            "summary": "💻 Implement เสร็จสิ้น",
            "details": {
                "feature": payload.get("description", ""),
                "files_modified": payload.get("files", []),
                "status": "รอ QA",
            },
        }

    async def _fix_bug(self, task: dict) -> dict:
        return {
            "status": "completed",
            "summary": "🐛 แก้บั๊กเสร็จสิ้น",
            "details": {"bug": task.get("payload", {}).get("description", ""), "fix_applied": True},
        }

    async def _code_review(self, task: dict) -> dict:
        return {
            "status": "completed",
            "summary": "👀 Code review เสร็จสิ้น",
            "details": {"files_reviewed": task.get("payload", {}).get("files", []), "comments": []},
        }
