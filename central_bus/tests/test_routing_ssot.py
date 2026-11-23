"""ADR-040 Wave 1 — routing SSoT sync, engine adapter, and drift health tests.

Covers:
* transform of every rule in the real SSoT file (22)
* idempotent apply (run twice → same 22 rows, no duplicates)
* dry-run makes no writes
* changed rule updates in place
* DB-only rows are never deleted
* legacy `schema_migrations(version, …)` compatibility
* semantic matrix — payloads must route to the right department, not `ceo`
* health parity (`rules_in_sync`, `oldest_routed_age_seconds`)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import pytest_asyncio

from central_bus.db import DbManager
from central_bus.facts import FactsService
from central_bus.health import get_health
from central_bus.queue import SQLiteQueueManager
from central_bus.router import RoutingEngine
from central_bus.routing_sync import (
    DEFAULT_RULES_PATH,
    MIGRATION_NAME,
    RoutingRulesError,
    content_checksum,
    get_migration_record,
    load_rules_doc,
    routing_sync_status,
    sync_rules,
    transform_all,
)

# ── Fixtures ───────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db(tmp_path: Path):
    manager = DbManager(db_path=str(tmp_path / "bus.db"))
    await manager.init()
    yield manager
    await manager.close()


@pytest_asyncio.fixture
async def seeded_db(db):
    await sync_rules(db, dry_run=False)
    return db


@pytest_asyncio.fixture
async def seeded_engine(seeded_db):
    return RoutingEngine(seeded_db)


# ── SSoT transform ────────────────────────────────────────────────


class TestTransform:
    def test_transform_all_22_rules(self) -> None:
        doc = load_rules_doc(DEFAULT_RULES_PATH)
        rows = transform_all(doc)
        assert len(rows) == 22
        assert len({r["id"] for r in rows}) == 22
        assert all(
            r["route_to"] if "route_to" in r else r["target_department"] for r in rows
        )
        assert all(r["enabled"] == 1 for r in rows)
        # Stable key is the SSoT rule_id, not a random UUID.
        assert {r["id"] for r in rows} >= {"r_to_cfo", "r_fallback", "r_mirror_ceo"}

    def test_fallback_and_mirror_flags_survive_transform(self) -> None:
        rows = {r["id"]: r for r in transform_all(load_rules_doc(DEFAULT_RULES_PATH))}
        fallback_condition = json.loads(rows["r_fallback"]["condition"])
        assert fallback_condition["is_fallback"] is True
        assert fallback_condition["keywords"] == []
        mirror_condition = json.loads(rows["r_mirror_cfo"]["condition"])
        assert mirror_condition["mirror_check"] is True

    def test_transform_rejects_duplicate_rule_ids(self) -> None:
        doc = load_rules_doc(DEFAULT_RULES_PATH)
        broken = {"rules": [doc["rules"][0], dict(doc["rules"][0])]}
        with pytest.raises(RoutingRulesError, match="duplicate rule_id"):
            transform_all(broken)

    def test_transform_rejects_missing_route_to(self) -> None:
        with pytest.raises(RoutingRulesError, match="route_to"):
            transform_all({"rules": [{"rule_id": "x", "trigger": {"keywords": []}}]})

    def test_checksum_is_stable(self) -> None:
        doc = load_rules_doc(DEFAULT_RULES_PATH)
        assert content_checksum(doc) == content_checksum(
            load_rules_doc(DEFAULT_RULES_PATH)
        )
        assert len(content_checksum(doc)) == 16


# ── Sync behaviour ────────────────────────────────────────────────


class TestSync:
    async def test_dry_run_writes_nothing(self, db) -> None:
        result = await sync_rules(db, dry_run=True)
        assert result.json_count == 22
        assert len(result.inserted) == 22
        assert result.db_count_before == result.db_count_after == 0
        assert result.as_dict()["projected_in_sync"] is True
        row = await db.fetch_one("SELECT COUNT(*) AS cnt FROM routing_rules")
        assert row["cnt"] == 0
        assert await get_migration_record(db) is None

    async def test_apply_seeds_22_and_records_migration(self, db) -> None:
        result = await sync_rules(db, dry_run=False)
        assert result.db_count_after == 22
        assert len(result.inserted) == 22
        assert result.migration_applied is True
        row = await db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM routing_rules WHERE enabled = 1"
        )
        assert row["cnt"] == 22
        record = await get_migration_record(db)
        assert record is not None
        assert record["checksum"] == result.checksum
        assert record["name"] == MIGRATION_NAME

    async def test_apply_twice_is_idempotent(self, db) -> None:
        first = await sync_rules(db, dry_run=False)
        second = await sync_rules(db, dry_run=False)
        assert len(first.inserted) == 22
        assert second.inserted == []
        assert second.updated == []
        assert len(second.unchanged) == 22
        assert second.db_count_before == second.db_count_after == 22
        rows = await db.fetch_all("SELECT id FROM routing_rules ORDER BY id")
        assert len(rows) == 22
        assert len({r["id"] for r in rows}) == 22
        migrations = await db.fetch_all(
            "SELECT COUNT(*) AS cnt FROM schema_migrations WHERE name = ?",
            (MIGRATION_NAME,),
        )
        assert migrations[0]["cnt"] == 1

    async def test_apply_updates_changed_rule_in_place(
        self, db, tmp_path: Path
    ) -> None:
        await sync_rules(db, dry_run=False)

        doc = load_rules_doc(DEFAULT_RULES_PATH)
        for rule in doc["rules"]:
            if rule["rule_id"] == "r_to_cfo":
                rule["trigger"]["keywords"].append("treasury")
        changed_path = tmp_path / "routing_rules.json"
        changed_path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

        result = await sync_rules(db, rules_path=changed_path, dry_run=False)
        assert result.inserted == []
        assert result.updated == ["r_to_cfo"]
        assert result.db_count_before == result.db_count_after == 22
        row = await db.fetch_one(
            "SELECT condition FROM routing_rules WHERE id = 'r_to_cfo'"
        )
        assert "treasury" in json.loads(row["condition"])["keywords"]

    async def test_db_only_rows_are_preserved(self, db) -> None:
        await db.execute(
            """INSERT INTO routing_rules
               (id, name, description, source_agent, target_department,
                condition, priority, enabled, created_at, updated_at)
               VALUES ('manual_rule', 'manual', '', '.*', 'support',
                       '{"field": "type", "equals": "x"}', 10, 1,
                       datetime('now'), datetime('now'))"""
        )
        result = await sync_rules(db, dry_run=False)
        assert "manual_rule" in result.db_only
        assert result.db_count_after == 23  # 22 SSoT + 1 manual, nothing deleted
        row = await db.fetch_one(
            "SELECT target_department FROM routing_rules WHERE id = 'manual_rule'"
        )
        assert row["target_department"] == "support"

    async def test_legacy_version_schema_migration_record(self, db) -> None:
        await db.execute("DROP TABLE schema_migrations")
        await db.execute(
            """CREATE TABLE schema_migrations (
                   version TEXT PRIMARY KEY,
                   description TEXT,
                   checksum TEXT,
                   applied_at TEXT DEFAULT (datetime('now'))
               )"""
        )
        first = await sync_rules(db, dry_run=False)
        assert first.migration_shape == "version"
        record = await get_migration_record(db)
        assert record is not None and record["checksum"] == first.checksum
        second = await sync_rules(db, dry_run=False)
        assert second.inserted == []
        rows = await db.fetch_all("SELECT COUNT(*) AS cnt FROM schema_migrations")
        assert rows[0]["cnt"] == 1


# ── Semantic matrix — real SSoT, real engine ──────────────────────

SEMANTIC_MATRIX = [
    ("review the quarterly budget and cost report", "cfo"),
    ("deploy the backend api hotfix", "engineering"),
    ("run regression test suite for quality", "qa"),
    ("our solana smart contract needs an audit", "web3"),
    ("customer support ticket escalation", "support"),
    ("GDPR compliance review for the contract", "legal"),
    ("marketing content plan for the brand", "cmo"),
    ("fix a bug in the server", "engineering"),
    ("daily ops routine admin", "coo"),
    ("ช่วยดูเรื่องการเงินกับงบประมาณให้หน่อย", "cfo"),
]


class TestSemanticMatrix:
    @pytest.mark.parametrize(("text", "expected"), SEMANTIC_MATRIX)
    async def test_payload_routes_to_expected_department(
        self, seeded_engine: RoutingEngine, text: str, expected: str
    ) -> None:
        dept = await seeded_engine.match("ceo", {"text": text})
        assert dept == expected, f"{text!r} → {dept}, expected {expected}"

    async def test_no_match_uses_ssot_fallback_not_hardcoded_ceo(
        self, seeded_engine: RoutingEngine
    ) -> None:
        # SSoT r_fallback routes to COO; the engine must honour that file.
        dept = await seeded_engine.match("ceo", {"text": "hello there, nice weather"})
        assert dept == "coo"

    async def test_most_hits_wins(self, seeded_engine: RoutingEngine) -> None:
        # engineering: fix + bug + server (3) vs qa: bug (1)
        dept = await seeded_engine.match(
            "ceo", {"text": "fix a bug in the server quickly"}
        )
        assert dept == "engineering"

    async def test_count_rules_matches_ssot(self, seeded_engine: RoutingEngine) -> None:
        assert await seeded_engine.count_rules() == 22


# ── Health / drift visibility ─────────────────────────────────────


class TestHealthParity:
    async def test_rules_in_sync_false_when_db_empty(self, db) -> None:
        status = await routing_sync_status(db)
        assert status["json_rules"] == 22
        assert status["db_rules"] == 0
        assert status["rules_in_sync"] is False
        assert status["migration_applied"] is False

    async def test_rules_in_sync_true_after_seed(self, seeded_db) -> None:
        status = await routing_sync_status(seeded_db)
        assert status["json_rules"] == 22
        assert status["db_rules"] == 22
        assert status["rules_in_sync"] is True
        assert status["migration_applied"] is True
        assert status["error"] is None

    async def test_health_response_contains_drift_fields(self, seeded_db) -> None:
        qm = SQLiteQueueManager(seeded_db)
        health = await get_health(
            db=seeded_db,
            qm=qm,
            facts_service=FactsService(seeded_db),
            engine=RoutingEngine(seeded_db),
            started_at=0,
        )
        assert isinstance(health, dict)
        assert health["routing_rules"] == 22
        assert health["rules_in_sync"] is True
        assert health["routing_json_rules"] == 22
        assert health["oldest_routed_age_seconds"] is None

    async def test_oldest_routed_age_none_when_queue_empty(self, db) -> None:
        qm = SQLiteQueueManager(db)
        assert await qm.oldest_routed_age_seconds() is None

    async def test_oldest_routed_age_tracks_routed_backlog(self, db) -> None:
        qm = SQLiteQueueManager(db)
        msg = await qm.create_message(
            trace_id="t-1", task_id="p-1", agent_id="ceo", payload={"text": "hi"}
        )
        await qm.update_status(msg["id"], "routed")
        age = await qm.oldest_routed_age_seconds()
        assert age is not None and 0 <= age < 10

        # An old routed message must dominate the age signal.
        await db.execute(
            "UPDATE queue SET updated_at = '2026-11-20 00:00:00' WHERE id = ?",
            (msg["id"],),
        )
        old_age = await qm.oldest_routed_age_seconds()
        assert old_age is not None and old_age > 86400
