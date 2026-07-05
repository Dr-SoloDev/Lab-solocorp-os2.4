"""
QA Agent Adapter — Test Planning & Quality Gate Validation

The QA adapter generates test plans, validates quality gates, and produces
structured test reports.  It is the final checkpoint before any deliverable
leaves a phase.
"""

from ..adapter import AgentAdapter, register


@register
class QAAdapter(AgentAdapter):
    """Test plan generation, quality gate validation, evidence collection."""

    agent_id = "qa"
    display_name = "QA"
    description = "Test plan generation, quality gate validation, evidence collection"

    def build_prompt(self, context: dict) -> str:
        """Build a QA / test-planning prompt.

        Expected context keys:
            - ``feature`` (str): Feature or deliverable description.
            - ``project_id`` (str, optional): Project identifier.
            - ``test_types`` (list[str], optional): Required test types
              (e.g. ``unit``, ``integration``, ``e2e``, ``security``).
            - ``guard_names`` (list[str], optional): Specific quality gates
              to validate.
        """
        feature = context.get("feature", "No feature description provided.")
        project_id = context.get("project_id", "unspecified")
        test_types = context.get("test_types", ["unit", "integration"])
        guards = context.get("guard_names", [])

        lines = [
            f"# QA Test Plan — Project [{project_id}]",
            "",
            "คุณคือหัวหน้าฝ่าย QA ของ SoloCorp OS",
            "คุณต้องสร้าง test plan และตรวจสอบ quality gates "
            "ก่อนปล่อย deliverable",
            "",
            f"## Feature / Deliverable",
            f"{feature}",
        ]

        if test_types:
            lines.extend([
                "",
                "## ประเภทการทดสอบที่ต้องการ",
                *[f"- {t}" for t in test_types],
            ])

        if guards:
            lines.extend([
                "",
                "## Quality Gates ที่ต้องตรวจ",
                *[f"- {g}" for g in guards],
            ])

        lines.extend([
            "",
            "## รูปแบบคำตอบ",
            "```",
            "test_cases: <รายการ test cases, comma-separated>",
            "coverage_areas: <พื้นที่ที่ครอบคลุม, comma-separated>",
            "gate_status: <pass|fail|partial>",
            "recommendation: <proceed|fix_before_merge|block>",
            "evidence_required: <สิ่งที่ต้องมีเป็นหลักฐาน, comma-separated>",
            "```",
        ])

        return "\n".join(lines)

    def parse_response(self, raw: str) -> dict:
        """Parse a QA response into a structured test plan / gate result.

        Returns:
            Dict with keys ``test_cases``, ``coverage_areas``, ``gate_status``,
            ``recommendation``, ``evidence_required``.
        """
        lines = raw.strip().splitlines()
        result: dict = {
            "test_cases": [],
            "coverage_areas": [],
            "gate_status": "",
            "recommendation": "",
            "evidence_required": [],
        }

        for line in lines:
            lower = line.strip().lower()

            if lower.startswith("test_cases:"):
                raw_cases = line.split(":", 1)[1].strip()
                result["test_cases"] = [c.strip() for c in raw_cases.split(",") if c.strip()]
            elif lower.startswith("coverage_areas:"):
                raw_areas = line.split(":", 1)[1].strip()
                result["coverage_areas"] = [a.strip() for a in raw_areas.split(",") if a.strip()]
            elif lower.startswith("gate_status:"):
                result["gate_status"] = line.split(":", 1)[1].strip().lower()
            elif lower.startswith("recommendation:"):
                result["recommendation"] = line.split(":", 1)[1].strip().lower()
            elif lower.startswith("evidence_required:"):
                raw_ev = line.split(":", 1)[1].strip()
                result["evidence_required"] = [e.strip() for e in raw_ev.split(",") if e.strip()]

        return result
