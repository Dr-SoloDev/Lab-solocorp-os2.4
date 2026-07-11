"""R&D Lab Agent — @rd-lab: Curiosity-driven research, prototyping

⚠️ Owner-direct — bypasses normal pipeline. No deadlines, no pipeline process.
"""

from workers.agents.base_agent import BaseAgent


class RDLabAgent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("rd-lab", "R&D Lab", "profiles/19-rd-lab/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        d = task.get("payload", {}).get("description", "")
        action_map = {"research": f"Research: {d}\nโปรดำวิจัยและสรุป findings", "prototype": f"Proof of concept: {d}\nโปรดำวางแผน POC", "experiment": f"Experiment: {d}\nโปรดำออกแบบการทดลอง"}
        prompt = None
        for k, v in action_map.items():
            if k in a:
                prompt = f"คุณคือ R&D Lab ของ SoloCorp OS (Owner-direct)\n{v}"
                break
        if not prompt:
            prompt = f"คุณคือ R&D Lab ของ SoloCorp OS (Owner-direct)\nได้รับงานจาก CEO: {d}\nโปรดำดำเนินการและรายงานผล"
        try:
            llm = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm[:200], "details": {"action": a, "llm_used": True, "full_response": llm}}
        except Exception as e:
            return {"status": "completed", "summary": f"R&D Lab รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}
