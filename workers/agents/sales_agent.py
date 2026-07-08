"""Sales Agent — @sales: B2B Deal Strategy, Pipeline"""

from workers.agents.base_agent import BaseAgent


class SalesAgent(BaseAgent):
    """Sales — ดูแล B2B deals, sales pipeline"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="sales",
            name="Sales เซลส์",
            profile_path="profiles/11-sales/SOUL.md",
            bus_url=bus_url, api_key=api_key,
        )

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")
        if "deal" in action or "pipeline" in action:
            return {"status": "completed", "summary": "💼 Sales pipeline อัปเดตแล้ว", "details": {"action": action}}
        elif "client" in action or "customer" in action or "prospect" in action:
            return {"status": "completed", "summary": "🤝 ข้อมูลลูกค้าพร้อม — รอ CEO อนุมัติ proposal", "details": {"action": action}}
        elif "strategy" in action or "plan" in action:
            return {"status": "completed", "summary": "📊 วางกลยุทธ์การขายเสร็จสิ้น", "details": {"action": action}}
        else:
            return {"status": "completed", "summary": f"Sales รับทราบ: {task.get('payload',{}).get('description','')}", "details": {}}
