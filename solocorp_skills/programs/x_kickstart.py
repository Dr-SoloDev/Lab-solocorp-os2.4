"""X Video Kickstart Bonus — Rules Engine + Posting Tracker

ทุกอย่างในไฟล์นี้มาจาก **เอกสารทางการ** (Terms คุมเหนือ Help Page):

  • Help Center: https://help.x.com/en/using-x/video-kickstart-bonus
  • Terms (ผูกพัน): https://legal.x.com/en/x-creator-kickstart-bonus-terms
    (Effective: October 15, 2026)

ข้อที่ "แข็ง" ที่สุด — Terms §4(a):
  • "The Qualifying Video must be yours. You must have created the video"
  • "not mass-produced solely to manufacture qualifying posts"
  • "not posted solely through unauthorized automation"
  → **AI ทำคลิปให้ = ไม่นับ** · **โพสต์อัตโนมัติ = เสี่ยง**
  → บทบาทของ SoloCorp = ช่วยคิด/ช่วยเขียน/ช่วยตรวจ/ช่วยจัดเวลา
    **ไม่ใช่ผลิตคลิป และไม่กด Publish แทน**
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

__all__ = [
    "PROGRAM",
    "PT",
    "TH",
    "pt_now",
    "pt_day",
    "safe_posting_window_th",
    "VideoProbe",
    "probe_video",
    "check_video",
    "PostingTracker",
    "eligibility_checklist",
    "clip_checklist_md",
    "TRACKER_ROOT",
]

PT = ZoneInfo("America/Los_Angeles")
TH = ZoneInfo("Asia/Bangkok")

ROOT = Path(__file__).resolve().parent.parent.parent
TRACKER_ROOT = ROOT / "bus" / "programs" / "x-kickstart"


# ══════════════════════════════════════════════════════════════════════
# โปรแกรม (จาก Terms §2.a)
# ══════════════════════════════════════════════════════════════════════

PROGRAM: dict[str, Any] = {
    "name": "X Video Kickstart Bonus",
    "terms_effective": "2026-10-15",
    "terms_url": "https://legal.x.com/en/x-creator-kickstart-bonus-terms",
    "help_url": "https://help.x.com/en/using-x/video-kickstart-bonus",
    "periods": [
        {
            "name": "Period 1",
            "start_pt": "2026-10-15T00:00:00",
            "end_pt": "2026-11-14T23:59:59",
            "enroll_deadline_pt": "2026-10-30T23:59:59",
        },
    ],
    "required_videos": 15,          # Terms §2
    "required_posting_days": 15,    # Terms §2 — calendar days in Pacific Time
    "max_duration_s": 180,          # Terms §4(a) — under 3 minutes
    "aspect_ratio": (9, 16),        # Terms §4(a) — vertical
    "keep_public_days_after_period": 30,   # Terms §4(e)
    "bonus_usd_range": (1000, 5000),
    "premium_plus_free_months": 12,
    "timezone": "America/Los_Angeles",
}

# Terms §4(a) — คลิปที่ "ไม่นับ" (ต้องเช็ค)
DISQUALIFIERS: tuple[dict[str, str], ...] = (
    {"id": "not_yours", "label": "ไม่ใช่ของครีเอเตอร์เอง", "detail": "Terms §4(a)"},
    {"id": "watermark", "label": "มีลายน้ำ/ชื่อ/โลโก้ของแพลตฟอร์มอื่น", "detail": "Terms §4(a)"},
    {"id": "branded", "label": "เป็น branded content / paid partnership / โปรโมตโฆษณา", "detail": "Terms §4(a)"},
    {"id": "community_note", "label": "มี Community Note ที่ถูกโหวตว่า Helpful", "detail": "Terms §4(a)"},
    {"id": "mass_produced", "label": "ผลิตเป็นชุดเพื่อจุดประสงค์ให้ครบโควตา", "detail": "Terms §4(a)"},
    {"id": "unauthorized_automation", "label": "โพสต์ผ่าน automation ที่ไม่ได้รับอนุญาต", "detail": "Terms §4(a), §6"},
    {"id": "near_duplicate", "label": "คลิปซ้ำ/ใกล้เคียงกันโพสต์เพื่อเพิ่มจำนวน", "detail": "Terms §4(a), §6"},
    {"id": "deleted_or_private", "label": "ถูกลบ/ทำเป็น private/ถูกถอด — หลุดนับ", "detail": "Terms §2.b, §4(a)"},
    {"id": "posted_before_enroll", "label": "โพสต์ก่อนกด Enroll — ไม่นับ", "detail": "Terms §4(a)"},
    {"id": "posted_outside_period", "label": "โพสต์นอกช่วง Pilot Period — ไม่นับ", "detail": "Terms §4(a)"},
)

# Terms §3 — Eligibility (ทั้งบุคคล ไม่ใช่ต่อคลิป)
ELIGIBILITY_GATES: tuple[dict[str, str], ...] = (
    {"id": "age", "label": "อายุ 18 ขึ้นไป", "detail": "Terms §3"},
    {"id": "country", "label": "อยู่ในประเทศที่ Original Content Rewards ให้บริการ (ไทยอยู่ในรายการ)", "detail": "Terms §3"},
    {"id": "email", "label": "ยืนยันอีเมลแล้ว", "detail": "Terms §3"},
    {"id": "premium", "label": "มี X Premium / Premium Business ที่เข้าเกณฑ์", "detail": "Terms §3"},
    {"id": "payout", "label": "ผูก X Money (สหรัฐฯ) หรือ Stripe (นอกสหรัฐฯ) + ผ่าน identity verification", "detail": "Terms §3, §5(d)"},
    {"id": "standing", "label": "บัญชีอยู่ในสถานะ good standing", "detail": "Terms §3"},
    {"id": "not_prohibited", "label": "ไม่ใช่ Prohibited Person (sanctions) และไม่ทำงานในรัฐบาล/เป็นนักการเมือง", "detail": "Terms §3, §6"},
    {"id": "invited", "label": "ได้รับเชิญและกด Enroll ใน Creator Studio ก่อน deadline", "detail": "Terms §2.a"},
)


# ══════════════════════════════════════════════════════════════════════
# เวลา — Pacific Time คือหัวใจ
# ══════════════════════════════════════════════════════════════════════


def pt_now() -> datetime:
    """เวลาปัจจุบันใน Pacific Time (Terms §2: ทุก deadline เป็น PT)"""
    return datetime.now(PT)


def pt_day(dt: Optional[datetime] = None) -> date:
    """calendar day ตาม Pacific Time — 12:00am PT ถึง 11:59pm PT (Terms §2)"""
    if dt is None:
        dt = pt_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PT)
    return dt.astimezone(PT).date()


def safe_posting_window_th() -> tuple[str, str]:
    """ช่วงเวลาไทยที่ปลอดภัย — โพสต์แล้ว PT day ตรงกับวันไทย

    TH = PT + 15 ชม. → ช่วง TH 15:00-23:59 ของวัน D และ 00:00-14:59 ของวัน D+1
    ต่างก็ยังตกใน PT day D → **โพสต์หลัง 15:00 ไทย = วันตรงกันเสมอ**
    """
    return ("15:00", "23:59")


def pt_day_for_local(dt_local: datetime) -> date:
    """วันตาม PT ของเวลาท้องถิ่นที่กำหนด (รองรับ TH)"""
    if dt_local.tzinfo is None:
        dt_local = dt_local.replace(tzinfo=TH)
    return dt_local.astimezone(PT).date()


def _parse_pt(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp).replace(tzinfo=PT)


# ══════════════════════════════════════════════════════════════════════
# ตรวจไฟล์วิดีโอ (Terms §4(a))
# ══════════════════════════════════════════════════════════════════════


@dataclass
class VideoProbe:
    """ผลตรวจไฟล์วิดีโอ"""
    path: str
    width: int = 0
    height: int = 0
    duration_s: float = 0.0
    ok: bool = True
    error: str = ""

    @property
    def ratio(self) -> float:
        return (self.width / self.height) if self.height else 0.0

    @property
    def is_vertical(self) -> bool:
        """9:16 โดยยอมให้คลาดเล็กน้อย (ความกว้าง/ความสูง ≈ 0.5625)"""
        return bool(self.height) and abs(self.ratio - 9 / 16) < 0.02

    @property
    def duration_ok(self) -> bool:
        return 0 < self.duration_s < PROGRAM["max_duration_s"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path, "width": self.width, "height": self.height,
            "duration_s": round(self.duration_s, 2), "is_vertical": self.is_vertical,
            "duration_ok": self.duration_ok, "error": self.error,
        }


def probe_video(path: str | Path) -> VideoProbe:
    """อ่าน metadata ของไฟล์วิดีโอด้วย ffprobe"""
    p = Path(path)
    if not p.exists():
        return VideoProbe(path=str(p), ok=False, error="ไม่พบไฟล์")
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height:format=duration",
             "-of", "json", str(p)],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(r.stdout or "{}")
        streams = data.get("streams") or [{}]
        st = streams[0]
        dur = (data.get("format") or {}).get("duration") or st.get("duration") or 0
        return VideoProbe(
            path=str(p),
            width=int(st.get("width") or 0),
            height=int(st.get("height") or 0),
            duration_s=float(dur),
        )
    except Exception as e:
        return VideoProbe(path=str(p), ok=False, error=f"{type(e).__name__}: {e}")


def check_video(path: str | Path) -> list[dict[str, Any]]:
    """ตรวจไฟล์เทียบเงื่อนไขที่ตรวจได้ด้วยเครื่อง (Terms §4(a))

    คืน list ของ {rule, ok, detail}
    """
    vp = probe_video(path)
    checks: list[dict[str, Any]] = []

    checks.append({
        "rule": "แนวตั้ง 9:16",
        "ok": vp.is_vertical,
        "detail": (f"{vp.width}x{vp.height} (ratio {vp.ratio:.3f})" if vp.width
                   else vp.error or "อ่านข้อมูลไฟล์ไม่ได้"),
    })
    checks.append({
        "rule": f"ความยาว < {PROGRAM['max_duration_s']} วิ (3 นาที)",
        "ok": vp.duration_ok,
        "detail": f"{vp.duration_s:.1f} วิ" if vp.duration_s else vp.error,
    })
    return checks


# ══════════════════════════════════════════════════════════════════════
# Tracker — นับ posting days ตาม Pacific Time
# ══════════════════════════════════════════════════════════════════════


@dataclass
class PostingTracker:
    """นับวันที่โพสต์ (PT) + คลิปที่โพสต์

    เก็บเอง เพราะ tracker ของ X เป็น "informational only" และ Final Count
    อาจต่ำกว่า (Terms §2.b, §2.c) → ต้องมีบันทึกของเราเอง
    """
    creator: str
    enrolled_at: Optional[str] = None       # ISO — local time ที่กด Enroll
    days: list[str] = field(default_factory=list)      # PT calendar days
    videos: list[dict[str, Any]] = field(default_factory=list)
    path: Optional[Path] = None

    # ── persistence ────────────────────────────────────────────────
    def tracker_path(self) -> Path:
        base = TRACKER_ROOT / self.creator
        base.mkdir(parents=True, exist_ok=True)
        return base / "tracker.json"

    def load(self) -> "PostingTracker":
        p = self.tracker_path()
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                self.enrolled_at = d.get("enrolled_at")
                self.days = list(d.get("days", []))
                self.videos = list(d.get("videos", []))
            except Exception:
                pass
        return self

    def save(self) -> Path:
        p = self.tracker_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "creator": self.creator,
            "enrolled_at": self.enrolled_at,
            "days": sorted(set(self.days)),
            "videos": self.videos,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    # ── enroll ─────────────────────────────────────────────────────
    def enroll(self, when_local: Optional[datetime] = None) -> str:
        """บันทึกเวลากด Enroll — หลังจากนี้เท่านั้นที่นับ (Terms §4(a))"""
        when = when_local or datetime.now(TH)
        self.enrolled_at = when.isoformat()
        self.save()
        return self.enrolled_at

    def is_enrolled(self) -> bool:
        return bool(self.enrolled_at)

    # ── record ─────────────────────────────────────────────────────
    def record_post(self, *, title: str, url: str, posted_local: Optional[datetime] = None,
                    video_path: Optional[str] = None) -> dict[str, Any]:
        """บันทึกการโพสต์ 1 คลิป → คืนสรุปวันนั้น"""
        when = posted_local or datetime.now(TH)
        d_pt = pt_day_for_local(when)
        d_str = d_pt.isoformat()
        is_new_day = d_str not in self.days
        if is_new_day:
            self.days.append(d_str)
        self.videos.append({
            "title": title,
            "url": url,
            "posted_local": when.isoformat(),
            "pt_day": d_str,
            "video_path": str(video_path) if video_path else None,
        })
        self.save()
        return {"pt_day": d_str, "new_day": is_new_day, "count": len(self.videos)}

    # ── status ─────────────────────────────────────────────────────
    def status(self, now_pt: Optional[datetime] = None) -> dict[str, Any]:
        """สถานะปัจจุบันเทียบเกณฑ์"""
        now = now_pt or pt_now()
        today = pt_day(now)
        period = self.current_period(now)
        days = set(self.days)
        need_days = PROGRAM["required_posting_days"]
        need_vids = PROGRAM["required_videos"]

        used = len(days)
        done = max(0, used - need_days)
        left_days = max(0, need_days - used)
        left_vids = max(0, need_vids - len(self.videos))

        days_left_in_period = None
        deadline_passed = False
        if period:
            end = _parse_pt(period["end_pt"])
            days_left_in_period = (end.date() - today).days + 1
            deadline_passed = now > end
            enroll_deadline = _parse_pt(period["enroll_deadline_pt"])
            deadline_passed = deadline_passed or now > enroll_deadline

        posted_today = today.isoformat() in days
        safe_from, safe_to = safe_posting_window_th()

        return {
            "creator": self.creator,
            "enrolled": self.is_enrolled(),
            "enrolled_at": self.enrolled_at,
            "pt_today": today.isoformat(),
            "posted_today": posted_today,
            "safe_posting_window_th": f"{safe_from}-{safe_to}",
            "days_used": used,
            "days_needed": need_days,
            "days_left": left_days,
            "days_over_needed": done,
            "videos_posted": len(self.videos),
            "videos_needed": need_vids,
            "videos_left": left_vids,
            "days_left_in_period": days_left_in_period,
            "period": period["name"] if period else None,
            "period_over": deadline_passed,
            "on_track": (not deadline_passed and used >= need_days
                         and left_days <= (days_left_in_period or 0)),
            "keep_public_until": (
                (period and (_parse_pt(period["end_pt"]).date()
                             + timedelta(days=PROGRAM["keep_public_days_after_period"])))
                if period else None),
        }

    def current_period(self, now_pt: Optional[datetime] = None) -> Optional[dict[str, Any]]:
        now = now_pt or pt_now()
        for p in PROGRAM["periods"]:
            if _parse_pt(p["start_pt"]) <= now <= _parse_pt(p["end_pt"]):
                return p
        return None

    def next_period(self) -> Optional[dict[str, Any]]:
        now = pt_now()
        future = [p for p in PROGRAM["periods"] if _parse_pt(p["end_pt"]) > now]
        return future[0] if future else None


# ══════════════════════════════════════════════════════════════════════
# Checklist
# ══════════════════════════════════════════════════════════════════════


def eligibility_checklist() -> str:
    """checklist รายบุคคล (Terms §3) — ต้องผ่านก่อนโพสต์อะไรก็ตาม"""
    lines = ["# 👤 Eligibility — ผ่านก่อน (Terms §3)", ""]
    for g in ELIGIBILITY_GATES:
        lines.append(f"- [ ] **{g['label']}**  _({g['detail']})_")
    lines += [
        "",
        "> ถ้าข้อไหนยังไม่ผ่าน → บอนัสนั้นรอบจะไม่ออก "
        "(Terms §5.d: ไม่จ่ายจน onboarding + identity verification เสร็จ)",
    ]
    return "\n".join(lines)


def clip_checklist_md(creator: str, title: str, video_path: Optional[str] = None,
                      origin_rows: Optional[list[dict[str, str]]] = None,
                      tracker_status: Optional[dict[str, Any]] = None) -> str:
    """checklist ก่อนโพสต์คลิป 1 ชิ้น (Terms §4)"""
    lines = [f"# ✅ ก่อนโพสต์ — {title}", "", f"**ครีเอเตอร์:** {creator}", ""]

    lines += ["## 1 · ไฟล์ผ่านเงื่อนไข (ตรวจอัตโนมัติได้)", ""]
    if video_path:
        for c in check_video(video_path):
            mark = "✅" if c["ok"] else "❌"
            lines.append(f"- [{mark}] {c['rule']} — {c['detail']}")
    else:
        lines.append("- [ ] แนวตั้ง 9:16 (1080x1920) — ตรวจด้วย `ffprobe`")
        lines.append("- [ ] ความยาว < 3 นาที")
    lines += [
        "- [ ] ไม่มีลายน้ำ/ชื่อ/โลโก้ของแพลตฟอร์มอื่น",
        "      _เคล็ดลับจาก X: เอาไฟล์ต้นฉบับจากกล้อง อย่า save จากแอปอื่น_",
        "",
        "## 2 · เนื้อหา (ต้องตอบด้วยตัวเอง — ตรวจอัตโนมัติไม่ได้)",
        "",
        "- [ ] **เป็นของครีเอเตอร์เอง** — ถ่าย/ทำเอง (Terms §4(a))",
        "      _คลิปที่ AI ทำให้ = ไม่นับ · คลิปจากแพลตฟอร์มอื่นนับได้ถ้าเป็นของครีเอเตอร์_",
        "- [ ] **ไม่ใช่ branded content / paid partnership / โปรโมตโฆษณา** — โปรแกรมนี้นับเฉพาะคอนเทนต์ที่ไม่ใช่ของแบรนด์",
        "- [ ] **ไม่ใช่คลิปซ้ำ** — คลิปเดิมโพสต์ซ้ำนับแค่ 1",
        "- [ ] ไม่ใช่ mass-produced ที่ทำเพื่อจุดประสงค์ให้ครบโควตา",
        "- [ ] **ไม่ได้โพสต์ผ่าน automation ที่ไม่ได้รับอนุญาต** — ให้ครีเอเตอร์กด Publish เอง (Terms §4(a), §6)",
        "- [ ] ไม่มี Community Note ที่ถูกโหวตว่า Helpful",
        "- [ ] เผยแพร่ตามกฎ FTC ถ้าเป็นการโปรโมต/มีส่วนร่วม",
        "",
        "## 3 · ต้นทาง (ตลิ่งที่มา — ยังไม่ตรึง)",
        "",
        "| ชิ้น | ที่มา | สิทธิ์ |",
        "|:--|:--|:--|",
    ]
    for r in (origin_rows or []):
        lines.append(f"| {r.get('item', '')} | {r.get('source', '')} | {r.get('license', '')} |")
    if not origin_rows:
        lines.append("| _(ยังไม่ได้ใส่)_ | — | — |")
    lines.append("")

    if tracker_status:
        s = tracker_status
        lines += [
            "## 4 · สถานะโควตา (นับเอง — tracker ของ X เป็นเพียงข้อมูลบอกทาง)",
            "",
            f"- วันที่โพสต์แล้ว: **{s['days_used']}/{s['days_needed']}** "
            f"(เหลืออีก {s['days_left']} วัน)",
            f"- คลิปแล้ว: **{s['videos_posted']}/{s['videos_needed']}** (เหลืออีก {s['videos_left']})",
            f"- วันนี้ (PT {s['pt_today']}): "
            f"{'✅ โพสต์แล้ว' if s['posted_today'] else '❌ ยังไม่ได้โพสต์วันนี้'}",
            f"- ช่วงเวลาไทยที่ปลอดภัย: **{s['safe_posting_window_th']}**",
        ]
        if s.get("days_left_in_period") is not None:
            lines.append(f"- เหลือวันในรอบ: **{s['days_left_in_period']} วัน**")
        if s.get("keep_public_until"):
            lines.append(f"- ⚠️ ต้องคงโพสต์ไว้ (public + ไม่แก้) จนถึง **{s['keep_public_until']}**")
        lines.append("")

    lines += [
        "> ห้าม: ลบ / ทำเป็น protected / แก้โพสต์ — จะหลุดนับ (Terms §2.b, §4(a), §4(e))",
    ]
    return "\n".join(lines)
