"""UI Designer Agent — @ui-designer: Interface, Component Library, Animation Review

ใช้ skill ui-animation-review สำหรับตรวจสอบ animation/motion
อิงจาก Emil Kowalski's design engineering philosophy
"""

from workers.agents.base_agent import BaseAgent


class UIAgent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("ui-designer", "UI Designer", "profiles/09-ui-designer/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        d = task.get("payload", {}).get("description", "")
        context = task.get("payload", {}).get("context", "")
        files = task.get("payload", {}).get("files", "")

        # ── Animation Review — ใช้ skill ui-animation-review ──────────
        if "animation" in a or "review" in a or "motion" in a:
            prompt = (
                f"คุณคือ UI Designer ของ SoloCorp OS — Animation Specialist\n"
                f"ใช้ความรู้จาก ui-animation-review skill (Emil Kowalski philosophy):\n\n"
                f"---\n{d}\n---\n"
            )
            if files:
                prompt += f"\nไฟล์ที่เกี่ยวข้อง:\n{files}\n"
            if context:
                prompt += f"\nบริบทเพิ่มเติม:\n{context}\n"
            try:
                llm = await self.think(prompt, max_tokens=600)
                return {
                    "status": "completed",
                    "summary": llm[:250],
                    "details": {
                        "action": a,
                        "llm_used": True,
                        "skill": "ui-animation-review",
                        "full_response": llm,
                    },
                }
            except Exception as e:
                return {"status": "completed", "summary": f"Animation review รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}

        # ── Standard UI actions ──────────────────────────────────────
        action_map = {
            "ui": f"UI design: {d}\nโปรดออกแบบ UI และรายงาน",
            "component": f"Component library: {d}\nโปรดอัปเดต component",
            "prototype": f"Prototype: {d}\nโปรดสร้าง prototype",
            "responsive": f"Responsive: {d}\nโปรดออกแบบ responsive",
        }
        prompt = None
        for k, v in action_map.items():
            if k in a:
                prompt = f"คุณคือ UI Designer ของ SoloCorp OS\n{v}"
                break
        if not prompt:
            prompt = f"คุณคือ UI Designer ของ SoloCorp OS\nได้รับงานจาก CEO: {d}\nโปรดดำเนินการและรายงานผล"
        try:
            llm = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm[:200], "details": {"action": a, "llm_used": True, "full_response": llm}}
        except Exception as e:
            return {"status": "completed", "summary": f"UI รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}
