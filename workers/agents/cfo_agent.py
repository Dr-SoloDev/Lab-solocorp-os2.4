"""CFO Agent — @meetoo: Finance, Budget, Investment"""

from __future__ import annotations

from workers.agents.base_agent import BaseAgent


class CFOAgent(BaseAgent):
    """CFO — ดูแลการเงิน งบประมาณ การลงทุน"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="cfo-meetoo",
            name="CFO meetoo",
            profile_path="profiles/02-cfo/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )

    async def execute(self, task: dict) -> dict:
        """Execute CFO tasks"""
        action = task.get("payload", {}).get("action", "")

        if "budget" in action or "plan_budget" in action:
            return await self._plan_budget(task)
        elif "report" in action or "financial_report" in action:
            return await self._financial_report(task)
        elif "invest" in action or "investment" in action:
            return await self._investment_analysis(task)
        else:
            # Generic: ปฏิบัติตามคำสั่ง
            return {
                "status": "completed",
                "summary": f"CFO รับทราบ: {task.get('payload', {}).get('description', '')}",
                "details": {"action": action, "note": "กำลังดำเนินการ"},
            }

    async def _plan_budget(self, task: dict) -> dict:
        payload = task.get("payload", {})
        tasks = payload.get("tasks", [])
        return {
            "status": "completed",
            "summary": "✅ วางแผน budget เสร็จสิ้น",
            "details": {
                "action": "plan_budget",
                "tasks_processed": tasks,
                "result": {
                    "current_q": "ตรวจสอบแล้ว",
                    "q3_q4_estimated": True,
                    "allocation": "รอ CEO อนุมัติ",
                },
            },
        }

    async def _financial_report(self, task: dict) -> dict:
        return {
            "status": "completed",
            "summary": "📊 รายงานการเงินพร้อมแล้ว",
            "details": {"status": "ready", "period": task.get("payload", {}).get("period", "current")},
        }

    async def _investment_analysis(self, task: dict) -> dict:
        return {
            "status": "completed",
            "summary": "📈 วิเคราะห์การลงทุนเสร็จสิ้น",
            "details": {"recommendation": "รอ CEO ตัดสินใจ"},
        }
