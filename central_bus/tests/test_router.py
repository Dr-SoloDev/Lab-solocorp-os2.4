"""Tests for central_bus.router — RoutingEngine + A/B Test 50/50."""

from __future__ import annotations

import hashlib
import pytest
import pytest_asyncio

from central_bus.db import DbManager, new_id, now_iso
from central_bus.router import (
    RoutingEngine,
    route as jsonl_route,
    priority_for as jsonl_priority_for,
    _route_governance,
    _has_thai,
    should_use_v2,
    route_ab_test,
    route_v2,
    get_ab_report,
    reset_ab_metrics,
)
from central_bus.models import BusMessage


# ── Fixtures ───────────────────────────────────────────────────────


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
    rules = [
        {
            "id": new_id(), "name": "engineering tasks",
            "source_agent": ".*", "target_department": "engineering",
            "condition": '{"field": "type", "equals": "code"}',
            "priority": 50, "enabled": 1,
        },
        {
            "id": new_id(), "name": "qa tasks",
            "source_agent": ".*", "target_department": "qa",
            "condition": '{"field": "type", "equals": "test"}',
            "priority": 40, "enabled": 1,
        },
        {
            "id": new_id(), "name": "fallback",
            "source_agent": ".*", "target_department": "ceo",
            "condition": None, "priority": 0, "enabled": 1,
        },
    ]
    for rule in rules:
        await db.execute(
            """INSERT INTO routing_rules
               (id, name, source_agent, target_department, condition,
                priority, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rule["id"], rule["name"], rule["source_agent"],
             rule["target_department"], rule["condition"],
             rule["priority"], rule["enabled"], now_iso(), now_iso()),
        )
    await e.invalidate_cache()
    yield e


@pytest.fixture
def any_msg() -> BusMessage:
    return BusMessage(
        from_dept="engineering", to_dept="", type="HANDOFF",
        project_id="test", phase="dev",
        payload={"text": "Need to fix a login bug"},
        trace_id="test-trace-001",
    )


@pytest.fixture
def gov_msg() -> BusMessage:
    return BusMessage(
        from_dept="architect", to_dept="", type="GOVERNANCE",
        project_id="test", phase="ops",
        payload={"gov_event": "guard_failed", "gov_detail": "test"},
        trace_id="gov-trace-001",
    )


@pytest.fixture
def ao_msg() -> BusMessage:
    return BusMessage(
        from_dept="engineering", to_dept="", type="AO_REQUEST",
        project_id="test", phase="dev",
        payload={"query": "check pipeline status"},
        trace_id="ao-trace-001",
    )


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
        rule_id = new_id()
        await db.execute(
            """INSERT INTO routing_rules
               (id, name, source_agent, target_department,
                priority, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (rule_id, "architect-only", r"^archi.*",
             "architect", 60, 1, now_iso(), now_iso()),
        )
        await engine.invalidate_cache()
        dept = await engine.match(source_agent="architect", payload={})
        assert dept == "architect"

    async def test_match_disabled_rule(self, engine: RoutingEngine, db) -> None:
        rule_id = new_id()
        await db.execute(
            """INSERT INTO routing_rules
               (id, name, source_agent, target_department,
                priority, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
            (rule_id, "disabled", ".*", "marketing", 100, now_iso(), now_iso()),
        )
        await engine.invalidate_cache()
        dept = await engine.match(source_agent="anyone", payload={"type": "ad"})
        assert dept == "ceo"


# ── RoutingEngine utility ────────────────────────────────────────


class TestEngineUtils:
    async def test_count_rules(self, engine: RoutingEngine) -> None:
        assert await engine.count_rules() >= 3

    async def test_invalidate_cache(self, engine: RoutingEngine) -> None:
        await engine.invalidate_cache()
        assert engine._last_refresh == 0.0

    async def test_ttl_cache(self, engine: RoutingEngine) -> None:
        await engine.match(source_agent="x", payload={})
        first_refresh = engine._last_refresh
        assert first_refresh > 0
        await engine.match(source_agent="x", payload={})
        assert engine._last_refresh == first_refresh


# ── Condition evaluation ─────────────────────────────────────────


class TestConditionEvaluation:
    def test_equals_true(self) -> None:
        assert RoutingEngine._evaluate_condition(
            {"field": "status", "equals": "completed"}, {"status": "completed"},
        )

    def test_equals_false(self) -> None:
        assert not RoutingEngine._evaluate_condition(
            {"field": "status", "equals": "failed"}, {"status": "completed"},
        )

    def test_contains_true(self) -> None:
        assert RoutingEngine._evaluate_condition(
            {"field": "description", "contains": "urgent"},
            {"description": "This is an urgent task"},
        )

    def test_exists_true(self) -> None:
        assert RoutingEngine._evaluate_condition(
            {"field": "priority", "exists": True}, {"priority": "high"},
        )

    def test_exists_false(self) -> None:
        assert RoutingEngine._evaluate_condition(
            {"field": "priority", "exists": True}, {"other": "value"},
        ) is False

    def test_and_condition(self) -> None:
        assert RoutingEngine._evaluate_condition(
            {"and": [{"field": "type", "equals": "code"}, {"field": "lang", "equals": "python"}]},
            {"type": "code", "lang": "python"},
        )

    def test_and_condition_false(self) -> None:
        assert not RoutingEngine._evaluate_condition(
            {"and": [{"field": "type", "equals": "code"}, {"field": "lang", "equals": "rust"}]},
            {"type": "code", "lang": "python"},
        )

    def test_or_condition(self) -> None:
        assert RoutingEngine._evaluate_condition(
            {"or": [{"field": "type", "equals": "code"}, {"field": "type", "equals": "test"}]},
            {"type": "test"},
        )


# ── Thai text detection ─────────────────────────────────────────


class TestThaiDetection:
    def test_thai_text(self) -> None:
        assert _has_thai("\u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35\u0e04\u0e23\u0e31\u0e1a")

    def test_non_thai_text(self) -> None:
        assert not _has_thai("hello world")

    def test_mixed_text(self) -> None:
        assert _has_thai("hello \u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35 world")


# ── Governance routing logic ─────────────────────────────────────


class TestGovernanceRouting:
    def _make_msg(self, gov_event: str) -> BusMessage:
        return BusMessage(
            from_dept="architect", to_dept="orchestrator",
            type="GOVERNANCE", project_id="test", phase="ops",
            payload={"gov_event": gov_event, "gov_detail": "test"},
            trace_id="gov-test",
        )

    def test_guard_failed_to_orchestrator(self) -> None:
        assert _route_governance(self._make_msg("guard_failed")) == "orchestrator"

    def test_rfc_created_to_orchestrator(self) -> None:
        assert _route_governance(self._make_msg("rfc_created")) == "orchestrator"

    def test_adr_accepted_to_architect(self) -> None:
        assert _route_governance(self._make_msg("adr_accepted")) == "architect"

    def test_unknown_event_defaults_to_architect(self) -> None:
        assert _route_governance(self._make_msg("unknown_event")) == "architect"


# ═══════════════════════════════════════════════════════════════════════
# A/B Test 50/50 — should_use_v2
# ═══════════════════════════════════════════════════════════════════════


class TestShouldUseV2:
    """Tests for deterministic 50/50 split."""

    def test_none_trace_id_defaults_to_legacy(self) -> None:
        assert should_use_v2("") is False
        assert should_use_v2(None) is False  # type: ignore

    def test_same_trace_id_always_same_variant(self) -> None:
        """Deterministic: same input always yields same output."""
        results = [should_use_v2("fixed-trace-42") for _ in range(100)]
        assert all(r == results[0] for r in results)

    def test_different_trace_ids_produce_both_variants(self) -> None:
        """With enough trace_ids, we should see both v2 and legacy."""
        v2_count = 0
        legacy_count = 0
        for i in range(200):
            trace_id = f"test-trace-{i:04d}"
            if should_use_v2(trace_id):
                v2_count += 1
            else:
                legacy_count += 1
        assert v2_count > 0 and legacy_count > 0
        # Should be roughly 50/50 (within 30% for 200 samples)
        total = v2_count + legacy_count
        v2_pct = v2_count / total * 100
        assert 20 <= v2_pct <= 80, f"v2={v2_pct:.1f}% is outside 20-80% range"

    def test_trace_id_hash_uses_md5_first_nibble(self) -> None:
        """Verify implementation: first hex digit < 8 = v2."""
        # Force a trace_id whose MD5 starts with '0'
        for candidate in range(10000):
            tid = f"force-v2-{candidate:04d}"
            h = hashlib.md5(tid.encode()).hexdigest()
            if h[0] == "0":
                assert should_use_v2(tid) is True
                break
        for candidate in range(10000):
            tid = f"force-legacy-{candidate:04d}"
            h = hashlib.md5(tid.encode()).hexdigest()
            if h[0] == "f":
                assert should_use_v2(tid) is False
                break


# ═══════════════════════════════════════════════════════════════════════
# A/B Test 50/50 — route_ab_test
# ═══════════════════════════════════════════════════════════════════════


class TestRouteABTest:
    """Tests for the A/B test routing wrapper."""

    def setup_method(self):
        reset_ab_metrics()

    def test_bypass_for_governance(self, gov_msg) -> None:
        """System messages bypass A/B test."""
        result = route_ab_test(gov_msg)
        assert result["variant"] == "bypass"

    def test_bypass_for_ao(self, ao_msg) -> None:
        """AO messages bypass A/B test."""
        result = route_ab_test(ao_msg)
        assert result["variant"] == "bypass"

    def test_routes_to_department(self, any_msg) -> None:
        """A/B test routes to a valid department."""
        result = route_ab_test(any_msg)
        assert result["department"] in (
            "ceo", "cfo", "cmo", "orchestrator", "architect", "product",
            "engineering", "design", "ui_designer", "qa", "sales", "support",
            "legal", "web3", "content_creator", "neteng", "cybersec", "psychology",
        )
        assert result["variant"] in ("v2", "legacy")

    def test_result_contains_all_keys(self, any_msg) -> None:
        """Result dict has all required metadata."""
        result = route_ab_test(any_msg)
        assert "department" in result
        assert "variant" in result
        assert "confidence" in result
        assert "latency_ms" in result
        assert "trace_id" in result
        assert result["trace_id"] == any_msg.trace_id

    def test_latency_is_positive(self, any_msg) -> None:
        """Routing latency should be a positive number."""
        result = route_ab_test(any_msg)
        assert result["latency_ms"] >= 0

    def test_trace_id_consistency(self) -> None:
        """Same trace_id always gets same variant."""
        msg1 = BusMessage(
            from_dept="engineering", to_dept="", type="HANDOFF",
            project_id="test", phase="dev",
            payload={"text": "Need budget approval"},
            trace_id="deterministic-999",
        )
        results = [route_ab_test(msg1)["variant"] for _ in range(5)]
        assert all(v == results[0] for v in results)

    def test_both_variants_seen_across_trace_ids(self) -> None:
        """Across many trace_ids, both v2 and legacy are observed."""
        v2_count = 0
        legacy_count = 0
        for i in range(100):
            msg = BusMessage(
                from_dept="engineering", to_dept="", type="HANDOFF",
                project_id="test", phase="dev",
                payload={"text": f"Test message number {i}"},
                trace_id=f"ab-dist-{i:04d}",
            )
            result = route_ab_test(msg)
            if result["variant"] == "v2":
                v2_count += 1
            else:
                legacy_count += 1
        assert v2_count > 0 and legacy_count > 0
        # Allow variance: 100 samples, 10-90% acceptable
        total = v2_count + legacy_count
        v2_pct = v2_count / total * 100
        assert 10 <= v2_pct <= 90, f"v2={v2_pct:.1f}% too extreme"


# ═══════════════════════════════════════════════════════════════════════
# A/B Test 50/50 — get_ab_report
# ═══════════════════════════════════════════════════════════════════════


class TestGetABReport:
    """Tests for A/B test metrics report."""

    def setup_method(self):
        reset_ab_metrics()

    def test_report_contains_expected_keys(self, any_msg) -> None:
        """Report has summary, latency, departments sections."""
        route_ab_test(any_msg)
        report = get_ab_report(db=None)
        assert "summary" in report
        assert "latency" in report
        assert "departments" in report
        assert "test_name" in report
        assert report["test_name"] == "route_v2 vs route (50/50 A/B Test)"

    def test_summary_counts_match(self) -> None:
        """After N routes, summary counts should reflect total."""
        reset_ab_metrics()
        for i in range(20):
            msg = BusMessage(
                from_dept="engineering", to_dept="", type="HANDOFF",
                project_id="test", phase="dev",
                payload={"text": f"msg {i}"},
                trace_id=f"report-test-{i:03d}",
            )
            route_ab_test(msg)
        report = get_ab_report(db=None)
        total = report["summary"]["v2"]["count"] + report["summary"]["legacy"]["count"]
        assert total == 20

    def test_latency_stats_are_numeric(self, any_msg) -> None:
        """Latency stats are floats or ints."""
        route_ab_test(any_msg)
        report = get_ab_report(db=None)
        for variant in ("v2", "legacy"):
            lat = report["latency"].get(variant, {})
            if lat.get("sample_size", 0) > 0:
                assert isinstance(lat["mean_ms"], float)
                assert isinstance(lat["p50_ms"], float)

    def test_department_distribution(self, any_msg) -> None:
        """Department counts show where routes went."""
        route_ab_test(any_msg)
        report = get_ab_report(db=None)
        depts = report["departments"]
        assert len(depts) > 0

    def test_reset_ab_metrics_clears_counts(self) -> None:
        """After reset, summary counts should be zero."""
        msg = BusMessage(
            from_dept="engineering", to_dept="", type="HANDOFF",
            project_id="test", phase="dev",
            payload={"text": "test"},
            trace_id="reset-test",
        )
        route_ab_test(msg)
        assert get_ab_report(db=None)["summary"]["v2"]["count"] + \
               get_ab_report(db=None)["summary"]["legacy"]["count"] > 0
        reset_ab_metrics()
        report = get_ab_report(db=None)
        assert report["summary"]["v2"]["count"] == 0
        assert report["summary"]["legacy"]["count"] == 0

    def test_balance_info_in_report(self) -> None:
        """Report includes split balance information."""
        for i in range(50):
            msg = BusMessage(
                from_dept="engineering", to_dept="", type="HANDOFF",
                project_id="test", phase="dev",
                payload={"text": f"balance test {i}"},
                trace_id=f"balance-{i:03d}",
            )
            route_ab_test(msg)
        report = get_ab_report(db=None)
        if "split_balance" in report:
            sb = report["split_balance"]
            assert "v2_percent" in sb
            assert "legacy_percent" in sb
            assert abs(sb["v2_percent"] + sb["legacy_percent"] - 100) < 1
