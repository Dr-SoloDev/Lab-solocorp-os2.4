"""Tests for central_bus.queue — SQLiteQueueManager."""

from __future__ import annotations

import json
import pytest
import pytest_asyncio

from central_bus.db import DbManager
from central_bus.queue import SQLiteQueueManager, enqueue, dequeue, USE_SQLITE
from central_bus.models import BusMessage


@pytest_asyncio.fixture
async def db():
    """Fresh in-memory SQLite database for each test."""
    d = DbManager(db_path=":memory:")
    await d.init()
    yield d
    await d.close()


@pytest_asyncio.fixture
async def qm(db):
    """SQLiteQueueManager backed by the test database."""
    return SQLiteQueueManager(db)


# ── create_message ────────────────────────────────────────────────


class TestCreateMessage:
    async def test_basic_create(self, qm: SQLiteQueueManager) -> None:
        msg = await qm.create_message(
            trace_id="trace-001",
            task_id="task-001",
            agent_id="changful",
            payload={"action": "build", "feature": "auth"},
        )
        assert msg["trace_id"] == "trace-001"
        assert msg["task_id"] == "task-001"
        assert msg["agent_id"] == "changful"
        assert msg["status"] == "pending"
        assert msg["priority"] == "normal"
        assert msg["retry_count"] == 0
        assert msg["max_retries"] == 3
        assert msg["id"] is not None

    async def test_create_with_overrides(self, qm: SQLiteQueueManager) -> None:
        msg = await qm.create_message(
            trace_id="trace-002",
            task_id="task-002",
            agent_id="architect",
            payload={"type": "RFC"},
            target_agent="product",
            priority="high",
            max_retries=5,
        )
        assert msg["target_agent"] == "product"
        assert msg["priority"] == "high"
        assert msg["max_retries"] == 5

    async def test_id_is_unique(self, qm: SQLiteQueueManager) -> None:
        m1 = await qm.create_message("t1", "t1", "a1", {})
        m2 = await qm.create_message("t2", "t2", "a2", {})
        assert m1["id"] != m2["id"]


# ── get_message ──────────────────────────────────────────────────


