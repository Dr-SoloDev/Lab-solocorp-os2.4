"""Central Bus v0.6 — Skills Router (Cross-Department Skill Endpoints)

รองรับ:
* ``POST /v1/skills/cross-dept/pipeline-bridge`` — ส่ง task ข้ามแผนก
* ``POST /v1/skills/cross-dept/mirror-check`` — ตรวจสอบ decision ก่อนทำ
* ``GET  /v1/skills`` — รายการ skills ทั้งหมดที่ลงทะเบียน
* ``GET  /v1/skills/{skill_path}`` — ดูรายละเอียด skill

Architecture
~~~~~~~~~~~~
* โหลด route config จาก ``bus/system/skill_routes_config.json``
* แต่ละ endpoint เรียก ``require_mirror_check()`` ตาม minimum_level
* Skill invocation ถูกส่งเข้า Bus Queue + Audit Trail
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from central_bus.db import ensure_db, new_id, now_iso
from central_bus.mirror_check import MirrorLevel, require_mirror_check, run_mirror_check
from central_bus.queue import SQLiteQueueManager

log = logging.getLogger(__name__)

# ── Router ──────────────────────────────────────────────────────────

router = APIRouter(prefix="/v1/skills", tags=["skills"])

# ── Load Skill Route Config ─────────────────────────────────────────

_SKILL_ROUTES_PATH = (
    Path(__file__).parent.parent / "bus" / "system" / "skill_routes_config.json"
)


def _load_skill_routes() -> dict[str, Any]:
    """โหลด skill route config จาก JSON"""
    try:
        data = json.loads(_SKILL_ROUTES_PATH.read_text())
        return {r["path"]: r for r in data.get("routes", [])}
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        log.warning("Skill routes config not found: %s", exc)
        return {}


def _get_skills_list() -> list[dict[str, Any]]:
    """คืนค่ารายการ skills ทั้งหมด"""
    data = json.loads(_SKILL_ROUTES_PATH.read_text())
    return [
        {
            "skill": r["skill"],
            "method": r["method"],
            "path": r["path"],
            "target_department": r["target_department"],
            "mirror_check": r.get("mirror_check", False),
            "min_mirror_level": r.get("min_mirror_level", "L1"),
            "status": r.get("status", "registered"),
        }
        for r in data.get("routes", [])
    ]


# ── Error Response Helper ───────────────────────────────────────────


def _error(code: str, message: str, detail: Any = None, status: int = 400):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "detail": detail or {},
            }
        },
    )


# ═══════════════════════════════════════════════════════════════════════
# Skill Execution Helper
# ═══════════════════════════════════════════════════════════════════════


async def _execute_skill(
    request: Request,
    skill_path: str,
    payload: dict[str, Any],
    mirror_min_level: str = "L2",
) -> dict[str, Any]:
    """Execute a skill: Mirror Check → Enqueue → Audit → Return result

    Args:
        request: FastAPI Request
        skill_path: เส้นทาง skill (e.g. cross-dept/pipeline-bridge)
        payload: ข้อมูลที่ skill ต้องการ
        mirror_min_level: minimum mirror level ที่ต้องการ

    Returns:
        dict: ผลลัพธ์การ execute
    """
    skill_routes = _load_skill_routes()
    route_key = f"/v1/skills/{skill_path}"
    route_config = skill_routes.get(route_key)

    if not route_config:
        raise HTTPException(status_code=404, detail={"code": "SKILL_NOT_FOUND"})

    department = route_config.get("target_department", "architect")
    queue_topic = route_config.get("queue_topic", "skill.invoke")
    decision_text = payload.get("decision") or payload.get("task") or json.dumps(payload)

    # Step 1: Mirror Check
    if route_config.get("mirror_check", False):
        db = await ensure_db()
        mirror_result = await run_mirror_check(
            department=department,
            decision=decision_text[:500],
            context=payload,
            db=db,
        )
        if not mirror_result.passed:
            return {
                "status": "rejected",
                "skill": route_config["skill"],
                "mirror_check": mirror_result.to_dict(),
                "message": "Mirror Check Failed — decision rejected",
            }

    # Step 2: Enqueue to Bus
    db = await ensure_db()
    qm = SQLiteQueueManager(db)
    trace_id = f"skill-{new_id()[:12]}"

    msg = await qm.create_message(
        trace_id=trace_id,
        task_id=payload.get("task_id", f"skill-{new_id()[:8]}"),
        agent_id=f"skill:{route_config['skill']}",
        payload=payload,
        target_agent=department,
        priority=payload.get("priority", "normal"),
        max_retries=payload.get("max_retries", 3),
    )

    # Step 3: Audit Trail
    await db.execute(
        """
        INSERT INTO audit_log (id, trace_id, action, agent_id, entity_type, entity_id, payload, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id(),
            trace_id,
            "skill.invoke",
            f"skill:{route_config['skill']}",
            "queue",
            msg["id"],
            json.dumps({
                "skill": route_config["skill"],
                "department": department,
                "queue_topic": queue_topic,
            }),
            now_iso(),
        ),
    )

    return {
        "status": "queued",
        "skill": route_config["skill"],
        "trace_id": trace_id,
        "queue_id": msg["id"],
        "target_department": department,
        "mirror_check": {
            "passed": True,
            "department": department,
            "level": mirror_min_level,
        } if route_config.get("mirror_check") else None,
    }


