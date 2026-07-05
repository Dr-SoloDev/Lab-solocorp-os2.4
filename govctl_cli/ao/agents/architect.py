"""
Architect Agent Adapter — Architecture Review & ADR Validation

The Architect adapter handles architecture decision reviews, ADR validation,
RFC assessments, and design-system oversight — ensuring every change fits the
system's architectural integrity.
"""

from ..adapter import AgentAdapter, register


@register
class ArchitectAdapter(AgentAdapter):
    """Architecture review, ADR validation, RFC assessment, design-system oversight."""

    agent_id = "architect"
    display_name = "Architect"
    description = "Architecture review, ADR validation, RFC assessment"

    def build_prompt(self, context: dict) -> str:
        """Build an architecture review prompt.

        Expected context keys:
            - ``proposal`` (str): The architecture proposal or RFC abstract.
            - ``project_id`` (str, optional): Project identifier.
            - ``proposal_type`` (str, optional): ``adr`` | ``rfc`` | ``design``.
            - ``constraints`` (list[str], optional): Known constraints to evaluate.
        """
        proposal = context.get("proposal", "No proposal provided.")
        project_id = context.get("project_id", "unspecified")
        proposal_type = context.get("proposal_type", "rfc")
        constraints = context.get("constraints", [])

        lines = [
            f"# Architect Review — {proposal_type.upper()} — Project [{project_id}]",
            "",
            "คุณคือพี่ทรงศักดิ์ สถาปนิกของ SoloCorp OS ผู้รักษาความสมบูรณ์ของระบบ",
            "คุณต้องตรวจสอบ proposal นี้ก่อน approve เพื่อให้แน่ใจว่าไม่มี",
            "architecture debt, security hole, หรือ violation ของ ADR ที่มีอยู่",
            "",
            f"## Proposal ({proposal_type.upper()})",
            f"{proposal}",
        ]

        if constraints:
            lines.extend([
                "",
                "## Constraints ที่ต้องพิจารณา",
                *[f"- {c}" for c in constraints],
            ])

        lines.extend([
            "",
            "## รูปแบบคำตอบ",
            "```",
            "verdict: <approved|changes_requested|rejected>",
            "rationale: <เหตุผลทางสถาปัตยกรรม>",
            "concerns: <ข้อกังวล, comma-separated>",
            "adr_required: <yes|no>",
            "suggested_adr_title: <ถ้าต้องการ ADR ใหม่>",
            "```",
        ])

        return "\n".join(lines)

    def parse_response(self, raw: str) -> dict:
        """Parse an Architect response into a structured review verdict.

        Returns:
            Dict with keys ``verdict``, ``rationale``, ``concerns``,
            ``adr_required``, ``suggested_adr_title``.
        """
        lines = raw.strip().splitlines()
        result: dict = {
            "verdict": "",
            "rationale": "",
            "concerns": [],
            "adr_required": False,
            "suggested_adr_title": "",
        }

        for line in lines:
            lower = line.strip().lower()
            if lower.startswith("verdict:"):
                result["verdict"] = line.split(":", 1)[1].strip()
            elif lower.startswith("rationale:"):
                result["rationale"] = line.split(":", 1)[1].strip()
            elif lower.startswith("concerns:"):
                raw_concerns = line.split(":", 1)[1].strip()
                result["concerns"] = [c.strip() for c in raw_concerns.split(",") if c.strip()]
            elif lower.startswith("adr_required:"):
                val = line.split(":", 1)[1].strip().lower()
                result["adr_required"] = val in ("yes", "true", "y")
            elif lower.startswith("suggested_adr_title:"):
                result["suggested_adr_title"] = line.split(":", 1)[1].strip()

        return result
