"""Central Bus — Audit Logger (SQLite backend).

Replaces the JSONL-file implementation with async INSERTs into the
``audit_log`` table managed by :mod:`central_bus.db`.

Public surface
--------------
AuditLogger          — class with log_action / log_error / log_message
log(msg)             — module-level async helper (backward-compat)
read(project_id, …)  — module-level async query (backward-compat)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from central_bus.db import ensure_db, new_id
from central_bus.models import BusMessage

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AuditLogger — primary class
# ---------------------------------------------------------------------------


class AuditLogger:
    """Async audit logger that writes to the ``audit_log`` SQLite table."""

    # ------------------------------------------------------------------
    # Core write methods
    # ------------------------------------------------------------------

    async def log_action(
        self,
        action: str,
        *,
        agent_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        payload: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> str:
        """INSERT one row into audit_log; returns the new row id."""
        row_id = new_id()
        created_at = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload) if payload is not None else None

        db = await ensure_db()
        await db.execute(
            """
            INSERT INTO audit_log
                (id, trace_id, action, agent_id, entity_type, entity_id, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (row_id, trace_id, action, agent_id, entity_type, entity_id, payload_json, created_at),
        )
        _log.debug("audit INSERT id=%s action=%s agent=%s", row_id, action, agent_id)
        return row_id

    async def log_error(
        self,
        error: str | Exception,
        *,
        agent_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        trace_id: str | None = None,
    ) -> str:
        """INSERT an error row into audit_log; returns the new row id."""
        payload = {"error": str(error)}
        return await self.log_action(
            "error",
            agent_id=agent_id,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            trace_id=trace_id,
        )

    async def log_message(self, msg: BusMessage) -> str:
        """INSERT a BusMessage as an audit row; returns the new row id."""
        return await self.log_action(
            msg.type,
            agent_id=msg.from_dept,
            entity_type="bus_message",
            entity_id=msg.id,
            payload={"to_dept": msg.to_dept, "project_id": msg.project_id, **msg.payload},
            trace_id=msg.trace_id,
        )

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def read(
        self,
        project_id: str | None = None,
        date: str | None = None,
        *,
        limit: int = 500,
    ) -> list[dict]:
        """Return audit rows as plain dicts.

        ``project_id`` filters on payload JSON (best-effort).
        ``date`` filters rows where created_at starts with that date string
        (format YYYY-MM-DD). Defaults to today.
        """
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        db = await ensure_db()

        if project_id:
            rows = await db.fetch_all(
                """
                SELECT * FROM audit_log
                WHERE created_at LIKE ?
                  AND (payload LIKE ? OR entity_id LIKE ?)
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"{date}%", f"%{project_id}%", f"%{project_id}%", limit),
            )
        else:
            rows = await db.fetch_all(
                """
                SELECT * FROM audit_log
                WHERE created_at LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"{date}%", limit),
            )

        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_logger = AuditLogger()


# ---------------------------------------------------------------------------
# Module-level async helpers — backward-compatible API
# ---------------------------------------------------------------------------


async def log(msg: BusMessage) -> str:
    """Async drop-in for the old sync ``log(msg)``."""
    return await _logger.log_message(msg)


async def read(project_id: str, date: str | None = None) -> list[dict]:
    """Async drop-in for the old sync ``read(project_id, date)``."""
    return await _logger.read(project_id, date)
