"""Tests for central_bus.bus_tags — governance tags + PII redact.

FP (ต้องรอด): ทศนิยม coverage / timestamp / ค่าคงที่วิทยาศาสตร์ จากข้อมูลจริง.
FN (ต้องโดน): บัตร (ติด/เว้นวรรค/ขีด) + เบอร์ (0/+66/เว้นวรรค).
"""
import inspect

from central_bus.bus_tags import (
    _thai_id_valid,
    log_access,
    redact_pii,
    validate_tags,
)


def _make_valid_id(base12: str, sep: str = "") -> str:
    assert len(base12) == 12 and base12.isdigit()
    total = sum(int(base12[i]) * (13 - i) for i in range(12))
    check = (11 - total % 11) % 10
    digits = base12 + str(check)
    assert _thai_id_valid(digits)
    if not sep:
        return digits
    # 1-XXXX-XXXXX-XX-X (format บัตรจริง)
    return f"{digits[0]}{sep}{digits[1:5]}{sep}{digits[5:10]}{sep}{digits[10:12]}{sep}{digits[12]}"


def test_validate_fills_defaults_warn():
    m = validate_tags({}, where="t")
    assert m["workstream"] == "SOLOCORP-CORE"
    assert m["sensitivity"] == "CONF"


def test_validate_keeps_good_tags():
    m = validate_tags({"workstream": "CUSTOMER-SCRAP", "sensitivity": "PUB"}, where="t")
    assert m == {"workstream": "CUSTOMER-SCRAP", "sensitivity": "PUB"}


def test_coverage_decimals_survive():
    # FP จากข้อมูลจริง (qa-gate evidence) — ห้ามโดนเด็ดขาด
    for s in ("coverage 9.683966367062917 ok",
              "coverage 70.8008094825094 failed",
              "publishedAt 1774314682404",
              "0.2817188376"):
        cleaned, found = redact_pii(s)
        assert (cleaned, found) == (s, False), s


def test_phone_plain():
    cleaned, found = redact_pii("โทร 0812345678 นะ")
    assert (cleaned, found) == ("โทร [REDACTED:PHONE] นะ", True)


def test_phone_plus66():
    for s in ("+66812345678", "+66 812345678", "66812345678"):
        cleaned, found = redact_pii(f"ติดต่อ {s} ด่วน")
        assert found and "[REDACTED:PHONE]" in cleaned, s


def test_phone_spaced():
    cleaned, found = redact_pii("เบอร์ 081 234 5678 ครับ")
    assert found and "[REDACTED:PHONE]" in cleaned


def test_id_plain_valid():
    tid = _make_valid_id("110070009070")
    cleaned, found = redact_pii(f"เลขบัตร {tid} จบ")
    assert (cleaned, found) == ("เลขบัตร [REDACTED:ID] จบ", True)


def test_id_spaced_dashed_valid():
    for tid in (_make_valid_id("110070009070", " "),
                _make_valid_id("110070009070", "-")):
        cleaned, found = redact_pii(f"บัตร {tid} นะ")
        assert found and cleaned == "บัตร [REDACTED:ID] นะ", tid


def test_id_bad_checksum_kept():
    cleaned, found = redact_pii("เลข 110070009071 ครับ")
    assert found is False and "110070009071" in cleaned


def test_log_access_takes_no_value():
    assert "value" not in str(inspect.signature(log_access))
