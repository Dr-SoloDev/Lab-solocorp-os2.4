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

_PHONE_RE = re.compile(r"(?<![0-9.])0[689][0-9]{8}(?![0-9])")
_ID_CANDIDATE_RE = re.compile(r"(?<![0-9.])[1-8][0-9]{12}(?![0-9])")


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
        if _thai_id_valid(m.group(0)):
            found = True
            return "[REDACTED:ID]"
        return m.group(0)  # checksum ไม่ผ่าน = ไม่ใช่บัตร (เช่น ทศนิยม) → คงไว้

    out = _ID_CANDIDATE_RE.sub(_id_sub, text)
    out, n = _PHONE_RE.subn("[REDACTED:PHONE]", out)
    return out, found or n > 0
