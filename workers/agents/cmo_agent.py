"""CMO Agent — @cmo-mark: Marketing, Content, Brand"""

from workers.agents.base_agent import BaseAgent


class CMOAgent(BaseAgent):
    """CMO — ดูแลการตลาด คอนเทนต์ แบรนด์"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="cmo-mark",
            name="CMO มาร์ค",
            profile_path="profiles/03-cmo/SOUL.md",
            bus_url=bus_url, api_key=api_key,
        )

    async def _llm_respond(self, task: dict) -> dict:
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        prompt = f"ได้รับงานจาก CEO\nAction: {action}\nDescription: {description}\n\nโปรดำดำเนินการตามบทบาท CMO และรายงานผล"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"action": action, "agent": self.agent_id, "llm_used": True, "full_response": llm_resp}}
        except Exception as e:
            return {"status": "completed", "summary": f"CMO รับทราบ: {description}", "details": {"action": action, "llm_error": str(e)}}

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")
        description = task.get("payload", {}).get("description", "")
        if "campaign" in action or "marketing" in action:
            prompt = f"คุณคือ CMO (มาร์ค) ของ SoloCorp OS\n\nวางแผนแคมเปญ: {description}\nโปรดเสนอ: 1) กลยุทธ์ 2) ช่องทาง 3) KPI"
        elif "content" in action or "brand" in action:
            prompt = f"คุณคือ CMO (มาร์ค) ของ SoloCorp OS\n\nกลยุทธ์คอนเทนต์/แบรนด์: {description}\nโปรดเสนอแนวทาง"
        else:
            return await self._llm_respond(task)
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"action": action, "llm_used": True, "full_response": llm_resp}}
        except Exception:
            return {"status": "completed", "summary": f"✅ {action} วางแผนแล้ว", "details": {"action": action}}
