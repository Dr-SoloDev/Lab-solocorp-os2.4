"""
Engineering Agent Adapter — Technical Implementation & Sprint Planning

The Engineering adapter handles technical implementation planning, sprint task
decomposition, code-review guidance, and execution tracking for all engineering
work across the system.
"""

from ..adapter import AgentAdapter, register


@register
class EngineeringAdapter(AgentAdapter):
    """Technical implementation planning, sprint decomposition, code execution."""

    agent_id = "engineering"
    display_name = "Engineering"
    description = "Technical implementation, sprint planning, code quality"

    def build_prompt(self, context: dict) -> str:
        """Build an engineering implementation prompt.

        Expected context keys:
            - ``task`` (str): Technical task description.
            - ``project_id`` (str, optional): Project identifier.
            - ``tech_stack`` (list[str], optional): Technologies involved.
            - ``acceptance_criteria`` (list[str], optional): Acceptance criteria
              the implementation must satisfy.
        """
        task = context.get("task", "No task provided.")
        project_id = context.get("project_id", "unspecified")
        tech_stack = context.get("tech_stack", [])
        criteria = context.get("acceptance_criteria", [])

        lines = [
            f"# Engineering Implementation Plan — Project [{project_id}]",
            "",
            "คุณคือช่างฟูล หัวหน้าฝ่ายวิศวกรรมของ SoloCorp OS",
            "คุณต้องวางแผนการ implement, แบ่งงานเป็น sprint tasks, "
            "และกำหนด technical approach",
            "",
            f"## งานที่จะ implement",
            f"{task}",
        ]

        if tech_stack:
            lines.extend([
                "",
                "## เทคโนโลยีที่เกี่ยวข้อง",
                *[f"- {t}" for t in tech_stack],
            ])

        if criteria:
            lines.extend([
                "",
                "## Acceptance Criteria",
                *[f"- {c}" for c in criteria],
            ])

        lines.extend([
            "",
            "## รูปแบบคำตอบ",
            "```",
            "approach: <แนวทางทางเทคนิค>",
            "tasks: <รายการงานย่อย, comma-separated>",
            "estimated_hours: <ชั่วโมงโดยประมาณ>",
            "dependencies: <สิ่งที่ต้องมีก่อน, comma-separated>",
            "risks: <ความเสี่ยงทางเทคนิค, comma-separated>",
            "```",
        ])

        return "\n".join(lines)

    def parse_response(self, raw: str) -> dict:
        """Parse an Engineering response into implementation plan fields.

        Returns:
            Dict with keys ``approach``, ``tasks``, ``estimated_hours``,
            ``dependencies``, ``risks``.
        """
        lines = raw.strip().splitlines()
        result: dict = {
            "approach": "",
            "tasks": [],
            "estimated_hours": "",
            "dependencies": [],
            "risks": [],
        }

        for line in lines:
            lower = line.strip().lower()

            if lower.startswith("approach:"):
                result["approach"] = line.split(":", 1)[1].strip()
            elif lower.startswith("tasks:"):
                raw_tasks = line.split(":", 1)[1].strip()
                result["tasks"] = [t.strip() for t in raw_tasks.split(",") if t.strip()]
            elif lower.startswith("estimated_hours:"):
                result["estimated_hours"] = line.split(":", 1)[1].strip()
            elif lower.startswith("dependencies:"):
                raw_deps = line.split(":", 1)[1].strip()
                result["dependencies"] = [d.strip() for d in raw_deps.split(",") if d.strip()]
            elif lower.startswith("risks:"):
                raw_risks = line.split(":", 1)[1].strip()
                result["risks"] = [r.strip() for r in raw_risks.split(",") if r.strip()]

        return result
