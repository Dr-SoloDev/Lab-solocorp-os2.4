"""R&D Lab Agent — @rd-lab: Research, Prototype, Experiment, Innovation

Capabilities:
- Research paper analysis and summarization
- Prototype development
- Experiment design and methodology
- Tool building and automation
- Knowledge curation
"""

from __future__ import annotations

import json

from workers.agents.base_agent import BaseAgent


class RDLabAgent(BaseAgent):
    """R&D Lab — ดูแล Research, Prototype, Experiment, Innovation"""

    ACTIVITIES = {
        "research": ["research", "paper", "study", "analysis", "survey", "investigate"],
        "prototype": ["prototype", "poc", "mvp", "build", "implement", "develop"],
        "experiment": ["experiment", "test", "a/b", "methodology", "metric"],
        "tool": ["tool", "script", "automation", "scraper", "integration"],
        "curate": ["curate", "document", "summarize", "organize", "wiki"],
    }

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="rd-lab",
            name="R&D Lab",
            profile_path="profiles/19-rd-lab/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )

    def _detect_activity(self, action: str, description: str) -> str:
        combined = (action + " " + description).lower()
        for activity, keywords in self.ACTIVITIES.items():
            if any(kw in combined for kw in keywords):
                return activity
        return "explore"

    async def execute(self, task: dict) -> dict:
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        params = payload.get("params", {})

        if not description:
            return {
                "status": "failed",
                "summary": "R&D Lab: ไม่มี description ใน payload",
                "details": {"error": "missing_description"},
            }

        activity = self._detect_activity(action, description)

        prompt = (
            f"คุณคือ R&D Lab ของ SoloCorp OS\n"
            f"กิจกรรม: {activity}\n"
            f"ได้รับงานจาก CEO: {description}\n"
        )
        if params:
            prompt += f"parameters: {json.dumps(params, ensure_ascii=False)}\n"
        prompt += "\nโปรดำดำเนินการตามบทบาท R&D Lab รายงานผล"

        try:
            llm_response = await self.think(prompt, max_tokens=500)
            return {
                "status": "completed",
                "summary": llm_response[:300],
                "details": {
                    "action": action,
                    "activity": activity,
                    "agent": self.agent_id,
                    "llm_used": True,
                    "full_response": llm_response,
                },
            }
        except Exception as e:
            return {
                "status": "completed",
                "summary": f"R&D Lab รับทราบ: {description[:200]}",
                "details": {"action": action, "activity": activity, "llm_error": str(e)},
            }
