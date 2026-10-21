"""Regression test — LLM provider ต้องเรียก judgment agent ที่ไม่มีเครื่องมือ

Defect (2026-10-21): `opencode run --pure --model <m>` ที่รันใน repo จะโหลด
agent config ของโปรเจกต์ → persona หลัก (ceo-turbo) → โมเดลพยายามใช้เครื่องมือ
(bash / git / read) → permission ถูก auto-reject → run จบ exit 0 แต่ stdout ว่าง
→ provider เห็น "ค่าว่าง" → เปลี่ยนโมเดลไปตัวถัดไปจนหมด → "⚠️ LLM ไม่พร้อม"
→ ทุกอย่างที่พึ่ง think() ใช้ไม่ได้จริง (mirror check · worker agents · creator pipeline)

Fix: เรียกด้วย `--agent llm-judge` (agent ที่ปิดสิทธิ์เครื่องมือทั้งหมด)
Fallback: ถ้า agent ไม่มี/ไม่รู้จัก → retry โดยไม่ใส่ --agent

Deterministic: mock asyncio.create_subprocess_exec → ไม่แตะ LLM จริง
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from workers import llm_provider as lp  # noqa: E402

AGENT_ENV = "SOLOCORP_LLM_AGENT"
MODEL = "opencode/minimax-m3.1-flash-free"


class _FakeProc:
    """หน้าตา process ของ asyncio subprocess (พอให้ provider ใช้งานได้)"""

    def __init__(self, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
        self._stdout = stdout
        self._stderr = stderr
        self._returncode = returncode
        self.killed = False

    async def communicate(self, input=None):  # noqa: A002 - ต้องตรง signature subprocess
        return self._stdout, self._stderr

    async def wait(self) -> int:
        return self._returncode

    def kill(self) -> None:
        self.killed = True


def _mock_exec(monkeypatch, script):
    """ติดตั้ง mock asyncio.create_subprocess_exec

    script = list ของ (stdout, stderr, returncode) หรือ Exception
    คืนค่า = list ของ cmd ที่ถูกเรียก (ตามลำดับ)
    """
    calls: list[list[str]] = []
    queue = list(script)

    async def fake_exec(*cmd, **kwargs):
        calls.append(list(cmd))
        item = queue.pop(0) if queue else (b"YES\n", b"", 0)
        if isinstance(item, BaseException):
            raise item
        stdout, stderr, code = item
        return _FakeProc(stdout, stderr, code)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    return calls


def _agent_arg(cmd: list[str]):
    """ค่าหลัง --agent (None = ไม่มี flag)"""
    if "--agent" not in cmd:
        return None
    return cmd[cmd.index("--agent") + 1]


# ══════════════════════════════════════════════════════════════════════
# 1. ค่า default — ต้องเรียกด้วย judgment agent
# ══════════════════════════════════════════════════════════════════════


class TestAgentFlag:
    def test_runs_with_judge_agent_by_default(self, monkeypatch):
        monkeypatch.delenv(AGENT_ENV, raising=False)
        calls = _mock_exec(monkeypatch, [(b"YES\n", b"", 0)])

        result = asyncio.run(lp._run_opencode("prompt", MODEL))

        assert result == "YES"
        assert len(calls) == 1
        assert _agent_arg(calls[0]) == "llm-judge"

    def test_judge_agent_file_exists_in_repo(self):
        """ไฟล์ agent ต้องอยู่ใน .opencode/agents/ ของ repo (ไม่งั้น fix ใช้ไม่ได้)"""
        agent_file = _ROOT / ".opencode" / "agents" / "llm-judge.md"
        assert agent_file.is_file(), f"ไม่พบไฟล์ agent: {agent_file}"

    def test_model_and_pure_flags_still_present(self, monkeypatch):
        """flag เดิมต้องไม่หาย (ไม่ใช่งานของ defect นี้ แต่กัน regression)"""
        monkeypatch.delenv(AGENT_ENV, raising=False)
        calls = _mock_exec(monkeypatch, [(b"YES\n", b"", 0)])

        asyncio.run(lp._run_opencode("prompt", MODEL))

        cmd = calls[0]
        assert "--pure" in cmd
        assert "--model" in cmd
        assert cmd[cmd.index("--model") + 1] == MODEL

    def test_env_var_overrides_agent_name(self, monkeypatch):
        """SOLOCORP_LLM_AGENT override ได้ (ใช้ agent ที่มีไฟล์จริงใน repo)"""
        monkeypatch.setenv(AGENT_ENV, "qa")
        calls = _mock_exec(monkeypatch, [(b"OK\n", b"", 0)])

        result = asyncio.run(lp._run_opencode("prompt", MODEL))

        assert result == "OK"
        assert _agent_arg(calls[0]) == "qa"

    def test_missing_agent_file_skips_agent_flag(self, monkeypatch):
        """ถ้าไม่มีไฟล์ agent → ไม่ใส่ --agent (ไม่พัง แค่ไม่ได้ fix)"""
        monkeypatch.setenv(AGENT_ENV, "agent-that-does-not-exist")
        calls = _mock_exec(monkeypatch, [(b"OK\n", b"", 0)])

        result = asyncio.run(lp._run_opencode("prompt", MODEL))

        assert result == "OK"
        assert _agent_arg(calls[0]) is None


# ══════════════════════════════════════════════════════════════════════
# 2. Fallback — agent ใช้ไม่ได้ → retry โดยไม่ใส่ --agent
# ══════════════════════════════════════════════════════════════════════


class TestAgentFallback:
    def test_fallback_without_agent_when_agent_unknown(self, monkeypatch):
        monkeypatch.delenv(AGENT_ENV, raising=False)
        calls = _mock_exec(monkeypatch, [
            RuntimeError("opencode run exit 1: unknown agent: llm-judge"),
            (b"YES\n", b"", 0),
        ])

        result = asyncio.run(lp._run_opencode("prompt", MODEL))

        assert result == "YES"
        assert len(calls) == 2
        assert _agent_arg(calls[0]) == "llm-judge"  # ครั้งแรกใช้ agent
        assert _agent_arg(calls[1]) is None         # ครั้งที่สอง fallback ไม่ใส่ --agent

    def test_non_agent_error_is_not_retried_without_agent(self, monkeypatch):
        """error ที่ไม่เกี่ยวกับ agent → ไม่ retry (พฤติกรรมเดิม)"""
        monkeypatch.delenv(AGENT_ENV, raising=False)
        calls = _mock_exec(monkeypatch, [
            RuntimeError("opencode run exit 1: Model not found: opencode/dead-model"),
        ])

        with pytest.raises(RuntimeError, match="Model not found"):
            asyncio.run(lp._run_opencode("prompt", MODEL))

        assert len(calls) == 1
        assert _agent_arg(calls[0]) == "llm-judge"


# ══════════════════════════════════════════════════════════════════════
# 3. ตัวช่วย — ตรวจ logic การตัดสินใจ
# ══════════════════════════════════════════════════════════════════════


class TestAgentHelpers:
    def test_default_agent_name(self, monkeypatch):
        monkeypatch.delenv(AGENT_ENV, raising=False)
        assert lp._agent_name() == "llm-judge"

    def test_env_agent_name(self, monkeypatch):
        monkeypatch.setenv(AGENT_ENV, "qa")
        assert lp._agent_name() == "qa"

    def test_blank_env_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv(AGENT_ENV, "   ")
        assert lp._agent_name() == "llm-judge"

    def test_looks_like_agent_error(self):
        assert lp._looks_like_agent_error("unknown agent: llm-judge") is True
        assert lp._looks_like_agent_error('agent "llm-judge" not found') is True
        assert lp._looks_like_agent_error("unknown flag: --agent") is True
        assert lp._looks_like_agent_error("Model not found: opencode/x") is False
        assert lp._looks_like_agent_error("permission requested: bash") is False
        assert lp._looks_like_agent_error("") is False
