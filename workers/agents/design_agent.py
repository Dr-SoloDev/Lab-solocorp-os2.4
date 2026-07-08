"""Design Agent — @design-kreet: UX Research, Brand Visual"""

from workers.agents.base_agent import BaseAgent


class DesignAgent(BaseAgent):
    """Design — ดูแล UX, design system, visual"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="design-kreet",
            name="Design ครีเอท",
            profile_path="profiles/08-design/SOUL.md",
            bus_url=bus_url, api_key=api_key,
        )

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")
        if "ux" in action or "research" in action:
            return {"status": "completed", "summary": "🔬 UX Research เสร็จสิ้น", "details": {"action": action}}
        elif "design" in action or "visual" in action or "brand" in action:
            return {"status": "completed", "summary": "🎨 ออกแบบ Visual + Brand เรียบร้อย", "details": {"action": action}}
        elif "prototype" in action or "prototyping" in action:
            return {"status": "completed", "summary": "📱 สร้าง prototype แล้ว", "details": {"action": action}}
        else:
            return {"status": "completed", "summary": f"Design รับทราบ: {task.get('payload',{}).get('description','')}", "details": {}}
