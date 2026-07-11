"""UI Designer Agent — @ui-designer: Interface, Component Library"""

from workers.agents.base_agent import BaseAgent


class UIAgent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("ui-designer", "UI Designer", "profiles/09-ui-designer/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        d = task.get("payload", {}).get("description", "")
        action_map = {"ui": f"UI design: {d}\nโปรดำออกแบบ UI และรายงาน", "component": f"Component library: {d}\nโปรดำอัปเดต component", "prototype": f"Prototype: {d}\nโปรดำสร้าง prototype", "responsive": f"Responsive: {d}\nโปรดำออกแบบ responsive"}
        prompt = None
        for k, v in action_map.items():
            if k in a:
                prompt = f"คุณคือ UI Designer ของ SoloCorp OS\n{v}"
                break
        if not prompt:
            prompt = f"คุณคือ UI Designer ของ SoloCorp OS\nได้รับงานจาก CEO: {d}\nโปรดำดำเนินการและรายงานผล"
        try:
            llm = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm[:200], "details": {"action": a, "llm_used": True, "full_response": llm}}
        except Exception as e:
            return {"status": "completed", "summary": f"UI รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}
