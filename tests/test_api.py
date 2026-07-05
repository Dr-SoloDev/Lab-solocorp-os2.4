"""
Phase 3-4 Integration Tests — API, Pipeline, Dashboard

Uses FastAPI TestClient (httpx) to test API endpoints against the real
FastAPI app.  All tests are self-contained — they run against the actual
API app instance with real file-system reads from bus/ and gov/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from govctl_cli.api.main import app
from govctl_cli.monitor import collect_metrics, list_projects, count_toml

# ---------------------------------------------------------------------------
# Test client fixture
# ---------------------------------------------------------------------------

client = TestClient(app)


# ===========================================================================
# Health
# ===========================================================================


class TestAPIHealth:
    def test_api_health_returns_200(self):
        """GET /api/v1/health returns ok status (may be 200 or 503)."""
        resp = client.get("/api/v1/health")
        # Health may return 503 when degraded (e.g. AO CLI not installed)
        assert resp.status_code in (200, 503)
        data = resp.json()
        # In degraded state, data is wrapped in {"detail": {...}}
        if resp.status_code == 503:
            data = data.get("detail", data)
        assert "status" in data
        assert data["status"] in ("ok", "degraded")

    def test_api_health_has_components(self):
        """Health response includes component status dict."""
        resp = client.get("/api/v1/health")
        data = resp.json()
        if resp.status_code == 503:
            data = data.get("detail", data)
        assert "components" in data
        assert "api" in data["components"]
        assert "gov_dir" in data["components"]

    def test_health_status_is_ok_not_healthy(self):
        """Health status must be ok or degraded — never 'healthy'."""
        resp = client.get("/api/v1/health")
        assert resp.status_code in (200, 503)
        data = resp.json()
        if resp.status_code == 503:
            data = data.get("detail", data)
        assert data.get("status") != "healthy", (
            f"status must not be 'healthy', got {data.get('status')!r}"
        )
        assert data.get("status") in ("ok", "degraded"), (
            f"status must be ok or degraded, got {data.get('status')!r}"
        )


# ===========================================================================
# Governance endpoints
# ===========================================================================


class TestGovernanceAPI:
    def test_api_list_adrs_returns_items(self):
        """GET /api/v1/gov/adrs returns items list."""
        resp = client.get("/api/v1/gov/adrs")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_api_list_adrs_count_matches_toml(self):
        """ADR count from API matches actual TOML file count."""
        resp = client.get("/api/v1/gov/adrs")
        data = resp.json()
        expected = count_toml(_project_root / "gov" / "adr")
        assert data["total"] == expected

    def test_api_list_rfcs_returns_items(self):
        """GET /api/v1/gov/rfcs returns items list."""
        resp = client.get("/api/v1/gov/rfcs")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_api_list_guards_returns_items(self):
        """GET /api/v1/gov/guards returns items list."""
        resp = client.get("/api/v1/gov/guards")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_api_create_adr(self):
        """POST /api/v1/gov/adrs creates a new ADR (201 + file created)."""
        resp = client.post("/api/v1/gov/adrs", json={
            "title": "Test ADR via API",
            "status": "proposed",
            "domain": "test",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data

        # Verify a TOML file was created on disk
        adr_id = data["id"]
        adr_path = _project_root / "gov" / "adr" / f"{adr_id}.toml"
        assert adr_path.exists(), f"ADR file not created: {adr_path}"

        # Cleanup
        if adr_path.exists():
            adr_path.unlink()

    def test_api_get_adr_by_id(self):
        """GET /api/v1/gov/adrs/{id} returns detail."""
        # Pick first available ADR
        resp = client.get("/api/v1/gov/adrs")
        adrs = resp.json().get("items", [])
        if not adrs:
            pytest.skip("No ADRs available to test GET by ID")

        adr_id = adrs[0]["id"]
        resp = client.get(f"/api/v1/gov/adrs/{adr_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == adr_id
        assert "decision" in data or "context" in data

    def test_api_get_nonexistent_adr_returns_404(self):
        """GET /api/v1/gov/adrs/NONEXISTENT returns 404."""
        resp = client.get("/api/v1/gov/adrs/NONEXISTENT-999")
        assert resp.status_code == 404


# ===========================================================================
# Agent endpoints
# ===========================================================================


class TestAgentAPI:
    def test_api_list_agents_returns_items(self):
        """GET /api/v1/agents returns items list."""
        resp = client.get("/api/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_api_list_agents_has_expected_ids(self):
        """Agent list contains required agent IDs."""
        resp = client.get("/api/v1/agents")
        data = resp.json()
        ids = {a["agent_id"] for a in data["items"]}
        expected = {"ceo", "orchestrator"}
        assert expected.issubset(ids), f"Missing agents. Got: {ids}"

    def test_api_run_unknown_agent_returns_404(self):
        """POST /api/v1/agents/unknown/run returns 404."""
        resp = client.post("/api/v1/agents/unknown/run", json={"context": {"task": "test"}})
        assert resp.status_code == 404

    def test_api_run_known_agent_returns_202(self):
        """POST /api/v1/agents/ceo/run returns 202."""
        resp = client.post("/api/v1/agents/ceo/run", json={
            "context": {"task": "Evaluate test project", "project_id": "test-integration"},
        })
        # 202 or 200 depending on whether async queuing or sync fallback
        assert resp.status_code in (200, 202)
        data = resp.json()
        assert "status" in data
        assert data["status"] in ("pending", "queued")
        assert data["agent_id"] == "ceo"


# ===========================================================================
# Pipeline endpoints
# ===========================================================================


class TestPipelineAPI:
    def test_api_pipeline_status_returns_list(self):
        """GET /api/v1/pipeline/status returns a list of projects."""
        resp = client.get("/api/v1/pipeline/status")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_api_pipeline_project_has_required_fields(self):
        """Each project in pipeline has required fields."""
        resp = client.get("/api/v1/pipeline/status")
        projects = resp.json()
        if projects:
            p = projects[0]
            assert "project_id" in p
            assert "name" in p
            assert "status" in p
            assert "phase" in p
            assert "progress_pct" in p
            assert "phases" in p


# ===========================================================================
# Metrics / Monitoring
# ===========================================================================


class TestMetricsAPI:
    def test_api_metrics_returns_all_keys(self):
        """GET /api/v1/metrics returns complete metrics object."""
        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200
        data = resp.json()
        required_keys = [
            "timestamp", "active_projects", "queued_messages",
            "queued_by_priority", "health_score",
        ]
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"

    def test_api_metrics_priority_breakdown(self):
        """queued_by_priority has the correct keys."""
        resp = client.get("/api/v1/metrics")
        data = resp.json()
        q = data.get("queued_by_priority", {})
        for p in ("critical", "high", "normal", "low"):
            assert p in q, f"Missing priority: {p}"

    def test_api_metrics_non_negative_counts(self):
        """All numeric metric values are non-negative."""
        resp = client.get("/api/v1/metrics")
        data = resp.json()
        for key in ("active_projects", "queued_messages", "dead_letter_count"):
            assert data.get(key, 0) >= 0, f"{key} negative: {data.get(key)}"


# ===========================================================================
# Dashboard static files
# ===========================================================================


class TestDashboardStatic:
    def test_dashboard_index_served(self):
        """GET / returns dashboard HTML."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "SoloCorp" in resp.text

    def test_dashboard_css_served(self):
        """GET /static/dashboard.css returns CSS."""
        resp = client.get("/static/dashboard.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers["content-type"]

    def test_dashboard_js_served(self):
        """GET /static/dashboard.js returns JS."""
        resp = client.get("/static/dashboard.js")
        assert resp.status_code == 200
        ct = resp.headers["content-type"]
        assert "javascript" in ct or "text" in ct


# ===========================================================================
# Monitor collector unit tests (pure, no HTTP)
# ===========================================================================


class TestMonitorCollector:
    def test_collect_metrics_returns_dict(self):
        """collect_metrics() returns a dict with expected keys."""
        metrics = collect_metrics()
        assert isinstance(metrics, dict)
        for key in ("timestamp", "active_projects", "queued_messages", "adr_count", "rfc_count", "guard_count", "agent_count", "recent_events"):
            assert key in metrics, f"Missing key: {key}"

    def test_collect_metrics_counts_match_files(self):
        """collect_metrics() counts match actual file counts."""
        metrics = collect_metrics()
        assert metrics["adr_count"] == count_toml(_project_root / "gov" / "adr")
        assert metrics["rfc_count"] == count_toml(_project_root / "gov" / "rfc")
        assert metrics["guard_count"] == count_toml(_project_root / "gov" / "guards")

    def test_list_projects_returns_list(self):
        """list_projects() returns a list of project dicts."""
        projects = list_projects()
        assert isinstance(projects, list)
        if projects:
            p = projects[0]
            for key in ("project_id", "name", "status", "phase", "progress_pct", "phases"):
                assert key in p, f"Missing key: {key}"

    def test_count_toml_on_nonexistent_dir(self):
        """count_toml() returns 0 for nonexistent directory."""
        assert count_toml(Path("/nonexistent/path")) == 0

    def test_agent_count_always_5(self):
        """agent_count is always 5."""
        metrics = collect_metrics()
        assert metrics["agent_count"] == 5

    def test_total_queued_equals_sum(self):
        """total_queued equals sum of all priority queues."""
        metrics = collect_metrics()
        q = metrics["queued_messages"]
        expected = sum(q.values())
        assert metrics["total_queued"] == expected
