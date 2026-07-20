"""Cyber Security Agent — @cybersec-sai: Threat Detection, Incident Response, Security

Capabilities:
- Threat analysis and classification
- Incident response coordination
- Vulnerability assessment
- Security compliance checking
- Red team coordination
"""

from __future__ import annotations

import json

from workers.agents.base_agent import BaseAgent


class CyberSecAgent(BaseAgent):
    """Cyber Security — ดูแล Threat Detection, Vulnerability, Incident Response"""

    SEVERITY_KEYWORDS = {
        "critical": ["critical", "breach", "ransomware", "data leak", "cve-"],
        "high": ["exploit", "vulnerability", "intrusion", "malware"],
        "medium": ["scan", "suspicious", "anomaly", "warning"],
        "low": ["info", "notice", "observation"],
    }

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="cybersec-sai",
            name="CyberSec ซาย",
            profile_path="profiles/17-cybersec/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )

    def _classify_severity(self, description: str) -> str:
        desc_lower = description.lower()
        for sev, keywords in self.SEVERITY_KEYWORDS.items():
            if any(kw in desc_lower for kw in keywords):
                return sev
        return "low"

    async def execute(self, task: dict) -> dict:
        """Execute security tasks ด้วยพลัง LLM"""
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        params = payload.get("params", {})

        if not description:
            return {
                "status": "failed",
                "summary": "CyberSec Agent: ไม่มี description ใน payload",
                "details": {"error": "missing_description"},
            }

        severity = self._classify_severity(description)

        prompt = (
            f"คุณคือ Cyber Security (ซาย) ของ SoloCorp OS\n"
            f"ระดับความรุนแรง: {severity.upper()}\n"
            f"ได้รับงานจาก CEO: {description}\n"
        )
        if params:
            prompt += f"parameters: {json.dumps(params, ensure_ascii=False)}\n"
        prompt += (
            f"\nวิเคราะห์และดำเนินการ:\n"
            f"1. ระบุ threat/intent\n"
            f"2. แนวทางการตอบสนอง\n"
            f"3. มาตรการป้องกัน\n"
            f"รายงานผล"
        )

        try:
            llm_response = await self.think(prompt, max_tokens=500)
            return {
                "status": "completed",
                "summary": llm_response[:300],
                "details": {
                    "action": action,
                    "severity": severity,
                    "agent": self.agent_id,
                    "llm_used": True,
                    "full_response": llm_response,
                },
            }
        except Exception as e:
            return {
                "status": "completed",
                "summary": f"{severity.upper()}: รับทราบ {description[:200]}",
                "details": {"action": action, "severity": severity, "llm_error": str(e)},
            }
