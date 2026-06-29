import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from central_bus.models import BusMessage
from central_bus.exceptions import classify, handle, escalate, read_escalations


def make_msg(text="error occurred", project_id="proj_p3") -> BusMessage:
    return BusMessage(
        from_dept="engineering", to_dept="qa", type="EXCEPTION",
        project_id=project_id, phase="dev",
        payload={"text": text}, trace_id="trace_p3"
    )


# ── Classify tests ───────────────────────────────────────────────────────────

def test_classify_critical():
    assert classify(make_msg("production down critical crash")) == "CRITICAL"

def test_classify_high():
    assert classify(make_msg("task failed with error")) == "HIGH"

def test_classify_med():
    assert classify(make_msg("performance degraded warning")) == "MED"

def test_classify_low():
    assert classify(make_msg("task completed successfully")) == "LOW"


# ── Handle + Retry tests ─────────────────────────────────────────────────────

def test_handle_success_no_retry():
    fn = MagicMock(return_value="ok")
    result = handle(make_msg(), fn)
    assert result == "ok"
    assert fn.call_count == 1

def test_handle_retries_on_failure(monkeypatch, tmp_path):
    import central_bus.exceptions as ex
    monkeypatch.setattr(ex, "ESCALATION_LOG", tmp_path / "esc.jsonl")
    monkeypatch.setattr(ex, "RETRY_DELAYS", [0, 0, 0])

    call_count = 0
    def flaky(msg):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("transient")
        return "recovered"

    result = handle(make_msg(), flaky)
    assert result == "recovered"
    assert call_count == 3

def test_handle_exhausted_escalates(monkeypatch, tmp_path):
    import central_bus.exceptions as ex
    monkeypatch.setattr(ex, "ESCALATION_LOG", tmp_path / "esc.jsonl")
    monkeypatch.setattr(ex, "RETRY_DELAYS", [0, 0, 0])

    with pytest.raises(RuntimeError):
        handle(make_msg("error"), lambda m: (_ for _ in ()).throw(RuntimeError("boom")))

    entries = [l for l in (tmp_path / "esc.jsonl").read_text().splitlines() if l]
    assert len(entries) == 1


# ── Escalate tests ───────────────────────────────────────────────────────────

def test_escalate_logs_entry(tmp_path, monkeypatch):
    import central_bus.exceptions as ex
    monkeypatch.setattr(ex, "ESCALATION_LOG", tmp_path / "esc.jsonl")
    escalate(make_msg(), "HIGH", reason="test reason")
    entries = read_escalations.__wrapped__(tmp_path / "esc.jsonl") if hasattr(read_escalations, "__wrapped__") else None
    # read directly
    import json
    lines = (tmp_path / "esc.jsonl").read_text().splitlines()
    entry = json.loads(lines[0])
    assert entry["severity"] == "HIGH"
    assert entry["reason"] == "test reason"

def test_escalate_critical_writes_ceo_alert(tmp_path, monkeypatch):
    import central_bus.exceptions as ex
    monkeypatch.setattr(ex, "ESCALATION_LOG", tmp_path / "esc.jsonl")
    alert_path = tmp_path / "ceo_alerts.jsonl"
    monkeypatch.setattr(ex, "_notify_ceo", lambda e: alert_path.open("a").write(
        __import__("json").dumps(e) + "\n"
    ))
    escalate(make_msg("critical crash"), "CRITICAL", reason="system down")
    assert alert_path.exists()
