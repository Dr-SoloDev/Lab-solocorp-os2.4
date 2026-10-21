"""Redaction + Publish Gate — ประตูก่อนเนื้อหาออกสู่โลก

ทำไมต้องมี: เนื้อหาทุกอันถูก **ขุดจากงานจริงใน repo** (ADR / session-log / git log /
bus/evidence) → repo คือแหล่งข้อมูลสด 3 ชั้น:
  1. **PDPA** — ชื่อ/ราคา/ร้านของลูกค้าในระบบ POS
  2. **พ.ร.บ.ความลับทางการค้า** — กลไกภายใน, port, path, ชื่อ service
  3. **git log** — ชื่อ+อีเมลผู้พัฒนา, path เครื่อง

มุม legal (legal-tulya, 2026-10-20):
  • D0 public = ปัญหา/ผล/เหตุผล/หลักฐานที่ verify แล้ว
  • D1 internal = ตัดให้เหลือผลลัพธ์ + เลขที่ไม่ระบุตัวตน
  • D2 secret = กลไก, port, path, คีย์, ชื่อลูกค้า, ชื่อคน, รายได้ = ห้ามโพสต์

มุมจิตวิทยา (psych, 2026-10-20) — เกณฑ์ publish (R1-R5):
  R1 หลักฐานตรวจสอบได้ 1 อันทุกโพสต์
  R2 แสดงความล้มเหลว 1 ชิ้น + ต้นทุน (ไม่ใช่ 0 = ดูโชว์, ไม่ใช่ 3 = ดูบ่น)
  R3 มีบรรทัด "ยังไม่ได้ทำ / ยังไม่รู้" เสมอ (calibration)
  R4 ห้ามเทียบกับคนอื่น · ห้ามวัดคนอื่น · ห้ามขออะไร
  R5 ปิดด้วยคำถามเปิด 1 ข้อ ไม่ใช่ CTA ขาย
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = [
    "RedactionResult",
    "GateResult",
    "redact",
    "publish_gate",
    "gate_report_md",
    "BLOCK_PATTERNS",
    "FLAG_PATTERNS",
]


# ══════════════════════════════════════════════════════════════════════
# Patterns
# ══════════════════════════════════════════════════════════════════════

# ── D2 secret → ตัดออกอัตโนมัติ ────────────────────────────────────
BLOCK_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("SECRET", "SECRET",
     r"\bsk-[A-Za-z0-9_\-]{8,}"),
    ("SECRET", "SECRET",
     r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[\w]{20,})"),
    ("SECRET", "SECRET",
     r"\b(?:AKIA|ASIA|AIza)[\w\-]{16,}"),
    ("SECRET", "SECRET",
     r"(?i)(?:api[_-]?key|secret|token|password|passwd|bearer)\s*[:=]\s*['\"]?[\w\-./+=]{8,}"),
    ("SECRET", "SECRET",
     r"(?i)\bBearer\s+[\w\-._~+/]{20,}={0,2}"),
    ("EMAIL", "PII",
     r"\b[\w.%+\-]+@[\w\-]+\.[A-Za-z]{2,}\b"),
    ("PHONE", "PII",
     r"(?:0|\+66[\s-]?|66[\s-]?)([689](?:[\s-]?\d){8})"),
    ("ID_CARD", "PII",
     r"([1-8](?:[\s-]?[0-9]){12})(?![\s-]?[0-9])"),
    ("IBAN", "PII",
     r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
    ("ACCT", "PII",
     r"(?i)(?:เลขบัญชี|เลขที่|account\s*(?:no\.?|number)?|พร้อมเพย์)\s*[:=]?\s*\d{3,6}[-\s]\d{3,5}[-\s]\d{3,5}\b"),
    ("TAXID", "PII",
     r"(?i)(?:เลขทะเบียน|เลขภาษี|เลขประจำตัวผู้เสียภาษี|vat|tax\s*id)\s*[:=]?\s*[\d\-]{10,13}\b"),
    ("PLATE", "PII",
     r"\b[ก-ฮ]{1,2}\s?\d{4}\s*[ก-ฮ]{1,3}\b"),
    ("PATH", "INTERNAL",
     r"(?:/home/|/Users/|[A-Z]:\\Users\\)[^\s\"'|]+"),
    ("INT_HOST", "INTERNAL",
     r"\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0|(?:10|192\.168)\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d{2,5})?\b"),
)

# ── ต้องให้คนอนุมัติ (ไม่ลบทิ้ง เพราะบางครั้งวัดผลได้) ──────────────
FLAG_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("CUSTOMER", "PII",
     r"(?i)(?:ลูกค้า|client|customer|ผู้ซื้อ)\s*[:=]?\s*[\wก-๙][\wก-๙ .\-]{1,40}"),
    ("VENDOR", "PII",
     r"(?i)(?:คู่แข่ง|competitor|เทียบกับ)\s*[:=]?\s*[\wก-๙][\wก-๙ .\-]{1,30}"),
    ("CLAIM", "METRIC",
     r"(?i)(?:ผู้ติดตาม|followers|ยอดผู้ใช้|รางวัล|award|อันดับ)\D{0,10}\d[\d,\.]*"),
    ("MONEY", "METRIC",
     r"(?i)(?:รายได้|revenue|\barr\b|mrr|ต้นทุน|cost|runway|ยอดขาย|งบประมาณ)\D{0,12}\d[\d,\.]*"),
    ("PORT", "INTERNAL",
     r"(?i)(?:port|พอร์ต)\s*[:=]?\s*\d{2,5}\b"),
)

# ── คำที่ห้ามพูด (legal + cmo) ─────────────────────────────────────────
BANNED_PHRASES: tuple[tuple[str, str], ...] = (
    (r"(?i)โตแน่นอน|การันตี|รับประกัน", "อ้างความสำเร็จที่วัดไม่ได้"),
    (r"(?i)\b\d+\s*x\b|\b10x\b", "อ้างตัวคูณโตโดยไม่มีข้อมูล"),
    (r"(?i)production[- ]ready|ดีกว่าทุก|เร็วกว่าทุก|ดีที่สุด", "เปรียบเทียบโดยไม่มี benchmark"),
    (r"(?i)โปรโมชัน|รางวัล|ส่วนลด|โบนัส", "ทำให้ตัวตนกลายเป็นโฆษณา"),
    (r"(?i)คุณต้อง|ควรทำตามนี้|ทุกคนควร", "ฟังดูเหมือนสั่งสอน"),
    (r"(?i)ติดต่อเรา|จ้างเรา|สั่งซื้อ|สนใจบริการ", "CTA ขาย (ต้องเป็นคำถามเปิดแทน)"),
    (r"(?i)รีบ|อย่าพลาด|อย่าลืม", "คำเร่งเร้า (FOMO) — ต้องเป็นคำถามเปิดแทน"),
)


# ══════════════════════════════════════════════════════════════════════
# ผลลัพธ์
# ══════════════════════════════════════════════════════════════════════


@dataclass
class RedactionResult:
    """ผลการกรองข้อมูล"""
    ok: bool = True                       # ไม่มีอะไรค้างที่ต้องแก้
    text: str = ""                        # ข้อความหลัง redact
    blocked: list[dict[str, Any]] = field(default_factory=list)   # ถูกตัด
    flagged: list[dict[str, Any]] = field(default_factory=list)   # ต้องคนอนุมัติ
    banned: list[dict[str, Any]] = field(default_factory=list)    # คำที่ห้ามพูด

    @property
    def needs_approval(self) -> bool:
        return bool(self.flagged or self.banned)

    def summary(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "blocked": len(self.blocked),
            "flagged": len(self.flagged),
            "banned": len(self.banned),
            "labels": sorted({f["label"] for f in self.blocked + self.flagged}),
        }


@dataclass
class GateResult:
    """ผล publish gate (R1-R5 จาก psych + เงื่อนไข redaction จาก legal)"""
    passed: bool = False
    checks: list[dict[str, Any]] = field(default_factory=list)

    def add(self, rule: str, ok: bool, detail: str = "") -> None:
        self.checks.append({"rule": rule, "ok": ok, "detail": detail})

    def failures(self) -> list[dict[str, Any]]:
        return [c for c in self.checks if not c["ok"]]


# ══════════════════════════════════════════════════════════════════════
# Redact
# ══════════════════════════════════════════════════════════════════════


def redact(text: str, *, strip_banned: bool = False) -> RedactionResult:
    """กรองข้อมูลก่อนโพสต์

    - D2 secret → ตัดทิ้งอัตโนมัติ แทนด้วย ``[REDACTED:<label>]``
    - ชื่อลูกค้า/คู่แข่ง/ตัวเลขที่วัดผลได้ → **ไม่ลบ** แต่ flag ให้คนอนุมัติ
    - คำที่ห้ามพูด → flag (หรือตัด ถ้า strip_banned=True)
    """
    res = RedactionResult(text=text or "")

    for label, tier, pattern in BLOCK_PATTERNS:
        regex = re.compile(pattern)
        matches = list(regex.finditer(res.text))
        if not matches:
            continue
        res.blocked.append({
            "label": label, "tier": tier, "count": len(matches),
            "sample": matches[0].group(0)[:40],
        })
        res.text = regex.sub(f"[REDACTED:{label}]", res.text)

    for label, tier, pattern in FLAG_PATTERNS:
        regex = re.compile(pattern)
        matches = list(regex.finditer(res.text))
        if not matches:
            continue
        res.flagged.append({
            "label": label, "tier": tier, "count": len(matches),
            "sample": matches[0].group(0)[:40],
        })

    for pattern, reason in BANNED_PHRASES:
        regex = re.compile(pattern)
        matches = list(regex.finditer(res.text))
        if not matches:
            continue
        res.banned.append({
            "label": reason, "count": len(matches),
            "sample": matches[0].group(0)[:40],
        })
        if strip_banned:
            res.text = regex.sub("[ข้อความที่ไม่ควรเผยแพร่]", res.text)

    res.ok = not res.needs_approval
    return res


# ══════════════════════════════════════════════════════════════════════
# Publish gate
# ══════════════════════════════════════════════════════════════════════

_EVIDENCE_RE = re.compile(
    r"(https?://\S+|\b[0-9a-f]{7,40}\b|decisions/[\w\-./]+\.md|bus/[\w\-./]+\.json|"
    r"scripts/[\w\-./]+\.py|tests/[\w\-./]+\.py|git\s+[0-9a-f]{7,10}|"
    r"\bADR-\d{2,4}\b|\bADR-\d{2,4}-[\w\-]+\.md\b)",
    re.I,
)
_NOTDONE_RE = re.compile(
    r"(ยังไม่ได้|ยังไม่รู้|ยังไม่เสร็จ|ยังไม่ได้ทำ|ไม่รู้ว่า|ยังไม่เคย|"
    r"TODO|ยังไม่พร้อม|ต้องทำต่อ|ยังไม่ได้แก้)", re.I,
)
_QUESTION_RE = re.compile(
    r"[?？]|ไหม|มั้ย|"
    r"หรือยัง|อะไร|ยังไง|"
    r"คนไหน|อยากให้|คุณเจอ|มีใคร",
    re.I)
_CTA_RE = re.compile(
    r"(?:ติดต่อเรา|จ้างเรา|สั่งซื้อ|สนใจบริการ|คุณต้อง|ควรทำตามนี้|"
    r"ทุกคนควร|รีบ|อย่าพลาด|อย่าลืม)", re.I,
)
_COMPARE_RE = re.compile(
    r"(ดีกว่าทุก|เร็วกว่าทุก|ดีที่สุด|เทียบกับ|อันดีกว่า|"
    r"\bvs\.?\s+[A-Z]|production[- ]ready)", re.I,
)


def publish_gate(
    text: str,
    *,
    redaction: Optional[RedactionResult] = None,
    require_evidence: bool = True,
) -> GateResult:
    """ตรวจก่อน publish — R1-R5 (psych) + เงื่อนไข redaction (legal)

    Returns:
        GateResult: passed=True เมื่อผ่านทุกข้อ
    """
    g = GateResult()
    body = text or ""

    # ── จาก legal: ต้องไม่มีข้อมูลที่ยังไม่ถูกจัดการ ──
    if redaction is not None:
        g.add("L1 ไม่มีข้อมูล D2 (secret/พ.ร.บ.ความลับ) หลุด",
              not redaction.blocked,
              f"{len(redaction.blocked)} รายการ" if redaction.blocked else "สะอาด")
        g.add("L2 ไม่มีรายการที่รอคนอนุมัติ",
              not redaction.flagged,
              ", ".join(sorted({f['label'] for f in redaction.flagged}))
              if redaction.flagged else "ไม่มี")
        g.add("L3 ไม่มีคำที่ห้ามพูด",
              not redaction.banned,
              "; ".join(f"{b['sample']}" for b in redaction.banned)
              if redaction.banned else "ไม่มี")

    # ── R1: หลักฐานตรวจสอบได้ ──
    ev = _EVIDENCE_RE.findall(body)
    g.add("R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน",
          bool(ev) or not require_evidence,
          f"{len(ev)} รายการ: {', '.join(str(e) for e in ev[:3])}" if ev else "ไม่มี")

    # ── R2: แสดงความล้มเหลว 1 ชิ้น + ต้นทุน ──
    has_failure = bool(re.search(
        r"(เจอปัญหา|พัง|ผิด|ตาย|โกหก|ค้าง|ล้ม|หาย|เสีย|ไม่ได้|ไม่มี|error|bug)", body, re.I))
    has_cost = bool(re.search(
        r"(ต้นทุน|เสียเวลา|\d+\s*(?:นาที|ชั่วโมง|วัน|บาท|\$)|เพราะ|เพื่อ)", body, re.I))
    g.add("R2 แสดงความล้มเหลวและต้นทุน/เหตุผล",
          has_failure and has_cost,
          "มีรอยแผล" if has_failure else "ไม่มีรอยแผล")

    # ── R3: มีบรรทัด "ยังไม่ได้ทำ" ──
    nd = _NOTDONE_RE.findall(body)
    g.add("R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration)",
          bool(nd),
          nd[0] if nd else "ไม่มี — เสี่ยงดูมั่นใจเกินจริง")

    # ── R4: ห้ามเทียบ/ห้ามวัดคนอื่น/ห้ามขออะไร ──
    g.add("R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง",
          not _COMPARE_RE.search(body) and not _CTA_RE.search(body),
          "พบคำต้องห้าม" if (_COMPARE_RE.search(body) or _CTA_RE.search(body)) else "สะอาด")

    # ── R5: ปิดด้วยคำถามเปิด ไม่ใช่ CTA ──
    g.add("R5 ปิดด้วยคำถามเปิด 1 ข้อ",
          bool(_QUESTION_RE.search(body)),
          "มีคำถาม" if _QUESTION_RE.search(body) else "ไม่มีคำถาม")

    g.passed = not g.failures()
    return g


def gate_report_md(redaction: RedactionResult, gate: GateResult) -> str:
    """รายงาน gate เป็น markdown (แนบกับแพ็กเกจก่อน publish)"""
    lines = ["# 🚦 Publish Gate", ""]
    lines.append("## ตัวกรองข้อมูล")
    if not redaction.blocked and not redaction.flagged and not redaction.banned:
        lines.append("- ✅ ไม่พบข้อมูลที่ต้องกรอง")
    for f in redaction.blocked:
        lines.append(f"- 🔒 ถูกตัด `{f['label']}` ×{f['count']} (ตัวอย่าง: `{f['sample']}`)")
    for f in redaction.flagged:
        lines.append(f"- ⚠️ ต้องคนอนุมัติ `{f['label']}` ×{f['count']} (ตัวอย่าง: `{f['sample']}`)")
    for f in redaction.banned:
        lines.append(f"- 🚫 คำที่ห้ามพูด: `{f['sample']}` ({f['label']})")

    lines += ["", "## เกณฑ์ publish (R1-R5)"]
    for c in gate.checks:
        mark = "✅" if c["ok"] else "❌"
        detail = f" — {c['detail']}" if c.get("detail") else ""
        lines.append(f"- {mark} **{c['rule']}**{detail}")

    lines += ["", f"**ผล: {'ผ่าน — พร้อม publish' if gate.passed else 'ไม่ผ่าน — ต้องแก้ก่อน'}**"]
    return "\n".join(lines)
