import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from central_bus import BusMessage, enqueue, dequeue, drain, route, priority_for


def make_msg(**kwargs) -> BusMessage:
    defaults = dict(
        from_dept="engineering", to_dept="qa", type="HANDOFF",
        project_id="proj_test", phase="dev",
        payload={"text": "test"}, trace_id="trace_001"
    )
    return BusMessage(**{**defaults, **kwargs})


# ── Queue tests ──────────────────────────────────────────────────────────────

def test_enqueue_dequeue(tmp_path, monkeypatch):
    import central_bus.queue as q
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path)
    msg = make_msg()
    enqueue(msg)
    result = dequeue("normal")
    assert result is not None
    assert result.id == msg.id

def test_dequeue_empty(tmp_path, monkeypatch):
    import central_bus.queue as q
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path)
    assert dequeue("normal") is None

def test_fifo_order(tmp_path, monkeypatch):
    import central_bus.queue as q
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path)
    m1, m2 = make_msg(), make_msg()
    enqueue(m1)
    enqueue(m2)
    assert dequeue("normal").id == m1.id
    assert dequeue("normal").id == m2.id

def test_drain(tmp_path, monkeypatch):
    import central_bus.queue as q
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path)
    for _ in range(3):
        enqueue(make_msg())
    msgs = drain("normal")
    assert len(msgs) == 3
    assert dequeue("normal") is None

def test_priority_queues_isolated(tmp_path, monkeypatch):
    import central_bus.queue as q
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path)
    high_msg = make_msg(priority="high")
    enqueue(high_msg)
    assert dequeue("normal") is None
    assert dequeue("high").id == high_msg.id


# ── Router tests ─────────────────────────────────────────────────────────────

def test_route_to_qa():
    msg = make_msg(payload={"text": "run test suite and check quality"})
    assert route(msg) == "qa"

def test_route_to_engineering():
    msg = make_msg(payload={"text": "fix backend bug in API"})
    assert route(msg) == "engineering"

def test_route_to_cfo():
    msg = make_msg(payload={"text": "review budget and cost"})
    assert route(msg) == "cfo"

def test_route_to_web3():
    msg = make_msg(payload={"text": "deploy smart contract on solana"})
    assert route(msg) == "web3"

def test_route_to_legal():
    msg = make_msg(payload={"text": "check pdpa compliance"})
    assert route(msg) == "legal"

def test_route_fallback():
    msg = make_msg(payload={"text": "random unrelated topic xyz"})
    assert route(msg) == "ceo"

def test_priority_for_qa():
    assert priority_for("qa") == "high"

def test_priority_for_engineering():
    assert priority_for("engineering") == "normal"

def test_priority_for_unknown():
    assert priority_for("ceo") == "normal"
