"""End-to-end tests for A/B Test 50/50 deploy (CMD-002-A).

Runs against the real FastAPI app (same pattern as test_api.py) with the
admin key.  Proves:
  1. /v1/route_v1 + /v1/route_v2 return the deterministically selected variant
  2. 100 live requests split ~50/50 (within 35-65%)
  3. /v1/ab-test/report returns counts per variant + split ratio

No pytest-asyncio required (CI-safe): the DB singleton is lazy-initialised
inside request handling, so a plain sync fixture swapping settings.db_path
is sufficient.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from central_bus.ab_test import reset_metrics
from central_bus.config import settings
from central_bus.db import reset_db_for_testing
from central_bus.main import app

VALID_DEPTS = (
    "ceo", "cfo", "cmo", "orchestrator", "architect", "product",
    "engineering", "design", "ui_designer", "qa", "sales", "support",
    "legal", "web3", "content_creator", "neteng", "cybersec", "psychology",
)

client = TestClient(app)
client.headers.setdefault("X-API-Key", "sk-solocorp-admin-local-dev-001")


@pytest.fixture(autouse=True)
def _isolate_state():
    """In-memory DB (avoid touching a real db file) + clean A/B metrics."""
    reset_db_for_testing()
    old_path = settings.db_path
    settings.db_path = ":memory:"
    reset_metrics()
    yield
    settings.db_path = old_path
    reset_db_for_testing()
    reset_metrics()


# ── Variant endpoints ──────────────────────────────────────────────


class TestVariantEndpoints:
    def test_route_v1_returns_selected_variant(self) -> None:
        resp = client.get("/v1/route_v1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["experiment"] == "route_split"
        assert data["variant"] in ("v1", "v2")
        assert data["request_id"]
        assert data["route_to"] in VALID_DEPTS
        assert data["split_ratio"] == "50/50"
        assert data["routing_impl"]

    def test_route_v2_returns_selected_variant(self) -> None:
        resp = client.get("/v1/route_v2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["experiment"] == "route_split"
        assert data["variant"] in ("v1", "v2")
        assert data["endpoint"] == "/v1/route_v2"

    def test_same_request_id_same_variant_both_endpoints(self) -> None:
        v1 = client.get("/v1/route_v1", params={"request_id": "fixed-id-777"}).json()["variant"]
        v2 = client.get("/v1/route_v2", params={"request_id": "fixed-id-777"}).json()["variant"]
        assert v1 == v2

    def test_force_variant_override(self) -> None:
        assert client.get("/v1/route_v1", params={"force": "v1"}).json()["variant"] == "v1"
        assert client.get("/v1/route_v2", params={"force": "v2"}).json()["variant"] == "v2"

    def test_requires_api_key(self) -> None:
        resp = client.get("/v1/route_v1", headers={"X-API-Key": ""})
        assert resp.status_code == 401


# ── Live split distribution ────────────────────────────────────────


class TestSplitDistribution:
    def test_100_requests_split_near_50_50(self) -> None:
        """100 live requests -> report shows ~50/50 (35-65% tolerance)."""
        for i in range(100):
            rid = f"ab-{i:04d}"
            endpoint = "/v1/route_v1" if i % 2 == 0 else "/v1/route_v2"
            resp = client.get(endpoint, params={"request_id": rid})
            assert resp.status_code == 200

        resp = client.get("/v1/ab-test/report")
        assert resp.status_code == 200
        exp = resp.json()["experiments"]["route_split"]
        assert exp["total"] == 100
        v1_pct = exp["variants"]["v1"]["percentage"]
        v2_pct = exp["variants"]["v2"]["percentage"]
        assert 35 <= v1_pct <= 65, f"v1={v1_pct}% outside 35-65% (100 requests)"
        assert abs(v1_pct + v2_pct - 100) < 1


# ── Report endpoint ────────────────────────────────────────────────


class TestReportEndpoint:
    def test_report_has_legacy_and_experiment_sections(self) -> None:
        resp = client.get("/v1/ab-test/report")
        assert resp.status_code == 200
        data = resp.json()
        # v0.6.2 (ADR-017) report preserved — backward compatible
        assert "summary" in data
        assert "split_ratio" in data
        # CMD-002-A experiment layer merged
        assert "experiments" in data
        exp = data["experiments"]["route_split"]
        assert exp["variants"]["v1"]["count"] == 0
        assert exp["variants"]["v2"]["count"] == 0
        assert exp["split_ratio"] == "50/50"

    def test_report_counts_reflect_hits(self) -> None:
        client.get("/v1/route_v1", params={"force": "v1"})
        client.get("/v1/route_v2", params={"force": "v2"})
        client.get("/v1/route_v2", params={"force": "v2"})
        report = client.get("/v1/ab-test/report").json()["experiments"]["route_split"]
        assert report["total"] == 3
        assert report["variants"]["v1"]["count"] == 1
        assert report["variants"]["v2"]["count"] == 2
