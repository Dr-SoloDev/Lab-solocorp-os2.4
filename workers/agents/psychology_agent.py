"""Psychology Agent — @psych-jit: Behavior, Behavioral Econ, Org Psych"""

from workers.agents.base_agent import BaseAgent


class PsychologyAgent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("psych-jit", "Psychology จิต", "profiles/18-psychology/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        d = task.get("payload", {}).get("description", "")
        action_map = {"behavior": f"Behavioral analysis: {d}\nโปรดำวิเคราะห์พฤติกรรม", "org": f"Org health: {d}\nโปรดำประเมินสุขภาพองค์กร", "user": f"User behavior: {d}\nโปรดำวิเคราะห์ผู้ใช้", "conflict": f"Conflict resolution: {d}\nโปรดำเสนอแนวทางแก้ไข"}
        prompt = None
        for k, v in action_map.items():
            if k in a:
                prompt = f"คุณคือ Psychology (จิต) ของ SoloCorp OS\n{v}"
                break
        if not prompt:
            prompt = f"คุณคือ Psychology (จิต) ของ SoloCorp OS\nได้รับงานจาก CEO: {d}\nโปรดำดำเนินการและรายงานผล"
        try:
            llm = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm[:200], "details": {"action": a, "llm_used": True, "full_response": llm}}
        except Exception as e:
            return {"status": "completed", "summary": f"Psychology รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}
