"""Sales Agent — @sales: B2B Deal Strategy, Pipeline"""

from workers.agents.base_agent import BaseAgent


class SalesAgent(BaseAgent):
    """Sales — ดูแล B2B deals, sales pipeline"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__("sales", "Sales เซลส์", "profiles/11-sales/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        d = task.get("payload", {}).get("description", "")
        action_map = {"deal": f"Deal strategy: {d}\nโปรดวิเคราะห์ deal และเสนอ strategy", "client": f"ลูกค้า: {d}\nโปรดวิเคราะห์ข้อมูลลูกค้า", "strategy": f"กลยุทธ์: {d}\nโปรดเสนอแผนกลยุทธ์การขาย"}
        prompt = None
        for k, v in action_map.items():
            if k in a:
                prompt = f"คุณคือ Sales (เซลส์) ของ SoloCorp OS\n{v}"
                break
        if not prompt:
            prompt = f"คุณคือ Sales (เซลส์) ของ SoloCorp OS\nได้รับงานจาก CEO: {d}\nโปรดำดำเนินการและรายงานผล"
        try:
            llm = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm[:200], "details": {"action": a, "llm_used": True, "full_response": llm}}
        except Exception as e:
            return {"status": "completed", "summary": f"Sales รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}
