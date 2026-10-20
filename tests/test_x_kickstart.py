"""Tests for X Video Kickstart Bonus — rules engine + Pacific-Time tracker

อ้างอิง: https://legal.x.com/en/x-creator-kickstart-bonus-terms (Terms คุมเหนือ Help Page)
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solocorp_skills.programs.x_kickstart import (  # noqa: E402
    DISQUALIFIERS,
    ELIGIBILITY_GATES,
    PROGRAM,
    PT,
    TH,
    PostingTracker,
    check_video,
    clip_checklist_md,
    eligibility_checklist,
    probe_video,
    pt_day,
    pt_day_for_local,
    safe_posting_window_th,
)


# ══════════════════════════════════════════════════════════════════════
# โปรแกรม
# ══════════════════════════════════════════════════════════════════════


class TestProgram:
    def test_core_numbers(self):
        assert PROGRAM["required_videos"] == 15
        assert PROGRAM["required_posting_days"] == 15
        assert PROGRAM["max_duration_s"] == 180
        assert PROGRAM["aspect_ratio"] == (9, 16)
        assert PROGRAM["keep_public_days_after_period"] == 30

    def test_period_1_dates_match_terms(self):
        p = PROGRAM["periods"][0]
        assert p["start_pt"].startswith("2026-10-15")
        assert p["end_pt"].startswith("2026-11-14")
        assert p["enroll_deadline_pt"].startswith("2026-10-30")

    def test_timezone_is_pacific(self):
        assert PROGRAM["timezone"] == "America/Los_Angeles"

    def test_disqualifiers_cover_terms_4a(self):
        ids = {d["id"] for d in DISQUALIFIERS}
        for must in ("not_yours", "watermark", "branded", "mass_produced",
                     "unauthorized_automation", "near_duplicate", "deleted_or_private"):
            assert must in ids, f"ขาดเงื่อนไข {must}"

    def test_eligibility_gates_cover_terms_3(self):
        ids = {g["id"] for g in ELIGIBILITY_GATES}
        for must in ("age", "country", "email", "premium", "payout", "standing", "invited"):
            assert must in ids, f"ขาด gate {must}"


# ══════════════════════════════════════════════════════════════════════
# Pacific Time
# ══════════════════════════════════════════════════════════════════════


class TestPacificTime:
    """Terms §2: ทุก deadline เป็น Pacific Time"""

    def test_pt_day_uses_pacific_not_local(self):
        # TH 2026-10-21 เวลา 10:00 = PT 2026-10-20 19:00 → PT day = 20
        th_morning = datetime(2026, 10, 21, 10, 0, tzinfo=TH)
        assert pt_day_for_local(th_morning) == date(2026, 10, 20)

    def test_th_evening_same_pt_day(self):
        # TH 2026-10-21 เวลา 20:00 = PT 2026-10-21 05:00 → PT day = 21
        th_evening = datetime(2026, 10, 21, 20, 0, tzinfo=TH)
        assert pt_day_for_local(th_evening) == date(2026, 10, 21)

    def test_safe_window_is_15_to_2359_th(self):
        assert safe_posting_window_th() == ("15:00", "23:59")

    def test_pt_day_of_utc(self):
        # PT เที่ยงคืนเริ่มวันใหม่ — 00:00 PT = วันใหม่, 23:59 PT = ยังวันเดิม
        assert pt_day(datetime(2026, 10, 21, 0, 0, tzinfo=PT)) == date(2026, 10, 21)
        assert pt_day(datetime(2026, 10, 20, 23, 59, tzinfo=PT)) == date(2026, 10, 20)


# ══════════════════════════════════════════════════════════════════════
# Tracker
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture()
def tracker(tmp_path, monkeypatch):
    import solocorp_skills.programs.x_kickstart as mod
    monkeypatch.setattr(mod, "TRACKER_ROOT", tmp_path)
    return PostingTracker(creator="test-creator")


class TestPostingTracker:
    def test_starts_empty(self, tracker):
        t = tracker.load()
        assert t.days == []
        assert t.videos == []
        assert t.is_enrolled() is False

    def test_enroll_records_time(self, tracker):
        t = tracker.load()
        t.enroll(datetime(2026, 10, 20, 9, 0, tzinfo=TH))
        assert t.is_enrolled() is True
        t2 = PostingTracker(creator="test-creator").load()
        assert t2.is_enrolled() is True

    def test_record_post_adds_pt_day(self, tracker):
        t = tracker.load()
        t.enroll(datetime(2026, 10, 20, 9, 0, tzinfo=TH))
        r = t.record_post(title="คลิป 1", url="https://x.com/a/1",
                          posted_local=datetime(2026, 10, 20, 20, 0, tzinfo=TH))
        assert r["pt_day"] == "2026-10-20"
        assert r["new_day"] is True

    def test_two_posts_same_day_counts_one_day(self, tracker):
        t = tracker.load()
        t.enroll(datetime(2026, 10, 20, 9, 0, tzinfo=TH))
        t.record_post(title="a", url="u1", posted_local=datetime(2026, 10, 20, 20, 0, tzinfo=TH))
        r = t.record_post(title="b", url="u2", posted_local=datetime(2026, 10, 20, 21, 0, tzinfo=TH))
        assert r["new_day"] is False
        assert len(t.days) == 1
        assert len(t.videos) == 2, "คลิปนับ 2 แต่วันนับ 1"

    def test_early_morning_th_posts_to_previous_pt_day(self, tracker):
        t = tracker.load()
        t.enroll(datetime(2026, 10, 20, 9, 0, tzinfo=TH))
        t.record_post(title="a", url="u1", posted_local=datetime(2026, 10, 21, 8, 0, tzinfo=TH))
        assert t.days == ["2026-10-20"], "โพสต์เช้าไทย = นับเป็นเมื่อวาน PT"

    def test_status_counts(self, tracker):
        t = tracker.load()
        t.enroll(datetime(2026, 10, 20, 9, 0, tzinfo=TH))
        for i in range(3):
            t.record_post(title=f"c{i}", url=f"u{i}",
                          posted_local=datetime(2026, 10, 20 + i, 20, 0, tzinfo=TH))
        s = t.status(datetime(2026, 10, 23, 12, 0, tzinfo=PT))
        assert s["days_used"] == 3
        assert s["days_left"] == 12
        assert s["videos_posted"] == 3
        assert s["videos_left"] == 12

    def test_status_reports_posted_today(self, tracker):
        t = tracker.load()
        t.enroll(datetime(2026, 10, 20, 9, 0, tzinfo=TH))
        t.record_post(title="a", url="u1", posted_local=datetime(2026, 10, 20, 20, 0, tzinfo=TH))
        s = t.status(datetime(2026, 10, 20, 22, 0, tzinfo=PT))
        assert s["posted_today"] is True

    def test_status_days_left_in_period(self, tracker):
        t = tracker.load()
        t.enroll(datetime(2026, 10, 20, 9, 0, tzinfo=TH))
        s = t.status(datetime(2026, 10, 20, 12, 0, tzinfo=PT))
        assert s["period"] == "Period 1"
        assert s["days_left_in_period"] == 26  # 20 ต.ค. → 14 พ.ย. = 26 วัน
        assert s["keep_public_until"] == date(2026, 12, 14)

    def test_tracker_persists(self, tracker, tmp_path):
        t = tracker.load()
        t.enroll(datetime(2026, 10, 20, 9, 0, tzinfo=TH))
        t.record_post(title="a", url="u1", posted_local=datetime(2026, 10, 20, 20, 0, tzinfo=TH))
        fresh = PostingTracker(creator="test-creator").load()
        assert fresh.days == ["2026-10-20"]
        assert len(fresh.videos) == 1


# ══════════════════════════════════════════════════════════════════════
# ตรวจไฟล์
# ══════════════════════════════════════════════════════════════════════


class TestVideoProbe:
    def test_missing_file(self, tmp_path):
        vp = probe_video(tmp_path / "ไม่มี.mp4")
        assert vp.ok is False
        assert vp.error

    def test_check_video_returns_two_rules(self, tmp_path):
        checks = check_video(tmp_path / "ไม่มี.mp4")
        assert len(checks) == 2
        assert "9:16" in checks[0]["rule"]
        assert checks[0]["ok"] is False

    def test_vertical_detection(self):
        from solocorp_skills.programs.x_kickstart import VideoProbe
        v = VideoProbe(path="x", width=1080, height=1920)
        assert v.is_vertical is True
        assert v.ratio == pytest.approx(0.5625)

    def test_landscape_rejected(self):
        from solocorp_skills.programs.x_kickstart import VideoProbe
        v = VideoProbe(path="x", width=1920, height=1080)
        assert v.is_vertical is False

    def test_duration_limit(self):
        from solocorp_skills.programs.x_kickstart import VideoProbe
        assert VideoProbe(path="x", duration_s=179.9).duration_ok is True
        assert VideoProbe(path="x", duration_s=180.1).duration_ok is False


# ══════════════════════════════════════════════════════════════════════
# Checklist
# ══════════════════════════════════════════════════════════════════════


class TestChecklists:
    def test_eligibility_has_all_gates(self):
        text = eligibility_checklist()
        for g in ELIGIBILITY_GATES:
            assert g["label"][:12] in text

    def test_eligibility_mentions_no_payout(self):
        text = eligibility_checklist()
        assert "onboarding" in text or "Stripe" in text

    def test_clip_checklist_blocks_ai_content(self):
        text = clip_checklist_md("โชค", "คลิปทดสอบ")
        assert "AI ทำให้ = ไม่นับ" in text

    def test_clip_checklist_blocks_auto_post(self):
        text = clip_checklist_md("โชค", "คลิปทดสอบ")
        assert "automation" in text

    def test_clip_checklist_blocks_branded(self):
        text = clip_checklist_md("โชค", "คลิปทดสอบ")
        assert "paid partnership" in text

    def test_clip_checklist_warns_not_to_delete(self):
        text = clip_checklist_md("โชค", "คลิปทดสอบ")
        assert "ห้าม" in text or "ลบ" in text

    def test_clip_checklist_includes_tracker_status(self):
        s = {
            "days_used": 3, "days_needed": 15, "days_left": 12,
            "videos_posted": 3, "videos_needed": 15, "videos_left": 12,
            "pt_today": "2026-10-20", "posted_today": False,
            "safe_posting_window_th": "15:00-23:59",
            "days_left_in_period": 26, "keep_public_until": "2026-12-14",
        }
        text = clip_checklist_md("โชค", "คลิปทดสอบ", tracker_status=s)
        assert "3/15" in text
        assert "15:00-23:59" in text
        assert "2026-12-14" in text

    def test_clip_checklist_lists_origin_rows(self):
        text = clip_checklist_md(
            "โชค", "คลิปทดสอบ",
            origin_rows=[{"item": "เพลง", "source": "YT Audio Library", "license": "CC"}],
        )
        assert "YT Audio Library" in text
