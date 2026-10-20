"""Tests for Cadence — จังหวะการโพสต์ (สัญญาระหว่างครีเอเตอร์กับระบบ)"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solocorp_skills.cadence import Cadence, load_cadence  # noqa: E402


SAMPLE = """# จังหวะการโพสต์ — Dr.SoloDev

| วัน | ข้อความ | คลิป | โน้ต |
|:--|:--:|:--:|:--|
| จันทร์ | ✅ | ✅ | |
| อังคาร | ✅ | ❌ | |
| พุธ | ✅ | ✅ | |
| พฤหัสบดี | ✅ | ❌ | |
| ศุกร์ | ✅ | ✅ | |
| เสาร์ | ❌ | ❌ | พัก |
| อาทิตย์ | ❌ | ❌ | พัก |

## ช่วงเร่งด่วน (7 วันแรก)

วันที่ **2026-10-20 ถึง 2026-10-26** → โพสต์ข้อความทุกวัน
"""


@pytest.fixture()
def cadence_file(tmp_path):
    p = tmp_path / "cadence.md"
    p.write_text(SAMPLE, encoding="utf-8")
    return p


class TestLoadCadence:
    def test_parses_weekdays(self, cadence_file):
        c = load_cadence(cadence_file)
        assert c.text_days == {0, 1, 2, 3, 4}, "จ.-ศ. ต้องโพสต์ข้อความ"
        assert c.clip_days == {0, 2, 4}, "คลิป จ./พ./ศ."
        assert 5 not in c.text_days and 6 not in c.text_days, "เสาร์-อาทิตย์ต้องพัก"

    def test_parses_ramp(self, cadence_file):
        c = load_cadence(cadence_file)
        assert c.ramp_from == "2026-10-20"
        assert c.ramp_to == "2026-10-26"

    def test_source_is_file(self, cadence_file):
        assert load_cadence(cadence_file).source == str(cadence_file)

    def test_missing_file_uses_default(self, tmp_path):
        c = load_cadence(tmp_path / "ไม่มี.md")
        assert c.source == "default"
        assert c.text_days == {0, 1, 2, 3, 4}
        assert c.clip_days == {0, 2, 4}

    def test_english_weekdays_supported(self, tmp_path):
        p = tmp_path / "c.md"
        p.write_text("| Day | Text | Clip |\n| Monday | ✅ | ✅ |\n| Sunday | ❌ | ❌ |\n",
                     encoding="utf-8")
        c = load_cadence(p)
        assert c.text_days == {0}
        assert c.clip_days == {0}


class TestPlanFor:
    def test_ramp_makes_every_day_post(self, cadence_file):
        c = load_cadence(cadence_file)
        # ภายในช่วงเร่งด่วน → ทุกวันรวมเสาร์-อาทิตย์
        sat = c.plan_for(date(2026, 10, 24))
        sun = c.plan_for(date(2026, 10, 25))
        assert sat["post_text"] is True
        assert sun["post_text"] is True
        assert sat["ramp"] is True

    def test_ramp_ends_on_ramp_to(self, cadence_file):
        c = load_cadence(cadence_file)
        assert c.plan_for(date(2026, 10, 26))["ramp"] is True
        assert c.plan_for(date(2026, 10, 27))["ramp"] is False

    def test_after_ramp_weekend_is_off(self, cadence_file):
        c = load_cadence(cadence_file)
        assert c.plan_for(date(2026, 11, 1))["post_text"] is False  # เสาร์
        assert c.plan_for(date(2026, 10, 28))["post_text"] is True  # พุธ

    def test_plan_has_reason(self, cadence_file):
        c = load_cadence(cadence_file)
        p = c.plan_for(date(2026, 10, 28))
        assert p["reason"]
        assert "พัก" in p["reason"] or "ตาราง" in p["reason"]

    def test_default_cadence(self):
        c = Cadence()
        assert c.plan_for(date(2026, 10, 21))["post_text"] is True  # พุธ
        assert c.plan_for(date(2026, 10, 24))["post_text"] is False  # เสาร์


class TestRealCadenceFile:
    """สัญญาจริงใน repo ต้องอ่านได้และสมเหตุสมผล"""

    def test_repo_cadence_readable(self):
        from solocorp_skills.cadence import DEFAULT_CADENCE_PATH
        c = load_cadence()
        assert c.source == str(DEFAULT_CADENCE_PATH), "ต้องอ่านไฟล์จริงได้ ไม่ใช่ default"
        assert c.text_days, "ต้องมีวันโพสต์ข้อความ"

    def test_repo_cadence_has_ramp(self):
        c = load_cadence()
        assert c.ramp_from and c.ramp_to, "ต้องมีช่วงเร่งด่วน 7 วัน"

    def test_repo_cadence_ramp_is_seven_days(self):
        from datetime import timedelta
        c = load_cadence()
        span = date.fromisoformat(c.ramp_to) - date.fromisoformat(c.ramp_from)
        assert span.days == 6, "ช่วงเร่งด่วนต้อง 7 วัน (รวมวันแรก-วันสุดท้าย)"
