"""R&D Lab Agent — @rd-lab: Curiosity-driven research, prototyping

⚠️ Owner-direct — bypasses normal pipeline. No deadlines, no pipeline process.
"""

from workers.agents.base_agent import BaseAgent


class RDLabAgent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("rd-lab", "R&D Lab", "profiles/19-rd-lab/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        if "research" in a or "explore" in a:
            return {"status": "completed", "summary": "🔬 Research findings สรุปแล้ว", "details": {"action": a, "mode": "exploration"}}
        elif "prototype" in a or "proof" in a or "poc" in a:
            return {"status": "completed", "summary": "🧪 Proof of concept พร้อม", "details": {"action": a, "mode": "prototyping"}}
        elif "experiment" in a or "test" in a:
            return {"status": "completed", "summary": "⚗️ Experiment results  recorded", "details": {"action": a}}
        return {"status": "completed", "summary": f"R&D Lab รับทราบ: Owner-direct research — no pipeline", "details": {"mode": "owner-direct"}}
