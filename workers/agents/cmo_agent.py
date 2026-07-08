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

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")
        if "campaign" in action or "marketing" in action:
            return {"status": "completed", "summary": "📢 แคมเปญการตลาดวางแผนแล้ว", "details": {"action": action}}
        elif "content" in action or "brand" in action:
            return {"status": "completed", "summary": "✍️ วางกลยุทธ์คอนเทนต์+แบรนด์แล้ว", "details": {"action": action}}
        else:
            return {"status": "completed", "summary": f"CMO รับทราบ: {task.get('payload',{}).get('description','')}", "details": {}}
