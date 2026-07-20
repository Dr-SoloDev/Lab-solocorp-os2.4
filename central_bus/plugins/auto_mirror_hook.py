#!/usr/bin/env python3
"""
🪞 Auto-Mirror Hook — SoloCorp OS (Phase 8.3)
System รัน mirror check auto ทุก decision L3+ โดยไม่ต้อง consciously นึก

Usage:
    from central_bus.plugins.auto_mirror_hook import auto_mirror, mirror_guard

    # As context manager (for any code block)
    async with auto_mirror(department="engineering", decision="Deploy new auth API"):
        # ถ้า mirror fail → raises MirrorCheckError
        await deploy()

    # As decorator (for functions)
    @mirror_guard(department="architect", min_level="L3")
    async def redesign_system():
        ...

    # Manual call (if you need to handle failure yourself)
    result = await auto_mirror_check("engineering", "Refactor database")
    if not result.passed:
        # handle it
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional

log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent.parent
MIRROR_CONFIG_PATH = BASE / "bus" / "system" / "mirror_config.json"
AUDIT_DIR = BASE / "bus" / "evidence"


class MirrorCheckError(Exception):
    """Raised when mirror check fails"""
    def __init__(self, department: str, decision: str, score: int, reason: str):
        self.department = department
        self.decision = decision
        self.score = score
        self.reason = reason
        super().__init__(f"Mirror Check FAILED [{department}] score={score}%: {reason[:100]}")


def _rag(v: float) -> str:
    if v >= 90: return "🟢"
    if v >= 70: return "🟡"
    return "🔴"


def _level_order(level: str) -> int:
    return {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}.get(level, 0)


def _load_mirror_config() -> dict:
    try:
        return json.loads(MIRROR_CONFIG_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"departments": {}}


def get_department_level(department: str) -> str | None:
    """Get mirror level for department from config"""
    config = _load_mirror_config()
    dept_config = config.get("departments", {}).get(department)
    if dept_config and dept_config.get("mirror_active"):
        return dept_config.get("level", "L1")
    return None


def _log_mirror_event(result: dict):
    """Log mirror check event to audit trail"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    audit_dir = AUDIT_DIR / today
    audit_dir.mkdir(parents=True, exist_ok=True)
    event_file = audit_dir / f"mirror-{result['department']}-{datetime.now(timezone.utc).strftime('%H%M%S')}.json"
    event_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))


