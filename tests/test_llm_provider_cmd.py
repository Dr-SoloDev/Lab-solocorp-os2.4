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

        async def fake(full_prompt: str, model: str, *, timeout=None):
            calls.append(model)
            raise RuntimeError(f"opencode run exit 1: Model unavailable: {model}")

        monkeypatch.setattr(lp, "_run_opencode", fake)
        out = asyncio.run(lp.think("hi", model="opencode/minimax-m3.1-flash-free"))

        assert calls == lp.MODEL_FALLBACKS, f"คาดว่าแต่ละโมเดลครั้งเดียว ได้ {calls}"
        assert out.startswith("⚠️ LLM ไม่พร้อม")

    def test_nonexistent_model_then_chain_each_called_once(self, monkeypatch):
        """ชื่อที่ไม่รู้จักเลย → ลองตัวนั้นก่อน แล้วต่อด้วย chain ตัวละครั้งเดียว"""
        calls: list[str] = []

        async def fake(full_prompt: str, model: str, *, timeout=None):
            calls.append(model)
            raise RuntimeError("opencode run exit 1: Model unavailable: " + model)

        monkeypatch.setattr(lp, "_run_opencode", fake)
        asyncio.run(lp.think("hi", model="opencode/definitely-not-a-model"))

        assert calls == ["opencode/definitely-not-a-model", *lp.MODEL_FALLBACKS]
        assert all(calls.count(m) == 1 for m in calls), f"มีโมเดลถูกยิงซ้ำ: {calls}"

    def test_single_model_unavailable_called_once(self, monkeypatch):
        calls: list[str] = []

        async def fake(full_prompt: str, model: str, *, timeout=None):
            calls.append(model)
            raise RuntimeError("opencode run exit 1: Model unavailable: " + model)

        monkeypatch.setattr(lp, "_run_opencode", fake)
        asyncio.run(lp.think("hi", model="opencode/brand-new-model"))

        assert calls.count("opencode/brand-new-model") == 1

    def test_transient_error_still_retries(self, monkeypatch):
        """กัน over-correct: error ชั่วคราวต้องยัง retry ตามเดิม"""
        calls: list[str] = []

        async def fake(full_prompt: str, model: str, *, timeout=None):
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
