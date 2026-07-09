"""Central Bus v0.6 — SQLite Database Layer.

Provides:
  - DbManager: async SQLite connection lifecycle, schema init, WAL mode.
  - get_db: async generator / context manager for FastAPI dependency injection.
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator, AsyncIterator, Optional

import aiosqlite

from central_bus.config import settings

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
-- Bus: queue messages
CREATE TABLE IF NOT EXISTS queue (
    id              TEXT PRIMARY KEY,
    trace_id        TEXT NOT NULL,
    task_id         TEXT NOT NULL,
    agent_id        TEXT NOT NULL,
    target_agent    TEXT,
    priority        TEXT DEFAULT 'normal',
    status          TEXT DEFAULT 'pending',
    payload         TEXT NOT NULL,
    routing_hops    TEXT DEFAULT '[]',
    error_log       TEXT,
    retry_count     INTEGER DEFAULT 0,
    max_retries     INTEGER DEFAULT 3,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    completed_at    TEXT
);

-- Facts: durable key-value store with versioning
CREATE TABLE IF NOT EXISTS facts (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL,
    version         INTEGER DEFAULT 1,
    metadata        TEXT DEFAULT '{}',
    updated_by      TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- Routing Rules
CREATE TABLE IF NOT EXISTS routing_rules (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    source_agent    TEXT NOT NULL,
    target_department TEXT NOT NULL,
    condition       TEXT,
    priority        INTEGER DEFAULT 0,
    enabled         INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- Audit Trail
CREATE TABLE IF NOT EXISTS audit_log (
    id              TEXT PRIMARY KEY,
    trace_id        TEXT,
    action          TEXT NOT NULL,
    agent_id        TEXT,
    entity_type     TEXT,
    entity_id       TEXT,
    payload         TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Dead Letter Queue
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id              TEXT PRIMARY KEY,
    queue_id        TEXT NOT NULL,
    payload         TEXT NOT NULL,
    errors          TEXT NOT NULL,
    source_agent    TEXT NOT NULL,
    target_agent    TEXT,
    failed_at       TEXT DEFAULT (datetime('now')),
    resolved        INTEGER DEFAULT 0
);

-- After Action Reviews (AAR)
CREATE TABLE IF NOT EXISTS aar (
    id              TEXT PRIMARY KEY,
    trace_id        TEXT NOT NULL,
    task_id         TEXT,
    queue_id        TEXT,
    total_hops      INTEGER,
    total_retries   INTEGER,
    final_status    TEXT,
    latency_ms      INTEGER,
    failure_pattern TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Escalation log (from ADR-005)
CREATE TABLE IF NOT EXISTS escalations (
    id              TEXT PRIMARY KEY,
    project_id      TEXT,
    source_agent    TEXT NOT NULL,
    severity        TEXT DEFAULT 'warning',
    title           TEXT NOT NULL,
    detail          TEXT,
    status          TEXT DEFAULT 'open',
    assigned_to     TEXT,
    resolved_at     TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- CEO alerts (from ADR-005)
CREATE TABLE IF NOT EXISTS ceo_alerts (
    id              TEXT PRIMARY KEY,
    alert_type      TEXT NOT NULL,
    severity        TEXT DEFAULT 'critical',
    source          TEXT NOT NULL,
    title           TEXT NOT NULL,
    detail          TEXT,
    acknowledged    INTEGER DEFAULT 0,
    acknowledged_by TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Department API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    id              TEXT PRIMARY KEY,
    key_prefix      TEXT NOT NULL UNIQUE,
    key_hash        TEXT NOT NULL,
    department_id   TEXT NOT NULL,
    department_name TEXT NOT NULL,
    agent_id        TEXT NOT NULL,
    scope           TEXT DEFAULT 'dept',
    description     TEXT,
    enabled         INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    expires_at      TEXT,
    created_by      TEXT
);

-- ── Indexes ─────────────────────────────────────────────────────────
-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_queue_status_created ON queue(status, created_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_dept ON api_keys(department_id);
CREATE INDEX IF NOT EXISTS idx_queue_agent_status ON queue(agent_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id);

-- Simple indexes
CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status);
CREATE INDEX IF NOT EXISTS idx_queue_priority ON queue(priority);
CREATE INDEX IF NOT EXISTS idx_queue_agent ON queue(agent_id);
CREATE INDEX IF NOT EXISTS idx_queue_trace ON queue(trace_id);
CREATE INDEX IF NOT EXISTS idx_queue_created ON queue(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(key);
"""


