"""Tests for Creator Kit — ตัวแกนกลางของสนามแรก (ครีเอเตอร์สายสร้างตัวตน)

ตรวจส่วนที่ต้องตรงเป๊ะ: 4 ท่อน, โครงเวลาคลิป, ตลิ่ง 2 ชั้น, แพ็กเกจ 5 ไฟล์
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solocorp_skills.creator import (  # noqa: E402
    BRIDGE_TUBEAN,
    TIKTOK_BEATS,
    TUBEAN,
    CreatorProfile,
    build_package,
    build_script,
    profile_from_fact,
    profile_to_fact,
    slugify,
)


def _profile(**kw) -> CreatorProfile:
    base = dict(
        slug="freelance-clip",
        name="โชค",
        tubean={
            "tubean": "ฉันตัดต่อคลิปให้ร้านกาแฟ",
            "roeyphae": "เมื่อก่อนตัดให้สวย ๆ ลูกค้าบอกไม่ขายของให้ฉัน",
            "khondu": "ร้านกาแฟที่เมนูดีแต่ไม่มีใครเห็น",
            "hettai": "ฉันเคยอยากเปิดร้านแต่ไม่มีเงิน",
        },
        tone_words=["ชัดซื่อ", "มือช่าง", "เรียบง่าย"],
    )
    base.update(kw)
    return CreatorProfile(**base)


# ══════════════════════════════════════════════════════════════════════
# 4 ท่อน
# ══════════════════════════════════════════════════════════════════════


class TestTubean:
    """4 ท่อนตาม vision §5.5"""

    def test_has_four_tubean(self):
        assert len(TUBEAN) == 4

    def test_ids_and_names(self):
        ids = [t["id"] for t in TUBEAN]
        assert ids == ["tubean", "roeyphae", "khondu", "hettai"]
        names = [t["name"] for t in TUBEAN]
        assert names == ["ตัวตน", "รอยแผล", "คนดู", "เหตุผลที่ยังทำ"]

    def test_every_tubean_has_question_and_example(self):
        for t in TUBEAN:
            assert t["question"].strip()
            assert t["example"].strip()

    def test_questions_are_open_ended(self):
        """คำถามต้องเป็นแบบน้ำ (เปิด) ไม่ใช่ ABCD"""
        for t in TUBEAN:
            q = t["question"]
            assert "?" in q or "ไหม" in q
            for letter in ("A.", "B.", "C.", "ก)", "ข)"):
                assert letter not in q

    def test_bridge_is_tubean_2_and_3(self):
        """ท่อน 2+3 = สะพานเชื่อมคน 2 ฝั่ง"""
        assert BRIDGE_TUBEAN == ("roeyphae", "khondu")

    def test_sides_split_two_and_two(self):
        sides = [t["side"] for t in TUBEAN]
        assert sides.count("creator") == 2
        assert sides.count("viewer") == 2

    def test_no_agent_jargon_in_questions(self):
        """§6: ภาษาต้องเป็นภาษาชาวบ้าน ไม่ใช้ศัพท์เอเจนต์"""
        banned = ["agent", "workflow", "pipeline", "orchestrat", "routing",
                  "dispatch", "schema", "payload", "heuristic"]
        for t in TUBEAN:
            low = t["question"].lower()
            for b in banned:
                assert b not in low, f"คำถาม '{t['question']}' ใช้ศัพท์เอเจนต์ '{b}'"


# ══════════════════════════════════════════════════════════════════════
# Profile
# ══════════════════════════════════════════════════════════════════════


class TestCreatorProfile:
    """โปรไฟล์ครีเอเตอร์"""

    def test_complete_when_all_four_plus_tone(self):
        p = _profile()
        assert p.is_complete() is True
        assert p.missing() == []

    def test_missing_lists_gaps(self):
        p = _profile(tubean={"tubean": "x"}, tone_words=["a"])
        gaps = p.missing()
        assert "รอยแผล" in gaps
        assert "คนดู" in gaps
        assert any("ตลิ่งโทน" in g for g in gaps)

    def test_requires_exactly_three_tone_words(self):
        p = _profile(tone_words=["a", "b"])
        assert p.is_complete() is False
        assert any("ตลิ่งโทน" in g for g in p.missing())

    def test_answer_lookup(self):
        p = _profile()
        assert p.answer("tubean").startswith("ฉันตัดต่อ")
        assert p.answer("ไม่มี") == ""


class TestSlugify:
    def test_english(self):
        assert slugify("Freelance Clip") == "freelance-clip"

    def test_thai_kept(self):
        assert "ฟรีแลนซ์" in slugify("ฟรีแลนซ์")

    def test_spaces_to_dash(self):
        assert slugify("a  b   c") == "a-b-c"

    def test_empty_fallback(self):
        assert slugify("") == "creator"


class TestFactRoundtrip:
    """profile ↔ facts"""

    def test_roundtrip(self):
        p = _profile()
        key, value = profile_to_fact(p)
        assert key == "creator.freelance-clip.profile"
        back = profile_from_fact({"key": key, "value": value})
        assert back is not None
        assert back.name == p.name
        assert back.tubean == p.tubean
        assert back.tone_words == p.tone_words
        assert back.is_complete()

    def test_value_carries_questions_for_agent(self):
        _, value = profile_to_fact(_profile())
        assert len(value["tubean_questions"]) == 4
        assert value["bridge_tubean"] == ["roeyphae", "khondu"]

    def test_from_fact_handles_json_string(self):
        p = _profile()
        _, value = profile_to_fact(p)
        back = profile_from_fact({"key": "creator.x.profile", "value": json.dumps(value)})
        assert back is not None and back.slug == "x"

    def test_from_fact_none(self):
        assert profile_from_fact({}) is None
        assert profile_from_fact({"value": "not json"}) is None


# ══════════════════════════════════════════════════════════════════════
# โครงคลิป
# ══════════════════════════════════════════════════════════════════════


class TestTikTokBeats:
    """โครงคลิป TikTok — 4 ท่อน → 4 จังหวะเวลา"""

    def test_four_beats(self):
        assert len(TIKTOK_BEATS) == 4

    def test_each_beat_maps_to_a_tubean(self):
        ids = {t["id"] for t in TUBEAN}
        for b in TIKTOK_BEATS:
            assert b["tubean"] in ids

    def test_beats_cover_all_four_tubean_in_order(self):
        assert [b["tubean"] for b in TIKTOK_BEATS] == [
            "tubean", "roeyphae", "khondu", "hettai"]

    def test_timings_are_continuous(self):
        for prev, nxt in zip(TIKTOK_BEATS, TIKTOK_BEATS[1:]):
            assert prev["end"] == nxt["start"], "เวลาต้องต่อกัน ไม่มีช่องว่าง"

    def test_hook_within_three_seconds(self):
        assert TIKTOK_BEATS[0]["end"] <= 3

    def test_total_under_one_minute(self):
        assert TIKTOK_BEATS[-1]["end"] <= 60


class TestBuildScript:
    """build_script — ประกอบสคริปต์จาก 4 ท่อน"""

    def test_beats_carry_profile_text(self):
        p = _profile()
        s = build_script(p, {"title": "ทดสอบ", "why": "เพราะ..."})
        assert len(s["beats"]) == 4
        assert s["beats"][0]["text"] == p.answer("tubean")
        assert s["beats"][1]["text"] == p.answer("roeyphae")

    def test_carries_title_why_tone(self):
        p = _profile()
        s = build_script(p, {"title": "คลิป A", "why": "ทดสอบเหตุผล"})
        assert s["title"] == "คลิป A"
        assert s["why"] == "ทดสอบเหตุผล"
        assert s["tone_words"] == p.tone_words

    def test_caption_and_hashtags(self):
        s = build_script(_profile(), {"title": "t"},
                         caption="แคปชัน", hashtags=["คาเฟ่", "ตัดต่อ"])
        assert s["caption"] == "แคปชัน"
        assert s["hashtags"] == ["คาเฟ่", "ตัดต่อ"]

    def test_tubean_name_present(self):
        s = build_script(_profile(), {"title": "t"})
        assert s["beats"][2]["tubean_name"] == "คนดู"


# ══════════════════════════════════════════════════════════════════════
# แพ็กเกจ
# ══════════════════════════════════════════════════════════════════════


class TestBuildPackage:
    """build_package — แพ็กเกจพร้อมโพสต์ 5 ไฟล์"""

    def _pkg(self, tmp_path, **kw):
        p = _profile()
        s = build_script(p, {"title": "คลิปทดสอบ", "why": "w"}, **kw)
        return p, s, build_package(p, s, tmp_path / "out")

    def test_writes_five_files(self, tmp_path):
        _, _, r = self._pkg(tmp_path)
        assert len(r["files"]) == 5

    def test_all_expected_files_present(self, tmp_path):
        _, _, r = self._pkg(tmp_path)
        joined = " ".join(r["files"])
        for ext in ("script", "shots", "caption", "origin", "checklist"):
            assert ext in joined

    def test_script_file_has_table_and_timings(self, tmp_path):
        p, s, r = self._pkg(tmp_path)
        text = (tmp_path / "out" / f"{r['slug']}.script.md").read_text(encoding="utf-8")
        assert "0–3 วิ" in text
        assert "3–30 วิ" in text
        assert p.answer("khondu") in text

    def test_caption_file(self, tmp_path):
        p = _profile()
        s = build_script(p, {"title": "คลิปทดสอบ"}, caption="แคปชันจริง",
                         hashtags=["คาเฟ่"])
        r = build_package(p, s, tmp_path / "out")
        text = (tmp_path / "out" / f"{r['slug']}.caption.md").read_text(encoding="utf-8")
        assert "แคปชันจริง" in text
        assert "#คาเฟ่" in text

    def test_origin_log_has_columns(self, tmp_path):
        p = _profile()
        s = build_script(p, {"title": "คลิปทดสอบ"})
        r = build_package(p, s, tmp_path / "out", origin=[
            {"item": "เพลง", "source": "YouTube Audio Library", "license": "CC"}])
        text = (tmp_path / "out" / f"{r['slug']}.origin.md").read_text(encoding="utf-8")
        assert "YouTube Audio Library" in text
        assert "CC" in text

    def test_origin_empty_warns(self, tmp_path):
        p = _profile()
        s = build_script(p, {"title": "คลิปทดสอบ"})
        r = build_package(p, s, tmp_path / "out")
        text = (tmp_path / "out" / f"{r['slug']}.origin.md").read_text(encoding="utf-8")
        assert "ยังไม่ได้ใส่" in text

    def test_checklist_has_tone_and_origin_sections(self, tmp_path):
        p = _profile()
        s = build_script(p, {"title": "คลิปทดสอบ"})
        r = build_package(p, s, tmp_path / "out")
        text = (tmp_path / "out" / f"{r['slug']}.checklist.md").read_text(encoding="utf-8")
        assert "ตลิ่งโทน" in text
        assert "ตลิ่งที่มา" in text
        for w in p.tone_words:
            assert w in text

    def test_checklist_blocks_when_tone_missing(self, tmp_path):
        p = _profile(tone_words=[])
        s = build_script(p, {"title": "คลิปทดสอบ"})
        r = build_package(p, s, tmp_path / "out")
        text = (tmp_path / "out" / f"{r['slug']}.checklist.md").read_text(encoding="utf-8")
        assert "ยังไม่ได้ตั้งตลิ่งโทน" in text

    def test_checklist_forbids_sales_promise(self, tmp_path):
        p = _profile()
        s = build_script(p, {"title": "คลิปทดสอบ"})
        r = build_package(p, s, tmp_path / "out")
        text = (tmp_path / "out" / f"{r['slug']}.checklist.md").read_text(encoding="utf-8")
        assert "รวยเร็ว" in text
        assert "ยอดขาย" in text
