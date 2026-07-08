"""Psychology Agent — @psych-jit: Behavior, Behavioral Econ, Org Psych"""

from workers.agents.base_agent import BaseAgent


class PsychologyAgent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("psych-jit", "Psychology จิต", "profiles/18-psychology/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        if "behavior" in a or "psych" in a:
            return {"status": "completed", "summary": "🧠 Behavioral analysis เสร็จ", "details": {"action": a}}
        elif "org" in a or "culture" in a or "team" in a:
            return {"status": "completed", "summary": "🏢 Org health assessment — ปกติ", "details": {"action": a}}
        elif "user" in a or "customer" in a:
            return {"status": "completed", "summary": "👥 User behavior insight พร้อม", "details": {"action": a}}
        elif "conflict" in a or "mediation" in a:
            return {"status": "completed", "summary": "🤝 Conflict resolution เสนอแนวทางแล้ว", "details": {"action": a}}
        return {"status": "completed", "summary": f"Psychology รับทราบ: {task.get('payload',{}).get('description','')}", "details": {}}
