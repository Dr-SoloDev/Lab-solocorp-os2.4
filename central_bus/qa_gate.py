from .state import get, send_back, update_phase
from .exceptions import escalate
from .models import BusMessage

# Minimum conditions per phase before it can be marked "done"
GATE_RULES: dict[str, list[str]] = {
    "spec":   ["prd_approved"],
    "design": ["ux_approved"],
    "arch":   ["adr_approved"],
    "dev":    ["code_review_passed", "unit_tests_passed"],
    "qa":     ["e2e_passed", "no_critical_bugs"],
    "deploy": ["smoke_test_passed", "monitoring_active"],
}


def check(project_id: str, phase: str, evidence: dict) -> tuple[bool, list[str]]:
    """Return (passed, missing_conditions).  evidence is a dict of {condition: bool}."""
    required = GATE_RULES.get(phase, [])
    missing = [c for c in required if not evidence.get(c)]
    return (len(missing) == 0), missing


def advance(project_id: str, phase: str, evidence: dict, trace_id: str = "") -> bool:
    """Advance phase to 'done' if gate passes, else send back + escalate."""
    passed, missing = check(project_id, phase, evidence)
    if passed:
        update_phase(project_id, phase, "done")
        return True

    # Gate failed — P2 send-back (first-class): ส่งงานกลับพร้อมเหตุผล + นับรอบ
    # (ครบ 3 รอบ send_back() จะพลิก phase เป็น failed รอคนเอง)
    send_back(project_id, phase, missing=missing, by="qa_gate")
    # Escalate as MED (พฤติกรรมเดิม — ยังมีเหมือนเดิม)
    state = get(project_id)
    msg = BusMessage(
        from_dept="qa", to_dept="orchestrator", type="EXCEPTION",
        project_id=project_id, phase=phase,
        payload={"text": f"QA gate failed: {missing}", "missing": missing},
        trace_id=trace_id or project_id,
        priority="high",
    )
    escalate(msg, "MED", reason=f"Gate blocked: {missing}")
    return False
