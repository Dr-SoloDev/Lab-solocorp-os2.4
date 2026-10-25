"""Edge cases: brief_path ที่ไม่ใช่ไฟล์อ่านได้ → ต้อง failed · ไม่ใช่ exception

เคสจริงจาก D3 harness (case 14): `brief_path` เป็น directory →
`read_file()` โยน `IsADirectoryError` ออกมาจาก `Path.read_text()`
ก่อนถึง guard `brief.startswith("❌")` → `execute()` ระเบิด → harness บันทึก CRASH

สัญญา: input เสีย → `{"status": "failed", "details": {"error": "brief_unreadable"}}`
ไม่ว่าไฟล์จะไม่ใช่ไฟล์ / อ่านไม่ได้ / เป็น binary — และ `execute()` ต้องไม่ raise
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workers.agents.content_agent import ContentAgent  # noqa: E402


def _agent(tmp_path: Path) -> ContentAgent:
    # log แยกต่อเทสต์ — ห้ามเขียนทับ evidence log ของ repo
    return ContentAgent(log_path=str(tmp_path / "tool-calls.jsonl"))


async def _run(tmp_path: Path, brief_path) -> dict:
    return await _agent(tmp_path).execute({"payload": {"brief_path": str(brief_path)}})


def _assert_failed_unreadable(result: dict) -> None:
    assert result["status"] == "failed", result
    assert result["details"]["error"] == "brief_unreadable", result
    # ต้องบันทึก read ที่ล้มเหลวไว้เป็นหลักฐาน ไม่ใช่กลืนเงียบ
    reads = [c for c in result["details"]["tool_calls"] if c["tool"] == "read_file"]
    assert reads and reads[-1]["ok"] is False, reads


async def test_brief_path_is_directory_returns_failed(tmp_path):
    """เคส D3 #14 — IsADirectoryError ต้องกลายเป็น failed ไม่ใช่ crash"""
    result = await _run(tmp_path, tmp_path)  # tmp_path = directory จริง
    _assert_failed_unreadable(result)


async def test_brief_path_binary_file_returns_failed(tmp_path):
    """ไฟล์ binary → UnicodeDecodeError ต้องกลายเป็น failed"""
    binary = tmp_path / "brief.bin"
    binary.write_bytes(b"\xff\xfe\x00\x01\x80binary")
    result = await _run(tmp_path, binary)
    _assert_failed_unreadable(result)


async def test_brief_path_missing_file_returns_failed(tmp_path):
    """ไฟล์ไม่มีจริง → sentinel ❌ จาก read_file → failed (พฤติกรรมเดิมต้องคงอยู่)"""
    result = await _run(tmp_path, tmp_path / "nope.md")
    _assert_failed_unreadable(result)


@pytest.mark.skipif(os.geteuid() == 0, reason="root อ่านไฟล์ chmod 000 ได้ — permission ไม่ถูกบังคับ")
async def test_brief_path_unreadable_file_returns_failed(tmp_path):
    """ไฟล์ไม่มีสิทธิ์อ่าน → PermissionError (OSError) ต้องกลายเป็น failed"""
    locked = tmp_path / "locked.md"
    locked.write_text("brief", encoding="utf-8")
    locked.chmod(0o000)
    try:
        result = await _run(tmp_path, locked)
    finally:
        locked.chmod(0o644)
    _assert_failed_unreadable(result)


async def test_permission_error_from_read_file_returns_failed(tmp_path, monkeypatch):
    """OSError family ต้องถูกจับแม้รันเป็น root (chmod ไม่บังคับ) — ยืนยันด้วย monkeypatch"""
    agent = _agent(tmp_path)

    async def boom(path: str) -> str:
        raise PermissionError(f"denied: {path}")

    monkeypatch.setattr(agent, "read_file", boom)
    result = await agent.execute({"payload": {"brief_path": "bus/evidence"}})
    _assert_failed_unreadable(result)


async def test_unexpected_error_still_surfaces(tmp_path, monkeypatch):
    """กันกวาดขยะ: bug ที่ไม่ใช่ I/O ต้องยังระเบิดออกมา ไม่ถูกกลืนเป็น failed เงียบ ๆ"""
    agent = _agent(tmp_path)

    async def bug(path: str) -> str:
        raise TypeError("bug ในโค้ด ไม่ใช่ input เสีย")

    monkeypatch.setattr(agent, "read_file", bug)
    with pytest.raises(TypeError):
        await agent.execute({"payload": {"brief_path": "brief.md"}})
