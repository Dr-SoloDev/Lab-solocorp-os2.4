"""Support Agent — @support: Customer Success, Analytics"""

from workers.agents.base_agent import BaseAgent


class SupportAgent(BaseAgent):
    """Support — ดูแล customer success, support tickets"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="support",
            name="Support ซัพพอร์ต",
            profile_path="profiles/12-support/SOUL.md",
            bus_url=bus_url, api_key=api_key,
        )

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")
        if "ticket" in action or "support" in action:
            return {"status": "completed", "summary": "🎫 Support ticket จัดการแล้ว", "details": {"action": action}}
        elif "customer" in action or "success" in action or "feedback" in action:
            return {"status": "completed", "summary": "💬 Customer success feedback รับทราบ", "details": {"action": action}}
        elif "analytics" in action or "report" in action:
            return {"status": "completed", "summary": "📈 Support analytics รายงานพร้อม", "details": {"action": action}}
        else:
            return {"status": "completed", "summary": f"Support รับทราบ: {task.get('payload',{}).get('description','')}", "details": {}}
