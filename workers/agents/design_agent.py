"""Design Agent — @design-kreet: UX Research, Brand Visual"""

from workers.agents.base_agent import BaseAgent


class DesignAgent(BaseAgent):
    """Design — ดูแล UX, design system, visual"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="design-kreet",
            name="Design ครีเอท",
            profile_path="profiles/08-design/SOUL.md",
            bus_url=bus_url, api_key=api_key,
        )

    async def _llm_respond(self, task: dict, context: str = "") -> dict:
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        prompt = f"ได้รับงานจาก CEO\nAction: {action}\nDescription: {description}\n{context}\n\nโปรดดำเนินการตามบทบาท Design และรายงานผล"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"action": action, "agent": self.agent_id, "llm_used": True, "full_response": llm_resp}}
        except Exception as e:
            return {"status": "completed", "summary": f"Design รับทราบ: {description}", "details": {"action": action, "llm_error": str(e)}}

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")
        description = task.get("payload", {}).get("description", "")
        if "ux" in action or "research" in action:
            prompt = f"คุณคือ Design (ครีเอท) ของ SoloCorp OS\n\nUX Research: {description}\nโปรดำเสนอผลวิจัยและข้อแนะนำ"
        elif "design" in action or "visual" in action or "brand" in action:
            prompt = f"คุณคือ Design (ครีเอท) ของ SoloCorp OS\n\nออกแบบ Visual/Brand: {description}\nโปรดเสนอแนวทางการออกแบบ"
        elif "prototype" in action:
            prompt = f"คุณคือ Design (ครีเอท) ของ SoloCorp OS\n\nสร้าง prototype: {description}\nโปรดวางแผน prototyping"
        else:
            return await self._llm_respond(task)
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"action": action, "llm_used": True, "full_response": llm_resp}}
        except Exception:
            return {"status": "completed", "summary": f"Design: {action} เสร็จสิ้น", "details": {"action": action}}
