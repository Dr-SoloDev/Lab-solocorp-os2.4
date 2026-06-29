import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path(__file__).parent / "state.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS loops (
        id TEXT PRIMARY KEY,
        last_run TEXT,
        last_result TEXT,
        failures INTEGER DEFAULT 0
    )""")
    c.commit()
    return c


def last_run(loop_id: str) -> datetime | None:
    with _conn() as c:
        row = c.execute("SELECT last_run FROM loops WHERE id=?", (loop_id,)).fetchone()
    return datetime.fromisoformat(row[0]) if row and row[0] else None


def record(loop_id: str, result: str, success: bool = True) -> None:
    with _conn() as c:
        c.execute("""
            INSERT INTO loops(id, last_run, last_result, failures) VALUES(?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                last_run = excluded.last_run,
                last_result = excluded.last_result,
                failures = CASE WHEN excluded.failures=0 THEN 0 ELSE failures+1 END
        """, (loop_id, datetime.now().isoformat(), result[:500], 0 if success else 1))
