"""Shared SQLite database (WAL mode, singleton) for CTO MCP (Phase 1).

Migrated from central_bus/unified_technical.db (Wave 1: sha256-verified copy
to central_bus/cto.db; source file kept until CTO green per 2-step deprecation).
"""

from __future__ import annotations

import aiosqlite
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = ROOT / "central_bus" / "cto.db"


class UnifiedDbManager:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._init_lock = None

    async def init(self) -> None:
        import asyncio

        if self._init_lock is None:
            self._init_lock = asyncio.Lock()
        async with self._init_lock:
            if self._conn is not None:
                return
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = await aiosqlite.connect(str(self.db_path))
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode=WAL;")
            await self._conn.execute("PRAGMA foreign_keys=ON;")
            await self._conn.execute("PRAGMA busy_timeout=5000;")
            await self._conn.executescript(self._schema_sql())
            await self._conn.commit()

    def _schema_sql(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS tool_calls (
            id TEXT PRIMARY KEY,
            module TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            trace_id TEXT,
            status TEXT DEFAULT 'pending',
            input_summary TEXT,
            output_summary TEXT,
            error TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS build_artifacts (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            module TEXT NOT NULL,
            artifact_path TEXT NOT NULL,
            sha256 TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS qa_evidence (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            suite_id TEXT NOT NULL,
            status TEXT NOT NULL,
            note TEXT,
            evidence_file TEXT,
            sha256 TEXT,
            recorded_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_tool_calls_module ON tool_calls(module);
        CREATE INDEX IF NOT EXISTS idx_tool_calls_trace ON tool_calls(trace_id);
        CREATE INDEX IF NOT EXISTS idx_qa_evidence_task ON qa_evidence(task_id);
        """

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        async with self._conn.execute(sql, params) as cur:
            await self._conn.commit()
            return cur

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None


db_manager = UnifiedDbManager()
