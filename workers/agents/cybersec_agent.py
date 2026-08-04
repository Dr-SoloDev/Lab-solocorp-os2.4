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

    # Rule-based playbook per severity — fallback เมื่อ LLM ไม่พร้อม
    PLAYBOOKS = {
        "critical": {
            "response": "INCIDENT RESPONSE: isolate affected systems, revoke credentials, preserve evidence, notify CEO + CTO immediately, begin forensics",
            "action": "escalate_incident",
            "sla": "15 min",
        },
        "high": {
            "response": "Patch/contain the exploited surface, rotate keys, deploy monitoring rules, report within 1h",
            "action": "contain_and_patch",
            "sla": "1 hour",
        },
        "medium": {
            "response": "Investigate anomaly, correlate logs, validate threat, update threat intel",
            "action": "investigate",
            "sla": "4 hours",
        },
        "low": {
            "response": "Log observation, monitor trend, include in weekly security review",
            "action": "log_and_monitor",
            "sla": "24 hours",
        },
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

    @staticmethod
    def _llm_usable(result: str) -> bool:
        """LLM output ใช้ได้ไหม — filter empty/failure จาก llm_provider"""
        return bool(result and not result.startswith("⚠️ LLM ไม่พร้อม"))

    def _playbook_fallback(self, severity: str, description: str, action: str) -> dict:
        """Rule-based fallback — ให้ผลงานจริงแม้ LLM ล้ม"""
        pb = self.PLAYBOOKS.get(severity, self.PLAYBOOKS["low"])
        return {
            "status": "completed",
            "summary": f"[{severity.upper()}] {pb['response']} — จาก: {description[:150]}",
            "details": {
                "action": action,
                "severity": severity,
                "agent": self.agent_id,
                "llm_used": False,
                "fallback": "playbook",
                "playbook_action": pb["action"],
                "sla": pb["sla"],
            },
        }

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
            if not self._llm_usable(llm_response):
                return self._playbook_fallback(severity, description, action)
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
            return self._playbook_fallback(severity, description, action)
