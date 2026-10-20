"""Creator Kit — เครื่องมือของสนามแรก: ครีเอเตอร์สายสร้างตัวตน (TikTok)

สร้างจาก vision §5.3–5.6 (LOCKED 2026-10-15) + ที่ Owner แตะยืนยัน 2026-10-20:
  • 4 ท่อนเรื่อง (ตัวตน / รอยแผล / คนดู / เหตุผลที่ยังทำ)
  • ท่อน 2+3 = สะพานเชื่อมคน 2 ฝั่ง
  • ตลิ่ง 2 ชั้น: ตลิ่งโทน (3 คำนาม) + ตลิ่งที่มา (origin log)
  • โครงคลิป TikTok: hook 0-3 วิ → เนื้อ 3-30 → คนดู 30-45 → ปิด 45-55

โมดูลนี้เก็บส่วนที่ **ต้องตรงเป๊ะ** (โครง 4 ท่อน, เวลา, แพ็กเกจไฟล์)
ส่วนที่คิดเนื้อหา (ไอเดีย/สคริปต์) ให้ LLM ทำผ่าน skill
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

__all__ = [
    "TUBEAN",
    "TIKTOK_BEATS",
    "CreatorProfile",
    "profile_to_fact",
    "profile_from_fact",
    "upsert_profile",
    "load_profile",
    "build_script",
    "build_package",
    "slugify",
]

ROOT = Path(__file__).resolve().parent.parent
BUS_URL = os.environ.get("SOLOCORP_BUS_URL", "http://127.0.0.1:8099")
API_KEY = os.environ.get("SOLOCORP_API_KEY", "sk-solocorp-admin-local-dev-001")

FACT_PREFIX = "creator."


# ══════════════════════════════════════════════════════════════════════
# 4 ท่อน (จาก vision §5.5)
# ══════════════════════════════════════════════════════════════════════

TUBEAN: tuple[dict[str, str], ...] = (
    {
        "id": "tubean",
        "name": "ตัวตน",
        "side": "creator",
        "question": "คุณเป็นใคร — แล้วตอนนี้ทำอะไรอยู่?",
        "hint": "คำเดียวว่าคุณเป็นใคร + ตอนนี้ทำอะไรอยู่",
        "example": "ฉันเป็นคนทำ [งาน] — ตอนนี้กำลัง [ทำอะไร]",
    },
    {
        "id": "roeyphae",
        "name": "รอยแผล",
        "side": "creator",
        "question": "ตอนนี้คุณทำได้ดีกว่าตอนเริ่มยังไง — เคยล้มเหลวมากี่รอบก่อน?",
        "hint": "ท่อนที่คนจำได้สุด — ล้มเหลวยังไง แล้วอะไรเปลี่ยน",
        "example": "ตอนแรก [ล้มเหลวยังไง] … ตอนนี้ [อะไรเปลี่ยนไป]",
    },
    {
        "id": "khondu",
        "name": "คนดู",
        "side": "viewer",
        "question": "อยากให้ใครเห็นเรื่องนี้ — เขากำลังติดอะไรอยู่?",
        "hint": "คนกลุ่มไหน + เขาติดอะไรอยู่ตอนนี้",
        "example": "ฉันอยากให้ [คนกลุ่ม] ที่กำลัง [ปัญหา] เห็นว่า [ทางออก]",
    },
    {
        "id": "hettai",
        "name": "เหตุผลที่ยังทำ",
        "side": "viewer",
        "question": "ถ้าไร้เงินจากเรื่องนี้ 0 บาท — ยังทำต่อทำไม?",
        "hint": "เหตุผลที่ตื่นมาทำต่อ ไม่ใช่เหตุผลที่ขายได้",
        "example": "เพราะ [อยากเป็น / อยากให้เห็น / อยากได้ยอมรับ]",
    },
)

# ท่อน 2+3 = สะพานเชื่อมคน 2 ฝั่ง (vision §5.5)
BRIDGE_TUBEAN = ("roeyphae", "khondu")

# โครงคลิป TikTok — 4 ท่อน → 4 จังหวะ
TIKTOK_BEATS: tuple[dict[str, Any], ...] = (
    {"tubean": "tubean", "label": "hook", "start": 0, "end": 3,
     "role": "ดึงให้หยุดดู — บอกว่าเราคือใครใน 3 วินาที"},
    {"tubean": "roeyphae", "label": "เนื้อหาหลัก", "start": 3, "end": 30,
     "role": "ของจริง — ล้มเหลวกี่ครั้ง แล้วอะไรเปลี่ยน"},
    {"tubean": "khondu", "label": "หันมาหาคนดู", "start": 30, "end": 45,
     "role": "เชื่อมไปหาคนที่กำลังติดปัญหาเดียวกัน"},
    {"tubean": "hettai", "label": "ปิด + ปุ่มเรียกร้อง", "start": 45, "end": 55,
     "role": "ทำไมถึงยังทำ — แล้วชวนให้เขาทำอะไรต่อ"},
)


# ══════════════════════════════════════════════════════════════════════
# Profile
# ══════════════════════════════════════════════════════════════════════


@dataclass
class CreatorProfile:
    """โปรไฟล์ครีเอเตอร์ 1 คน = 4 ท่อน + ตลิ่งโทน 3 คำ"""

    slug: str
    name: str = ""
    tubean: dict[str, str] = field(default_factory=dict)      # id → คำตอบ
    tone_words: list[str] = field(default_factory=list)         # ตลิ่งโทน 3 คำ
    platform: str = "tiktok"
    created_at: str = ""
    updated_at: str = ""

    def answer(self, tubean_id: str) -> str:
        return self.tubean.get(tubean_id, "")

    def is_complete(self) -> bool:
        """ครบ 4 ท่อน + ตลิ่งโทน 3 คำ = พร้อมลงสนาม"""
        return (
            all(self.answer(t["id"]).strip() for t in TUBEAN)
            and len(self.tone_words) == 3
        )

    def missing(self) -> list[str]:
        gaps = [t["name"] for t in TUBEAN if not self.answer(t["id"]).strip()]
        if len(self.tone_words) != 3:
            gaps.append(f"ตลิ่งโทน (ต้อง 3 คำ — ตอนนี้ {len(self.tone_words)} คำ)")
        return gaps

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def slugify(text: str) -> str:
    """ทำ slug จากชื่อครีเอเตอร์ (ไทย/อังกฤษ)"""
    t = re.sub(r"[^\w฀-๿]+", "-", (text or "").strip().lower())
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t or "creator"


def profile_to_fact(profile: CreatorProfile) -> tuple[str, dict[str, Any]]:
    """แปลง profile เป็น fact (key + value) พร้อม metadata"""
    key = f"{FACT_PREFIX}{profile.slug}.profile"
    value = {
        "name": profile.name,
        "platform": profile.platform,
        "tubean": profile.tubean,
        "tone_words": profile.tone_words,
        "tubean_questions": [
            {"id": t["id"], "name": t["name"], "question": t["question"],
             "example": t["example"], "side": t["side"]}
            for t in TUBEAN
        ],
        "bridge_tubean": list(BRIDGE_TUBEAN),
        "updated_at": profile.updated_at,
    }
    return key, value


def profile_from_fact(fact: dict[str, Any]) -> Optional[CreatorProfile]:
    """แปลง fact กลับเป็น profile"""
    if not fact:
        return None
    v = fact.get("value")
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            return None
    if not isinstance(v, dict):
        return None
    slug = fact.get("key", "").replace(FACT_PREFIX, "").replace(".profile", "")
    return CreatorProfile(
        slug=slug,
        name=v.get("name", ""),
        tubean=v.get("tubean", {}) or {},
        tone_words=list(v.get("tone_words", []) or []),
        platform=v.get("platform", "tiktok"),
        created_at=v.get("created_at", ""),
        updated_at=v.get("updated_at", ""),
    )


def upsert_profile(profile: CreatorProfile, bus_url: Optional[str] = None,
                    api_key: Optional[str] = None) -> dict[str, Any]:
    """เขียน profile เข้าคลังความรู้ (facts)"""
    profile.updated_at = datetime.now(timezone.utc).isoformat()
    if not profile.created_at:
        profile.created_at = profile.updated_at
    key, value = profile_to_fact(profile)

    body = json.dumps({
        "key": key,
        "value": value,
        "metadata": {"workstream": "OWN-BIZ", "sensitivity": "INT"},
        "updated_by": "creator-kit",
    }, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f"{bus_url or BUS_URL}/v1/facts",
        data=body,
        headers={"X-API-Key": api_key or API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def load_profile(slug: str, bus_url: Optional[str] = None,
                 api_key: Optional[str] = None) -> Optional[CreatorProfile]:
    """ดึง profile จากคลังความรู้"""
    key = f"{FACT_PREFIX}{slug}.profile"
    url = f"{bus_url or BUS_URL}/v1/facts?prefix={key}"
    req = urllib.request.Request(url, headers={"X-API-Key": api_key or API_KEY})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    facts = data.get("facts", [])
    if not facts:
        return None
    return profile_from_fact(facts[0])


# ══════════════════════════════════════════════════════════════════════
# สคริปต์ + แพ็กเกจ
# ══════════════════════════════════════════════════════════════════════


def build_script(profile: CreatorProfile, idea: dict[str, str],
                 *, caption: str = "", hashtags: Optional[list[str]] = None,
                 shots: Optional[list[dict[str, str]]] = None) -> dict[str, Any]:
    """ประกอบสคริปต์จาก 4 ท่อน → 4 จังหวะตามเวลา

    Args:
        profile: โปรไฟล์ครีเอเตอร์ (4 ท่อน + ตลิ่งโทน)
        idea: {"title": ..., "why": ...} — ไอเดียที่เลือก
        caption: แคปชันสำหรับโพสต์
        hashtags: แฮชแท็ก
        shots: shot list (ถ้ามี)
    """
    beats = []
    for b in TIKTOK_BEATS:
        beats.append({
            **b,
            "tubean_name": next(t["name"] for t in TUBEAN if t["id"] == b["tubean"]),
            "text": profile.answer(b["tubean"]),
        })

    return {
        "slug": profile.slug,
        "creator": profile.name,
        "platform": profile.platform,
        "title": idea.get("title", ""),
        "why": idea.get("why", ""),
        "tone_words": profile.tone_words,
        "beats": beats,
        "caption": caption,
        "hashtags": hashtags or [],
        "shots": shots or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _checklist(profile: CreatorProfile, script: dict[str, Any]) -> str:
    """checklist ก่อนเผยแพร่ 1 หน้า (กรอบ 3 — เล่นสะอาด)"""
    lines = [
        "# ✅ Checklist ก่อนเผยแพร่",
        "",
        f"**คลิป:** {script.get('title', '')}",
        f"**ครีเอเตอร์:** {profile.name}  ·  **ตลิ่งโทน:** "
        f"{' / '.join(profile.tone_words) or '(ยังไม่ได้ตั้ง)'}",
        "",
        "## ตลิ่งโทน — ใช้เสียงนี้ไหม",
        "",
    ]
    for w in profile.tone_words:
        lines.append(f"- [ ] ทุกประโยคออกมาเป็น **{w}**")
    if not profile.tone_words:
        lines.append("- [ ] ⚠️ ยังไม่ได้ตั้งตลิ่งโทน 3 คำ — อย่าเผยแพร่")

    lines += [
        "",
        "## ตลิ่งที่มา — ใช้ของที่มีสิทธิ์",
        "",
        "- [ ] ภาพ/วิดีโอทุกชิ้นเป็นของเราเอง หรือมีใบอนุญาต",
        "- [ ] เพลงทุกเพลงมีใบอนุญาต (ค้นใน origin.md)",
        "- [ ] ฟอนต์/กราฟิกมีสิทธิ์",
        "- [ ] ไม่มีข้อมูลบุคคลอื่นที่ไม่ได้รับอนุญาต",
        "- [ ] ไม่เคลมผลงานคนอื่นเป็นของเรา",
        "",
        "## เนื้อหา",
        "",
        "- [ ] hook 3 วินาทีแรกดึงจริง (ไม่ใช่ออกมาก่อน)",
        "- [ ] มีรอยแผลของจริง (ไม่ใช่แค่ผลลัพธ์)",
        "- [ ] ระบุชัดว่าทำให้ใคร",
        "- [ ] ไม่มีคำสัญญาว่า 'รวยเร็ว' / 'ยอดขาย X เท่า'",
        "",
        "## ก่อนกดโพสต์",
        "",
        "- [ ] ดูคลิปเสียงมี 1 ครั้ง (มือถือจริง)",
        "- [ ] แคปชัน + แฮชแท็กตรงกับเนื้อหา",
        "- [ ] origin.md ครบทุกชิ้น",
        "",
        "> ติดอะไรไว้ 2 ข้อ ให้หยุดแล้วถาม — อย่าเผยแพร่ครบไปแล้วค่อยแก้",
    ]
    return "\n".join(lines)


def build_package(profile: CreatorProfile, script: dict[str, Any],
                  out_dir: Path, *, origin: Optional[list[dict[str, str]]] = None,
                  ) -> dict[str, Any]:
    """เขียนแพ็กเกจพร้อมโพสต์ลงโฟลเดอร์

    ไฟล์: script.md · shots.md · caption.md · origin.md · checklist.md
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    title = script.get("title") or "คลิป"
    safe = re.sub(r"[^\w฀-๿-]+", "-", title).strip("-") or "clip"

    # script.md
    s = [f"# 🎬 {title}", ""]
    if script.get("why"):
        s += [f"> **ทำไมเรื่องนี้:** {script['why']}", ""]
    s += ["| # | ท่อน | เวลา | บท |", "|:--|:--|:--|:--|"]
    for i, b in enumerate(script.get("beats", []), 1):
        s.append(f"| {i} | {b['label']} | {b['start']}–{b['end']} วิ | {b['text']} |")
    s += ["", "---", "", "### หน้าที่ของแต่ละจังหวะ", ""]
    for i, b in enumerate(script.get("beats", []), 1):
        s.append(f"{i}. **{b['label']}** — {b['role']}")
    (out_dir / f"{safe}.script.md").write_text("\n".join(s), encoding="utf-8")

    # shots.md
    sh = [f"# 🎥 Shot List — {title}", ""]
    if script.get("shots"):
        sh += ["| # | ภาพ | เสียง/พูด | เวลา |", "|:--|:--|:--|:--|"]
        for i, x in enumerate(script.get("shots", []), 1):
            sh.append(f"| {i} | {x.get('shot', '')} | {x.get('line', '')} | {x.get('time', '')} |")
    else:
        sh.append("_ยังไม่ได้แตก shot — ให้ LLM เติมจาก script.md_")
    (out_dir / f"{safe}.shots.md").write_text("\n".join(sh), encoding="utf-8")

    # caption.md
    c = [f"# ✍️ Caption — {title}", ""]
    c.append(script.get("caption") or "_(ยังไม่ได้เขียน caption)_")
    tags = script.get("hashtags") or []
    if tags:
        c += ["", " ".join(f"#{t.lstrip('#')}" for t in tags)]
    (out_dir / f"{safe}.caption.md").write_text("\n".join(c), encoding="utf-8")

    # origin.md — ตลิ่งที่มา
    o = [f"# 📜 Origin Log — {title}", "",
         "ทุกชิ้นที่ใช้ต้องมีที่มา — ไม่เก็บน้อยเกินจำเป็น ไม่เคลมเกินจริง", "",
         "| ชิ้น | ที่มา | สิทธิ์ | หมายเหตุ |", "|:--|:--|:--|:--|"]
    for x in (origin or []):
        o.append(f"| {x.get('item', '')} | {x.get('source', '')} | "
                 f"{x.get('license', '')} | {x.get('note', '')} |")
    if not origin:
        o.append("| _(ยังไม่ได้ใส่)_ | — | — | ต้องใส่ก่อนเผยแพร่ |")
    o += ["", f"บันทึกเมื่อ: {datetime.now(timezone.utc).isoformat()}"]
    (out_dir / f"{safe}.origin.md").write_text("\n".join(o), encoding="utf-8")

    # checklist.md
    (out_dir / f"{safe}.checklist.md").write_text(
        _checklist(profile, script), encoding="utf-8")

    return {
        "dir": str(out_dir),
        "files": sorted(p.name for p in out_dir.glob(f"{safe}.*")),
        "slug": safe,
    }
