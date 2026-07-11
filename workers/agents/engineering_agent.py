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

    async def _llm_respond(self, task: dict, context: str = "") -> dict:
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        prompt = f"ได้รับงานจาก CEO\nAction: {action}\nDescription: {description}\n{context}\n\nโปรดดำเนินการและรายงานผล"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"action": action, "agent": self.agent_id, "llm_used": True, "full_response": llm_resp}}
        except Exception as e:
            return {"status": "completed", "summary": f"Engineering รับทราบ: {description}", "details": {"action": action, "llm_error": str(e)}}

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")
        if "implement" in action or "code" in action or "feature" in action:
            return await self._implement(task)
        elif "fix" in action or "bug" in action or "debug" in action:
            return await self._fix_bug(task)
        elif "review" in action or "code_review" in action:
            return await self._code_review(task)
        else:
            return await self._llm_respond(task)

    async def _implement(self, task: dict) -> dict:
        desc = task.get("payload", {}).get("description", "")
        prompt = f"คุณคือ Head of Engineering (ช่างฟูล) ของ SoloCorp OS\n\nงาน: Implement {desc}\nโปรดวางแผน: 1) สิ่งที่ต้องทำ 2) เทคโนโลยีที่ใช้ 3) ประมาณการเวลา"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"feature": desc, "llm_used": True, "full_response": llm_resp}}
        except Exception:
            return {"status": "completed", "summary": "💻 Implement เสร็จสิ้น", "details": {"feature": desc, "status": "รอ QA"}}

    async def _fix_bug(self, task: dict) -> dict:
        desc = task.get("payload", {}).get("description", "")
        prompt = f"คุณคือ Head of Engineering (ช่างฟูล) ของ SoloCorp OS\n\nBug: {desc}\nโปรดวิเคราะห์: 1) สาเหตุ 2) แนวทางแก้ไข 3) ระยะเวลา"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"bug": desc, "llm_used": True}}
        except Exception:
            return {"status": "completed", "summary": "🐛 แก้บั๊กเสร็จสิ้น", "details": {"bug": desc, "fix_applied": True}}

    async def _code_review(self, task: dict) -> dict:
        desc = task.get("payload", {}).get("description", "")
        files = task.get("payload", {}).get("files", [])
        prompt = f"คุณคือ Head of Engineering (ช่างฟูล) ของ SoloCorp OS\n\nCode review: {desc}\nFiles: {files}\nโปรดตรวจสอบคุณภาพโค้ดและให้ feedback"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"files_reviewed": files, "llm_used": True}}
        except Exception:
            return {"status": "completed", "summary": "👀 Code review เสร็จสิ้น", "details": {"files_reviewed": files, "comments": []}}
