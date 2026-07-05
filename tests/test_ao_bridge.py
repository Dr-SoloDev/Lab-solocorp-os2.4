"""
Unit tests for govctl_cli/ao/bridge.py (ENG-05).

All filesystem and network calls are mocked so the tests run without side
effects on the real queue or PID files.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bus_message(**kwargs):
    """Return a minimal BusMessage for testing."""
    from central_bus.models import BusMessage

    defaults = dict(
        from_dept="engineering",
        to_dept="orchestrator",
        type="AO_REQUEST",
        project_id="test-proj",
        phase="dev",
        payload={"agent_id": "engineering", "task": "Do something"},
        trace_id="trace-test-001",
        priority="high",
    )
    defaults.update(kwargs)
    return BusMessage(**defaults)


# ---------------------------------------------------------------------------
# handle_ao_message
# ---------------------------------------------------------------------------


def test_handle_ao_message_ignores_non_ao_request():
    """Non-AO_REQUEST messages are ignored — returns None."""
    from govctl_cli.ao.bridge import handle_ao_message

    msg = _make_bus_message(type="HANDOFF")
    result = handle_ao_message(msg)
    assert result is None


def test_handle_ao_message_processes_ao_request(tmp_path, monkeypatch):
    """AO_REQUEST is processed; a response BusMessage is returned and enqueued."""
    import central_bus.queue as queue_module
    import central_bus.audit as audit_module
    from govctl_cli.ao.bridge import handle_ao_message

    # Isolate the queue so we don't write to the real bus directory
    monkeypatch.setattr(queue_module, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(
        queue_module, "DEAD_LETTER_DIR", tmp_path / "queue" / "dead_letter"
    )
    (tmp_path / "queue").mkdir(parents=True, exist_ok=True)

    # Stub audit_log so we don't touch real audit files
    monkeypatch.setattr(audit_module, "log", lambda msg: None)

    msg = _make_bus_message()

    with patch("govctl_cli.ao.bridge.process_ao_request") as mock_process:
        mock_process.return_value = {
            "agent_id": "engineering",
            "trace_id": "trace-test-001",
            "status": "success",
            "result": {"output": "done"},
        }
        with patch("govctl_cli.ao.bridge.enqueue") as mock_enqueue:
            response = handle_ao_message(msg)

    assert response is not None
    assert response.type in ("AO_RESPONSE", "AO_ERROR")
    assert response.trace_id == "trace-test-001"
    mock_enqueue.assert_called_once()
    mock_process.assert_called_once_with(msg)


def test_handle_ao_message_error_response(monkeypatch):
    """When process_ao_request returns status=error, type is AO_ERROR."""
    import central_bus.audit as audit_module
    from govctl_cli.ao.bridge import handle_ao_message

    monkeypatch.setattr(audit_module, "log", lambda msg: None)

    msg = _make_bus_message()

    with patch("govctl_cli.ao.bridge.process_ao_request") as mock_process:
        mock_process.return_value = {
            "agent_id": "engineering",
            "trace_id": "trace-test-001",
            "status": "error",
            "error": "adapter failure",
        }
        with patch("govctl_cli.ao.bridge.enqueue"):
            response = handle_ao_message(msg)

    assert response is not None
    from govctl_cli.ao.bridge import AO_ERROR_TYPE
    assert response.type == AO_ERROR_TYPE


# ---------------------------------------------------------------------------
# process_queue
# ---------------------------------------------------------------------------


def test_process_queue_empty_returns_zero():
    """process_queue returns 0 when queue is empty."""
    from govctl_cli.ao.bridge import process_queue

    with patch("govctl_cli.ao.bridge.dequeue", return_value=None):
        count = process_queue(batch_size=5)

    assert count == 0


def test_process_queue_counts_processed_messages(monkeypatch):
    """process_queue returns the number of AO_REQUEST messages handled.

    process_queue calls ``dequeue("high") or dequeue("normal") or dequeue("low")``
    per loop iteration, so we use a side_effect that returns a message only on
    the first "high" call and None for all other calls.
    """
    import central_bus.audit as audit_module
    from govctl_cli.ao.bridge import process_queue

    monkeypatch.setattr(audit_module, "log", lambda msg: None)

    msg1 = _make_bus_message(trace_id="t1")

    # Return msg1 on first call (high priority), None on all subsequent calls.
    call_count = {"n": 0}

    def _dequeue_side_effect(priority):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return msg1
        return None

    with patch("govctl_cli.ao.bridge.dequeue", side_effect=_dequeue_side_effect):
        with patch("govctl_cli.ao.bridge.handle_ao_message", return_value=MagicMock()):
            with patch("govctl_cli.ao.bridge.enqueue"):
                count = process_queue(batch_size=5)

    assert count == 1


# ---------------------------------------------------------------------------
# daemon_status / _read_pid / _is_running
# ---------------------------------------------------------------------------


def test_daemon_status_not_running(tmp_path, monkeypatch):
    """daemon_status returns running=False when no PID file exists."""
    from govctl_cli.ao import bridge as bridge_mod

    monkeypatch.setattr(bridge_mod, "PID_FILE", tmp_path / "ao_bridge.pid")

    status = bridge_mod.daemon_status()
    assert status["running"] is False
    assert status["pid"] is None


def test_daemon_status_running(tmp_path, monkeypatch):
    """daemon_status returns running=True when PID file contains live process."""
    from govctl_cli.ao import bridge as bridge_mod

    pid_file = tmp_path / "ao_bridge.pid"
    pid_file.write_text("99999")  # arbitrary PID

    monkeypatch.setattr(bridge_mod, "PID_FILE", pid_file)

    # _is_running uses os.kill(pid, 0); mock it to return True
    with patch("govctl_cli.ao.bridge._is_running", return_value=True):
        status = bridge_mod.daemon_status()

    assert status["running"] is True
    assert status["pid"] == 99999


# ---------------------------------------------------------------------------
# cmd_status (smoke)
# ---------------------------------------------------------------------------


def test_cmd_status_smoke(tmp_path, monkeypatch):
    """cmd_status runs without raising even when daemon is stopped."""
    from govctl_cli.ao import bridge as bridge_mod

    monkeypatch.setattr(bridge_mod, "PID_FILE", tmp_path / "ao_bridge.pid")

    result = bridge_mod.cmd_status()
    assert isinstance(result, dict)
    assert "running" in result
