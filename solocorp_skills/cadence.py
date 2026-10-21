"""Cadence — จังหวะการโพสต์ (สัญญาระหว่างครีเอเตอร์กับระบบ)

หลักการ (ADR-023 / vision §5.2):
  • "ความสม่ำเสมอ" วัดเป็น **โพสต์ได้จริงกี่วัน/30 วัน** ไม่ใช่ "อยากได้กี่วัน"
  • ระบบเป็นคนเสนอ → เจ้าของแค่กดอนุมัติ (ภาระของเจ้าของ = 1 คลิก)
  • ช่วงเร่งด่วน 7 วันแรก เพื่อเก็บข้อมูลให้พอตัดสินใจระยะยาว

ไฟล์สัญญา: ``bus/media/creator/cadence.md`` (แก้ด้วยมือได้)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

__all__ = [
    "Cadence",
    "load_cadence",
    "DEFAULT_CADENCE_PATH",
    "WEEKDAYS_TH",
]

DEFAULT_CADENCE_PATH = Path(__file__).resolve().parent.parent / "bus" / "media" / "creator" / "cadence.md"

WEEKDAYS_TH = {
    "จันทร์": 0, "อังคาร": 1, "พุธ": 2, "พฤหัสบดี": 3, "ศุกร์": 4, "เสาร์": 5, "อาทิตย์": 6,
}
_WEEKDAYS_EN = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4,
    "saturday": 5, "sunday": 6,
}


@dataclass
class Cadence:
    """จังหวะการโพสต์ที่ตกลงไว้"""
    text_days: set[int] = field(default_factory=lambda: {0, 1, 2, 3, 4})
    clip_days: set[int] = field(default_factory=lambda: {0, 2, 4})
    ramp_from: Optional[str] = None      # ISO date
    ramp_to: Optional[str] = None
    source: str = "default"
    raw: str = ""

    def is_ramp(self, d: date) -> bool:
        """อยู่ในช่วงเร่งด่วนไหม (ข้อความทุกวัน)"""
        if not self.ramp_from or not self.ramp_to:
            return False
        try:
            return (date.fromisoformat(self.ramp_from)
                    <= d <= date.fromisoformat(self.ramp_to))
        except ValueError:
            return False

    def plan_for(self, d: date) -> dict[str, object]:
        """แผนของวันนี้ — โพสต์อะไร, ทำไม"""
        ramp = self.is_ramp(d)
        want_text = ramp or (d.weekday() in self.text_days)
        want_clip = (d.weekday() in self.clip_days)
        if ramp:
            reason = "ช่วงเร่งด่วน 7 วันแรก — ทุกวันเพื่อเก็บข้อมูล"
        elif want_text:
            reason = f"วัน{WEEKDAYS_TH_INV.get(d.weekday(), '')} อยู่ในตารางปกติ"
        else:
            reason = "วันพัก — เป็นวันรวบรวมสัปดาห์"
        return {
            "date": d.isoformat(),
            "weekday": d.weekday(),
            "post_text": want_text,
            "post_clip": want_clip,
            "ramp": ramp,
            "reason": reason,
        }


WEEKDAYS_TH_INV = {v: k for k, v in WEEKDAYS_TH.items()}


def _parse_bool(cell: str) -> bool:
    return "✅" in cell or cell.strip().lower() in ("yes", "true", "ใช่")


def load_cadence(path: Optional[Path] = None) -> Cadence:
    """อ่าน cadence.md → กฎการโพสต์

    ถ้าไม่มีไฟล์ → ใช้ค่าเริ่มต้น (ข้อความ จ.-ศ. · คลิป จ./พ./ศ.)
    """
    p = Path(path) if path else DEFAULT_CADENCE_PATH
    if not p.exists():
        return Cadence(source="default")

    raw = p.read_text(encoding="utf-8")
    text_days: set[int] = set()
    clip_days: set[int] = set()
    ramp_from = ramp_to = None
    in_table = False

    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_table = False
            if "เร่งด่วน" in s:
                in_table = True
            continue
        # ช่วงเร่งด่วน: บรรทัด "วันที่ 2026-10-20 ถึง 2026-10-26" (ไม่ใช่ตาราง)
        if not s.startswith("|"):
            if "ถึง" in s or " to " in s.lower():
                dates = re.findall(r"\d{4}-\d{2}-\d{2}", s)
                if len(dates) >= 2 and (ramp_from is None or dates[0] < ramp_from):
                    ramp_from, ramp_to = dates[0], dates[1]
            continue
        cols = [c.strip() for c in s.strip("|").split("|")]
        if len(cols) < 3:
            continue
        head = cols[0]
        if head in ("วัน", "Day", "#") or set(head) <= set("-: "):
            continue
        if not head:
            continue

        # วันในตาราง
        wd = None
        if head in WEEKDAYS_TH:
            wd = WEEKDAYS_TH[head]
        elif head.lower() in _WEEKDAYS_EN:
            wd = _WEEKDAYS_EN[head.lower()]
        if wd is not None:
            if _parse_bool(cols[1]):
                text_days.add(wd)
            if len(cols) > 2 and _parse_bool(cols[2]):
                clip_days.add(wd)
            continue


    if not text_days and not clip_days:
        return Cadence(source="default")

    return Cadence(
        text_days=text_days or {0, 1, 2, 3, 4},
        clip_days=clip_days,
        ramp_from=ramp_from,
        ramp_to=ramp_to,
        source=str(p),
        raw=raw,
    )
