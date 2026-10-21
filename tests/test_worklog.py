"""Tests for Work Log Miner — ขุดเรื่องราวจากงานจริงใน repo

โหมด "สร้างตัวตน": เนื้อหาไม่ได้คิดขึ้นเอง แต่มาจาก ADR / session-log / git / evidence
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solocorp_skills.worklog import (  # noqa: E402
    WorkStory,
    _clean_md,
    _md_section,
    build_text_post,
    collect_stories,
    story_to_idea,
)


# ══════════════════════════════════════════════════════════════════════
# ตัวช่วย markdown
# ══════════════════════════════════════════════════════════════════════


class TestMarkdownHelpers:
    def test_md_section_extracts(self):
        text = "## บริบท\nเนื้อหา A\n\n## การตัดสินใจ\nเนื้อหา B\n\n## ผลกระทบ\nC"
        assert "เนื้อหา A" in _md_section(text, "บริบท")
        assert "เนื้อหอ B" in _md_section(text, "การตัดสินใจ") or \
               "เนื้อหา B" in _md_section(text, "การตัดสินใจ")

    def test_md_section_missing_returns_empty(self):
        assert _md_section("## อื่น\nx", "ไม่มี") == ""

    def test_clean_md_strips_markup(self):
        raw = "### หัวข้อ\n**ตัวหนา** `โค้ด`\n- bullet\n```\ncode\n```"
        out = _clean_md(raw)
        assert "**" not in out and "```" not in out
        assert "ตัวหนา" in out

    def test_clean_md_truncates(self):
        assert len(_clean_md("x" * 5000, max_chars=100)) == 100


# ══════════════════════════════════════════════════════════════════════
# เรื่องราว
# ══════════════════════════════════════════════════════════════════════


class TestWorkStory:
    def test_to_dict(self):
        s = WorkStory(kind="adr", ref="ADR-1.md", title="T", problem="p", fix="f", why="w")
        d = s.to_dict()
        assert d["kind"] == "adr" and d["problem"] == "p"

    def test_story_to_idea(self):
        s = WorkStory(kind="commit", ref="abc1234", title="fix: ปัญหา X",
                      problem="ระบบโกหก", fix="แก้ให้อ่าน SQLite", why="เพื่อให้เห็นความจริง")
        idea = story_to_idea(s)
        assert idea["title"] == "fix: ปัญหา X"
        assert idea["problem"] == "ระบบโกหก"
        assert idea["why"] == "เพื่อให้เห็นความจริง"
        assert idea["source"] == "abc1234"

    def test_story_to_idea_hook_from_problem(self):
        s = WorkStory(kind="adr", ref="r", title="t",
                      problem="บรรทัดแรกของปัญหา\nบรรทัดที่สอง",
                      fix="f", why="w")
        idea = story_to_idea(s)
        assert idea["hook"].startswith("บรรทัดแรก")
        assert "\n" not in idea["hook"]


class TestBuildTextPost:
    def test_post_has_all_four_parts(self):
        s = WorkStory(kind="commit", ref="abc", title="t",
                      problem="เจอปัญหา A", fix="แก้ B", why="เพราะ C",
                      evidence="git abc")
        post = build_text_post(s)
        assert "เจอปัญหา: เจอปัญหา A" in post
        assert "แก้: แก้ B" in post
        assert "เพราะ: เพราะ C" in post
        assert "หลักฐาน: git abc" in post

    def test_post_has_signature(self):
        post = build_text_post(WorkStory(kind="c", ref="r", title="t",
                                        problem="p", fix="f", why="w"))
        assert "Dr.Solodev" in post
        assert "frontier builder" in post

    def test_post_accepts_dict(self):
        post = build_text_post({"problem": "p1", "fix": "f1", "why": "w1",
                                 "evidence": "e1"})
        assert "เจอปัญหา: p1" in post
        assert "เพราะ: w1" in post

    def test_post_without_parts_still_works(self):
        post = build_text_post(WorkStory(kind="c", ref="r", title="แค่ชื่อเรื่อง"))
        assert "แค่ชื่อเรื่อง" in post
        assert "Dr.Solodev" in post

    def test_post_custom_handle(self):
        post = build_text_post({"title": "t"}, handle="โชค", tagline="ฟรีแลนซ์")
        assert "— โชค · ฟรีแลนซ์" in post

    def test_post_no_sales_promise(self):
        """vision §5.2: ห้ามขายฝันยอดขาย"""
        post = build_text_post({"problem": "p", "fix": "f", "why": "w",
                                 "evidence": "e"})
        for banned in ("รวยเร็ว", "ยอดขาย", "ผู้ติดตาม", "การันตี"):
            assert banned not in post


# ══════════════════════════════════════════════════════════════════════
# ขุดจาก repo จริง
# ══════════════════════════════════════════════════════════════════════


class TestCollectStories:
    def test_finds_stories_in_real_repo(self):
        stories = collect_stories(days=30, limit=20, min_score=1)
        assert len(stories) > 0, "repo ต้องมีเรื่องที่ขุดได้"

    def test_stories_have_required_fields(self):
        for s in collect_stories(days=30, limit=10, min_score=1):
            assert s.kind in ("adr", "commit", "session", "evidence")
            assert s.title.strip()
            assert s.ref

    def test_sorts_by_score_desc(self):
        stories = collect_stories(days=30, limit=20, min_score=1)
        scores = [s.score for s in stories]
        assert scores == sorted(scores, reverse=True)

    def test_adr_stories_have_decision(self):
        stories = [s for s in collect_stories(days=30, limit=30, min_score=1)
                   if s.kind == "adr"]
        assert stories, "ต้องขุด ADR ได้"
        for s in stories:
            assert s.fix.strip(), f"ADR {s.ref} ไม่มีการตัดสินใจ"

    def test_min_score_filters(self):
        loose = collect_stories(days=30, limit=30, min_score=1)
        strict = collect_stories(days=30, limit=30, min_score=99)
        assert len(strict) <= len(loose)

    def test_kind_filter(self):
        only_adr = collect_stories(days=30, kinds=("adr",), limit=10, min_score=1)
        assert all(s.kind == "adr" for s in only_adr)

    def test_limit_respected(self):
        assert len(collect_stories(days=30, limit=3, min_score=1)) <= 3
