"""Legal Agent — @legal-tulya: Compliance, Contracts, Law"""

from workers.agents.base_agent import BaseAgent


class LegalAgent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("legal-tulya", "Legal ตุลย์", "profiles/13-legal/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        d = task.get("payload", {}).get("description", "")
        action_map = {"contract": f"สัญญา: {d}\nโปรดำตรวจสอบสัญญาและให้คำแนะนำ", "compliance": f"Compliance: {d}\nโปรดำตรวจสอบ compliance", "tos": f"TOS/Policy: {d}\nโปรดำตรวจสอบเอกสารทางกฎหมาย"}
        prompt = None
        for k, v in action_map.items():
            if k in a:
                prompt = f"คุณคือ Legal (ตุลย์) ของ SoloCorp OS\n{v}"
                break
        if not prompt:
            prompt = f"คุณคือ Legal (ตุลย์) ของ SoloCorp OS\nได้รับงานจาก CEO: {d}\nโปรดำดำเนินการและรายงานผล"
        try:
            llm = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm[:200], "details": {"action": a, "llm_used": True, "full_response": llm}}
        except Exception as e:
            return {"status": "completed", "summary": f"Legal รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}
