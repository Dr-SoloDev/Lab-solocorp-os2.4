"""Regression: llm_provider ต้องไม่ส่ง flag ที่ `opencode run` ไม่รู้จัก

เคสจริง 2026-10-25: `opencode run --pure ...` →
"Unrecognized flag: --pure in command opencode run" → ทั้ง 7 โมเดลใน fallback
chain ล้มเหมือนกันหมด → `think()` คืน "⚠️ LLM ไม่พร้อม" → agent ทุกตัวตายเงียบ

เทสนี้ตรวจ argv ที่จะถูก exec จริง (ไม่ยิง network)
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workers import llm_provider as lp  # noqa: E402

# flag ที่ opencode v2.1.4 ไม่มี (ยืนยันด้วย `opencode run --help`)
REMOVED_FLAGS = ("--pure",)


# ══════════════════════════════════════════════════════════════════════
# _CMD_WITH_FLAGS — base argv
# ══════════════════════════════════════════════════════════════════════


class TestCmdWithFlags:
    def test_no_removed_flags(self):
        assert [f for f in lp._CMD_WITH_FLAGS if f in REMOVED_FLAGS] == []

    def test_starts_with_bin_then_run(self):
        assert lp._CMD_WITH_FLAGS[0] == lp._CMD
        assert lp._CMD_WITH_FLAGS[1] == "run"

    def test_bin_is_opencode(self):
        assert Path(lp._CMD_WITH_FLAGS[0]).name == "opencode"

    def test_has_read_only_agent(self):
        """ต้องมี --agent <name> — ไม่งั้น subprocess ค้างที่ permission prompt"""
        argv = lp._CMD_WITH_FLAGS
        assert "--agent" in argv
        agent = argv[argv.index("--agent") + 1]
        assert agent == "plan"
        assert lp._AGENT == "plan"


# ══════════════════════════════════════════════════════════════════════
# --agent override
# ══════════════════════════════════════════════════════════════════════


class TestAgentOverride:
    def test_opencode_agent_env_override(self, monkeypatch):
        monkeypatch.setenv("OPENCODE_AGENT", "custom-readonly")
        try:
            reloaded = importlib.reload(lp)
            assert reloaded._AGENT == "custom-readonly"
            assert reloaded._CMD_WITH_FLAGS == [reloaded._CMD, "run", "--agent", "custom-readonly"]
        finally:
            monkeypatch.delenv("OPENCODE_AGENT", raising=False)
            importlib.reload(lp)

    def test_default_agent_is_plan(self):
        assert lp._AGENT == os.environ.get("OPENCODE_AGENT", "plan")


# ══════════════════════════════════════════════════════════════════════
# dead-model detection — "Model unavailable" ต้องไม่ retry 3 ครั้ง
# ══════════════════════════════════════════════════════════════════════


class TestDeadModelDetection:
    def test_unavailable_is_dead(self):
        assert lp._is_dead_model_error("opencode run exit 1: Model unavailable: opencode/x")

    def test_not_found_is_dead(self):
        assert lp._is_dead_model_error("opencode run exit 1: Model not found: opencode/x")

    def test_case_insensitive(self):
        assert lp._is_dead_model_error("MODEL UNAVAILABLE: x")

    def test_transient_error_is_not_dead(self):
        assert not lp._is_dead_model_error("permission requested: shell")
        assert not lp._is_dead_model_error("opencode run exit 1: timeout")


class TestThinkUnavailableSkipsRetries:
    def test_each_unavailable_model_called_once(self, monkeypatch):
        """โมเดลที่ยืนยันว่าตายแล้ว (minimax/longcat หาย upstream 2026-10-25)
        → map เข้า chain และยิงแต่ละโมเดลครั้งเดียว ไม่ retry"""
        calls: list[str] = []

        async def fake(full_prompt: str, model: str, *, timeout=None, session_id=None):
            calls.append(model)
            raise RuntimeError(f"opencode run exit 1: Model unavailable: {model}")

        monkeypatch.setattr(lp, "_run_opencode", fake)
        out = asyncio.run(lp.think("hi", model="opencode/minimax-m3.1-flash-free"))

        assert calls == lp.MODEL_FALLBACKS, f"คาดว่าแต่ละโมเดลครั้งเดียว ได้ {calls}"
        assert out.startswith("⚠️ LLM ไม่พร้อม")

    def test_nonexistent_model_then_chain_each_called_once(self, monkeypatch):
        """ชื่อที่ไม่รู้จักเลย → ลองตัวนั้นก่อน แล้วต่อด้วย chain ตัวละครั้งเดียว"""
        calls: list[str] = []

        async def fake(full_prompt: str, model: str, *, timeout=None, session_id=None):
            calls.append(model)
            raise RuntimeError("opencode run exit 1: Model unavailable: " + model)

        monkeypatch.setattr(lp, "_run_opencode", fake)
        asyncio.run(lp.think("hi", model="opencode/definitely-not-a-model"))

        assert calls == ["opencode/definitely-not-a-model", *lp.MODEL_FALLBACKS]
        assert all(calls.count(m) == 1 for m in calls), f"มีโมเดลถูกยิงซ้ำ: {calls}"

    def test_single_model_unavailable_called_once(self, monkeypatch):
        calls: list[str] = []

        async def fake(full_prompt: str, model: str, *, timeout=None, session_id=None):
            calls.append(model)
            raise RuntimeError("opencode run exit 1: Model unavailable: " + model)

        monkeypatch.setattr(lp, "_run_opencode", fake)
        asyncio.run(lp.think("hi", model="opencode/brand-new-model"))

        assert calls.count("opencode/brand-new-model") == 1

    def test_transient_error_still_retries(self, monkeypatch):
        """กัน over-correct: error ชั่วคราวต้องยัง retry ตามเดิม"""
        calls: list[str] = []

        async def fake(full_prompt: str, model: str, *, timeout=None, session_id=None):
            calls.append(model)
            raise RuntimeError("opencode run exit 1: boom")

        async def no_sleep(_seconds):
            return None

        monkeypatch.setattr(lp, "_run_opencode", fake)
        monkeypatch.setattr(asyncio, "sleep", no_sleep)
        asyncio.run(lp.think("hi", model="opencode/brand-new-model"))

        assert calls[0] == "opencode/brand-new-model"
        assert calls[:3] == ["opencode/brand-new-model"] * 3


# ══════════════════════════════════════════════════════════════════════
# _run_opencode — argv จริงที่ส่งเข้า create_subprocess_exec
# ══════════════════════════════════════════════════════════════════════


class _FakeProc:
    returncode = 0

    def __init__(self, argv: list[str], stdout: bytes = b"OK") -> None:
        self.argv = argv
        self._stdout = stdout
        self.stdin_input = b""

    async def communicate(self, input: bytes | None = None):
        self.stdin_input = input or b""
        return self._stdout, b""

    async def wait(self) -> int:
        return 0

    def kill(self) -> None:  # pragma: no cover - never hit in these tests
        pass


def _patch_exec(monkeypatch) -> dict:
    captured: dict = {}

    async def fake_exec(*argv, **kwargs):
        captured["argv"] = list(argv)
        captured["kwargs"] = kwargs
        return _FakeProc(list(argv))

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    return captured


class TestRunOpencodeArgv:
    def test_argv_has_model_and_no_removed_flags(self, monkeypatch):
        captured = _patch_exec(monkeypatch)
        out = asyncio.run(lp._run_opencode("hello", "opencode/some-model"))

        argv = captured["argv"]
        assert argv[:2] == [lp._CMD, "run"]
        assert "--model" in argv
        assert argv[argv.index("--model") + 1] == "opencode/some-model"
        assert "--agent" in argv
        assert argv[argv.index("--agent") + 1] == lp._AGENT
        for flag in REMOVED_FLAGS:
            assert flag not in argv, f"{flag} ยังอยู่ใน argv: {argv}"
        assert out == "OK"

    def test_prompt_goes_through_stdin_not_argv(self, monkeypatch):
        captured = _patch_exec(monkeypatch)
        asyncio.run(lp._run_opencode("สวัสดี ช่วยตอบ", "opencode/m"))
        assert "สวัสดี ช่วยตอบ" not in captured["argv"]


# ══════════════════════════════════════════════════════════════════════
# OPENCODE_BIN override ยังทำงาน
# ══════════════════════════════════════════════════════════════════════


class TestBinOverride:
    def test_opencode_bin_env_override(self, monkeypatch):
        monkeypatch.setenv("OPENCODE_BIN", "/tmp/custom/opencode")
        try:
            reloaded = importlib.reload(lp)
            assert reloaded._CMD == "/tmp/custom/opencode"
            assert reloaded._CMD_WITH_FLAGS == ["/tmp/custom/opencode", "run", "--agent", "plan"]
            assert [f for f in reloaded._CMD_WITH_FLAGS if f in REMOVED_FLAGS] == []
        finally:
            monkeypatch.delenv("OPENCODE_BIN", raising=False)
            importlib.reload(lp)

    def test_default_bin_unchanged(self):
        assert lp._CMD == os.environ.get(
            "OPENCODE_BIN", os.path.expanduser("~/.opencode/bin/opencode")
        )


# ══════════════════════════════════════════════════════════════════════
# Token accounting + quota lock (2026-10-25 incident)
#
# บริบท: โควตาฟรีหมดกลางวัน · 186 requests ถูกยิงเข้ากำแพง 429 เปล่า ๆ
# เพราะไม่มีการวัดต่อ call และไม่มีความจำว่า "โควตาตายแล้ว"
# ══════════════════════════════════════════════════════════════════════

import json  # noqa: E402

REAL_429 = (
    '{"type":"error","error":{"type":"provider.free-limit","message":"Free usage '
    'limit reached.","status":429},"retryAfterMs":63736000}'
)


class TestSessionFlag:
    """ทุก call ต้องมี session id ของเราเอง → ตามรอย usage ได้ 1:1"""

    def test_session_flag_in_argv(self, monkeypatch):
        captured = _patch_exec(monkeypatch)
        asyncio.run(lp._run_opencode("hi", "opencode/m", session_id="ses_llmabc123"))
        argv = captured["argv"]
        assert "--session" in argv
        assert argv[argv.index("--session") + 1] == "ses_llmabc123"

    def test_no_session_flag_when_not_given(self, monkeypatch):
        captured = _patch_exec(monkeypatch)
        asyncio.run(lp._run_opencode("hi", "opencode/m"))
        assert "--session" not in captured["argv"]


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    """แยก ledger/quota/usage ออกจากของจริง — ไม่แตะ bus/system"""
    monkeypatch.setattr(lp.token_ledger, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(lp.token_ledger, "QUOTA_PATH", tmp_path / "quota.json")

    usage = {
        "requests": 1, "input": 10, "output": 20, "reasoning": 5,
        "cache_read": 100, "cache_write": 0, "failed": 0, "cost": 0.0, "error": "",
    }

    async def fake_usage(session_id, **kw):
        return dict(usage)

    monkeypatch.setattr(lp.token_ledger, "read_session_usage_async", fake_usage)
    return tmp_path


def _ledger_rows(path):
    f = path / "ledger.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


class TestCallAccounting:
    def test_successful_call_recorded(self, isolated, monkeypatch):
        async def fake(full_prompt, model, *, timeout=None, session_id=None):
            return "OK"

        monkeypatch.setattr(lp, "_run_opencode", fake)
        out = asyncio.run(lp.think("hi", agent="content-creator-sek"))

        assert out == "OK"
        rows = _ledger_rows(isolated)
        assert len(rows) == 1
        row = rows[0]
        assert row["ok"] is True
        assert row["agent"] == "content-creator-sek"
        assert row["model"] == lp.DEFAULT_MODEL
        assert row["requests"] == 1
        assert row["output"] == 20
        assert row["session_id"].startswith("ses_llm")
        assert row["duration_ms"] >= 0

    def test_failed_call_recorded_with_error(self, isolated, monkeypatch):
        async def fake(full_prompt, model, *, timeout=None, session_id=None):
            raise RuntimeError("opencode run exit 1: Model unavailable: x")

        monkeypatch.setattr(lp, "_run_opencode", fake)
        asyncio.run(lp.think("hi", agent="qa"))

        rows = _ledger_rows(isolated)
        assert rows, "call ที่ล้มก็ต้องมีร่องรอยใน ledger"
        assert all(r["ok"] is False for r in rows)
        assert all(r["error"] for r in rows)

    def test_accounting_failure_does_not_break_call(self, isolated, monkeypatch):
        """ledger เขียนไม่ได้ → ยังต้องได้คำตอบจาก LLM"""
        async def fake(full_prompt, model, *, timeout=None, session_id=None):
            return "OK"

        def boom(*a, **kw):
            raise OSError("disk full")

        monkeypatch.setattr(lp, "_run_opencode", fake)
        monkeypatch.setattr(lp.token_ledger, "record", boom)
        assert asyncio.run(lp.think("hi")) == "OK"


class TestQuotaFailFast:
    def test_locked_quota_makes_zero_calls(self, isolated, monkeypatch):
        calls: list[str] = []

        async def fake(full_prompt, model, *, timeout=None, session_id=None):
            calls.append(model)
            return "OK"

        monkeypatch.setattr(lp, "_run_opencode", fake)
        lp.token_ledger.lock_quota(
            int(__import__("time").time() * 1000) + 600_000, "free-limit", model="x"
        )

        out = asyncio.run(lp.think("hi"))
        assert calls == [], "โควตาล็อกอยู่ต้องไม่ยิง LLM เลย"
        assert out.startswith("⚠️ LLM ไม่พร้อม")
        assert "ล็อก" in out

    def test_429_locks_and_stops_chain(self, isolated, monkeypatch):
        calls: list[str] = []

        async def fake(full_prompt, model, *, timeout=None, session_id=None):
            calls.append(model)
            raise RuntimeError(f"opencode run exit 1: {REAL_429}")

        monkeypatch.setattr(lp, "_run_opencode", fake)
        out = asyncio.run(lp.think("hi"))

        assert len(calls) == 1, f"เจอ 429 แล้วต้องหยุดทั้ง chain ไม่ไล่ทุกโมเดล ({calls})"
        assert "free-tier" in out.lower()
        st = lp.token_ledger.quota_status()
        assert st["locked"] is True
        assert st["remaining_s"] > 60_000  # ~17.7 ชม. จาก retryAfterMs

        # call ถัดไปต้องไม่ยิงอีก
        calls.clear()
        asyncio.run(lp.think("hi"))
        assert calls == []

    def test_402_funds_also_locks(self, isolated, monkeypatch):
        async def fake(full_prompt, model, *, timeout=None, session_id=None):
            raise RuntimeError("Insufficient account funds")

        monkeypatch.setattr(lp, "_run_opencode", fake)
        asyncio.run(lp.think("hi"))
        assert lp.token_ledger.quota_status()["reason"] == "funds"


class TestBudgetGuard:
    def test_over_daily_ceiling_makes_zero_calls(self, isolated, monkeypatch):
        calls: list[str] = []

        async def fake(full_prompt, model, *, timeout=None, session_id=None):
            calls.append(model)
            return "OK"

        monkeypatch.setattr(lp, "_run_opencode", fake)
        monkeypatch.setenv("SOLOCORP_LLM_DAILY_REQUESTS", "1")
        lp.token_ledger.record({"requests": 1, "output": 10}, path=isolated / "ledger.jsonl")

        out = asyncio.run(lp.think("hi"))
        assert calls == []
        assert "เกินงบรายวัน" in out

    def test_under_ceiling_still_calls(self, isolated, monkeypatch):
        async def fake(full_prompt, model, *, timeout=None, session_id=None):
            return "OK"

        monkeypatch.setattr(lp, "_run_opencode", fake)
        monkeypatch.setenv("SOLOCORP_LLM_DAILY_REQUESTS", "100")
        assert asyncio.run(lp.think("hi")) == "OK"
