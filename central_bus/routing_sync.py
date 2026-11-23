#!/usr/bin/env python3
"""Central Bus — routing_rules SSoT sync (ADR-040, Wave 1).

``bus/system/routing_rules.json`` is the **single source of truth** for routing.
The SQLite ``routing_rules`` table is a derived index, not a second authority.
This module performs a one-way, idempotent, upsert-by-stable-id sync:

* stable key = JSON ``rule_id`` → SQLite ``routing_rules.id``
* re-running produces the same rows; no duplicates, no random ids
* existing rows are never deleted (rows only in the DB are reported)
* a ``schema_migrations`` record (``002-routing-rules``) pins the source checksum

Usage
~~~~~
::

    # Dry run (default) — validate + show what would change, no writes
    python -m central_bus.routing_sync

    # Apply to the DB configured by CENTRAL_BUS_DB_PATH (repo-relative)
    python -m central_bus.routing_sync --apply

    # Target a specific DB (e.g. the live daemon DB)
    python -m central_bus.routing_sync --db /data/projects/Lab-solocorp-os2.4/central_bus/bus.db --apply

    # Machine-readable output (evidence)
    python -m central_bus.routing_sync --dry-run --json

Exit codes: 0 = ok (dry run included), 1 = sync/validation error,
2 = bad invocation or unusable --db path.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from central_bus.config import settings
from central_bus.db import DbManager, now_iso

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES_PATH = REPO_ROOT / "bus" / "system" / "routing_rules.json"

MIGRATION_NAME = "002-routing-rules"
MIGRATION_DESC = "Seed routing_rules from bus/system/routing_rules.json (ADR-040 SSoT)"

PRIORITY_TO_INT = {"critical": 100, "high": 50, "normal": 10, "low": 0}

# Columns written on upsert (order used by INSERT and by the comparison).
ROW_COLUMNS = (
    "id",
    "name",
    "description",
    "source_agent",
    "target_department",
    "condition",
    "priority",
    "enabled",
)


# ═══════════════════════════════════════════════════════════════════════
# Source parsing / transform
# ═══════════════════════════════════════════════════════════════════════


class RoutingRulesError(ValueError):
    """Raised when the SSoT file or target DB cannot be used safely."""


def load_rules_doc(rules_path: Path | str = DEFAULT_RULES_PATH) -> dict[str, Any]:
    """Load and validate the routing rules document."""
    path = Path(rules_path)
    if not path.exists():
        raise RoutingRulesError(f"routing rules file not found: {path}")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RoutingRulesError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("rules"), list):
        raise RoutingRulesError(f"{path}: expected an object with a 'rules' list")
    if not doc["rules"]:
        raise RoutingRulesError(f"{path}: 'rules' is empty")
    return doc


def content_checksum(doc: dict[str, Any]) -> str:
    """Stable 16-char checksum of the SSoT content (same style as 001)."""
    raw = json.dumps(doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _condition_for(rule: dict[str, Any], seq: int) -> dict[str, Any]:
    """Build the SQLite condition payload from a JSON rule.

    The seeded trigger shape is ``{"keywords": [...]}``. We keep it verbatim
    and add the metadata the engine needs (fallback/mirror flags) plus an
    explicit file-order index for deterministic ties. No routing target is
    duplicated inside the condition — ``target_department`` stays authoritative.
    """
    trigger = rule.get("trigger") or {}
    if not isinstance(trigger, dict):
        raise RoutingRulesError(f"{rule.get('rule_id')}: 'trigger' must be an object")
    keywords = trigger.get("keywords")
    if keywords is None:
        keywords = []
    if not isinstance(keywords, list) or not all(isinstance(k, str) for k in keywords):
        raise RoutingRulesError(
            f"{rule.get('rule_id')}: 'trigger.keywords' must be a list of strings"
        )
    condition = dict(trigger)
    condition["keywords"] = keywords
    condition["_seq"] = seq
    if rule.get("is_fallback"):
        condition["is_fallback"] = True
    if rule.get("mirror_check"):
        condition["mirror_check"] = True
    return condition


def transform_rule(rule: dict[str, Any], seq: int) -> dict[str, Any]:
    """Transform one JSON rule to a ``routing_rules`` row (stable id)."""
    rule_id = rule.get("rule_id")
    if not isinstance(rule_id, str) or not rule_id.strip():
        raise RoutingRulesError(f"rule at index {seq}: missing or invalid 'rule_id'")
    route_to = rule.get("route_to")
    if not isinstance(route_to, str) or not route_to.strip():
        raise RoutingRulesError(f"{rule_id}: missing or invalid 'route_to'")
    condition = _condition_for(rule, seq)
    return {
        "id": rule_id,
        "name": rule.get("name") or rule_id,
        "description": rule.get("note", ""),
        "source_agent": ".*",
        "target_department": route_to,
        "condition": json.dumps(condition, sort_keys=True, ensure_ascii=False),
        "priority": PRIORITY_TO_INT.get(str(rule.get("priority", "normal")), 10),
        "enabled": 1,
    }


def transform_all(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Transform every rule, rejecting duplicate ids."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for seq, rule in enumerate(doc["rules"]):
        if not isinstance(rule, dict):
            raise RoutingRulesError(f"rule at index {seq} is not an object")
        row = transform_rule(rule, seq)
        if row["id"] in seen:
            raise RoutingRulesError(f"duplicate rule_id in SSoT: {row['id']}")
        seen.add(row["id"])
        rows.append(row)
    return rows


# ═══════════════════════════════════════════════════════════════════════
# schema_migrations compatibility (two on-disk shapes exist)
# ═══════════════════════════════════════════════════════════════════════


async def _schema_migrations_columns(db: DbManager) -> set[str]:
    rows = await db.fetch_all("PRAGMA table_info(schema_migrations)")
    return {r["name"] for r in rows}


async def get_migration_record(
    db: DbManager, name: str = MIGRATION_NAME
) -> Optional[dict[str, Any]]:
    """Return the migration record, tolerating both schema_migrations shapes.

    * repo/current schema:  ``(id, name, applied_at, checksum, description)``
    * legacy live schema:   ``(version, description, checksum, applied_at)``
    """
    cols = await _schema_migrations_columns(db)
    if "name" in cols:
        return await db.fetch_one(
            "SELECT name, checksum, applied_at, description FROM schema_migrations WHERE name = ?",
            (name,),
        )
    if "version" in cols:
        return await db.fetch_one(
            "SELECT version AS name, checksum, applied_at, description FROM schema_migrations WHERE version = ?",
            (name,),
        )
    return None


async def record_migration(
    db: DbManager, checksum: str, name: str = MIGRATION_NAME
) -> str:
    """Insert/update the migration record. Returns the shape that was written."""
    cols = await _schema_migrations_columns(db)
    if "name" in cols:
        await db.execute(
            """
            INSERT INTO schema_migrations (id, name, checksum, description)
            VALUES (lower(hex(randomblob(16))), ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                checksum = excluded.checksum,
                description = excluded.description,
                applied_at = datetime('now')
            """,
            (name, checksum, MIGRATION_DESC),
        )
        return "name"
    if "version" in cols:
        await db.execute(
            """
            INSERT INTO schema_migrations (version, checksum, description)
            VALUES (?, ?, ?)
            ON CONFLICT(version) DO UPDATE SET
                checksum = excluded.checksum,
                description = excluded.description,
                applied_at = datetime('now')
            """,
            (name, checksum, MIGRATION_DESC),
        )
        return "version"
    raise RoutingRulesError(
        "schema_migrations table has neither 'name' nor 'version' column — "
        "refusing to write a migration record"
    )


# ═══════════════════════════════════════════════════════════════════════
# Sync engine
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class SyncResult:
    dry_run: bool
    rules_path: str
    db_path: str
    json_count: int
    db_count_before: int
    db_count_after: int
    inserted: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    db_only: list[str] = field(default_factory=list)
    checksum: str = ""
    migration_shape: Optional[str] = None
    migration_applied: bool = False

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rules_in_sync"] = self.json_count == self.db_count_after
        data["projected_enabled"] = self.db_count_after + (
            len(self.inserted) if self.dry_run else 0
        )
        data["projected_in_sync"] = self.json_count == data["projected_enabled"]
        data["rollback_sql"] = self._rollback_sql()
        return data

    def _rollback_sql(self) -> str:
        """SQL that undoes only what this sync inserted (never updates/deletes others).

        ``schema_migrations`` has two on-disk shapes; both statements are
        emitted as comments so the operator runs the one matching the DB.
        """
        if not self.inserted:
            return "-- nothing inserted by this run"
        ids = ", ".join("'" + i.replace("'", "''") + "'" for i in self.inserted)
        return (
            f"DELETE FROM routing_rules WHERE id IN ({ids});\n"
            f"-- new-schema DB:  DELETE FROM schema_migrations WHERE name = '{MIGRATION_NAME}';\n"
            f"-- legacy-schema DB: DELETE FROM schema_migrations WHERE version = '{MIGRATION_NAME}';"
        )


async def _existing_rows(db: DbManager) -> dict[str, dict[str, Any]]:
    rows = await db.fetch_all(
        "SELECT id, name, description, source_agent, target_department, "
        "condition, priority, enabled FROM routing_rules"
    )
    return {r["id"]: dict(r) for r in rows}


def _row_equal(existing: dict[str, Any], wanted: dict[str, Any]) -> bool:
    for col in (
        "name",
        "description",
        "source_agent",
        "target_department",
        "condition",
    ):
        current = existing.get(col)
        if col == "description" and current is None:
            current = ""
        if current != wanted[col]:
            return False
    if int(existing.get("priority") or 0) != wanted["priority"]:
        return False
    if int(existing.get("enabled") or 0) != wanted["enabled"]:
        return False
    return True


async def _upsert(db: DbManager, row: dict[str, Any]) -> None:
    await db.execute(
        """
        INSERT INTO routing_rules
            (id, name, description, source_agent, target_department,
             condition, priority, enabled, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            source_agent = excluded.source_agent,
            target_department = excluded.target_department,
            condition = excluded.condition,
            priority = excluded.priority,
            enabled = excluded.enabled,
            updated_at = excluded.updated_at
        """,
        (
            row["id"],
            row["name"],
            row["description"],
            row["source_agent"],
            row["target_department"],
            row["condition"],
            row["priority"],
            row["enabled"],
            now_iso(),
            now_iso(),
        ),
    )


async def sync_rules(
    db: DbManager,
    *,
    rules_path: Path | str = DEFAULT_RULES_PATH,
    dry_run: bool = True,
    db_path: str = "",
) -> SyncResult:
    """Sync the JSON SSoT into SQLite. Idempotent; never deletes rows."""
    doc = load_rules_doc(rules_path)
    wanted_rows = transform_all(doc)
    checksum = content_checksum(doc)
    existing = await _existing_rows(db)

    result = SyncResult(
        dry_run=dry_run,
        rules_path=str(Path(rules_path).resolve()),
        db_path=str(db_path or getattr(db, "_db_path", "")),
        json_count=len(wanted_rows),
        db_count_before=len(existing),
        db_count_after=len(existing),
        checksum=checksum,
    )

    for wanted in wanted_rows:
        current = existing.get(wanted["id"])
        if current is None:
            result.inserted.append(wanted["id"])
            if not dry_run:
                await _upsert(db, wanted)
        elif _row_equal(current, wanted):
            result.unchanged.append(wanted["id"])
        else:
            result.updated.append(wanted["id"])
            if not dry_run:
                await _upsert(db, wanted)

    wanted_ids = {r["id"] for r in wanted_rows}
    result.db_only = sorted(set(existing) - wanted_ids)
    if result.db_only:
        log.warning(
            "DB has %d routing rule(s) not present in the SSoT (left untouched): %s",
            len(result.db_only),
            ", ".join(result.db_only),
        )

    if not dry_run:
        result.migration_shape = await record_migration(db, checksum)
        result.migration_applied = True

    count_row = await db.fetch_one(
        "SELECT COUNT(*) AS cnt FROM routing_rules WHERE enabled = 1"
    )
    result.db_count_after = count_row["cnt"] if count_row else 0

    return result


async def routing_sync_status(
    db: DbManager,
    *,
    rules_path: Path | str = DEFAULT_RULES_PATH,
) -> dict[str, Any]:
    """Drift snapshot for health checks — never raises."""
    status: dict[str, Any] = {
        "json_rules": None,
        "db_rules": None,
        "rules_in_sync": False,
        "checksum": None,
        "migration_applied": False,
        "error": None,
    }
    try:
        doc = load_rules_doc(rules_path)
        status["json_rules"] = len(doc["rules"])
        status["checksum"] = content_checksum(doc)
    except Exception as exc:  # noqa: BLE001 — health must not fail on a bad file
        status["error"] = f"rules file: {exc}"
        log.warning("Routing SSoT unreadable for health: %s", exc)
    try:
        row = await db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM routing_rules WHERE enabled = 1"
        )
        status["db_rules"] = row["cnt"] if row else 0
    except Exception as exc:  # noqa: BLE001
        status["error"] = f"db: {exc}"
        log.warning("Routing rules count failed for health: %s", exc)
        return status
    try:
        record = await get_migration_record(db)
        status["migration_applied"] = record is not None
    except Exception as exc:  # noqa: BLE001
        log.warning("Migration record lookup failed for health: %s", exc)
    status["rules_in_sync"] = (
        status["json_rules"] is not None
        and status["db_rules"] is not None
        and status["json_rules"] == status["db_rules"]
    )
    return status


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════


def resolve_db_path(raw: str | None) -> Path:
    """Resolve --db or the configured path to an absolute, existing file.

    A relative configured path is resolved against the repo root (the daemon
    runs with the repo as cwd). A missing file is an error: never create a
    fresh DB by accident when the intent was to seed the live one.
    """
    path = Path(raw) if raw else Path(settings.db_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    path = path.resolve()
    if not path.exists():
        raise RoutingRulesError(f"database not found: {path}")
    if not path.is_file():
        raise RoutingRulesError(f"database path is not a file: {path}")
    return path


async def _db_has_routing_table(db: DbManager) -> bool:
    row = await db.fetch_one(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'routing_rules'"
    )
    return row is not None


async def _run(args: argparse.Namespace) -> int:
    try:
        db_path = resolve_db_path(args.db)
        db = DbManager(db_path=str(db_path))
        await db.init(init_schema=False)  # never run SCHEMA_SQL against a live DB
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    try:
        if not await _db_has_routing_table(db):
            print(
                f"ERROR: {db_path} has no routing_rules table — is this a Central Bus DB?",
                file=sys.stderr,
            )
            return 2
        result = await sync_rules(
            db,
            rules_path=args.rules,
            dry_run=args.dry_run,
            db_path=str(db_path),
        )
    except RoutingRulesError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        log.exception("Routing sync failed")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        await db.close()

    payload = result.as_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    mode = "DRY RUN (no writes)" if result.dry_run else "APPLIED"
    print(f"routing sync — {mode}")
    print(
        f"  rules file : {result.rules_path}  ({result.json_count} rules, sha256:{result.checksum})"
    )
    print(f"  database   : {result.db_path}")
    print(f"  rows       : {result.db_count_before} → {result.db_count_after} enabled")
    print(
        f"  insert     : {len(result.inserted)}  update: {len(result.updated)}  unchanged: {len(result.unchanged)}"
    )
    if result.inserted:
        print(f"  inserted ids: {', '.join(result.inserted)}")
    if result.db_only:
        print(f"  db-only (untouched): {', '.join(result.db_only)}")
    print(f"  in sync    : {payload['rules_in_sync']}")
    if result.dry_run:
        print(
            f"  projected  : {payload['projected_enabled']} enabled "
            f"(in sync: {payload['projected_in_sync']})"
        )
    if not result.dry_run:
        print(
            f"  migration  : {MIGRATION_NAME} recorded via '{result.migration_shape}' schema"
        )
    else:
        print("  (dry run — re-run with --apply to write)")
    return 0


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync bus/system/routing_rules.json (SSoT) into SQLite routing_rules.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="validate and report changes without writing (default)",
    )
    mode.add_argument(
        "--apply",
        dest="dry_run",
        action="store_false",
        help="write changes (idempotent upsert by rule_id)",
    )
    parser.add_argument(
        "--db", default=None, help="path to the target Central Bus SQLite DB"
    )
    parser.add_argument(
        "--rules", default=str(DEFAULT_RULES_PATH), help="path to the SSoT JSON"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--verbose", "-v", action="store_true", help="debug logging")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
