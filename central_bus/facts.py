"""Central Bus v0.6 — Facts Service.

Durable key-value store with versioning, glob-to-LIKE pattern matching,
and metadata support.

Glob matching
~~~~~~~~~~~~~
The ``list_facts(prefix=...)`` method accepts glob-style patterns and
translates them to SQLite ``LIKE``:

    ========  ===========
    Glob       SQL LIKE
    ========  ===========
    ``*``     ``%``
    ``?``     ``_``
    ``***``   ``%``  (``*`` wildcard escape)
    ========  ===========

Example::

    # Fetch all facts for agent "changful"
    facts = await facts_service.list_facts("agent.status.changful*")
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from central_bus.config import settings
from central_bus.db import DbManager, new_id, now_iso

log = logging.getLogger(__name__)


def _glob_to_like(pattern: str) -> str:
    """Convert a glob-style pattern to a SQLite ``LIKE`` pattern.

    * ``*`` → ``%``  (match any sequence)
    * ``?`` → ``_``  (match single character)
    """
    return pattern.replace("*", "%").replace("?", "_")


class FactsService:
    """Durable key-value store with versioning.

    All methods are async and expect a ``DbManager`` instance.
    """

    def __init__(self, db: DbManager) -> None:
        self._db = db

    # ── Read ────────────────────────────────────────────────────────

    async def get_fact(self, key: str) -> Optional[dict[str, Any]]:
        """Fetch a single fact by exact key match.

        Returns the row as a dict (with ``value`` parsed from JSON) or
        ``None``.
        """
        row = await self._db.fetch_one(
            "SELECT * FROM facts WHERE key = ?", (key,)
        )
        if row is None:
            return None
        return self._row_to_dict(row)

    async def list_facts(
        self, prefix: Optional[str] = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """List facts, optionally filtered by a prefix / glob pattern.

        When ``prefix`` is provided, the method converts glob characters
        (``*``, ``?``) to SQLite ``LIKE`` wildcards.
        """
        if prefix:
            like_pattern = _glob_to_like(prefix)
            rows = await self._db.fetch_all(
                "SELECT * FROM facts WHERE key LIKE ? ORDER BY key ASC LIMIT ?",
                (like_pattern, limit),
            )
        else:
            rows = await self._db.fetch_all(
                "SELECT * FROM facts ORDER BY key ASC LIMIT ?", (limit,)
            )
        return [self._row_to_dict(r) for r in rows]

    # ── Write ───────────────────────────────────────────────────────

    async def set_fact(
        self,
        key: str,
        value: Any,
        metadata: Optional[dict[str, Any]] = None,
        updated_by: Optional[str] = None,
    ) -> dict[str, Any]:
        """Upsert a fact.  If the key already exists, *version* is
        incremented and *updated_at* is refreshed.

        Returns the full row as a dict.
        """
        value_str = json.dumps(value, ensure_ascii=False)
        metadata_str = json.dumps(metadata or {}, ensure_ascii=False)
        now = now_iso()

        existing = await self.get_fact(key)
        if existing:
            # UPDATE — increment version
            new_version = existing["version"] + 1
            await self._db.execute(
                """
                UPDATE facts
                SET value = ?, version = ?, metadata = ?,
                    updated_by = ?, updated_at = ?
                WHERE key = ?
                """,
                (value_str, new_version, metadata_str, updated_by, now, key),
            )
            log.debug("Fact updated: %s (v%d)", key, new_version)
        else:
            # INSERT
            new_version = 1
            await self._db.execute(
                """
                INSERT INTO facts (key, value, version, metadata, updated_by,
                                   created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (key, value_str, new_version, metadata_str, updated_by, now, now),
            )
            log.debug("Fact created: %s (v%d)", key, new_version)

        return {
            "key": key,
            "value": value,
            "version": new_version,
            "metadata": metadata or {},
            "updated_by": updated_by,
            "updated_at": now,
        }

    async def delete_fact(self, key: str) -> bool:
        """Delete a fact by key.  Returns ``True`` if a row was removed."""
        cur = await self._db.execute(
            "DELETE FROM facts WHERE key = ?", (key,)
        )
        return cur.rowcount > 0

    # ── Count ────────────────────────────────────────────────────────

    async def count_facts(self) -> int:
        """Return the total number of facts in the store."""
        row = await self._db.fetch_one("SELECT COUNT(*) AS cnt FROM facts")
        return row["cnt"] if row else 0

    # ── Internal helpers ────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row) -> dict[str, Any]:
        """Convert a SQLite Row to a dict, parsing JSON fields."""
        d = dict(row)
        # Parse stored JSON strings back to Python objects
        try:
            d["value"] = json.loads(d["value"])
        except (json.JSONDecodeError, TypeError):
            pass  # keep as raw string
        try:
            d["metadata"] = json.loads(d["metadata"])
        except (json.JSONDecodeError, TypeError):
            d["metadata"] = {}
        return d
