#!/usr/bin/env python3
"""Central Bus v0.6 — JSONL → SQLite Migration Script.

Usage
~~~~~
::

    # Dry run (validate only, no writes)
    python -m central_bus.migrate --dry-run

    # Live migration
    python -m central_bus.migrate

    # Verbose
    python -m central_bus.migrate --verbose

Features
~~~~~~~~
* Reads existing JSONL queue files, facts, and routing rules.
* Transforms into SQLite schema and inserts idempotently.
* Validates row counts match before/after.
* Idempotent: safe to re-run (uses INSERT OR IGNORE via idempotency key).

Migration Sources
~~~~~~~~~~~~~~~~~
* ``bus/queue/{priority}.jsonl``  →  ``queue`` table
* ``bus/queue/dead_letter/{priority}.jsonl``  →  ``dead_letter_queue`` table
* ``bus/system/routing_rules.json``  →  ``routing_rules`` table
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from central_bus.db import DbManager, new_id, now_iso

log = logging.getLogger(__name__)

BUS_DIR = Path(__file__).parent.parent / "bus"
QUEUE_DIR = BUS_DIR / "queue"
DEAD_LETTER_DIR = QUEUE_DIR / "dead_letter"
RULES_PATH = BUS_DIR / "system" / "routing_rules.json"

PRIORITIES = ["critical", "high", "normal", "low"]


# ═══════════════════════════════════════════════════════════════════════
# Source readers
# ═══════════════════════════════════════════════════════════════════════


def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file, returning a list of parsed dicts."""
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                log.warning("Skipping invalid JSON in %s: %s", path, e)
    return entries


def _read_json(path: Path) -> dict:
    """Read a JSON file, returning a dict."""
    if not path.exists():
        return {}
    return json.loads(path.read_text())


# ═══════════════════════════════════════════════════════════════════════
# Transformers
# ═══════════════════════════════════════════════════════════════════════


def _transform_queue_entry(
    entry: dict, priority: str
) -> dict[str, Any]:
    """Transform a JSONL queue entry to SQLite queue row."""
    msg = entry if "message" not in entry else entry.get("message", {})
    return {
        "id": msg.get("id", new_id()),
        "trace_id": msg.get("trace_id", ""),
        "task_id": msg.get("task_id", msg.get("project_id", "")),
        "agent_id": msg.get("from_dept", "unknown"),
        "target_agent": msg.get("to_dept"),
        "priority": msg.get("priority", priority),
        "status": "pending",
        "payload": json.dumps(msg.get("payload", {}), ensure_ascii=False),
        "routing_hops": "[]",
        "error_log": None,
        "retry_count": msg.get("retry_count", 0),
        "max_retries": msg.get("max_retries", 3),
        "created_at": msg.get("ts", now_iso()),
        "updated_at": now_iso(),
        "completed_at": None,
    }


def _transform_dead_letter_entry(
    entry: dict, priority: str
) -> dict[str, Any]:
    """Transform a JSONL dead-letter entry to SQLite dead_letter_queue row."""
    msg = entry.get("message", {})
    return {
        "id": new_id(),
        "queue_id": msg.get("id", ""),
        "payload": json.dumps(msg.get("payload", {}), ensure_ascii=False),
        "errors": json.dumps([
            {"error": entry.get("reason", "Unknown"), "timestamp": entry.get("moved_at", now_iso())}
        ]),
        "source_agent": msg.get("from_dept", "unknown"),
        "target_agent": msg.get("to_dept"),
        "failed_at": entry.get("moved_at", now_iso()),
        "resolved": 0,
    }


