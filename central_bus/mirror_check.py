"""Mirror Check Protocol — Middleware สำหรับตรวจสอบ decision สะท้อน Dr.solodev Owner

ก่อน department head ตัดสินใจสำคัญ ระบบจะตรวจสอบผ่าน 3 คำถาม:
1. "Dr.solodev จะทำแบบนี้ไหม?"
2. "Decision นี้สะท้อนตัวตนของ Dr.solodev หรือไม่?"
3. "ถ้า Owner เห็น decision นี้ จะ approve หรือ reject?"

Architecture
~~~~~~~~~~~~
* ``MirrorChecker`` — คลาสหลักสำหรับตรวจสอบ mirror check
* ``require_mirror_check(min_level)`` — FastAPI dependency สำหรับ guard endpoints
* ผลลัพธ์ถูกบันทึกลง audit trail โดยอัตโนมัติ

Intensity Levels
~~~~~~~~~~~~~~~~
L5 — Full Mirror (CEO): ทุก decision
L4 — Strategic (Architect): Decision ที่ impact 2+ departments
L3 — Financial (CFO): Budget > 3,000 บาท
L2 — Advisory (Engineering): Major refactor / API design
L1 — Monitor (Future): รับทราบอย่างเดียว
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any, Optional

from fastapi import HTTPException

log = logging.getLogger(__name__)

# ── Mirror Level ─────────────────────────────────────────────────────


class MirrorLevel(str, Enum):
    L5_FULL = "L5"
    L4_STRATEGIC = "L4"
    L3_FINANCIAL = "L3"
    L2_ADVISORY = "L2"
    L1_MONITOR = "L1"

    def __ge__(self, other: "MirrorLevel") -> bool:
        order = ["L1", "L2", "L3", "L4", "L5"]
        return order.index(self.value) >= order.index(other.value)

    def __le__(self, other: "MirrorLevel") -> bool:
        order = ["L1", "L2", "L3", "L4", "L5"]
        return order.index(self.value) <= order.index(other.value)


# ── Mirror Check Questions ──────────────────────────────────────────

MIRROR_QUESTIONS: dict[str, list[str]] = {
    "L5": [
        "ลูกพี่จะทำแบบนี้ไหม?",
        "Decision นี้สะท้อนตัวตนของ Dr.solodev หรือไม่?",
        "ถ้า Owner เห็น decision นี้ จะยิ้มหรือส่ายหัว?",
    ],
    "L4": [
        "Dr.solodev จะออกแบบระบบนี้ยังไง?",
        "Decision นี้ทำให้ระบบดีขึ้นสำหรับ Owner หรือไม่?",
        "Owner จะ approve architecture นี้ไหม?",
    ],
    "L3": [
        "Dr.solodev ในมุม conservative จะ approve ไหม?",
        "Worst case นี้ Owner รับได้ไหม?",
        "Owner จะดีใจหรือเสียใจที่ใช้เงินนี้?",
    ],
    "L2": [
        "Dr.solodev จะเขียน code แบบนี้ไหม?",
        "Code นี้ maintainable พอที่ Owner จะ approve หรือไม่?",
        "Owner จะภูมิใจใน code นี้ไหม?",
    ],
    "L1": [
        "Decision นี้มี impact อะไรบ้าง?",
        "Owner ควรรู้อะไรเกี่ยวกับ decision นี้?",
    ],
}

# ── Mirror Config (โหลดจาก mirror_config.json) ──────────────────────

import os
from pathlib import Path

_MIRROR_CONFIG_PATH = Path(__file__).parent.parent / "bus" / "system" / "mirror_config.json"


def _load_mirror_config() -> dict:
    """โหลด mirror config จาก JSON"""
    try:
        return json.loads(_MIRROR_CONFIG_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        log.warning("Mirror config not found: %s — using defaults", exc)
        return {"departments": {}}


def get_department_level(department: str) -> MirrorLevel | None:
    """Query the mirror level for a given department from config."""
    config = _load_mirror_config()
    dept_config = config.get("departments", {}).get(department)
    if not dept_config or not dept_config.get("mirror_active"):
        return None
    level_str = dept_config.get("level", "L1")
    try:
        return MirrorLevel(level_str)
    except ValueError:
        return MirrorLevel.L1_MONITOR


# ── Mirror Check Result ─────────────────────────────────────────────


class MirrorCheckResult:
    """ผลลัพธ์จากการตรวจสอบ Mirror Check"""

    def __init__(
        self,
        passed: bool,
        department: str,
        level: MirrorLevel | None,
        decision: str,
        question_results: list[dict[str, Any]],
        score: int,
        reason: str = "",
    ):
        self.passed = passed
        self.department = department
        self.level = level
        self.decision = decision
        self.question_results = question_results
        self.score = score
        self.reason = reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "department": self.department,
            "level": self.level.value if self.level else None,
            "decision": self.decision[:200],
            "question_results": self.question_results,
            "score": self.score,
            "reason": self.reason[:500] if self.reason else "",
        }

    def to_audit_entry(self) -> dict[str, Any]:
        return {
            "action": "mirror_check",
            "detail": {
                "result": "pass" if self.passed else "fail",
                "department": self.department,
                "level": self.level.value if self.level else "none",
                "score": self.score,
                "reason": self.reason[:200] if self.reason else "",
            },
        }


# ── LLM Evaluation ────────────────────────────────────────────────


async def _evaluate_mirror_question(question: str, decision: str, department: str) -> bool:
    """Evaluate a single mirror question using the LLM.

    Calls the LLM provider to check if the decision aligns with
    what Dr.solodev Owner would do.
    """
    try:
        from workers.llm_provider import think

        prompt = (
            f"คุณคือ Mirror Check Protocol ของ SoloCorp OS\n"
            f"Department: {department}\n"
            f"Decision ที่ต้องตรวจสอบ: {decision}\n\n"
            f"Mirror Question: {question}\n\n"
            f"ตอบแค่ YES หรือ NO เท่านั้น:\n"
            f"YES = decision สอดคล้องกับสิ่งที่ Dr.solodev Owner จะทำ\n"
            f"NO = decision ไม่สอดคล้อง"
        )
        result = await think(prompt, max_tokens=10)
        answer = result.strip().upper() if result else "NO"
        return answer.startswith("Y")
    except Exception as exc:
        log.warning("Mirror LLM evaluation failed: %s — defaulting to FAIL", exc)
        return False


# ── Main Check Logic ────────────────────────────────────────────────


async def run_mirror_check(
    department: str,
    decision: str,
    context: dict[str, Any] | None = None,
    *,
    db=None,
) -> MirrorCheckResult:
    """รัน Mirror Check สำหรับ department + decision ที่กำหนด

    Args:
        department: ชื่อ department (ceo, architect, cfo, engineering)
        decision: คำอธิบาย decision ที่กำลังจะทำ
        context: context เพิ่มเติม (optional)
        db: DB connection สำหรับบันทึก audit (optional)

    Returns:
        MirrorCheckResult — บอกว่าผ่านหรือไม่ พร้อมรายละเอียด
    """
    level = get_department_level(department)
    if level is None:
        # Department ไม่มี mirror active → pass อัตโนมัติ
        return MirrorCheckResult(
            passed=True,
            department=department,
            level=None,
            decision=decision,
            question_results=[],
            score=100,
            reason="Department has no mirror check requirement",
        )

    questions = MIRROR_QUESTIONS.get(level.value, MIRROR_QUESTIONS.get("L1", []))
    question_results = []
    passed_count = 0

    for i, question in enumerate(questions):
        # Call LLM to evaluate each mirror question against the decision
        q_pass = await _evaluate_mirror_question(question, decision, department)
        if q_pass:
            passed_count += 1

        question_results.append({
            "question_id": i + 1,
            "question": question,
            "result": "pass" if q_pass else "fail",
            "confidence": 0.90 if q_pass else 0.0,
        })

    score = int((passed_count / len(questions)) * 100) if questions else 100
    passed = score >= 60  # threshold: 60%+

    # บันทึก audit
    if db is not None:
        try:
            from central_bus.db import new_id, now_iso

            await db.execute(
                """
                INSERT INTO audit_log (id, trace_id, action, agent_id, entity_type, entity_id, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id(),
                    f"mirror-{department}-{new_id()[:8]}",
                    "mirror_check",
                    department,
                    "mirror",
                    f"mc-{new_id()[:8]}",
                    json.dumps({
                        "result": "pass" if passed else "fail",
                        "department": department,
                        "level": level.value,
                        "score": score,
                    }),
                    now_iso(),
                ),
            )
        except Exception as exc:
            log.warning("Failed to write mirror check audit: %s", exc)

    reason = ""
    if not passed:
        reason = (
            f"Mirror Check FAILED for {department} "
            f"(score={score}%, threshold=60%). "
            f"Decision may not align with Dr.solodev Owner's identity."
        )

    return MirrorCheckResult(
        passed=passed,
        department=department,
        level=level,
        decision=decision,
        question_results=question_results,
        score=score,
        reason=reason,
    )


# ── FastAPI Dependency ──────────────────────────────────────────────


def require_mirror_check(min_level: str = "L2"):
    """Factory สำหรับ FastAPI Dependency ที่บังคับ Mirror Check

    ใช้งาน:
    ```python
    @app.post("/v1/skills/cross-dept/pipeline-bridge")
    async def invoke_skill(
        payload: dict,
        _=Depends(require_mirror_check("L3")),
    ):
        ...
    ```
    """
    min_level_enum = MirrorLevel(min_level)

    async def dependency(department: str = "architect", decision: str = ""):
        level = get_department_level(department)
        if level is None:
            # ไม่มี mirror requirement → pass
            return True

        if level < min_level_enum:
            # department level ต่ำกว่าที่ skill กำหนด
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "MIRROR_LEVEL_INSUFFICIENT",
                    "message": (
                        f"Skill requires Mirror Level {min_level}, "
                        f"but {department} has {level.value}"
                    ),
                },
            )

        result = await run_mirror_check(department, decision)
        if not result.passed:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "MIRROR_CHECK_FAILED",
                    "message": result.reason,
                    "score": result.score,
                },
            )
        return True

    return dependency
