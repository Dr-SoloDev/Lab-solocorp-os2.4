"""Integration tests for Central Bus v0.6.

Tests the full observe → route → update → AAR flow end-to-end.
"""

from __future__ import annotations

import json
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from central_bus.db import DbManager, ensure_db, reset_db_for_testing
from central_bus.config import settings
from central_bus.main import app
from central_bus.guard_runner import BusGuardRunner


pytestmark = pytest.mark.usefixtures("_setup_db")


@pytest_asyncio.fixture
async def _setup_db():
    """Ensure the DB is initialised in :memory: mode for the test client."""
    reset_db_for_testing()
    old_path = settings.db_path
    settings.db_path = ":memory:"
    db = await ensure_db()
    yield
    await db.close()
    reset_db_for_testing()
    settings.db_path = old_path


client = TestClient(app)
client.headers.setdefault("X-API-Key", "sk-solocorp-admin-local-dev-001")


# ── Health check ─────────────────────────────────────────────────


class TestHealth:
    def test_health_endpoint(self) -> None:
        resp = client.get("/v1/health")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "status" in data
        assert "version" in data
        assert data["version"] == "0.6.0"

    def test_health_returns_metrics(self) -> None:
        resp = client.get("/v1/health")
        assert resp.status_code in (200, 503)
        data = resp.json()
        if "db" in data:
            assert "queue_pending" in data["db"]
            assert "queue_failed" in data["db"]
            assert "queue_dead" in data["db"]
        assert "uptime_seconds" in data


# ── Observe endpoint ────────────────────────────────────────────


