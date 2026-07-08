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

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")

        if "roadmap" in action or "plan" in action:
            return await self._plan_roadmap(task)
        elif "prd" in action or "spec" in action or "requirement" in action:
            return await self._write_prd(task)
        elif "delivery" in action or "deliver" in action:
            return await self._plan_delivery(task)
        else:
            return {"status": "completed", "summary": f"Product รับทราบ: {task.get('payload', {}).get('description', '')}", "details": {}}

    async def _plan_roadmap(self, task: dict) -> dict:
        return {
            "status": "completed",
            "summary": "🗺️ Roadmap วางแผนแล้ว",
            "details": {
                "features": task.get("payload", {}).get("features", []),
                "timeline": "Q3-Q4",
                "priority": task.get("priority", "normal"),
            },
        }

    async def _write_prd(self, task: dict) -> dict:
        return {
            "status": "completed",
            "summary": "📄 PRD เขียนเสร็จสิ้น",
            "details": {
                "feature": task.get("payload", {}).get("description", ""),
                "status": "พร้อมให้ Engineering implement",
            },
        }

    async def _plan_delivery(self, task: dict) -> dict:
        return {
            "status": "completed",
            "summary": "🚀 Delivery plan พร้อม",
            "details": {"milestones": [], "estimated_date": "TBD"},
        }
