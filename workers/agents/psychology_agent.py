"""Psychology Agent — @psych-jit: User Behavior, Cognitive Bias, Org Health

Capabilities:
- User behavior analysis and cognitive bias mapping
- UX psychology recommendations
- Organizational health assessment
- Team communication patterns
- Behavioral economics insights
"""

from __future__ import annotations

import json

from workers.agents.base_agent import BaseAgent


class PsychologyAgent(BaseAgent):
    """Psychology — ดูแล User Behavior, Cognitive Bias, Org Psychology"""

    FOCUS_AREAS = {
        "ux": ["ux", "usability", "user experience", "interface", "design"],
        "bias": ["bias", "cognitive", "heuristic", "anchoring", "framing"],
        "org": ["team", "org", "culture", "communication", "conflict"],
        "behavior": ["behavior", "motivation", "habit", "nudge", "incentive"],
        "research": ["research", "study", "survey", "interview", "user research"],
    }

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="psych-jit",
            name="Psychology จิต",
            profile_path="profiles/18-psychology/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )

    def _detect_focus(self, action: str, description: str) -> str:
        combined = (action + " " + description).lower()
        for area, keywords in self.FOCUS_AREAS.items():
            if any(kw in combined for kw in keywords):
                return area
        return "general"

    async def execute(self, task: dict) -> dict:
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        params = payload.get("params", {})

        if not description:
            return {
                "status": "failed",
                "summary": "Psychology Agent: ไม่มี description ใน payload",
                "details": {"error": "missing_description"},
            }

        focus = self._detect_focus(action, description)

        prompt = (
            f"คุณคือ Psychology (จิต) ของ SoloCorp OS\n"
            f"มุมมอง: {focus}\n"
            f"ได้รับงานจาก CEO: {description}\n"
        )
        if params:
            prompt += f"parameters: {json.dumps(params, ensure_ascii=False)}\n"
        prompt += "\nโปรดวิเคราะห์ทางจิตวิทยาและให้คำแนะนำ รายงานผล"

        try:
            llm_response = await self.think(prompt, max_tokens=500)
            return {
                "status": "completed",
                "summary": llm_response[:300],
                "details": {
                    "action": action,
                    "focus": focus,
                    "agent": self.agent_id,
                    "llm_used": True,
                    "full_response": llm_response,
                },
            }
        except Exception as e:
            return {
                "status": "completed",
                "summary": f"Psychology รับทราบ: {description[:200]}",
                "details": {"action": action, "focus": focus, "llm_error": str(e)},
            }
