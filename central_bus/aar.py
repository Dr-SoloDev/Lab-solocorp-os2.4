"""AAR (After Action Review) generation logic for Central Bus."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from central_bus.db import DbManager, new_id, now_iso

log = logging.getLogger(__name__)


class AARGenerator:
    """Generates and persists After Action Review entries for terminal tasks."""

    def __init__(self, db: DbManager) -> None:
        self.db = db

    async def generate(
        self,
        *,
        trace_id: str,
        queue_id: str,
        status: str,
        error: Optional[str],
        updated: dict[str, Any],
    ) -> tuple[Optional[str], str]:
        """Generate an AAR entry when a task reaches a terminal status.

        Returns (aar_id, final_status).
        aar_id is None if the status is not terminal (completed/failed).
        final_status may be promoted to "dead" if retry budget is exhausted.
        """
        aar_id = None
        final_status = status
        is_terminal = status in ("completed", "failed")

        if is_terminal:
            retry_count = updated.get("retry_count", 0)
            max_retries = updated.get("max_retries", 3)
            is_dead = retry_count >= max_retries and status == "failed"

            if is_dead:
                final_status = "dead"

            # Calculate latency
            created_at_str = updated.get("created_at", now_iso())
            try:
                created_dt = datetime.fromisoformat(created_at_str)
                latency_ms = int(
                    (datetime.now(timezone.utc) - created_dt).total_seconds() * 1000
                )
            except (ValueError, TypeError):
                latency_ms = 0

            entry = {
                "aar_id": f"aar-{new_id()}",
                "trace_id": trace_id,
                "task_id": updated.get("task_id", ""),
                "queue_id": queue_id,
                "total_hops": len(
                    json.loads(updated.get("routing_hops", "[]"))
                ),
                "total_retries": retry_count,
                "final_status": final_status,
                "latency_ms": latency_ms,
                "failure_pattern": (error if is_dead else None),
                "notes": None,
                "created_at": now_iso(),
            }

            await self.db.execute(
                """
                INSERT INTO aar (id, trace_id, task_id, queue_id, total_hops,
                                 total_retries, final_status, latency_ms,
                                 failure_pattern, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["aar_id"],
                    trace_id,
                    entry["task_id"],
                    queue_id,
                    entry["total_hops"],
                    retry_count,
                    final_status,
                    latency_ms,
                    entry["failure_pattern"],
                    None,
                    entry["created_at"],
                ),
            )
            aar_id = entry["aar_id"]
            log.info(
                "AAR generated: %s (trace=%s, status=%s, latency=%dms)",
                aar_id,
                trace_id,
                final_status,
                latency_ms,
            )

        return aar_id, final_status
