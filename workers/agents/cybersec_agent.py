"""CyberSec Agent — @cybersec-sai: Threat Detection, Vulnerability, IR"""

from workers.agents.base_agent import BaseAgent


class CyberSecAgent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("cybersec-sai", "CyberSec ซาย", "profiles/17-cybersec/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        d = task.get("payload", {}).get("description", "")
        action_map = {"threat": f"Threat assessment: {d}\nโปรดำประเมินภัยคุกคาม", "vulnerability": f"Vulnerability scan: {d}\nโปรดำตรวจสอบช่องโหว่", "incident": f"Incident response: {d}\nโปรดำวางแผนรับมือ", "audit": f"Security audit: {d}\nโปรดำตรวจสอบความปลอดภัย"}
        prompt = None
        for k, v in action_map.items():
            if k in a:
                prompt = f"คุณคือ CyberSec (ซาย) ของ SoloCorp OS\n{v}"
                break
        if not prompt:
            prompt = f"คุณคือ CyberSec (ซาย) ของ SoloCorp OS\nได้รับงานจาก CEO: {d}\nโปรดำดำเนินการและรายงานผล"
        try:
            llm = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm[:200], "details": {"action": a, "llm_used": True, "full_response": llm}}
        except Exception as e:
            return {"status": "completed", "summary": f"CyberSec รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}
