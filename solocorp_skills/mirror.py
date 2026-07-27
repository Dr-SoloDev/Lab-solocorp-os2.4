"""Mirror check functionality."""

from __future__ import annotations
from typing import Optional
from solocorp_skills.core import SolocorpError, SolocorpClient


def mirror_check(
    decision: str,
    priority: str = "L3",
    context: Optional[str] = None,
) -> dict:
    """Run mirror check for a decision.

    Checks if decision aligns with Owner's vision using 3 questions:
    1. Does this align with Owner's vision?
    2. Would Owner approve this decision?
    3. What's the worst case if wrong?

    Args:
        decision: Decision to check
        priority: Priority level (L1-L5)
        context: Additional context

    Returns:
        Dict with aligned (bool), score (0-100), verdict (PASS/FAIL/ESCALATE)
    """
    client = SolocorpClient()
    if client.is_ready():
        try:
            return client._api_post("/v1/mirror/check", {
                "decision": decision,
                "priority": priority,
                "context": context,
            })
        except Exception as e:
            raise SolocorpError(f"Mirror check failed: {e}")

    # Local fallback: simple heuristic
    return _mirror_local(decision, priority)


def _mirror_local(decision: str, priority: str) -> dict:
    """Local mirror check fallback."""
    l3_decision = priority in ("L3", "L4", "L5")
    return {
        "decision": decision,
        "priority": priority,
        "aligned": l3_decision,
        "score": 100 if l3_decision else 0,
        "verdict": "ESCALATE" if l3_decision else "PASS",
        "note": "Local fallback — Central Bus unavailable",
    }
