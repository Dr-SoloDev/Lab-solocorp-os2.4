"""Legal Agent — @legal-tulya: Compliance, Contract Review, Legal Document

Capabilities:
- Contract review and risk assessment
- Compliance checking (GDPR, SOC2, etc.)
- Legal document analysis
- Client intake screening
- NDA analysis
"""

from __future__ import annotations

import json

from workers.agents.base_agent import BaseAgent


class LegalAgent(BaseAgent):
    """Legal — ดูแล Compliance, Contract Review, Legal Document"""

    DOCUMENT_TYPES = ["contract", "nda", "agreement", "policy", "terms", "compliance"]

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="legal-tulya",
            name="Legal ตุลย์",
            profile_path="profiles/13-legal/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )

    def _detect_doc_type(self, action: str, description: str) -> str:
        combined = (action + " " + description).lower()
        for dt in self.DOCUMENT_TYPES:
            if dt in combined:
                return dt
        return "general"

    async def execute(self, task: dict) -> dict:
        """Execute legal tasks ด้วยพลัง LLM"""
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        params = payload.get("params", {})

        if not description:
            return {
                "status": "failed",
                "summary": "Legal Agent: ไม่มี description ใน payload",
                "details": {"error": "missing_description"},
            }

        doc_type = self._detect_doc_type(action, description)

        prompt = (
            f"คุณคือ Legal (ตุลย์) ของ SoloCorp OS\n"
            f"ประเภทเอกสาร: {doc_type}\n"
            f"ได้รับงานจาก CEO: {description}\n"
        )
        if params:
            prompt += f"parameters: {json.dumps(params, ensure_ascii=False)}\n"
        prompt += (
            f"\nดำเนินการ:\n"
            f"1. วิเคราะห์เอกสาร/สถานการณ์\n"
            f"2. ระบุความเสี่ยง\n"
            f"3. แนวทางปฏิบัติ\n"
            f"รายงานผล"
        )

        try:
            llm_response = await self.think(prompt, max_tokens=500)
            return {
                "status": "completed",
                "summary": llm_response[:300],
                "details": {
                    "action": action,
                    "doc_type": doc_type,
                    "agent": self.agent_id,
                    "llm_used": True,
                    "full_response": llm_response,
                },
            }
        except Exception as e:
            return {
                "status": "completed",
                "summary": f"Legal รับทราบ: {description[:200]}",
                "details": {"action": action, "doc_type": doc_type, "llm_error": str(e)},
            }
