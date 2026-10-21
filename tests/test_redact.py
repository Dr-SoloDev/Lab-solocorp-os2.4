"""Tests for Redaction + Publish Gate — ประตูก่อนเนื้อหาออกสู่โลก

ทีม legal (legal-tulya) + psych ระบุกฎไว้ 2026-10-20 — ที่นี่คือการล็อกกฎให้เป็นโค้ด
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solocorp_skills.redact import (  # noqa: E402
    BLOCK_PATTERNS,
    BANNED_PHRASES,
    FLAG_PATTERNS,
    gate_report_md,
    publish_gate,
    redact,
)


# ══════════════════════════════════════════════════════════════════════
# Redact — D2 secret
# ══════════════════════════════════════════════════════════════════════


class TestRedactBlocks:
    """ข้อมูล D2 = ต้องถูกตัดออกอัตโนมัติ"""

    @pytest.mark.parametrize("text,label", [
        ("key is sk-abc1234567890xyz", "SECRET"),
        ("token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123", "SECRET"),
        ("api_key = 'superSecretValue123'", "SECRET"),
        ("ติดต่อ admin@solocorp.dev", "EMAIL"),
        ("โทร 0812345678", "PHONE"),
        ("เลขบัญชี 123-456-7890", "ACCT"),
        ("อยู่ที่ /home/drsolodev/secret.txt", "PATH"),
        ("รันที่ localhost:8099", "INT_HOST"),
    ])
    def test_blocks_and_marks(self, text, label):
        r = redact(text)
        assert r.blocked, f"ไม่พบ {label} ใน '{text}'"
        assert any(b["label"] == label for b in r.blocked)
        assert "[REDACTED:" in r.text
        assert label not in r.text or "REDACTED" in r.text

    def test_clean_text_untouched(self):
        text = "เจอปัญหา: ระบบค้าง แก้โดยเพิ่ม health check"
        r = redact(text)
        assert r.text == text
        assert not r.blocked
        assert r.ok


class TestRedactFlags:
    """ข้อมูลที่วัดผลได้ → flag ให้คนอนุมัติ ไม่ลบทิ้ง"""

    @pytest.mark.parametrize("text,label", [
        ("รายได้ 120,000 บาท", "MONEY"),
        ("ยอดขายเดือนนี้ 50000", "MONEY"),
        ("ผู้ติดตาม 12,000 คน", "CLAIM"),
    ])
    def test_flags_not_blocks(self, text, label):
        r = redact(text)
        assert r.flagged, f"ไม่พบ flag {label}"
        assert any(f["label"] == label for f in r.flagged)
        assert not r.blocked, "MONEY/CLAIM ต้อง flag ไม่ใช่ block"
        assert r.needs_approval is True
        assert r.ok is False

    def test_customer_name_flagged(self):
        r = redact("ลูกค้า: ร้านกาแฟบ้านสวน")
        assert any(f["label"] == "CUSTOMER" for f in r.flagged)


class TestBannedPhrases:
    """คำที่ห้ามพูด (legal + cmo)"""

    @pytest.mark.parametrize("text", [
        "ผลัพธ์นี้โตแน่นอน",
        "รับประกันว่าได้ผล",
        "ทำได้ 10x เร็วกว่าทุก",
        "production-ready จริง",
        "ดีกว่าทุกค่าย",
        "ติดต่อเราได้เลย",
        "คุณต้องทำตามนี้",
        "อย่าพลาด ลดกอง",
    ])
    def test_detects_banned(self, text):
        r = redact(text)
        assert r.banned, f"ไม่พบคำต้องห้ามใน '{text}'"
        assert r.needs_approval is True

    def test_strip_banned_removes(self):
        r = redact("ผลัพธ์นี้โตแน่นอนแน่", strip_banned=True)
        assert "โตแน่นอน" not in r.text


# ══════════════════════════════════════════════════════════════════════
# Publish gate — R1-R5
# ══════════════════════════════════════════════════════════════════════


GOOD_POST = """เจอปัญหา: โมเดลที่สั่งใช้ 2 ตัวไม่มีอยู่จริง ได้คำตอบว่าง
ต้นทุน: ทุกงานต้องรอ 3 โมเดล (ช่วงละ ~40 วิ) แล้วงานก็ไม่ได้ผลลัพธ์
แก้: ให้ watchdog ตรวจชื่อโมเดลทุก 6 ชม.
หลักฐาน: decisions/ADR-021-model-health-check.md
ยังไม่ได้ทำ: ยังไม่ได้ยืนยันว่าโมเดลคิดได้จริง
ถ้าคุณเคยเจอแบบนี้ เจอบ่อยไหมครับ"""


class TestPublishGate:
    """เกณฑ์ publish R1-R5 (จาก psych) + L1-L3 (จาก legal)"""

    def test_good_post_passes(self):
        r = redact(GOOD_POST)
        g = publish_gate(r.text, redaction=r)
        assert g.passed, f"ไม่ผ่าน: {g.failures()}"
        assert len(g.checks) == 8

    def test_r1_requires_evidence(self):
        bad = GOOD_POST.replace("decisions/ADR-021-model-health-check.md", "")
        g = publish_gate(bad)
        assert not g.passed
        assert any("R1" in f["rule"] for f in g.failures())

    def test_r2_requires_failure_and_cost(self):
        no_cost = "เจอปัญหา: ระบบค้าง\nหลักฐาน: decisions/x.md\nยังไม่ได้ทำ: ยัง\nเจอบ่อยไหมครับ"
        g = publish_gate(no_cost)
        assert not g.passed
        assert any("R2" in f["rule"] for f in g.failures())

    def test_r3_requires_not_done_line(self):
        no_nd = GOOD_POST.replace("ยังไม่ได้ทำ: ยังไม่ได้ยืนยันว่าโมเดลคิดได้จริง", "")
        g = publish_gate(no_nd)
        assert not g.passed
        assert any("R3" in f["rule"] for f in g.failures())

    def test_r4_blocks_cta_and_comparison(self):
        cta = GOOD_POST + "\nติดต่อเราได้เลย"
        g = publish_gate(cta)
        assert not g.passed
        assert any("R4" in f["rule"] for f in g.failures())

    def test_r5_requires_question(self):
        no_q = GOOD_POST.replace("เจอบ่อยไหมครับ", "เจอบ่อยครับ")
        g = publish_gate(no_q)
        assert not g.passed
        assert any("R5" in f["rule"] for f in g.failures())

    def test_l1_fails_when_secret_present(self):
        r = redact("เจอปัญหา: key sk-abcdefgh12345678")
        g = publish_gate(r.text, redaction=r)
        assert not g.passed
        assert any("L1" in f["rule"] for f in g.failures())

    def test_l2_fails_when_flag_pending(self):
        r = redact("รายได้ 120,000 บาท")
        g = publish_gate(r.text, redaction=r)
        assert not g.passed
        assert any("L2" in f["rule"] for f in g.failures())

    def test_gate_report_md(self):
        r = redact(GOOD_POST)
        g = publish_gate(r.text, redaction=r)
        report = gate_report_md(r, g)
        assert "Publish Gate" in report
        assert "ผ่าน" in report
        assert report.count("✅") >= 8


class TestPatternIntegrity:
    """pattern ต้องครอบคลุมและไม่ซ้ำซ้อนพัง"""

    def test_block_and_flag_do_not_overlap_labels(self):
        block_labels = {p[0] for p in BLOCK_PATTERNS}
        flag_labels = {p[0] for p in FLAG_PATTERNS}
        assert not (block_labels & flag_labels), \
            f"label ซ้ำ: {block_labels & flag_labels}"

    def test_all_patterns_compile(self):
        import re
        for _, _, pattern in BLOCK_PATTERNS + FLAG_PATTERNS:
            re.compile(pattern)

    def test_banned_phrases_compile(self):
        import re
        for pattern, _ in BANNED_PHRASES:
            re.compile(pattern)

    def test_secret_not_in_flag_only(self):
        """รหัสต้องถูก block เสมอ ไม่ใช่แค่ flag"""
        r = redact("รหัสคือ sk-abc1234567890xyz")
        assert r.blocked
        assert not r.flagged
