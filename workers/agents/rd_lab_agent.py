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

    # Output structure ต่อ activity — enforcement รูปแบบผลงาน
    ACTIVITY_OUTPUTS = {
        "research": "research question + method + sources + next steps",
        "prototype": "goal + tech stack + scope + success criteria",
        "experiment": "hypothesis + metrics + sample + evaluation plan",
        "tool": "purpose + inputs + outputs + integration points",
        "curate": "topic + key findings + tags + reference links",
        "explore": "idea + feasibility + risks + recommended action",
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

        @staticmethod
        def _llm_usable(result: str) -> bool:
            return bool(result and not result.startswith("⚠️ LLM ไม่พร้อม"))

        def _output_fallback(activity: str, description: str, action: str) -> dict:
            """Rule-based fallback — output structure ตาม activity แม้ LLM ล้ม"""
            structure = self.ACTIVITY_OUTPUTS.get(activity, self.ACTIVITY_OUTPUTS["explore"])
            return {
                "status": "completed",
                "summary": f"[{activity.upper()}] output: {structure} — จาก: {description[:150]}",
                "details": {
                    "action": action,
                    "activity": activity,
                    "agent": self.agent_id,
                    "llm_used": False,
                    "fallback": "activity_output",
                    "output_structure": structure,
                },
            }

        try:
            llm_response = await self.think(prompt, max_tokens=500)
            if not _llm_usable(llm_response):
                return _output_fallback(activity, description, action)
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
            return _output_fallback(activity, description, action)
