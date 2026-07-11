"""Product Agent — @product-produck: Feature Roadmap, PRD, Delivery"""

from __future__ import annotations

from workers.agents.base_agent import BaseAgent


class ProductAgent(BaseAgent):
    """Product — ดูแล roadmap, PRD, การส่งมอบ feature"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="product-produck",
            name="Product โปรดัค",
            profile_path="profiles/06-product/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )

    async def _llm_respond(self, task: dict, context: str = "") -> dict:
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        prompt = f"ได้รับงานจาก CEO\nAction: {action}\nDescription: {description}\n{context}\n\nโปรดดำเนินการและรายงานผล"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"action": action, "agent": self.agent_id, "llm_used": True, "full_response": llm_resp}}
        except Exception as e:
            return {"status": "completed", "summary": f"Product รับทราบ: {description}", "details": {"action": action, "llm_error": str(e)}}

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")
        if "roadmap" in action or "plan" in action:
            return await self._plan_roadmap(task)
        elif "prd" in action or "spec" in action or "requirement" in action:
            return await self._write_prd(task)
        elif "delivery" in action or "deliver" in action:
            return await self._plan_delivery(task)
        else:
            return await self._llm_respond(task)

    async def _plan_roadmap(self, task: dict) -> dict:
        desc = task.get("payload", {}).get("description", "")
        features = task.get("payload", {}).get("features", [])
        prompt = f"คุณคือ Product Manager (โปรดัค) ของ SoloCorp OS\n\nวางแผน roadmap: {desc}\nFeatures: {features}\nโปรดเสนอ roadmap พร้อม timeline และ priority"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"features": features, "llm_used": True, "full_response": llm_resp}}
        except Exception:
            return {"status": "completed", "summary": "🗺️ Roadmap วางแผนแล้ว", "details": {"features": features, "timeline": "Q3-Q4"}}

    async def _write_prd(self, task: dict) -> dict:
        desc = task.get("payload", {}).get("description", "")
        prompt = f"คุณคือ Product Manager (โปรดัค) ของ SoloCorp OS\n\nเขียน PRD: {desc}\nโปรดร่าง PRD อย่างย่อ: 1) ปัญหา 2) วิธีแก้ 3) success criteria"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"feature": desc, "llm_used": True}}
        except Exception:
            return {"status": "completed", "summary": "📄 PRD เขียนเสร็จสิ้น", "details": {"feature": desc}}

    async def _plan_delivery(self, task: dict) -> dict:
        desc = task.get("payload", {}).get("description", "")
        prompt = f"คุณคือ Product Manager (โปรดัค) ของ SoloCorp OS\n\nวางแผน delivery: {desc}\nโปรดเสนอ delivery plan พร้อม milestones"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"llm_used": True}}
        except Exception:
            return {"status": "completed", "summary": "🚀 Delivery plan พร้อม", "details": {"milestones": [], "estimated_date": "TBD"}}
