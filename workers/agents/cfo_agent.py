"""CFO Agent — @meetoo: Finance, Budget, Investment (พลัง LLM)"""

from __future__ import annotations

import json

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
        """Execute CFO tasks ด้วยพลัง LLM"""
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        params = payload.get("params", {})

        # ให้ LLM คิดและตอบตามบทบาท
        prompt_parts = [f"ได้รับงานจาก CEO:"]
        if description:
            prompt_parts.append(f"คำอธิบาย: {description}")
        prompt_parts.append(f"action: {action}")
        if params:
            prompt_parts.append(f"parameters: {json.dumps(params, ensure_ascii=False)}")
        prompt_parts.append(f"\nโปรดดำเนินการและรายงานผล")

        llm_response = await self.think("\n".join(prompt_parts), max_tokens=400)

        return {
            "status": "completed",
            "summary": llm_response[:200],
            "details": {
                "action": action,
                "agent": self.agent_id,
                "llm_used": True,
                "full_response": llm_response,
            },
        }