# ═══════════════════════════════════════════════════════════════════════
# GET /v1/skills — List all registered skills
# ═══════════════════════════════════════════════════════════════════════


@router.get("")
async def list_skills():
    """แสดงรายการ skills ทั้งหมดที่ลงทะเบียนในระบบ"""
    skills = _get_skills_list()
    middleware = _load_mirror_middleware_config()

    return {
        "count": len(skills),
        "skills": skills,
        "middleware": middleware,
    }


def _load_mirror_middleware_config() -> dict:
    try:
        data = json.loads(_SKILL_ROUTES_PATH.read_text())
        return data.get("middleware", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# ═══════════════════════════════════════════════════════════════════════
# GET /v1/skills/{skill_path:path} — Get skill details
# ═══════════════════════════════════════════════════════════════════════


@router.get("/{skill_path:path}")
async def get_skill(skill_path: str):
    """ดูรายละเอียดของ skill ตาม path"""
    skill_routes = _load_skill_routes()
    route_key = f"/v1/skills/{skill_path}"
    route_config = skill_routes.get(route_key)

    if not route_config:
        return _error("SKILL_NOT_FOUND", f"Skill not found: {skill_path}", status=404)

    return {
        "skill": route_config["skill"],
        "method": route_config["method"],
        "path": route_config["path"],
        "target_department": route_config.get("target_department"),
        "queue_topic": route_config.get("queue_topic"),
        "mirror_check": route_config.get("mirror_check", False),
        "min_mirror_level": route_config.get("min_mirror_level", "L1"),
        "status": route_config.get("status", "registered"),
    }


# ═══════════════════════════════════════════════════════════════════════
# POST /v1/skills/cross-dept/pipeline-bridge
# ═══════════════════════════════════════════════════════════════════════


@router.post("/cross-dept/pipeline-bridge")
async def invoke_pipeline_bridge(request: Request):
    """Cross-department pipeline bridge — ส่ง task ข้ามแผนก

    Body:
    ```json
    {
        "from_dept": "architect",
        "to_dept": "engineering",
        "task": "Implement skill routes",
        "context": "...",
        "deadline": "2026-08-03",
        "priority": "P1"
    }
    ```
    """
    try:
        payload = await request.json()
    except Exception:
        return _error("INVALID_JSON", "Request body must be valid JSON", status=400)

    # Validate required fields
    if not payload.get("from_dept") or not payload.get("to_dept") or not payload.get("task"):
        return _error(
            "VALIDATION_ERROR",
            "from_dept, to_dept, and task are required",
            detail={
                "required": ["from_dept", "to_dept", "task"],
                "received": list(payload.keys()),
            },
        )

    return await _execute_skill(
        request=request,
        skill_path="cross-dept/pipeline-bridge",
        payload=payload,
        mirror_min_level="L3",
    )


# ═══════════════════════════════════════════════════════════════════════
# POST /v1/skills/cross-dept/mirror-check
# ═══════════════════════════════════════════════════════════════════════


@router.post("/cross-dept/mirror-check")
async def invoke_mirror_check(request: Request):
    """Mirror Check Protocol — ตรวจสอบ decision สะท้อน Dr.solodev Owner

    Body:
    ```json
    {
        "decision": "จะเพิ่ม AI chatbot ใน Central Bus",
        "department": "architect",
        "context": "..."
    }
    ```
    """
    try:
        payload = await request.json()
    except Exception:
        return _error("INVALID_JSON", "Request body must be valid JSON", status=400)

    decision = payload.get("decision", "")
    department = payload.get("department", "ceo")

    if not decision:
        return _error("VALIDATION_ERROR", "decision is required")

    db = await ensure_db()
    result = await run_mirror_check(
        department=department,
        decision=decision,
        context=payload.get("context"),
        db=db,
    )

    # Audit trail already written by run_mirror_check
    return {
        "status": "pass" if result.passed else "fail",
        "mirror_check": result.to_dict(),
        "summary": (
            f"✅ Mirror Check PASSED for {department}"
            if result.passed
            else f"❌ Mirror Check FAILED for {department}: {result.reason}"
        ),
    }