class TestObserve:
    def test_observe_basic(self) -> None:
        resp = client.post(
            "/v1/observe",
            json={
                "task_id": "integration-test-task",
                "source_agent": "test-agent",
                "payload": {"type": "code", "feature": "auth"},
                "priority": "high",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "routed"
        assert data["queue_id"] is not None
        assert data["trace_id"] is not None
        assert "route_to" in data
        assert "hops" in data

    def test_observe_missing_task_id(self) -> None:
        resp = client.post(
            "/v1/observe",
            json={"source_agent": "test-agent", "payload": {}},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_observe_missing_source_agent(self) -> None:
        resp = client.post(
            "/v1/observe",
            json={"task_id": "t1", "payload": {}},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data

    def test_observe_invalid_payload_type(self) -> None:
        resp = client.post(
            "/v1/observe",
            json={
                "task_id": "t1",
                "source_agent": "a1",
                "payload": [1, 2, 3],
            },
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_observe_invalid_json(self) -> None:
        resp = client.post(
            "/v1/observe",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data


# ── Context endpoint ────────────────────────────────────────────


class TestContext:
    def test_context_basic(self) -> None:
        resp = client.post(
            "/v1/context",
            json={
                "agent_id": "test-agent",
                "keys": [],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "context_id" in data
        assert data["facts"] == []
        assert "queue_pending" in data
        assert data["agent_health"] == "ok"

    def test_context_with_facts(self) -> None:
        # First set a fact via update
        from central_bus.db import ensure_db, now_iso
        import asyncio

        async def _set_fact():
            db = await ensure_db()
            await db.init()
            await db.execute(
                "INSERT INTO facts (key, value, version, metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("test.fact.hello", '"world"', 1, "{}", now_iso(), now_iso()),
            )

        asyncio.run(_set_fact())

        resp = client.post(
            "/v1/context",
            json={
                "agent_id": "test-agent",
                "keys": ["test.fact.*"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["facts"]) >= 1
        fact_keys = {f["key"] for f in data["facts"]}
        assert "test.fact.hello" in fact_keys

    def test_context_missing_agent_id(self) -> None:
        resp = client.post(
            "/v1/context",
            json={"keys": []},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data


# ── Update endpoint ─────────────────────────────────────────────


class TestUpdate:
    def test_update_completed(self) -> None:
        # First create a message
        observe_resp = client.post(
            "/v1/observe",
            json={
                "task_id": "update-test",
                "source_agent": "test-agent",
                "payload": {"type": "code"},
            },
        )
        assert observe_resp.status_code == 200
        queue_id = observe_resp.json()["queue_id"]
        trace_id = observe_resp.json()["trace_id"]

        # Then complete it
        resp = client.post(
            "/v1/update",
            json={
                "trace_id": trace_id,
                "queue_id": queue_id,
                "agent_id": "test-agent",
                "status": "completed",
                "result": {"output": "done"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "aar_id" in data
        assert data["dead_letter"] is False

    def test_update_nonexistent_queue(self) -> None:
        resp = client.post(
            "/v1/update",
            json={
                "trace_id": "no-such",
                "queue_id": "no-such-id",
                "agent_id": "test",
                "status": "completed",
            },
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_update_failed_dead_letter(self) -> None:
        # Create message with low max_retries
        observe_resp = client.post(
            "/v1/observe",
            json={
                "task_id": "fail-test",
                "source_agent": "test-agent",
                "payload": {"type": "code"},
                "priority": "low",
                "max_retries": 1,
            },
        )
        queue_id = observe_resp.json()["queue_id"]
        trace_id = observe_resp.json()["trace_id"]

        # Fail once (should dead-letter with max_retries=1)
        for _ in range(2):
            resp = client.post(
                "/v1/update",
                json={
                    "trace_id": trace_id,
                    "queue_id": queue_id,
                    "agent_id": "test-agent",
                    "status": "failed",
                    "error": "something broke",
                },
            )

        data = resp.json()
        assert data["dead_letter"] is True

    def test_update_missing_fields(self) -> None:
        resp = client.post(
            "/v1/update",
            json={"agent_id": "test-agent", "status": "completed"},
        )
        assert resp.status_code == 400


# ── AAR retrieval ───────────────────────────────────────────────


class TestAAR:
    def test_get_aar_nonexistent(self) -> None:
        resp = client.get("/v1/aar/no-such-trace")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_aar_after_completion(self) -> None:
        """Complete a message, then fetch its AAR."""
        observe_resp = client.post(
            "/v1/observe",
            json={
                "task_id": "aar-test",
                "source_agent": "test-agent",
                "payload": {"type": "code"},
            },
        )
        trace_id = observe_resp.json()["trace_id"]
        queue_id = observe_resp.json()["queue_id"]

        client.post(
            "/v1/update",
            json={
                "trace_id": trace_id,
                "queue_id": queue_id,
                "agent_id": "test-agent",
                "status": "completed",
                "result": {"ok": True},
            },
        )

        resp = client.get(f"/v1/aar/{trace_id}")
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) >= 1
        entry = entries[0]
        assert entry["trace_id"] == trace_id
        assert entry["final_status"] == "completed"
        assert entry["latency_ms"] >= 0


# ── BusGuardRunner unit tests ────────────────────────────────────


class TestBusGuardRunner:
    @pytest.mark.asyncio
    async def test_guard_pass(self) -> None:
        """Valid message passes all checks and returns True."""
        guard = BusGuardRunner()
        result = await guard.check({
            "source_agent": "test-agent",
            "payload": {"type": "code"},
            "priority": "high",
        })
        assert result is True

    @pytest.mark.asyncio
    async def test_guard_fail_missing_source(self) -> None:
        """Empty source_agent raises ValueError."""
        guard = BusGuardRunner()
        with pytest.raises(ValueError, match="source_agent"):
            await guard.check({
                "source_agent": "",
                "payload": {"type": "code"},
                "priority": "normal",
            })

    @pytest.mark.asyncio
    async def test_guard_fail_invalid_payload(self) -> None:
        """Payload as list raises ValueError."""
        guard = BusGuardRunner()
        with pytest.raises(ValueError, match="payload"):
            await guard.check({
                "source_agent": "test-agent",
                "payload": [1, 2, 3],
                "priority": "normal",
            })

    @pytest.mark.asyncio
    async def test_guard_fail_invalid_priority(self) -> None:
        """Unknown priority value raises ValueError."""
        guard = BusGuardRunner()
        with pytest.raises(ValueError, match="priority"):
            await guard.check({
                "source_agent": "test-agent",
                "payload": {"type": "code"},
                "priority": "urgent",
            })

    @pytest.mark.asyncio
    async def test_full_pipeline_with_guard(self) -> None:
        """Full pipeline: guard.check() passes → observe → route → update."""
        message = {
            "source_agent": "pipeline-agent",
            "payload": {"type": "code", "feature": "guard"},
            "priority": "normal",
        }

        # Step 1: pre-flight guard check
        guard = BusGuardRunner()
        guard_result = await guard.check(message)
        assert guard_result is True

        # Step 2: observe (route)
        observe_resp = client.post(
            "/v1/observe",
            json={"task_id": "guard-pipeline-test", **message},
        )
        assert observe_resp.status_code == 200
        data = observe_resp.json()
        assert data["status"] == "routed"
        queue_id = data["queue_id"]
        trace_id = data["trace_id"]
        assert queue_id is not None
        assert trace_id is not None

        # Step 3: update (complete)
        update_resp = client.post(
            "/v1/update",
            json={
                "trace_id": trace_id,
                "queue_id": queue_id,
                "agent_id": "pipeline-agent",
                "status": "completed",
                "result": {"guard_checked": True},
            },
        )
        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["status"] == "completed"
        assert update_data["dead_letter"] is False