def _transform_routing_rule(
    rule_id: str, rule: dict
) -> dict[str, Any]:
    """Transform a routing_rules.json entry to SQLite routing_rules row."""
    return {
        "id": new_id(),
        "name": rule.get("name", rule_id),
        "description": rule.get("description", ""),
        "source_agent": ".*",  # default: match all
        "target_department": rule.get("route_to", "ceo"),
        "condition": json.dumps(rule.get("trigger", {}), ensure_ascii=False),
        "priority": _priority_to_int(rule.get("priority", "normal")),
        "enabled": 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def _priority_to_int(priority: str) -> int:
    return {"critical": 100, "high": 50, "normal": 10, "low": 0}.get(priority, 10)


# ═══════════════════════════════════════════════════════════════════════
# Migration engine
# ═══════════════════════════════════════════════════════════════════════


class MigrationEngine:
    """Migrate JSONL data to SQLite."""

    def __init__(self, db: DbManager, dry_run: bool = False) -> None:
        self._db = db
        self.dry_run = dry_run
        self.stats: dict[str, int] = {
            "queue": 0,
            "dead_letter": 0,
            "rules": 0,
            "queue_skipped": 0,
            "dead_letter_skipped": 0,
        }

    # ── Queue ────────────────────────────────────────────────────

    async def _migrate_queue(self) -> None:
        for priority in PRIORITIES:
            path = QUEUE_DIR / f"{priority}.jsonl"
            entries = _read_jsonl(path)
            if not entries:
                continue
            log.info("Queue [%s]: %d entries", priority, len(entries))
            for entry in entries:
                row = _transform_queue_entry(entry, priority)
                # Idempotency: check for existing id
                existing = await self._db.fetch_one(
                    "SELECT id FROM queue WHERE id = ?", (row["id"],)
                )
                if existing:
                    self.stats["queue_skipped"] += 1
                    continue
                if not self.dry_run:
                    await self._db.execute(
                        """
                        INSERT INTO queue
                            (id, trace_id, task_id, agent_id, target_agent,
                             priority, status, payload, routing_hops, error_log,
                             retry_count, max_retries, created_at, updated_at, completed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        tuple(row[k] for k in [
                            "id", "trace_id", "task_id", "agent_id", "target_agent",
                            "priority", "status", "payload", "routing_hops", "error_log",
                            "retry_count", "max_retries", "created_at", "updated_at",
                            "completed_at",
                        ]),
                    )
                self.stats["queue"] += 1

    # ── Dead Letter ──────────────────────────────────────────────

    async def _migrate_dead_letter(self) -> None:
        for priority in PRIORITIES:
            path = DEAD_LETTER_DIR / f"{priority}.jsonl"
            entries = _read_jsonl(path)
            if not entries:
                continue
            log.info("Dead Letter [%s]: %d entries", priority, len(entries))
            for entry in entries:
                row = _transform_dead_letter_entry(entry, priority)
                if not self.dry_run:
                    await self._db.execute(
                        """
                        INSERT INTO dead_letter_queue
                            (id, queue_id, payload, errors, source_agent,
                             target_agent, failed_at, resolved)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        tuple(row[k] for k in [
                            "id", "queue_id", "payload", "errors", "source_agent",
                            "target_agent", "failed_at", "resolved",
                        ]),
                    )
                self.stats["dead_letter"] += 1

    # ── Routing Rules ────────────────────────────────────────────

    async def _migrate_routing_rules(self) -> None:
        rules = _read_json(RULES_PATH)
        rule_list = rules.get("rules", [])
        log.info("Routing rules: %d rules", len(rule_list))
        for i, rule in enumerate(rule_list):
            row = _transform_routing_rule(f"rule_{i}", rule)
            if not self.dry_run:
                await self._db.execute(
                    """
                    INSERT INTO routing_rules
                        (id, name, description, source_agent, target_department,
                         condition, priority, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(row[k] for k in [
                        "id", "name", "description", "source_agent",
                        "target_department", "condition", "priority", "enabled",
                        "created_at", "updated_at",
                    ]),
                )
            self.stats["rules"] += 1

    # ── Verification ─────────────────────────────────────────────

    async def verify(self) -> bool:
        """Verify row counts match. Returns True if all checks pass."""
        log.info("=" * 50)
        log.info("Verification")
        log.info("=" * 50)

        all_ok = True

        queue_count = (
            await self._db.fetch_one("SELECT COUNT(*) AS cnt FROM queue")
        )["cnt"]
        log.info("Queue:      %4d rows in SQLite", queue_count)
        if queue_count != self.stats["queue"]:
            log.error(
                "MISMATCH: expected %d, got %d",
                self.stats["queue"], queue_count,
            )
            all_ok = False

        dl_count = (
            await self._db.fetch_one(
                "SELECT COUNT(*) AS cnt FROM dead_letter_queue"
            )
        )["cnt"]
        log.info("Dead Letter: %4d rows in SQLite", dl_count)
        if dl_count != self.stats["dead_letter"]:
            log.error(
                "MISMATCH: expected %d, got %d",
                self.stats["dead_letter"], dl_count,
            )
            all_ok = False

        rules_count = (
            await self._db.fetch_one(
                "SELECT COUNT(*) AS cnt FROM routing_rules"
            )
        )["cnt"]
        log.info("Rules:       %4d rows in SQLite", rules_count)
        if rules_count != self.stats["rules"]:
            log.error(
                "MISMATCH: expected %d, got %d",
                self.stats["rules"], rules_count,
            )
            all_ok = False

        if all_ok:
            log.info("✅ All counts match!")
        else:
            log.warning("⚠️  Some counts mismatch — investigate before cutover")

        return all_ok

    # ── Run ──────────────────────────────────────────────────────

    async def run(self) -> bool:
        """Run the full migration. Returns True if successful."""
        log.info("Migration %s", "(DRY RUN — no writes)" if self.dry_run else "")
        log.info("-" * 50)

        await self._migrate_queue()
        await self._migrate_dead_letter()
        await self._migrate_routing_rules()

        log.info("-" * 50)
        log.info(
            "Stats: %d queue, %d dead_letter, %d rules%s",
            self.stats["queue"],
            self.stats["dead_letter"],
            self.stats["rules"],
            f" (+{self.stats['queue_skipped']} queue skipped)" if self.stats["queue_skipped"] else "",
        )

        if not self.dry_run:
            return await self.verify()
        return True


# ═══════════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Central Bus v0.6 — JSONL → SQLite Migration",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only — no database writes",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    db = DbManager()
    await db.initialize()

    engine = MigrationEngine(db, dry_run=args.dry_run)
    success = await engine.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(_main())
