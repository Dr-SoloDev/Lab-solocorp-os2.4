"""Tests for central_bus.router — RoutingEngine."""

from __future__ import annotations

import pytest
import pytest_asyncio

from central_bus.db import DbManager, new_id, now_iso
from central_bus.router import (
    RoutingEngine,
    route as jsonl_route,
    priority_for as jsonl_priority_for,
    _route_governance,
    _has_thai,
)
from central_bus.models import BusMessage


@pytest_asyncio.fixture
async def db():
    d = DbManager(db_path=":memory:")
    await d.init()
    yield d
    await d.close()


@pytest_asyncio.fixture
async def engine(db):
    """RoutingEngine backed by test DB, pre-populated with rules."""
    e = RoutingEngine(db)
    # Insert some sample rules
    rules = [
        {
            "id": new_id(),
            "name": "engineering tasks",
            "source_agent": ".*",
            "target_department": "engineering",
            "condition": '{"field": "type", "equals": "code"}',
            "priority": 50,
            "enabled": 1,
        },
        {
            "id": new_id(),
            "name": "qa tasks",
            "source_agent": ".*",
            "target_department": "qa",
            "condition": '{"field": "type", "equals": "test"}',
            "priority": 40,
            "enabled": 1,
        },
        {
            "id": new_id(),
            "name": "fallback",
            "source_agent": ".*",
            "target_department": "ceo",
            "condition": None,
            "priority": 0,
            "enabled": 1,
        },
    ]
    for rule in rules:
        await db.execute(
            """
            INSERT INTO routing_rules
                (id, name, source_agent, target_department, condition,
                 priority, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (rule["id"], rule["name"], rule["source_agent"],
             rule["target_department"], rule["condition"],
             rule["priority"], rule["enabled"], now_iso(), now_iso()),
        )
    await e.invalidate_cache()  # Force reload
    yield e


# ── RoutingEngine.match ──────────────────────────────────────────


class TestMatch:
    async def test_match_engineering(self, engine: RoutingEngine) -> None:
        dept = await engine.match(
            source_agent="changful",
            payload={"type": "code", "feature": "auth"},
        )
        assert dept == "engineering"

    async def test_match_qa(self, engine: RoutingEngine) -> None:
        dept = await engine.match(
            source_agent="tester",
            payload={"type": "test", "suite": "unit"},
        )
        assert dept == "qa"

    async def test_fallback_to_ceo(self, engine: RoutingEngine) -> None:
        dept = await engine.match(
            source_agent="unknown-agent",
            payload={"type": "unknown"},
        )
        assert dept == "ceo"

    async def test_match_with_regex_source(self, engine: RoutingEngine, db) -> None:
        """Test that source_agent regex is respected."""
        rule_id = new_id()
        await db.execute(
            """
            INSERT INTO routing_rules
                (id, name, source_agent, target_department,
                 priority, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (rule_id, "architect-only", r"^archi.*",
             "architect", 60, 1, now_iso(), now_iso()),
        )
        await engine.invalidate_cache()

        dept = await engine.match(source_agent="architect", payload={})
        assert dept == "architect"

    async def test_match_disabled_rule(self, engine: RoutingEngine, db) -> None:
        """Disabled rules should not match."""
        rule_id = new_id()
        await db.execute(
            """
            INSERT INTO routing_rules
                (id, name, source_agent, target_department,
                 priority, enabled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (rule_id, "disabled", ".*", "marketing", 100, now_iso(), now_iso()),
        )
        await engine.invalidate_cache()

        dept = await engine.match(source_agent="anyone", payload={"type": "ad"})
        # Should fall through to "ceo" since the marketing rule is disabled
        assert dept == "ceo"


# ── RoutingEngine utility ────────────────────────────────────────


class TestEngineUtils:
    async def test_count_rules(self, engine: RoutingEngine) -> None:
        assert await engine.count_rules() >= 3

    async def test_invalidate_cache(self, engine: RoutingEngine) -> None:
        await engine.invalidate_cache()
        assert engine._last_refresh == 0.0

    async def test_ttl_cache(self, engine: RoutingEngine) -> None:
        """After loading once, second call should use cache."""
        await engine.match(source_agent="x", payload={})
        first_refresh = engine._last_refresh
        assert first_refresh > 0
        # Second call should not refresh (same TTL)
        await engine.match(source_agent="x", payload={})
        assert engine._last_refresh == first_refresh


# ── Condition evaluation ─────────────────────────────────────────


class TestConditionEvaluation:
    def test_equals_true(self) -> None:
        assert RoutingEngine._evaluate_condition(
            {"field": "status", "equals": "completed"},
            {"status": "completed"},
        )

    def test_equals_false(self) -> None:
        assert not RoutingEngine._evaluate_condition(
            {"field": "status", "equals": "failed"},
            {"status": "completed"},
        )

    def test_contains_true(self) -> None:
        assert RoutingEngine._evaluate_condition(
            {"field": "description", "contains": "urgent"},
            {"description": "This is an urgent task"},
        )

    def test_exists_true(self) -> None:
        assert RoutingEngine._evaluate_condition(
            {"field": "priority", "exists": True},
            {"priority": "high"},
        )

    def test_exists_false(self) -> None:
        assert RoutingEngine._evaluate_condition(
            {"field": "priority", "exists": True},
            {"other": "value"},
        ) is False

    def test_and_condition(self) -> None:
        assert RoutingEngine._evaluate_condition(
            {"and": [
                {"field": "type", "equals": "code"},
                {"field": "lang", "equals": "python"},
            ]},
            {"type": "code", "lang": "python"},
        )

    def test_and_condition_false(self) -> None:
        assert not RoutingEngine._evaluate_condition(
            {"and": [
                {"field": "type", "equals": "code"},
                {"field": "lang", "equals": "rust"},
            ]},
            {"type": "code", "lang": "python"},
        )

    def test_or_condition(self) -> None:
        assert RoutingEngine._evaluate_condition(
            {"or": [
                {"field": "type", "equals": "code"},
                {"field": "type", "equals": "test"},
            ]},
            {"type": "test"},
        )


# ── Thai text detection ─────────────────────────────────────────


class TestThaiDetection:
    def test_thai_text(self) -> None:
        assert _has_thai("สวัสดีครับ")

    def test_non_thai_text(self) -> None:
        assert not _has_thai("hello world")

    def test_mixed_text(self) -> None:
        assert _has_thai("hello สวัสดี world")


# ── Governance routing logic (JSONL compat) ──────────────────────


class TestGovernanceRouting:
    def _make_msg(self, gov_event: str) -> BusMessage:
        return BusMessage(
            from_dept="architect", to_dept="orchestrator",
            type="GOVERNANCE", project_id="test", phase="ops",
            payload={"gov_event": gov_event, "gov_detail": "test"},
            trace_id="gov-test",
        )

    def test_guard_failed_to_orchestrator(self) -> None:
        msg = self._make_msg("guard_failed")
        assert _route_governance(msg) == "orchestrator"

    def test_rfc_created_to_orchestrator(self) -> None:
        msg = self._make_msg("rfc_created")
        assert _route_governance(msg) == "orchestrator"

    def test_adr_accepted_to_architect(self) -> None:
        msg = self._make_msg("adr_accepted")
        assert _route_governance(msg) == "architect"

    def test_unknown_event_defaults_to_architect(self) -> None:
        msg = self._make_msg("unknown_event")
        assert _route_governance(msg) == "architect"
