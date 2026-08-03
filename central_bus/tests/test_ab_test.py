"""Tests for central_bus.ab_test — A/B test experiment layer (CMD-002-A).

Covers the experiment registry, the deterministic 50/50 split, metrics
recording, and the report shape.
"""

from __future__ import annotations

import pytest

from central_bus.ab_test import (
    EXPERIMENTS,
    assign_variant,
    get_all_reports,
    get_report,
    record_decision,
    reset_metrics,
)


@pytest.fixture(autouse=True)
def _clean_metrics():
    reset_metrics()
    yield
    reset_metrics()


# ── Experiment registry ────────────────────────────────────────────


class TestRegistry:
    def test_route_split_registered(self) -> None:
        assert "route_split" in EXPERIMENTS
        cfg = EXPERIMENTS["route_split"]
        assert cfg["variants"] == ["v1", "v2"]
        assert cfg["weights"] == [50, 50]
        assert cfg["status"] == "active"


# ── Deterministic 50/50 split ──────────────────────────────────────


class TestAssignVariant:
    def test_deterministic_same_id_same_variant(self) -> None:
        results = {assign_variant("route_split", "fixed-request-42") for _ in range(100)}
        assert len(results) == 1
        assert results.pop() in ("v1", "v2")

    def test_empty_request_id_defaults_to_v1(self) -> None:
        assert assign_variant("route_split", "") == "v1"
        assert assign_variant("route_split", None) == "v1"  # type: ignore

    def test_both_variants_seen_across_ids(self) -> None:
        seen = {assign_variant("route_split", f"ab-{i:04d}") for i in range(200)}
        assert seen == {"v1", "v2"}

    def test_distribution_1000_ids_near_50_50(self) -> None:
        """The real 100-request split: 1000 ids must stay near 50/50."""
        counts = {"v1": 0, "v2": 0}
        for i in range(1000):
            counts[assign_variant("route_split", f"ab-{i:04d}")] += 1
        v1_pct = counts["v1"] / 1000 * 100
        assert 45 <= v1_pct <= 55, f"v1={v1_pct:.1f}% outside 45-55%"

    def test_unknown_experiment_raises(self) -> None:
        with pytest.raises(KeyError):
            assign_variant("no-such-experiment", "x")
        with pytest.raises(KeyError):
            get_report("no-such-experiment")


# ── Metrics + report ───────────────────────────────────────────────


class TestRecordAndReport:
    def test_counts_and_ratio_50_50(self) -> None:
        for i in range(30):
            record_decision("route_split", "v1", f"r-{i}")
        for i in range(30):
            record_decision("route_split", "v2", f"r-{i}")
        report = get_report("route_split")
        assert report["experiment"] == "route_split"
        assert report["total"] == 60
        assert report["variants"]["v1"]["count"] == 30
        assert report["variants"]["v2"]["count"] == 30
        assert report["variants"]["v1"]["percentage"] == 50.0
        assert report["variants"]["v2"]["percentage"] == 50.0
        assert report["split_ratio"] == "50/50"
        assert report["split_balance"]["is_balanced"] is True

    def test_report_ratio_mirrors_counts(self) -> None:
        for i in range(10):
            record_decision("route_split", "v1", f"x-{i}")
        for i in range(30):
            record_decision("route_split", "v2", f"x-{i}")
        report = get_report("route_split")
        assert report["total"] == 40
        assert report["variants"]["v1"]["percentage"] == 25.0
        assert report["variants"]["v2"]["percentage"] == 75.0
        assert report["split_balance"]["is_balanced"] is False

    def test_reset_clears_counts(self) -> None:
        record_decision("route_split", "v1", "one")
        assert get_report("route_split")["total"] == 1
        reset_metrics("route_split")
        assert get_report("route_split")["total"] == 0
        assert get_report("route_split")["variants"]["v1"]["count"] == 0

    def test_get_all_reports(self) -> None:
        record_decision("route_split", "v2", "one")
        reports = get_all_reports()
        assert "route_split" in reports
        assert reports["route_split"]["total"] == 1

    def test_recent_samples_captured(self) -> None:
        record_decision("route_split", "v1", "sample-1", meta={"endpoint": "/v1/route_v1"})
        report = get_report("route_split")
        assert len(report["recent_samples"]) == 1
        assert report["recent_samples"][0]["request_id"] == "sample-1"
        assert report["recent_samples"][0]["variant"] == "v1"
        assert report["recent_samples"][0]["meta"]["endpoint"] == "/v1/route_v1"