# ---------------------------------------------------------------------------
# DbManager — async connection + schema lifecycle
# ---------------------------------------------------------------------------


class DbManager:
    """Manages an async SQLite connection with WAL mode and schema init.

    Usage (singleton, shared across the bus daemon)::

        db = DbManager()
        await db.init()
        async with db.connect() as conn:
            await conn.execute_fetchall("SELECT 1")
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or settings.db_path
        self._conn: aiosqlite.Connection | None = None

    # ── Lifecycle ──────────────────────────────────────────────────

    async def init(self) -> None:
        """Open the connection, enable WAL / foreign_keys, create schema."""
        if self._conn is not None:
            return  # already initialised

        log.info("Opening SQLite at %s", self._db_path)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row

        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA foreign_keys=ON;")
        await self._conn.execute("PRAGMA busy_timeout=5000;")

        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.commit()

        log.info("SQLite schema ready — WAL mode active")

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            log.info("SQLite connection closed")

    @property
    def is_initialised(self) -> bool:
        return self._conn is not None

    # ── Connection access ─────────────────────────────────────────

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """Yield the shared connection.  The caller owns the transaction

        boundary — call ``await conn.commit()`` or let the context-manager
        auto-commit when used inside ``async with db.connect()``.

        Example::

            async with db.connect() as conn:
                await conn.execute("INSERT ...")
                await conn.commit()
        """
        if self._conn is None:
            raise RuntimeError("DbManager not initialised — call await db.init() first")
        yield self._conn

    # ── Convenience helpers ──────────────────────────────────────────

    async def fetch_one(
        self, sql: str, params: tuple = ()
    ) -> Optional[aiosqlite.Row]:
        """Execute query and return the first row (or None)."""
        async with self.connect() as conn:
            cur = await conn.execute(sql, params)
            return await cur.fetchone()

    async def fetch_all(
        self, sql: str, params: tuple = ()
    ) -> list[aiosqlite.Row]:
        """Execute query and return all rows."""
        async with self.connect() as conn:
            cur = await conn.execute(sql, params)
            return await cur.fetchall()

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a write statement and commit."""
        async with self.connect() as conn:
            cur = await conn.execute(sql, params)
            await conn.commit()
            return cur

    async def execute_many(
        self, sql: str, params_list: list[tuple]
    ) -> None:
        """Execute a write statement for many rows and commit."""
        async with self.connect() as conn:
            await conn.executemany(sql, params_list)
            await conn.commit()


# ---------------------------------------------------------------------------
# FastAPI dependency — shared DbManager instance
# ---------------------------------------------------------------------------

_db_instance: DbManager | None = None


async def get_db() -> AsyncGenerator[DbManager, None]:
    """FastAPI dependency: yields the shared DbManager.

    Usage in route::

        async def handler(db: DbManager = Depends(get_db)): ...
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DbManager()
        await _db_instance.init()
    yield _db_instance


async def ensure_db(db_path: str | None = None) -> DbManager:
    """Get or create the shared DbManager singleton.

    Use this in application code that needs a direct reference to the DB
    outside of FastAPI's dependency injection (e.g., _get_services()).
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DbManager(db_path=db_path)
        await _db_instance.init()
    return _db_instance


def reset_db_for_testing() -> None:
    """Reset the global DbManager singleton for test isolation."""
    global _db_instance
    _db_instance = None


# ── UUID helper ────────────────────────────────────────────────────────


def new_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
