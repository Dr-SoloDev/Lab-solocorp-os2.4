"""
=============================================================
  🔄 SoloCorp OS — AAR Generator
=============================================================
  Auto-generates After Action Reviews after task completion
  Integration point: agent_worker_service.process_task()
=============================================================
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("aar-generator")


def _new_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_routing_hops(task: dict) -> int:
    raw = task.get("routing_hops", "[]")
    if isinstance(raw, str):
        try:
            return len(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            return 0
    return len(raw) if isinstance(raw, list) else 0


def _extract_failure_pattern(error: Optional[str], result: dict) -> str:
    if error:
        if "timeout" in error.lower():
            return "timeout"
        if "rate limit" in error.lower():
            return "rate_limited"
        if "auth" in error.lower() or "key" in error.lower():
            return "authentication"
        if "not found" in error.lower():
            return "not_found"
        if "connection" in error.lower():
            return "connection_error"
        return "unknown_error"
    if result.get("status") in ("failed", "error"):
        return result.get("failure_reason", "unknown_error")
    return ""


def _build_notes(task: dict, result: dict) -> str:
    notes = []
    summary = result.get("summary", "")
    if summary:
        notes.append(summary)
    priority = task.get("priority", "normal")
    if priority != "normal":
        notes.append(f"priority={priority}")
    details = result.get("details", {})
    if isinstance(details, dict):
        for k, v in details.items():
            if isinstance(v, str) and len(v) < 100:
                notes.append(f"{k}={v}")
    return " | ".join(notes)


async def generate_aar(
    task: dict,
    result: dict,
    start_time: Optional[float] = None,
    error: Optional[str] = None,
) -> dict:
    """Generate After Action Review for a completed/failed task.

    Args:
        task: Original queue task dict
        result: Agent execution result dict
        start_time: time.monotonic() timestamp for latency calculation
        error: Error string if task failed

    Returns:
        AAR record dict
    """
    aar_id = _new_id()
    latency_ms = 0
    if start_time:
        latency_ms = int((time.monotonic() - start_time) * 1000)

    # Parse routing hops from task
    hops_str = task.get("routing_hops", "[]")
    if isinstance(hops_str, str):
        try:
            hops_data = json.loads(hops_str)
            total_hops = len(hops_data)
        except (json.JSONDecodeError, TypeError):
            total_hops = 0
    else:
        total_hops = len(hops_str) if isinstance(hops_str, list) else 0

    failure_pattern = _extract_failure_pattern(error, result)
    final_status = "failed" if error else result.get("status", "completed")
    notes = _build_notes(task, result)

    try:
        from central_bus.db import ensure_db

        db = await ensure_db()

        await db.execute(
            """
            INSERT INTO aar
                (id, trace_id, task_id, queue_id, total_hops,
                 total_retries, final_status, latency_ms,
                 failure_pattern, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                aar_id,
                task.get("trace_id", ""),
                task.get("id", ""),
                task.get("id", ""),
                total_hops,
                task.get("retry_count", 0),
                final_status,
                latency_ms,
                failure_pattern,
                notes[:500],
                _now_iso(),
            ),
        )

        log.info(
            f"📊 AAR generated: {aar_id[:8]} — "
            f"status={final_status} hops={total_hops} latency={latency_ms}ms"
        )
    except Exception as e:
        log.warning(f"⚠️ AAR insert failed: {e}")

    return {
        "id": aar_id,
        "trace_id": task.get("trace_id", ""),
        "final_status": final_status,
        "latency_ms": latency_ms,
        "total_hops": total_hops,
    }


async def get_aar_for_task(task_id: str) -> list[dict]:
    """Retrieve AAR records for a task."""
    try:
        from central_bus.db import ensure_db

        db = await ensure_db()
        rows = await db.fetch_all(
            "SELECT * FROM aar WHERE task_id = ? ORDER BY created_at DESC",
            (task_id,),
        )
        return [dict(r) for r in rows]
    except Exception as e:
        log.warning(f"⚠️ AAR lookup failed: {e}")
        return []


async def get_aar_summary() -> dict:
    """Get AAR summary across all tasks."""
    try:
        from central_bus.db import ensure_db

        db = await ensure_db()
        rows = await db.fetch_all(
            """
            SELECT final_status, COUNT(*) as cnt, AVG(latency_ms) as avg_latency
            FROM aar GROUP BY final_status
            """
        )
        total = sum(r["cnt"] for r in rows)
        return {
            "total": total,
            "by_status": {
                r["final_status"]: {
                    "count": r["cnt"],
                    "avg_latency_ms": round(r["avg_latency"] or 0, 1),
                }
                for r in rows
            },
        }
    except Exception as e:
        log.warning(f"⚠️ AAR summary failed: {e}")
        return {"total": 0, "by_status": {}}
