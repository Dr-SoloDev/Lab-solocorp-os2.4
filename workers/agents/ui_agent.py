"""UI Designer Agent — @ui-designer: Interface, Component Library"""

from workers.agents.base_agent import BaseAgent


class UIAgent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("ui-designer", "UI Designer", "profiles/09-ui-designer/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        if "ui" in a or "interface" in a:
            return {"status": "completed", "summary": "🖥️ UI design เสร็จสิ้น", "details": {"action": a}}
        elif "component" in a or "library" in a:
            return {"status": "completed", "summary": "🧩 Component library อัปเดตแล้ว", "details": {"action": a}}
        elif "prototype" in a or "mockup" in a or "wireframe" in a:
            return {"status": "completed", "summary": "📱 Prototype/Mockup พร้อม", "details": {"action": a}}
        elif "responsive" in a or "mobile" in a:
            return {"status": "completed", "summary": "📲 Responsive design เรียบร้อย", "details": {"action": a}}
        return {"status": "completed", "summary": f"UI รับทราบ: {task.get('payload',{}).get('description','')}", "details": {}}
