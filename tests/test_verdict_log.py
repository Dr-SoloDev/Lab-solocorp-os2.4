"""Verdict log v0 tests — hermetic (tmp_path + fakes, never touches prod state/inbox)."""
import json
from datetime import timedelta
from pathlib import Path

import loop_runner.main as M
import loop_runner.runner as R
import loop_runner.verdict_log as V


class FakeLoop(R.Loop):
    loop_id = "test-fake"
    interval = timedelta(hours=1)
    trust_level = 1
    mode = "pass"

    def should_run(self):
        return self.mode != "notdue"

    def run(self):
        if self.mode == "pass":
            return "✅ done"
        if self.mode == "skip":
            return "⏭ SKIP (x)"
        raise RuntimeError("boom")


def _lines(vdir: Path):
    day = __import__("datetime").date.today().isoformat()
    f = vdir / f"{day}.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()]


def test_main_logs_not_due(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "VDIR", tmp_path)
    monkeypatch.setattr(M, "ALL_LOOPS", [FakeLoop()])
    FakeLoop.mode = "notdue"
    M.main()
    got = _lines(tmp_path)
    assert len(got) == 1 and got[0]["verdict"] == "NOT_DUE" and got[0]["loop_id"] == "test-fake"


def test_main_dry_run_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "VDIR", tmp_path)
    monkeypatch.setattr(M, "ALL_LOOPS", [FakeLoop()])
    FakeLoop.mode = "notdue"
    M.main(dry_run=True)
    assert _lines(tmp_path) == []


def test_execute_verdicts(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "VDIR", tmp_path)
    monkeypatch.setattr(R, "record", lambda *a, **k: None)
    for mode, want in [("pass", "PASS"), ("skip", "SKIP")]:
        FakeLoop.mode = mode
        FakeLoop().execute()
    FakeLoop.mode = "fail"
    try:
        FakeLoop().execute()
    except RuntimeError:
        pass
    assert [l["verdict"] for l in _lines(tmp_path)] == ["PASS", "SKIP", "FAIL"]


def test_infer_and_fingerprint():
    assert V.infer_verdict("⏭ SKIP (x)") == "SKIP"
    assert V.infer_verdict("✅ ok") == "PASS"
    assert V.infer_verdict("⚠️ bad") == "FAIL"
    assert "111" in V.fingerprint("failed: <urlopen error [Errno 111] Conn>")
    assert V.fingerprint("at 2026-10-10T19:00:02+07:00 x") == V.fingerprint("at 2026-10-11T20:00:02+07:00 x")


def test_append_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "VDIR", Path("/nonexistent-dir-xyz/test"))
    V.append_verdict("x", "PASS", "y")  # must not raise (fail-safe telemetry)
