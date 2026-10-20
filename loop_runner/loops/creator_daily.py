"""Creator Daily — โมเดล B (เวิร์กโฟลว์) ของสนามแรก

หลักการที่ยึด (จาก Terms ของ X Video Kickstart Bonus ฉบับทางการ):
  • "The Qualifying Video must be **yours**" → เรา**ไม่ผลิตคลิปให้**
  • "not mass-produced solely to manufacture qualifying posts" → เรา**ไม่ผลิตเป็นชุด**
  • "not posted solely through unauthorized automation" → เรา**ไม่กด Publish แทน**

บทบาทของ SoloCorp = **ผู้เตรียม · ผู้ตรวจ · ผู้จัดการเวลา**
  1. เช้ามาเช็ค tracker → วันนี้โพสต์แล้วหรือยัง
  2. ยังไม่โพสต์ → เตรียม 3 ไอเดีย + โครงสคริปต์ (จาก 4 ท่อน) + แพ็กเกจ + checklist
  3. ส่ง inbox ให้ครีเอเตอร์ → ครีเอเตอร์ถ่าย/โพสต์เอง (กด Publish ด้วยตัวเอง)
  4. ครีเอเตอร์บอกผล → บันทึกวัน (นับเอง เพราะ tracker ของ X เป็นแค่ข้อมูลบอกทาง)

วนนี้ = เรื่องเดียวกับ vision §5.3: ตัวช่วยคิดไอเดีย + ตัวช่วยออกแบบสคริปต์ + เวิร์กโฟลว์ช่วยเดินงาน
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from ..runner import Loop
from ..state import last_run

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from solocorp_skills.creator import (  # noqa: E402
    CreatorProfile,
    build_package,
    build_script,
    load_profile,
)
from solocorp_skills.programs.x_kickstart import (  # noqa: E402
    TRACKER_ROOT,
    PostingTracker,
    clip_checklist_md,
)

BUS_URL = os.environ.get("SOLOCORP_BUS_URL", "http://127.0.0.1:8099")
API_KEY = os.environ.get("SOLOCORP_API_KEY", "sk-solocorp-admin-local-dev-001")
INBOX = Path(__file__).parent.parent.parent / "scripts" / "inbox.py"
OUT_ROOT = Path(__file__).parent.parent.parent / "bus" / "media" / "creator"

# โพสต์ช่วง 15:00+ ไทย = PT day ตรงกับวันไทย (ดู safe_posting_window_th)
IDEA_COUNT = 3


def _enrolled_creators() -> list[str]:
    """รายชื่อครีเอเตอร์ที่ enroll แล้ว (จาก tracker.json)"""
    if not TRACKER_ROOT.exists():
        return []
    out = []
    for p in sorted(TRACKER_ROOT.glob("*/tracker.json")):
        out.append(p.parent.name)
    return out


def _send_inbox(to: str, subject: str, body: str) -> bool:
    try:
        r = subprocess.run(
            [sys.executable, str(INBOX), "send", "creator_daily", to, subject, body[:1500]],
            capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        return r.returncode == 0 and "ไม่รู้จัก" not in (r.stdout or "")
    except Exception:
        return False


def _parse_json_array(raw: str) -> list[dict[str, str]]:
    """แปลง JSON array จาก LLM — ทนต่อการถูกตัดกลาง

    LLM มักตอบ JSON ไม่ครบ (โดน max_tokens ตัด) → ซ่อมโดยตัดที่
    วงเล็บปีกกาให้สมบูรณ์แล้วลองใหม่
    """
    raw = raw.strip()
    start, end = raw.find("["), raw.rfind("]")
    if start == -1:
        return []
    if end > start:
        try:
            data = json.loads(raw[start:end + 1])
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
        except Exception:
            pass
    # ซ่อม: ตัดที่ '}' ล่าสุด แล้วปิด array
    body = raw[start + 1:]
    last = body.rfind("}")
    if last == -1:
        return []
    for tail in ("]", "}]", "},]"):
        try:
            data = json.loads(body[:last + 1] + tail)
            if isinstance(data, list) and data:
                return [d for d in data if isinstance(d, dict)]
        except Exception:
            continue
    return []


def _generate_ideas(profile: CreatorProfile, recent_news: str) -> list[dict[str, str]]:
    """ให้ LLM คิดไอเดียจาก 4 ท่อน + ข่าวล่าสุด (ตัวช่วยคิดไอเดีย)"""
    from workers.llm_provider import think

    tubean_text = "\n".join(f"- {t['name']}: {profile.answer(t['id'])}" for t in
                           __import__("solocorp_skills.creator", fromlist=["TUBEAN"]).TUBEAN)
    prompt = (
        f"คุณคือตัวช่วยคิดไอเดียของครีเอเตอร์ชื่อ {profile.name}\n\n"
        f"เรื่อง 4 ท่อนของเขา:\n{tubean_text}\n\n"
        f"ตลิ่งโทน: {' / '.join(profile.tone_words)}\n\n"
        f"ข่าว/เทรนด์ล่าสุดที่เกี่ยวข้อง:\n{recent_news[:1200]}\n\n"
        f"คิดไอเดียสคริปต์แนวตั้ง (X short video) {IDEA_COUNT} ไอเดีย "
        f"สำหรับเขา คือแต่ละไอเดียต้อง:\n"
        f"1) เป็นเรื่องจริงจากรอยแผลของเขา (ท่อน 'รอยแผล')\n"
        f"2) ตอบคนดูที่เขาระบุไว้ (ท่อน 'คนดู')\n"
        f"3) เขียนเป็นภาษาชาวบ้าน ไม่ใช้ศัพท์เอเจนต์\n"
        f"4) ห้ามสัญญาว่ารวยเร็วหรือยอดขาย\n\n"
        f"เขียนสั้น ๆ: title ไม่เกิน 40 ตัว · why ไม่เกิน 100 ตัว · hook ไม่เกิน 70 ตัว\n"
        f"ตอบเป็น JSON array เท่านั้น ไม่ต้องมีคำอธิบายอื่น:\n"
        f'[{{"title":"...","why":"...","hook":"..."}}]'
    )
    raw = asyncio.run(think(prompt, max_tokens=1500, timeout=240))
    if raw.startswith("⚠️ LLM ไม่พร้อย"):
        return []
    return _parse_json_array(raw)
    try:
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            return []
        items = json.loads(raw[start:end + 1])
        return [i for i in items if isinstance(i, dict) and i.get("title")]
    except Exception:
        return []


def _recent_news() -> str:
    """ดึงข่าวล่าสุดจากคลังความรู้ (news_daily เขียนไว้แล้ว) — ไม่ต้องเรียกเว็บซ้ำ"""
    import urllib.request
    try:
        req = urllib.request.Request(
            f"{BUS_URL}/v1/facts?prefix=news.*",
            headers={"X-API-Key": API_KEY},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        lines = []
        for f in data.get("facts", [])[:3]:
            v = f.get("value")
            if isinstance(v, str):
                try:
                    v = json.loads(v)
                except Exception:
                    continue
            items = (v or {}).get("items", [])
            lines += [f"- {i.get('title')}" for i in items[:8]]
        return "\n".join(lines[:24])
    except Exception:
        return ""


class CreatorDailyLoop(Loop):
    """โมเดล B — เตรียมให้ครีเอเตอร์ทุกเช้า แล้วติดตามวันที่โพสต์"""

    loop_id = "creator_daily"
    interval = timedelta(hours=20)
    trust_level = 1  # L1 — เตรียมของ + ส่ง inbox เท่านั้น ไม่โพสต์แทน
    model_hint = None  # ใช้โมเดลหลักของ provider

    def should_run(self) -> bool:
        last = last_run(self.loop_id)
        if last is not None and last.date() >= datetime.now().date():
            return False
        return datetime.now().hour >= 7  # เช้าเท่านั้น (เผื่อเวลาไทย 15:00+ สำหรับโพสต์)

    def run(self) -> str:
        creators = _enrolled_creators()
        if not creators:
            return "⏭ creator_daily: ยังไม่มีครีเอเตอร์ที่ enroll — " \
                   "(สร้างที่ bus/programs/x-kickstart/<slug>/tracker.json)"

        news = _recent_news()
        prepared = 0
        skipped = 0
        lines = []

        for slug in creators:
            tracker = PostingTracker(creator=slug).load()
            s = tracker.status()
            if not s["enrolled"]:
                skipped += 1
                continue

            if s["posted_today"]:
                skipped += 1
                lines.append(f"· {slug}: โพสต์วันนี้แล้ว "
                             f"({s['days_used']}/{s['days_needed']} วัน)")
                continue

            if s.get("period_over"):
                skipped += 1
                lines.append(f"· {slug}: รอบนี้จบแล้ว / เลย deadline")
                continue

            profile = load_profile(slug)
            if profile is None or not profile.is_complete():
                skipped += 1
                lines.append(f"· {slug}: ยังไม่มีโปรไฟล์ 4 ท่อนที่ครบ — ข้าม")
                continue

            ideas = _generate_ideas(profile, news)
            if not ideas:
                skipped += 1
                lines.append(f"· {slug}: LLM ไม่พร้อย — ยังไม่ได้เตรียมไอเดีย")
                continue

            today = datetime.now().strftime("%Y-%m-%d")
            out_dir = OUT_ROOT / slug / today
            made = []
            for idx, idea in enumerate(ideas[:IDEA_COUNT], 1):
                script = build_script(profile, idea, caption=idea.get("hook", ""))
                pkg = build_package(profile, script, out_dir, suffix=f"{idx:02d}")
                # checklist ตามเงื่อนไขโปรแกรม
                (out_dir / f"{pkg['slug']}.checklist.md").write_text(
                    clip_checklist_md(profile.name, idea.get("title", ""),
                                     tracker_status=tracker.status()),
                    encoding="utf-8")
                made.append(pkg["slug"])

            prepared += 1
            lines.append(
                f"· {slug}: เตรียม {len(made)} ไอเดีย → {out_dir} "
                f"(วันนี้ยังไม่โพสต์ · {s['days_used']}/{s['days_needed']} วัน)")

        if prepared:
            _send_inbox(
                "ceo",
                f"🎬 creator_daily — เตรียมไอเดียให้ {prepared} ครีเอเตอร์",
                "\n".join(lines),
            )

        summary = (f"✅ creator_daily: เตรียมให้ {prepared} ครีเอเตอร์ · "
                   f"ข้าม {skipped}")
        if lines:
            summary += "\n" + "\n".join(lines)
        return summary
