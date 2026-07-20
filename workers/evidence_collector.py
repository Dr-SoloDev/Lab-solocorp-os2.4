"""
=============================================================
  📋 SoloCorp OS — Evidence Collector
=============================================================
  Auto-collects task evidence → DB + JSON files
  Integration point: agent_worker_service.process_task()
=============================================================
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("evidence-collector")

EVIDENCE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "bus",
    "evidence",
)


def _ensure_evidence_dir() -> str:
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    return EVIDENCE_DIR


def _new_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_evidence_file(task: dict, result: dict, evidence_id: str) -> str:
    """Write evidence as JSON file → bus/evidence/{evidence_id}.json"""
    evidence_dir = _ensure_evidence_dir()
    file_path = os.path.join(evidence_dir, f"{evidence_id}.json")

    payload = task.get("payload", "{}")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            payload = {"raw": payload}

    evidence_doc = {
        "evidence_id": evidence_id,
        "task_id": task.get("id"),
        "trace_id": task.get("trace_id"),
        "agent_id": task.get("target_agent"),
        "source_agent": task.get("agent_id"),
        "evidence_type": "task_result",
        "status": result.get("status", "completed"),
        "summary": result.get("summary", ""),
        "details": result.get("details", {}),
        "routing_hops": json.loads(task.get("routing_hops", "[]")),
        "retry_count": task.get("retry_count", 0),
        "created_at": _now_iso(),
    }

    with open(file_path, "w") as f:
        json.dump(evidence_doc, f, indent=2, default=str)

    return file_path


async def collect_evidence(
    task: dict, result: dict, latency_ms: Optional[int] = None
) -> dict:
    """Collect evidence from completed task → DB + JSON file

    Returns the evidence record dict.
    """
    evidence_id = _new_id()
    file_path = _write_evidence_file(task, result, evidence_id)

    try:
        from central_bus.db import ensure_db

        db = await ensure_db()

        payload = task.get("payload", "{}")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                payload = {"raw": payload}

        routing_hops_str = task.get("routing_hops", "[]")
        if isinstance(routing_hops_str, str):
            try:
                hops = json.loads(routing_hops_str)
            except (json.JSONDecodeError, TypeError):
                hops = []
        else:
            hops = routing_hops_str or []

        await db.execute(
            """
            INSERT INTO evidence
                (id, task_id, trace_id, agent_id, evidence_type,
                 evidence_file, summary, status, routing_hops,
                 retry_count, latency_ms, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                task.get("id", ""),
                task.get("trace_id", ""),
                task.get("target_agent", ""),
                "task_result",
                file_path,
                result.get("summary", "")[:500],
                result.get("status", "completed"),
                len(hops),
                task.get("retry_count", 0),
                latency_ms or 0,
                json.dumps(
                    {
                        "source_agent": task.get("agent_id"),
                        "priority": task.get("priority", "normal"),
                        "final_status": result.get("status", "completed"),
                    }
                ),
                _now_iso(),
            ),
        )

        log.info(f"📋 Evidence collected: {evidence_id} → {os.path.basename(file_path)}")
    except Exception as e:
        log.warning(f"⚠️ Evidence DB insert failed: {e}")

    return {
        "id": evidence_id,
        "file_path": file_path,
    }


async def get_evidence_for_task(task_id: str) -> list[dict]:
    """Retrieve all evidence records for a task."""
    try:
        from central_bus.db import ensure_db

        db = await ensure_db()
        rows = await db.fetch_all(
            "SELECT * FROM evidence WHERE task_id = ? ORDER BY created_at DESC",
            (task_id,),
        )
        return [dict(r) for r in rows]
    except Exception as e:
        log.warning(f"⚠️ Evidence lookup failed: {e}")
        return []


async def get_evidence_summary(agent_id: Optional[str] = None) -> dict:
    """Get evidence summary stats."""
    try:
        from central_bus.db import ensure_db

        db = await ensure_db()
        if agent_id:
            rows = await db.fetch_all(
                "SELECT status, COUNT(*) as cnt FROM evidence WHERE agent_id = ? GROUP BY status",
                (agent_id,),
            )
        else:
            rows = await db.fetch_all(
                "SELECT status, COUNT(*) as cnt FROM evidence GROUP BY status"
            )
        total = sum(r["cnt"] for r in rows)
        return {
            "total": total,
            "by_status": {r["status"]: r["cnt"] for r in rows},
            "agent_filter": agent_id,
        }
    except Exception as e:
        log.warning(f"⚠️ Evidence summary failed: {e}")
        return {"total": 0, "by_status": {}, "agent_filter": agent_id}
