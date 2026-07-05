"""
CEO Agent Adapter — Strategic Decision Making

The CEO adapter handles high-level strategic decisions, vision alignment,
and final authority calls that cascade to all departments.
"""

from ..adapter import AgentAdapter, register


@register
class CEOAdapter(AgentAdapter):
    """Strategic decision-making — top-level vision, final authority, escalation sink."""

    agent_id = "ceo"
    display_name = "CEO (ซีอีโอ)"
    description = "Strategic decisions, vision alignment, final authority"

    def build_prompt(self, context: dict) -> str:
        """Build a CEO-level strategic decision prompt.

        Expected context keys:
            - ``question`` (str): The strategic question to decide.
            - ``project_id`` (str, optional): Project identifier.
            - ``options`` (list[str], optional): Decision options to choose from.
            - ``impact_summary`` (str, optional): Known impact / trade-offs.
        """
        question = context.get("question") or context.get("task", "No question provided.")
        project_id = context.get("project_id", "unspecified")
        options = context.get("options", [])
        impact = context.get("impact_summary", "")

        lines = [
            f"# CEO Strategic Decision — Project [{project_id}]",
            "",
            "คุณคือ CEO ของ SoloCorp OS ผู้มีวิสัยทัศน์และอำนาจตัดสินใจสูงสุด",
            "คุณต้องตอบคำถามเชิงกลยุทธ์นี้โดยคำนึงถึงภาพรวมขององค์กรทั้งหมด",
            "",
            f"## คำถาม",
            f"{question}",
        ]

        if options:
            lines.extend([
                "",
                "## ตัวเลือกที่มี",
                *[f"- {i+1}. {opt}" for i, opt in enumerate(options)],
            ])

        if impact:
            lines.extend([
                "",
                "## ผลกระทบที่ทราบ",
                impact,
            ])

        lines.extend([
            "",
            "## รูปแบบคำตอบ",
            "```",
            "decision: <ตัวเลือกที่เลือก>",
            "rationale: <เหตุผลเชิงกลยุทธ์>",
            "risks: <ความเสี่ยงที่ต้อง monitor>",
            "confidence: <high|medium|low>",
            "```",
        ])

        return "\n".join(lines)

    def parse_response(self, raw: str) -> dict:
        """Parse a CEO agent response into structured decision fields.

        Expected format:
            decision: ...
            rationale: ...
            risks: ...
            confidence: high|medium|low

        Returns:
            Dict with keys ``decision``, ``rationale``, ``risks``,
            ``confidence``.
        """
        lines = raw.strip().splitlines()
        result: dict = {
            "decision": "",
            "rationale": "",
            "risks": "",
            "confidence": "medium",
        }

        for line in lines:
            lower = line.strip().lower()

            if lower.startswith("decision:"):
                result["decision"] = line.split(":", 1)[1].strip()
            elif lower.startswith("rationale:"):
                result["rationale"] = line.split(":", 1)[1].strip()
            elif lower.startswith("risks:"):
                result["risks"] = line.split(":", 1)[1].strip()
            elif lower.startswith("confidence:"):
                val = line.split(":", 1)[1].strip().lower()
                if val in ("high", "medium", "low"):
                    result["confidence"] = val

        return result
