"""
Orchestrator Agent Adapter — Pipeline Orchestration & Cross-Dept Coordination

The Orchestrator adapter uses the RFC-001 Complexity Matrix (threshold module)
to route tasks, coordinate across departments, and manage the pipeline lifecycle.
"""

from ..adapter import AgentAdapter, register

# Lazy import to avoid circular deps at module load
_THRESHOLD = None


def _get_threshold():
    global _THRESHOLD
    if _THRESHOLD is None:
        from govctl_cli.threshold import assess_complexity
        _THRESHOLD = assess_complexity
    return _THRESHOLD


@register
class OrchestratorAdapter(AgentAdapter):
    """Pipeline orchestration, cross-dept coordination, governance routing."""

    agent_id = "orchestrator"
    display_name = "Orchestrator"
    description = "Pipeline orchestration, cross-dept coordination, governance routing"

    # ── Complexity matrix integration ──────────────────────────────────

    def assess_complexity(self, answers: dict) -> dict:
        """Delegate to the threshold module for RFC-001 Complexity Matrix."""
        assess = _get_threshold()
        return assess(answers)

    # ── Prompt building ────────────────────────────────────────────────

    def build_prompt(self, context: dict) -> str:
        """Build an orchestration prompt for coordinating departments.

        Expected context keys:
            - ``task`` (str): Description of the task to orchestrate.
            - ``project_id`` (str, optional): Project identifier.
            - ``involved_depts`` (list[str], optional): Departments involved.
            - ``complexity_answers`` (dict, optional): Complexity matrix answers
              (``scope_impact``, ``reversibility``, ``resource_commitment``).
        """
        task = context.get("task", "No task description provided.")
        project_id = context.get("project_id", "unspecified")
        involved = context.get("involved_depts", [])
        complexity_answers = context.get("complexity_answers", {})

        # Run complexity assessment if answers provided
        complexity_result = None
        if complexity_answers:
            complexity_result = self.assess_complexity(complexity_answers)

        lines = [
            f"# Orchestrator Pipeline Coordination — Project [{project_id}]",
            "",
            "คุณคือ Orchestrator (พี่วุฒิ) ผู้บริหารสายพานกลางของ SoloCorp OS",
            "คุณต้องวางแผนการประสานงาน จัดลำดับความสำคัญ และกำหนด governance path",
            "",
            f"## งานที่ต้องประสาน",
            f"{task}",
        ]

        if involved:
            lines.extend([
                "",
                "## แผนกที่เกี่ยวข้อง",
                *[f"- {d}" for d in involved],
            ])

        if complexity_result:
            lines.extend([
                "",
                "## ผลการประเมิน Complexity Matrix (RFC-001)",
                f"Score: {complexity_result['score']}/3",
                f"Threshold: {complexity_result['threshold']}",
                f"Decision: {complexity_result['decision']}",
            ])

        lines.extend([
            "",
            "## รูปแบบคำตอบ",
            "```",
            "pipeline_plan: <แผนการดำเนินงาน>",
            "sequence: <ลำดับขั้นตอน>",
            "assigned_to: <แผนกที่รับผิดชอบหลัก>",
            "governance_path: <direct_adr|rfc|full_review>",
            "estimated_effort: <ระดับ effort>",
            "```",
        ])

        return "\n".join(lines)

    # ── Response parser ────────────────────────────────────────────────

    def parse_response(self, raw: str) -> dict:
        """Parse an Orchestrator response into pipeline plan fields.

        Returns:
            Dict with keys ``pipeline_plan``, ``sequence``, ``assigned_to``,
            ``governance_path``, ``estimated_effort``.
        """
        lines = raw.strip().splitlines()
        result: dict = {
            "pipeline_plan": "",
            "sequence": "",
            "assigned_to": "",
            "governance_path": "",
            "estimated_effort": "",
        }

        for line in lines:
            lower = line.strip().lower()
            if lower.startswith("pipeline_plan:"):
                result["pipeline_plan"] = line.split(":", 1)[1].strip()
            elif lower.startswith("sequence:"):
                result["sequence"] = line.split(":", 1)[1].strip()
            elif lower.startswith("assigned_to:"):
                result["assigned_to"] = line.split(":", 1)[1].strip()
            elif lower.startswith("governance_path:"):
                result["governance_path"] = line.split(":", 1)[1].strip()
            elif lower.startswith("estimated_effort:"):
                result["estimated_effort"] = line.split(":", 1)[1].strip()

        return result