async def auto_mirror_check(
    department: str,
    decision: str,
    priority: str = "P2",
    context: Optional[dict] = None,
) -> dict:
    """
    Auto-run mirror check for a decision.
    Returns result dict with pass/fail + score + reason.
    This is the synchronous-compatible version that can also be called async.
    """
    # 1. Determine level from priority
    pri_to_level = {"P0": "L5", "P1": "L3", "P2": "L2", "P3": "L1"}
    level = pri_to_level.get(priority, "L2")
    
    # 2. Check if department has a mirror config
    config_level = get_department_level(department)
    if config_level:
        level = config_level  # Use config level if set
    
    level_num = _level_order(level)
    
    # 3. Only L3+ needs actual mirror check
    if level_num < 3:
        result = {
            "department": department,
            "decision": decision[:200],
            "level": level,
            "priority": priority,
            "passed": True,
            "score": 100,
            "rag": "🟢",
            "reason": f"Level {level} — auto-passed (below L3 threshold)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _log_mirror_event(result)
        return result
    
    # 4. L3+ — simulate the 3 mirror questions
    questions = {
        "L3": [
            "Dr.solodev ในมุม conservative จะ approve ไหม",
            "Worst case นี้ Owner รับได้ไหม",
            "Owner จะดีใจหรือเสียใจกับ decision นี้"
        ],
        "L4": [
            "Dr.solodev จะออกแบบระบบนี้ยังไง",
            "Decision นี้ทำให้ระบบดีขึ้นสำหรับ Owner หรือไม่",
            "Owner จะ approve นี้ไหม"
        ],
        "L5": [
            "ลูกพี่จะทำแบบนี้ไหม",
            "Decision นี้สะท้อนตัวตนของ Dr.solodev หรือไม่",
            "ถ้า Owner เห็น decision นี้ จะยิ้มหรือส่ายหัว"
        ]
    }
    
    qs = questions.get(level, questions["L3"])
    
    # Try LLM evaluation
    passed_count = 0
    q_results = []
    
    async def _ask_llm(question: str) -> tuple[bool, str]:
        """Ask LLM with 5-second timeout. Returns (passed, reason)"""
        try:
            from workers.llm_provider import think
            prompt = (
                f"คุณคือ Mirror Check Protocol ของ SoloCorp OS\n"
                f"Department: {department}\n"
                f"Decision: {decision[:300]}\n\n"
                f"คำถาม: {question}\n\n"
                f"ตอบแค่ YES หรือ NO:\n"
                f"YES = decision สอดคล้องกับสิ่งที่ Dr.solodev Owner จะทำ\n"
                f"NO = decision ไม่สอดคล้อง"
            )
            answer = await asyncio.wait_for(think(prompt, max_tokens=10), timeout=5.0)
            q_pass = answer.strip().upper().startswith("Y") if answer else True
            return q_pass, ""
        except asyncio.TimeoutError:
            return False, "LLM timeout"
        except ImportError:
            return False, "No LLM provider"
        except Exception as exc:
            log.warning("LLM error: %s", exc)
            return False, f"LLM error: {exc}"
    
    for i, q in enumerate(qs):
        q_pass, fail_reason = await _ask_llm(q)
        if q_pass:
            passed_count += 1
        q_results.append({
            "question_id": i + 1,
            "question": q,
            "result": "pass" if q_pass else "fail",
            "reason": fail_reason if not q_pass else "",
        })
    
    # If ALL questions failed due to LLM unavailability → use deterministic fallback
    all_llm_fail = all(r.get("reason", "") in ("LLM timeout", "No LLM provider") for r in q_results) if q_results else False
    if all_llm_fail:
        log.warning("All LLM calls failed — using deterministic mirror rules")
        if level == "L5":
            passed_count = 0
            q_results = [{"question_id": i+1, "question": q, "result": "fail", "reason": "LLM unavailable — L5 requires Owner verification"} for i, q in enumerate(qs)]
        elif level == "L4":
            passed_count = 1
            q_results = [{"question_id": i+1, "question": q, "result": "pass" if i == 0 else "fail", "reason": "LLM unavailable — conservative L4"} for i, q in enumerate(qs)]
        else:
            passed_count = 2
            q_results = [{"question_id": i+1, "question": q, "result": "pass" if i < 2 else "fail", "reason": "LLM unavailable — moderate L3"} for i, q in enumerate(qs)]
    
    score = int((passed_count / len(qs)) * 100) if qs else 100
    threshold = 80 if level == "L5" else 60
    passed = score >= threshold
    
    reason = ""
    if not passed:
        reason = (
            f"Mirror Check FAILED [{department}] score={score}% (threshold={threshold}%) — {decision[:80]}"
        )
    
    result = {
        "department": department,
        "decision": decision[:200],
        "level": level,
        "priority": priority,
        "passed": passed,
        "score": score,
        "threshold": threshold,
        "rag": _rag(score),
        "question_results": q_results,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Log to audit trail
    _log_mirror_event(result)
    
    return result


@asynccontextmanager
async def auto_mirror(
    department: str,
    decision: str,
    priority: str = "P2",
    context: Optional[dict] = None,
) -> AsyncIterator[dict]:
    """
    Context manager: auto-run mirror check before executing.
    
    Usage:
        async with auto_mirror("engineering", "Deploy to prod", "P1") as result:
            if result["passed"]:
                await deploy()
    
    Raises MirrorCheckError if check fails.
    """
    result = await auto_mirror_check(department, decision, priority, context)
    if not result["passed"]:
        raise MirrorCheckError(department, decision, result["score"], result.get("reason", ""))
    yield result


def mirror_guard(department: str | None = None, min_level: str = "L3"):
    """
    Decorator: auto-run mirror check before function executes.
    
    Usage:
        @mirror_guard(department="architect", min_level="L3")
        async def redesign():
            ...
    
    The function's first arg or kwarg 'department'/'decision' can override.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            dept = department or kwargs.get("department", "ceo")
            dec = kwargs.get("decision", kwargs.get("description", func.__name__))
            pri = kwargs.get("priority", "P2")
            
            # Only check if meets min_level threshold
            pri_to_level = {"P0": "L5", "P1": "L3", "P2": "L2", "P3": "L1"}
            level_num = _level_order(pri_to_level.get(pri, "L2"))
            min_num = _level_order(min_level)
            
            if level_num >= min_num:
                result = await auto_mirror_check(dept, dec, pri)
                if not result["passed"]:
                    raise MirrorCheckError(dept, dec, result["score"], result.get("reason", ""))
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ── Quick CLI test ────────────────────────────────────────────────────
if __name__ == "__main__":    
    async def test():
        # Test L2 (auto-pass, no LLM needed)
        r = await auto_mirror_check("engineering", "Fix minor bug", "P2")
        print(f"  L2: {r['rag']} passed={r['passed']} score={r['score']} — {r['reason'][:60]}")
        
        # Test L3 (no LLM fallback)
        r = await auto_mirror_check("engineering", "Refactor auth system to use OAuth2", "P1")
        print(f"  L3: {r['rag']} passed={r['passed']} score={r['score']} {r.get('reason','')[:60]}")
        
        # Test L5 (no LLM fallback — should fail)
        r = await auto_mirror_check("ceo", "เปลี่ยน mission ของ SoloCorp OS", "P0")
        print(f"  L5: {r['rag']} passed={r['passed']} score={r['score']} {r.get('reason','')[:60]}")
        
        # Verify audit trail
        from pathlib import Path
        audit = Path(__file__).parent.parent.parent / "bus/evidence"
        files = list(audit.rglob("mirror-*.json"))
        print(f"\n  Audit trail: {len(files)} mirror events logged")
    
    asyncio.run(test())
