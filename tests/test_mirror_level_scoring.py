"""Regression test — Mirror check scoring ต้อง level-aware (ADR-028)

**บั๊กเดิม:** เกณฑ์ผ่าน 60% ใช้กับทุกระดับ (L1–L5) แต่คำถามของ L1/L2
ไม่ได้ถามว่า "Owner จะอนุมัติไหม" เสมอไป
เช่น L1 ถาม *"Owner ควรรู้อะไรเกี่ยวกับ decision นี้?"* → คำตอบ NO
หมายถึง "Owner ไม่ต้องรู้" ซึ่ง**ถูกต้อง**สำหรับงานระดับ L1
แต่ถูกนับเป็น fail → false negative → งานที่ไม่มีปัญหาดูเหมือนถูก mirror จับ

**กติกาใหม่:**
- L1 (monitor) / L2 (advisory) → advisory: บันทึก score ไว้ แต่ **ไม่ block** (passed=True เสมอ)
- L3+ → gate จริง เกณฑ์ 60% เดิม ไม่เปลี่ยน
"""
from __future__ import annotations

import pytest

from central_bus import mirror_check
from central_bus.mirror_check import MirrorLevel


class TestLevelAwareScoring:
    """ระดับ L1/L2 = advisory · L3+ = gate"""

    @pytest.mark.parametrize(
        "dept,expected_level",
        [
            ("qa", MirrorLevel.L1_MONITOR),
            ("content", MirrorLevel.L2_ADVISORY),
        ],
    )
    @pytest.mark.asyncio
    async def test_low_level_is_advisory_and_never_blocks(
        self, monkeypatch, dept, expected_level
    ):
        """ทุกคำถามตอบ NO (score=0) → ระดับ L1/L2 ต้องยังผ่าน (ไม่ block)"""
        monkeypatch.setattr(
            mirror_check, "get_department_level", lambda d: expected_level
        )

        async def fake_eval(question, decision, department):
            return False  # ทุกข้อ fail → score 0

        monkeypatch.setattr(mirror_check, "_evaluate_mirror_question", fake_eval)

        result = await mirror_check.run_mirror_check(dept, "decision ทดสอบ")

        assert result.advisory is True
        assert result.passed is True, "L1/L2 ต้องไม่ block"
        assert result.score == 0, "score ยังต้องบันทึกความจริง"
        assert "advisory" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_low_level_low_score_is_flagged_in_reason(self, monkeypatch):
        """score ต่ำต้องยังเห็นใน reason (ไม่หายไป)"""
        monkeypatch.setattr(
            mirror_check, "get_department_level", lambda d: MirrorLevel.L1_MONITOR
        )

        async def fake_eval(question, decision, department):
            return False

        monkeypatch.setattr(mirror_check, "_evaluate_mirror_question", fake_eval)

        result = await mirror_check.run_mirror_check("qa", "decision")

        assert result.score == 0
        assert "คะแนนต่ำกว่า 60%" in result.reason

    @pytest.mark.parametrize(
        "level", [MirrorLevel.L3_FINANCIAL, MirrorLevel.L4_STRATEGIC, MirrorLevel.L5_FULL]
    )
    @pytest.mark.asyncio
    async def test_high_level_still_blocks(self, monkeypatch, level):
        """L3+ ยัง block ตามเกณฑ์ 60% เดิม — ไม่ให้หลุด"""
        monkeypatch.setattr(mirror_check, "get_department_level", lambda d: level)

        async def fake_eval(question, decision, department):
            return False  # score 0 → ต้อง fail

        monkeypatch.setattr(mirror_check, "_evaluate_mirror_question", fake_eval)

        result = await mirror_check.run_mirror_check("ceo", "decision")

        assert result.advisory is False
        assert result.passed is False, "L3+ ต้องยัง block เมื่อ score ต่ำ"
        assert "FAILED" in result.reason

    @pytest.mark.asyncio
    async def test_high_level_passes_at_threshold(self, monkeypatch):
        """L3+ ที่ผ่านเกณฑ์ ต้องผ่าน (ไม่ให้กระทบพฤติกรรมเดิม)"""
        monkeypatch.setattr(
            mirror_check, "get_department_level", lambda d: MirrorLevel.L5_FULL
        )

        async def fake_eval(question, decision, department):
            return True

        monkeypatch.setattr(mirror_check, "_evaluate_mirror_question", fake_eval)

        result = await mirror_check.run_mirror_check("ceo", "decision")

        assert result.advisory is False
        assert result.passed is True
        assert result.score == 100

    @pytest.mark.asyncio
    async def test_result_dict_includes_advisory_flag(self, monkeypatch):
        """flag ต้องไปถึงผู้เรียก (to_dict) ไม่ใช่แค่ในโค้ด"""
        monkeypatch.setattr(
            mirror_check, "get_department_level", lambda d: MirrorLevel.L2_ADVISORY
        )

        async def fake_eval(question, decision, department):
            return False

        monkeypatch.setattr(mirror_check, "_evaluate_mirror_question", fake_eval)

        result = await mirror_check.run_mirror_check("content", "d")
        d = result.to_dict()

        assert d["advisory"] is True
        assert d["passed"] is True
        assert d["score"] == 0
