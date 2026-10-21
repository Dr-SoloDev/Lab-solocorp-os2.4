"""Regression tests — LLM provider / mirror check

กัน defect 2 ชั้นที่เจอระหว่าง deep health check (21 ต.ค. 2026):

1. **Mirror prompt เปิดช่องให้โมเดล "ตรวจสอบเพิ่ม"** → โมเดลขอสิทธิ์ bash/git →
   permission ถูก auto-reject → stdout ว่าง → provider คืน "LLM เปล่า" →
   mirror check ได้ NO ทุกครั้ง = fail-silent ไม่มีสัญญาณอะไรเลย

2. **Free-tier gate** → ทุกโมเดลใน chain ล้มเหมือนกัน → ถ้าไม่ fail-fast
   จะเสียเวลา 7 โมเดล × 3 retry ≈ 7 นาที เพื่อได้ข้อความเดียวกัน (ADR-017)
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from central_bus import mirror_check
from workers import llm_provider


# ─────────────────────────────────────────────────────────────────────
# 1. Mirror prompt ต้องปิดช่องโหว่
# ─────────────────────────────────────────────────────────────────────


class TestMirrorPrompt:
    """prompt ที่ส่งให้ LLM ต้องไม่เปิดโอกาสให้โมเดลไปใช้เครื่องมือ"""

    @pytest.mark.asyncio
    async def test_prompt_forbids_tools(self):
        captured: dict = {}

        async def fake_think(prompt, **kw):
            captured["prompt"] = prompt
            return "YES"

        with patch.object(llm_provider, "think", fake_think):
            result = await mirror_check._evaluate_mirror_question(
                "คำถามทดสอบ", "สถานการณ์ทดสอบ", "ceo"
            )

        assert result is True
        prompt = captured["prompt"]
        assert "ห้ามใช้เครื่องมือ" in prompt
        assert "YES" in prompt and "NO" in prompt

    @pytest.mark.asyncio
    async def test_prompt_has_no_verification_invitation(self):
        """ห้ามมีคำที่ชวนให้โมเดลไป 'ตรวจสอบ' — ต้นเหตุที่ทำให้โมเดลขอสิทธิ์"""
        captured: dict = {}

        async def fake_think(prompt, **kw):
            captured["prompt"] = prompt
            return "YES"

        with patch.object(llm_provider, "think", fake_think):
            await mirror_check._evaluate_mirror_question("Q", "D", "ceo")

        prompt = captured["prompt"]
        # คำเหล่านี้คือสิ่งที่ทำให้โมเดลไปหา tool (git log / ls / gh pr view)
        for trap in ("ตรวจสอบอะไรเพิ่ม", "อ่านไฟล์", "รันคำสั่ง"):
            assert trap in prompt, f"prompt ต้องระบุว่า {trap}"

    @pytest.mark.asyncio
    async def test_yes_passes(self):
        async def fake_think(prompt, **kw):
            return "YES"

        with patch.object(llm_provider, "think", fake_think):
            assert await mirror_check._evaluate_mirror_question("Q", "D", "ceo") is True

    @pytest.mark.asyncio
    async def test_no_fails(self):
        async def fake_think(prompt, **kw):
            return "NO"

        with patch.object(llm_provider, "think", fake_think):
            assert await mirror_check._evaluate_mirror_question("Q", "D", "ceo") is False

    @pytest.mark.asyncio
    async def test_empty_response_fails_safely(self):
        """LLM ไม่พร้อม → False (fail-safe) แต่ห้าม crash"""

        async def fake_think(prompt, **kw):
            return ""

        with patch.object(llm_provider, "think", fake_think):
            assert await mirror_check._evaluate_mirror_question("Q", "D", "ceo") is False

    @pytest.mark.asyncio
    async def test_unexpected_answer_fails_safely(self):
        """โมเดลตอบอย่างอื่น (เช่น ขอใช้เครื่องมือ) → ต้อง fail ไม่ใช่เดาว่า YES"""

        async def fake_think(prompt, **kw):
            return "ผมขอดู git log ก่อนนะครับ"

        with patch.object(llm_provider, "think", fake_think):
            assert await mirror_check._evaluate_mirror_question("Q", "D", "ceo") is False

    @pytest.mark.asyncio
    async def test_exception_fails_safely(self):
        async def fake_think(prompt, **kw):
            raise RuntimeError("boom")

        with patch.object(llm_provider, "think", fake_think):
            assert await mirror_check._evaluate_mirror_question("Q", "D", "ceo") is False


# ─────────────────────────────────────────────────────────────────────
# 2. Provider ต้อง fail-fast เมื่อเจอ free-tier gate
# ─────────────────────────────────────────────────────────────────────


class TestFreeTierFailFast:
    """free tier = ทุกโมเดลล้มเหมือนกัน → หยุด chain ไม่ retry ซ้ำ"""

    @pytest.mark.asyncio
    async def test_free_tier_stops_after_first_model(self):
        calls: list[str] = []

        async def fake_run(prompt, model, **kw):
            calls.append(model)
            raise RuntimeError(
                "opencode run exit 1: Error: OpenCode's free tier can only be used "
                "from within OpenCode."
            )

        with patch.object(llm_provider, "_run_opencode", fake_run):
            result = await llm_provider.think("prompt")

        assert len(calls) == 1, f"ควรหยุดที่โมเดลแรก แต่เรียกไป {len(calls)} ครั้ง"
        assert "free-tier" in result.lower()
        assert "⚠️" in result

    @pytest.mark.asyncio
    async def test_non_free_tier_error_still_falls_back(self):
        """error อื่น (เช่น model not found) → ยังต้องลองโมเดลถัดไป"""
        calls: list[str] = []

        async def fake_run(prompt, model, **kw):
            calls.append(model)
            if len(calls) == 1:
                raise RuntimeError("Model not found: opencode/fake-model")
            return "OK"

        with patch.object(llm_provider, "_run_opencode", fake_run):
            result = await llm_provider.think("prompt")

        assert len(calls) > 1, "ควร fallback ไปโมเดลถัดไป"
        assert result == "OK"

    @pytest.mark.asyncio
    async def test_empty_response_moves_to_next_model(self):
        """LLM เปล่า = เปลี่ยนโมเดลทันที (ไม่ retry ตัวเดิม)"""
        calls: list[str] = []

        async def fake_run(prompt, model, **kw):
            calls.append(model)
            return "" if len(calls) == 1 else "OK"

        with patch.object(llm_provider, "_run_opencode", fake_run):
            result = await llm_provider.think("prompt")

        assert len(calls) == 2
        assert result == "OK"