class TestGetMessage:
    async def test_get_existing(self, qm: SQLiteQueueManager) -> None:
        created = await qm.create_message("t1", "t1", "a1", {"hello": "world"})
        fetched = await qm.get_message(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert json.loads(fetched["payload"]) == {"hello": "world"}

    async def test_get_nonexistent(self, qm: SQLiteQueueManager) -> None:
        fetched = await qm.get_message("nonexistent-id")
        assert fetched is None


# ── get_pending ──────────────────────────────────────────────────


class TestGetPending:
    async def test_empty_queue(self, qm: SQLiteQueueManager) -> None:
        pending = await qm.get_pending()
        assert pending == []

    async def test_returns_pending_only(self, qm: SQLiteQueueManager) -> None:
        m = await qm.create_message("t1", "t1", "a1", {})
        await qm.update_status(m["id"], "completed")
        pending = await qm.get_pending()
        assert len(pending) == 0

    async def test_priority_order(self, qm: SQLiteQueueManager) -> None:
        await qm.create_message("t1", "t1", "a1", {}, priority="low")
        await qm.create_message("t2", "t2", "a2", {}, priority="critical")
        await qm.create_message("t3", "t3", "a3", {}, priority="high")
        pending = await qm.get_pending(limit=10)
        assert len(pending) == 3
        priorities = [p["priority"] for p in pending]
        assert priorities == ["critical", "high", "low"]

    async def test_filter_by_agent(self, qm: SQLiteQueueManager) -> None:
        await qm.create_message("t1", "t1", "alice", {})
        await qm.create_message("t2", "t2", "bob", {})
        alice_msgs = await qm.get_pending(agent_id="alice")
        assert len(alice_msgs) == 1
        assert alice_msgs[0]["agent_id"] == "alice"

    async def test_filter_by_priority(self, qm: SQLiteQueueManager) -> None:
        await qm.create_message("t1", "t1", "a1", {}, priority="high")
        await qm.create_message("t2", "t2", "a2", {}, priority="normal")
        high_msgs = await qm.get_pending(priority="high")
        assert len(high_msgs) == 1
        assert high_msgs[0]["priority"] == "high"

    async def test_limit(self, qm: SQLiteQueueManager) -> None:
        for i in range(5):
            await qm.create_message(f"t{i}", f"t{i}", "a1", {})
        pending = await qm.get_pending(limit=3)
        assert len(pending) == 3


# ── update_status ────────────────────────────────────────────────


class TestUpdateStatus:
    async def test_update_to_completed(self, qm: SQLiteQueueManager) -> None:
        m = await qm.create_message("t1", "t1", "a1", {})
        updated = await qm.update_status(m["id"], "completed")
        assert updated["status"] == "completed"
        assert updated["completed_at"] is not None

    async def test_error_log_append(self, qm: SQLiteQueueManager) -> None:
        m = await qm.create_message("t1", "t1", "a1", {})
        await qm.update_status(m["id"], "failed", error="Timeout")
        updated = await qm.update_status(m["id"], "failed", error="Again")
        errors = json.loads(updated["error_log"])
        assert len(errors) == 2
        assert errors[0]["error"] == "Timeout"
        assert errors[1]["error"] == "Again"

    async def test_dead_letter_after_max_retries(self, qm: SQLiteQueueManager) -> None:
        m = await qm.create_message(
            "t1", "t1", "a1", {}, max_retries=2,
        )
        # First fail (retry_count 0->1)
        await qm.update_status(m["id"], "failed", error="err1")
        # Second fail (retry_count 1->2, hits limit)
        await qm.update_status(m["id"], "failed", error="err2")

        dls = await qm.get_dead_letters()
        assert len(dls) == 1
        assert dls[0]["queue_id"] == m["id"]

    async def test_update_nonexistent(self, qm: SQLiteQueueManager) -> None:
        with pytest.raises(ValueError):
            await qm.update_status("no-such-id", "completed")


# ── counts ───────────────────────────────────────────────────────


class TestCounts:
    async def test_count_pending(self, qm: SQLiteQueueManager) -> None:
        assert await qm.count_pending() == 0
        m1 = await qm.create_message("t1", "t1", "a1", {})
        m2 = await qm.create_message("t2", "t2", "a2", {})
        assert await qm.count_pending() == 2
        await qm.update_status(m1["id"], "completed")
        assert await qm.count_pending() == 1

    async def test_count_failed(self, qm: SQLiteQueueManager) -> None:
        assert await qm.count_failed() == 0
        m = await qm.create_message("t1", "t1", "a1", {})
        await qm.update_status(m["id"], "failed", error="bad")
        assert await qm.count_failed() == 1

    async def test_count_dead_letters(self, qm: SQLiteQueueManager) -> None:
        assert await qm.count_dead_letters() == 0
        m = await qm.create_message("t1", "t1", "a1", {}, max_retries=1)
        await qm.update_status(m["id"], "failed", error="boom")
        assert await qm.count_dead_letters() == 1


# ── Backward compat JSONL functions ──────────────────────────────


class TestJsonlBackwardCompat:
    """These tests verify that existing JSONL functions still work."""

    _saved_offsets: dict[str, int] = {}

    def setup_method(self) -> None:
        """Save current offsets and set them to end-of-file so test messages are read."""
        from central_bus.queue import _read_offset, _write_offset, QUEUE_DIR
        import os
        for p in ("high", "normal", "low"):
            path = QUEUE_DIR / f"{p}.jsonl"
            line_count = 0
            if path.exists():
                with open(path) as f:
                    line_count = sum(1 for _ in f)
            self._saved_offsets[p] = _read_offset(p)
            _write_offset(p, line_count)

    def teardown_method(self) -> None:
        """Restore saved offsets."""
        from central_bus.queue import _read_offset, _write_offset
        # Rewind the file to undo the test's dequeue
        for p, offset in self._saved_offsets.items():
            _write_offset(p, offset)

    def test_enqueue_dequeue(self) -> None:
        """Basic JSONL enqueue/dequeue."""
        msg = BusMessage(
            from_dept="engineering", to_dept="qa",
            type="HANDOFF", project_id="test", phase="dev",
            payload={"file": "test.py"}, trace_id="jsonl-test",
        )
        enqueue(msg)
        result = dequeue("normal")
        assert result is not None
        assert result.trace_id == "jsonl-test"
        assert result.from_dept == "engineering"
