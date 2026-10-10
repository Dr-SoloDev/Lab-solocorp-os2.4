"""Central Bus — data-governance tags (warn-first).

หลักการ (docs/DATA-GOVERNANCE.md): ทุกข้อมูลต้องมีป้าย 2 แกน
  - workstream: SOLOCORP-CORE | CUSTOMER-{รหัส} | PERSONAL | OWN-BIZ | VERSION
  - sensitivity: PUB | INT | CONF (default ถ้าไม่ระบุ)

โหมด: warn (default) = เขียนได้แต่ log เตือน → เก็บข้อมูล 2-3 วันแล้วค่อยพลิกเป็น reject.
เปลี่ยนโหมดด้วย env BUS_TAG_MODE=reject (ไม่ต้องแก้โค้ด).
"""

from __future__ import annotations

import logging
import os
import re

log = logging.getLogger(__name__)

WORKSTREAMS = frozenset({"SOLOCORP-CORE", "PERSONAL", "OWN-BIZ", "VERSION"})
SENSITIVITY_LEVELS = ("PUB", "INT", "CONF")
DEFAULT_SENSITIVITY = "CONF"

STRICT = os.environ.get("BUS_TAG_MODE", "warn").lower() == "reject"


def _valid_workstream(ws: str) -> bool:
    if ws in WORKSTREAMS:
        return True
    # CUSTOMER-{รหัส} — ตัวอย่าง: CUSTOMER-SCRAP, CUSTOMER-BKK
    return bool(re.fullmatch(r"CUSTOMER-[A-Za-z0-9][A-Za-z0-9_-]{0,31}", ws or ""))


def validate_tags(metadata: dict | None, *, where: str = "?") -> dict:
    """ตรวจ + เติมป้ายให้ครบ. คืน metadata ที่ normalized แล้ว.

    warn mode: ป้ายขาด/ผิด → log warning แล้วไปต่อ (ไม่ block งานที่รันอยู่).
    reject mode (BUS_TAG_MODE=reject): raise ValueError.
    """
    meta = dict(metadata or {})
    problems: list[str] = []

    ws = meta.get("workstream")
    if not ws or not _valid_workstream(ws):
        problems.append(f"workstream ขาด/ผิด ({ws!r}) → ใส่ SOLOCORP-CORE")
        meta["workstream"] = "SOLOCORP-CORE"

    sens = str(meta.get("sensitivity", "")).upper()
    if sens not in SENSITIVITY_LEVELS:
        problems.append(f"sensitivity ขาด/ผิด ({meta.get('sensitivity')!r}) → ใส่ CONF")
        meta["sensitivity"] = DEFAULT_SENSITIVITY

    if problems:
        msg = f"[bus-tags:{where}] " + " | ".join(problems)
        if STRICT:
            raise ValueError(msg)
        log.warning(msg)
    return meta


def log_access(*, who: str, key: str, tier: str) -> None:
    """log การเข้าถึง — บันทึกแค่ ใคร/key/tier/เวลา ห้ามมี value เด็ดขาด."""
    log.info("[bus-access] who=%s key=%s tier=%s", who, key, tier)


# ── PII patterns (standalone เท่านั้น + checksum กันทศนิยม coverage) ──
#
# เบอร์: 0XXXXXXXXX หรือ +66XXXXXXXXX (เว้นวรรค/ขีดคั่นได้ทีละตัว)
# หมายเหตุ: 66 เปลือย (ไม่มี +) ก็จับ — นโยบายปลอดภัยไว้ก่อน (over-redact > leak)
#   marker ทำให้เห็นว่าถูกตัด ถ้าผิดก็รู้ ไม่เงียบ
_PHONE_RE = re.compile(
    r"(?<![0-9+])(?:0|\+66[\s-]?|66[\s-]?)([689](?:[\s-]?\d){8})(?![0-9])"
)
# บัตร: 13 หลัก เว้นวรรค/ขีดคั่นได้ทีละตัว (เช่น 1-1007-00153-55-07)
# ขอบท้ายกันเลขชุดยาวกว่า (เช่น 16 หลักจะไม่โดนตัดครึ่ง)
_ID_CANDIDATE_RE = re.compile(
    r"(?<![0-9.])([1-8](?:[\s-]?[0-9]){12})(?![\s-]?[0-9])"
)


def _strip_sep(s: str) -> str:
    return re.sub(r"[\s-]", "", s)


def _thai_id_valid(digits: str) -> bool:
    """checksum บัตรประชาชนไทย (mod-11) — ทศนิยม coverage ไม่มีวันผ่าน."""
    if len(digits) != 13 or not digits.isdigit():
        return False
    total = sum(int(digits[i]) * (13 - i) for i in range(12))
    return (11 - total % 11) % 10 == int(digits[12])


def redact_pii(text: str) -> tuple[str, bool]:
    """ตัดบัตร/เบอร์ออก ใส่ marker ให้เห็นว่าถูกตัด (ไม่ mutate เงียบ).

    Returns:
        (cleaned_text, found_any)
    """
    if not text:
        return text, False
    found = False

    def _id_sub(m: re.Match) -> str:
        nonlocal found
        digits = _strip_sep(m.group(0))
        if len(digits) == 13 and _thai_id_valid(digits):
            found = True
            return "[REDACTED:ID]"
        return m.group(0)  # checksum ไม่ผ่าน = ไม่ใช่บัตร (เช่น ทศนิยม) → คงไว้

    out = _ID_CANDIDATE_RE.sub(_id_sub, text)
    out, n = _PHONE_RE.subn("[REDACTED:PHONE]", out)
    return out, found or n > 0


def redact_obj(obj):
    """redact PII แบบ recursive ใน dict/list/str — คงโครงสร้างไว้ ใส่ marker ที่ถูกตัด.

    ใช้ชั่วคราวจนกว่า allowlist ต่อ builder (ขั้น 3) จะมาแทน (Owner-approved).
    """
    if isinstance(obj, str):
        cleaned, _ = redact_pii(obj)
        return cleaned
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact_obj(v) for v in obj]
    return obj
