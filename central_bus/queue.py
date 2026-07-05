"""Central Bus v0.6 — Queue Manager (SQLite backend + JSONL backward compat).

Architecture
~~~~~~~~~~~~
* Existing JSONL functions (``enqueue``, ``dequeue``, ``requeue``, …) remain
  **untouched** for backward compatibility when ``USE_SQLITE=False``.
* New ``SQLiteQueueManager`` class replaces them when ``USE_SQLITE=True``.
* The module-level ``queue`` singleton is configured at import time via
  ``central_bus.config.settings.use_sqlite``.

Retry Policy
~~~~~~~~~~~~
When ``update_status`` is called with ``status='failed'`` and
``retry_count >= max_retries``, the message is automatically moved to the
``dead_letter_queue`` table.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from central_bus.config import settings
from central_bus.db import DbManager, new_id, now_iso
from central_bus.models import BusMessage, Priority

log = logging.getLogger(__name__)

# ── Backward-compat constants ───────────────────────────────────────────
# (unchanged from existing code — do NOT remove)
QUEUE_DIR = Path(__file__).parent.parent / "bus" / "queue"
DEAD_LETTER_DIR = QUEUE_DIR / "dead_letter"
MAX_RETRIES = int(os.environ.get("CENTRAL_BUS_MAX_RETRIES", "3"))
COMPACT_THRESHOLD = 100

USE_SQLITE = settings.use_sqlite


# ═══════════════════════════════════════════════════════════════════════
# Existing JSONL functions — preserved for backward compat
# ═══════════════════════════════════════════════════════════════════════


def _queue_file(priority: Priority, dead_letter: bool = False) -> Path:
    base = DEAD_LETTER_DIR if dead_letter else QUEUE_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{priority}.jsonl"


def _offset_file(priority: Priority) -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return QUEUE_DIR / f"{priority}.offset"


def _read_offset(priority: Priority) -> int:
    import fcntl
    f = _offset_file(priority)
    if not f.exists():
        return 0
    try:
        return int(f.read_text().strip())
    except (ValueError, OSError):
        return 0


def _write_offset(priority: Priority, offset: int) -> None:
    _offset_file(priority).write_text(str(offset))


def _compact(path: Path, priority: Priority) -> None:
    import fcntl
    offset = _read_offset(priority)
    if offset == 0:
        return
    try:
        with open(path, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            lines = f.readlines()
            remaining = lines[offset:]
            f.seek(0)
            f.writelines(remaining)
            f.truncate()
            fcntl.flock(f, fcntl.LOCK_UN)
        _write_offset(priority, 0)
    except OSError:
        pass


def enqueue(msg: BusMessage) -> None:
    """JSONL enqueue — kept for backward compatibility."""
    import fcntl
    path = _queue_file(msg.priority)
    line = json.dumps(msg.__dict__) + "\n"
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(line)
        fcntl.flock(f, fcntl.LOCK_UN)


def dequeue(priority: Priority) -> BusMessage | None:
    """JSONL dequeue — kept for backward compatibility."""
    import fcntl
    path = _queue_file(priority)
    if not path.exists():
        return None
    with open(path, "r") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        lines = f.readlines()
        fcntl.flock(f, fcntl.LOCK_UN)

    offset = _read_offset(priority)
    while offset < len(lines) and not lines[offset].strip():
        offset += 1
    if offset >= len(lines):
        if offset > 0:
            import fcntl
            with open(path, "w") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.truncate(0)
                fcntl.flock(f, fcntl.LOCK_UN)
            _write_offset(priority, 0)
        return None
    line = lines[offset]
    _write_offset(priority, offset + 1)
    if (offset + 1) % COMPACT_THRESHOLD == 0:
        _compact(path, priority)
    data = json.loads(line)
    return BusMessage(**data)


def requeue(msg: BusMessage) -> bool:
    """JSONL requeue with retry — kept for backward compatibility."""
    msg.retry_count += 1
    if msg.retry_count > MAX_RETRIES:
        _enqueue_dead_letter(msg, "Max retries exceeded")
        return False
    enqueue(msg)
    return True


def _enqueue_dead_letter(msg: BusMessage, reason: str) -> None:
    """JSONL dead-letter enqueue — kept for backward compatibility."""
    import fcntl
    path = _queue_file(msg.priority, dead_letter=True)
    record = {
        "message": msg.__dict__,
        "reason": reason,
        "retry_count": msg.retry_count,
        "moved_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(record) + "\n")
        fcntl.flock(f, fcntl.LOCK_UN)


def list_dead_letters(priority: Priority | None = None) -> list[dict]:
    """JSONL list dead letters — kept for backward compatibility."""
    import fcntl
    results = []
    if priority:
        sources = [priority]
    else:
        sources = ["critical", "high", "normal", "low"]
    for prio in sources:
        path = _queue_file(prio, dead_letter=True)
        if not path.exists():
            continue
        with open(path) as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    return results


def drain(priority: Priority) -> list[BusMessage]:
    """JSONL drain — kept for backward compatibility."""
    msgs = []
    while (m := dequeue(priority)) is not None:
        msgs.append(m)
    return msgs


# ═══════════════════════════════════════════════════════════════════════
# SQLite Queue Manager — the v0.6 default
# ═══════════════════════════════════════════════════════════════════════


class SQLiteQueueManager:
    """SQLite-backed queue manager.

    All methods are async and expect a ``DbManager`` instance.
    """

    def __init__(self, db: DbManager) -> None:
        self._db = db

    # ── Create ──────────────────────────────────────────────────────

    async def create_message(
        self,
        trace_id: str,
        task_id: str,
        agent_id: str,
        payload: dict[str, Any],
        *,
        target_agent: Optional[str] = None,
        priority: str = "normal",
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Insert a new message into the queue.

        Returns the created row as a dict.
        """
        # Validate payload is valid JSON
        payload_str = json.dumps(payload, ensure_ascii=False)
        msg_id = new_id()
        now = now_iso()

        sql = """
            INSERT INTO queue
                (id, trace_id, task_id, agent_id, target_agent,
                 priority, status, payload, max_retries, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """
        await self._db.execute(sql, (
            msg_id, trace_id, task_id, agent_id, target_agent,
            priority, payload_str, max_retries, now, now,
        ))

        return {
            "id": msg_id,
            "trace_id": trace_id,
            "task_id": task_id,
            "agent_id": agent_id,
            "target_agent": target_agent,
            "priority": priority,
            "status": "pending",
            "payload": payload,
            "retry_count": 0,
            "max_retries": max_retries,
            "created_at": now,
            "updated_at": now,
        }

    # ── Read ────────────────────────────────────────────────────────

    async def get_message(self, message_id: str) -> Optional[dict[str, Any]]:
        """Fetch a single message by ID."""
        row = await self._db.fetch_one(
            "SELECT * FROM queue WHERE id = ?", (message_id,)
        )
        return dict(row) if row else None

    async def get_pending(
        self,
        *,
        agent_id: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Fetch pending messages, optionally filtered by agent/priority."""
        conditions = ["status = 'pending'"]
        params: list[Any] = []

        if agent_id:
            conditions.append("agent_id = ?")
            params.append(agent_id)
        if priority:
            conditions.append("priority = ?")
            params.append(priority)

        sql = f"""
            SELECT * FROM queue
            WHERE {' AND '.join(conditions)}
            ORDER BY
                CASE priority
                    WHEN 'critical' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'normal' THEN 2
                    WHEN 'low' THEN 3
                END,
                created_at ASC
            LIMIT ?
        """
        params.append(limit)
        rows = await self._db.fetch_all(sql, tuple(params))
        return [dict(r) for r in rows]

    async def count_pending(self) -> int:
        """Return the number of messages with status = 'pending'."""
        row = await self._db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM queue WHERE status = 'pending'"
        )
        return row["cnt"] if row else 0

    async def count_failed(self) -> int:
        """Return the number of messages with status = 'failed'."""
        row = await self._db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM queue WHERE status = 'failed'"
        )
        return row["cnt"] if row else 0

    # ── Update status / retry ────────────────────────────────────────

    async def update_status(
        self,
        message_id: str,
        status: str,
        *,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update a message's status.

        If ``status == 'failed'`` and the message's ``retry_count >= max_retries``,
        it is moved to the **dead-letter queue** automatically.

        Returns the updated row as a dict.
        """
        now = now_iso()
        msg = await self.get_message(message_id)
        if msg is None:
            raise ValueError(f"Message {message_id} not found")

        # Build update fields
        updates: list[str] = ["status = ?", "updated_at = ?"]
        params: list[Any] = [status, now]

        if status == "completed":
            updates.append("completed_at = ?")
            params.append(now)

        if error:
            # Append to error_log (JSON array)
            existing_errors = json.loads(msg.get("error_log") or "[]")
            retry_count = msg.get("retry_count", 0)
            existing_errors.append({
                "attempt": retry_count + 1,
                "error": error,
                "timestamp": now,
            })
            updates.append("error_log = ?")
            params.append(json.dumps(existing_errors))

            # Increment retry_count
            updates.append("retry_count = retry_count + 1")
            msg["retry_count"] = msg.get("retry_count", 0) + 1

        sql = f"UPDATE queue SET {', '.join(updates)} WHERE id = ?"
        params.append(message_id)
        await self._db.execute(sql, tuple(params))

        # ── Dead letter check ────────────────────────────────────────
        if (
            status == "failed"
            and msg.get("status") != "dead"
            and msg.get("retry_count", 0) >= msg.get("max_retries", 3)
        ):
            await self._move_to_dead_letter(
                message_id,
                errors=json.loads(msg.get("error_log") or "[]")
                + [{"error": error or "Max retries exceeded", "timestamp": now}],
            )

        # Re-fetch to get the current state after UPDATE
        updated = await self.get_message(message_id)
        return dict(updated) if updated else msg

    # ── Dead letter operations ──────────────────────────────────────

    async def _move_to_dead_letter(
        self, message_id: str, errors: list[dict[str, Any]]
    ) -> None:
        """Move a message from queue to dead_letter_queue."""
        msg = await self.get_message(message_id)
        if msg is None:
            return

        dl_id = new_id()
        await self._db.execute(
            """
            INSERT INTO dead_letter_queue
                (id, queue_id, payload, errors, source_agent, target_agent, failed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dl_id,
                message_id,
                msg.get("payload", "{}"),
                json.dumps(errors),
                msg.get("agent_id", "unknown"),
                msg.get("target_agent"),
                now_iso(),
            ),
        )
        log.warning("Message %s moved to dead_letter_queue as %s", message_id, dl_id)

        # Mark queue entry as dead to prevent duplicate dead-lettering
        await self._db.execute(
            "UPDATE queue SET status = 'dead' WHERE id = ?",
            (message_id,),
        )

    async def get_dead_letters(
        self, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        """List dead-letter entries, newest first."""
        rows = await self._db.fetch_all(
            "SELECT * FROM dead_letter_queue ORDER BY failed_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    async def count_dead_letters(self) -> int:
        """Return the number of unresolved dead-letter entries."""
        row = await self._db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM dead_letter_queue WHERE resolved = 0"
        )
        return row["cnt"] if row else 0


# ═══════════════════════════════════════════════════════════════════════
# Module-level convenience: auto-select JSONL vs SQLite
# ═══════════════════════════════════════════════════════════════════════

# Re-export the module-level flag so callers can check without importing settings
__all__ = [
    "USE_SQLITE",
    "SQLiteQueueManager",
    # backward-compat JSONL functions
    "enqueue", "dequeue", "requeue", "drain", "list_dead_letters",
    "_enqueue_dead_letter",
]
