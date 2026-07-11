"""Support Agent — @support: Customer Success, Analytics"""

from workers.agents.base_agent import BaseAgent


class SupportAgent(BaseAgent):
    """Support — ดูแล customer success, support tickets"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__("support", "Support ซัพพอร์ต", "profiles/12-support/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        d = task.get("payload", {}).get("description", "")
        action_map = {"ticket": f"Support ticket: {d}\nโปรดำจัดการ ticket และตอบกลับ", "customer": f"Customer success: {d}\nโปรดำดูแลลูกค้าและ feedback", "analytics": f"Analytics: {d}\nโปรดำวิเคราะห์ข้อมูล support"}
        prompt = None
        for k, v in action_map.items():
            if k in a:
                prompt = f"คุณคือ Support (ซัพพอร์ต) ของ SoloCorp OS\n{v}"
                break
        if not prompt:
            prompt = f"คุณคือ Support (ซัพพอร์ต) ของ SoloCorp OS\nได้รับงานจาก CEO: {d}\nโปรดำดำเนินการและรายงานผล"
        try:
            llm = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm[:200], "details": {"action": a, "llm_used": True, "full_response": llm}}
        except Exception as e:
            return {"status": "completed", "summary": f"Support รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}
