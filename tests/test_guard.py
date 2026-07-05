"""Guard checker unit tests — pure functions, no I/O or CLI mocking."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from govctl_cli.guard import (
    check_guard_001,
    check_guard_002,
    check_guard_003,
    check_guard_004,
    check_guard_005,
    check_guard_006,
)


def _valid_adr():
    return {
        "metadata": {
            "id": "ADR-099",
            "title": "Test ADR",
            "status": "proposed",
            "author": "Tester",
            "date": "2026-07-05",
        },
        "classification": {
            "domain": "architecture",
            "impact": "medium",
            "complexity": "low",
            "scope": "single-team",
        },
        "body": {
            "en": {
                "summary": "English summary",
                "context": "English context",
                "decision": "We will do X",
                "consequences": "English consequences",
            },
            "th": {
                "summary": "สรุปภาษาไทย",
                "context": "บริบทภาษาไทย",
                "decision": "เราจะทำ X",
                "consequences": "ผลกระทบภาษาไทย",
            },
        },
        "footer": {
            "references": [],
            "review_date": "2026-10-03",
        },
    }


# ===========================================================================
# GUARD-001: Schema Compliance
# ===========================================================================


class TestGuard001:
    def test_passes_valid_adr(self):
        issues = check_guard_001(_valid_adr())
        fail_issues = [i for i in issues if i["status"] == "FAIL"]
        assert fail_issues == []

    def test_fails_missing_id(self):
        data = _valid_adr()
        del data["metadata"]["id"]
        issues = check_guard_001(data)
        assert any("metadata.id" in i["field"] for i in issues)

    def test_fails_missing_title(self):
        data = _valid_adr()
        del data["metadata"]["title"]
        issues = check_guard_001(data)
        assert any("metadata.title" in i["field"] for i in issues)

    def test_fails_invalid_status(self):
        data = _valid_adr()
        data["metadata"]["status"] = "invalid_status"
        issues = check_guard_001(data)
        assert any("metadata.status" in i["field"] for i in issues)

    def test_fails_missing_author(self):
        data = _valid_adr()
        del data["metadata"]["author"]
        issues = check_guard_001(data)
        assert any("metadata.author" in i["field"] for i in issues)

    def test_fails_invalid_date_format(self):
        data = _valid_adr()
        data["metadata"]["date"] = "not-a-date"
        issues = check_guard_001(data)
        assert any("metadata.date" in i["field"] for i in issues)

    def test_fails_invalid_domain(self):
        data = _valid_adr()
        data["classification"]["domain"] = "invalid-domain"
        issues = check_guard_001(data)
        assert any("classification.domain" in i["field"] for i in issues)

    def test_fails_invalid_impact(self):
        data = _valid_adr()
        data["classification"]["impact"] = "extra-high"
        issues = check_guard_001(data)
        assert any("classification.impact" in i["field"] for i in issues)

    def test_fails_invalid_complexity(self):
        data = _valid_adr()
        data["classification"]["complexity"] = "extreme"
        issues = check_guard_001(data)
        assert any("classification.complexity" in i["field"] for i in issues)

    def test_fails_missing_scope(self):
        data = _valid_adr()
        data["classification"]["scope"] = ""
        issues = check_guard_001(data)
        assert any("classification.scope" in i["field"] for i in issues)

    def test_accepts_valid_statuses(self):
        for status in ("proposed", "draft", "accepted", "deprecated", "superseded"):
            data = _valid_adr()
            data["metadata"]["status"] = status
            fail = [i for i in check_guard_001(data) if i["status"] == "FAIL"]
            assert not fail, f"Failed for status '{status}': {fail}"

    def test_accepts_valid_domains(self):
        for domain in ("governance", "documentation", "architecture", "engineering", "product"):
            data = _valid_adr()
            data["classification"]["domain"] = domain
            fail = [i for i in check_guard_001(data) if i["status"] == "FAIL"]
            assert not fail, f"Failed for domain '{domain}': {fail}"


# ===========================================================================
# GUARD-002: Bilingual Completeness
# ===========================================================================


class TestGuard002:
    def test_passes_valid_bilingual(self):
        issues = check_guard_002(_valid_adr())
        fail_issues = [i for i in issues if i["status"] == "FAIL"]
        assert fail_issues == []

    def test_fails_missing_en_summary(self):
        data = _valid_adr()
        del data["body"]["en"]["summary"]
        issues = check_guard_002(data)
        assert any("body.en.summary" in i["field"] for i in issues)

    def test_fails_missing_th_context(self):
        data = _valid_adr()
        del data["body"]["th"]["context"]
        issues = check_guard_002(data)
        assert any("body.th.context" in i["field"] for i in issues)

    def test_fails_missing_en_decision_and_proposal(self):
        data = _valid_adr()
        del data["body"]["en"]["decision"]
        issues = check_guard_002(data)
        assert any("body.en.decision/proposal" in i["field"] for i in issues)

    def test_accepts_en_proposal_instead_of_decision(self):
        data = _valid_adr()
        del data["body"]["en"]["decision"]
        data["body"]["en"]["proposal"] = "RFC-style proposal"
        issues = check_guard_002(data)
        fail = [i for i in issues if i["status"] == "FAIL"]
        assert not any("body.en.decision/proposal" in i["field"] for i in fail)

    def test_accepts_th_proposal_instead_of_decision(self):
        data = _valid_adr()
        del data["body"]["th"]["decision"]
        data["body"]["th"]["proposal"] = "ข้อเสนอภาษาไทย"
        issues = check_guard_002(data)
        fail = [i for i in issues if i["status"] == "FAIL"]
        assert not any("body.th.decision/proposal" in i["field"] for i in fail)

    def test_fails_missing_en_consequences(self):
        data = _valid_adr()
        del data["body"]["en"]["consequences"]
        issues = check_guard_002(data)
        assert any("body.en.consequences" in i["field"] for i in issues)

    def test_fails_missing_th_summary_and_context(self):
        data = _valid_adr()
        del data["body"]["th"]["summary"]
        del data["body"]["th"]["context"]
        del data["body"]["th"]["decision"]
        del data["body"]["th"]["consequences"]
        issues = check_guard_002(data)
        fields = [i["field"] for i in issues]
        assert "body.th.summary" in fields
        assert "body.th.context" in fields
        assert "body.th.decision/proposal" in fields
        assert "body.th.consequences" in fields

    def test_passes_empty_body_returns_issues(self):
        issues = check_guard_002({})
        assert len(issues) >= 4


# ===========================================================================
# GUARD-003: Complexity Score
# ===========================================================================


class TestGuard003:
    def test_passes_valid_complexity_low(self):
        data = _valid_adr()
        data["classification"]["complexity"] = "low"
        issues = check_guard_003(data)
        fail = [i for i in issues if i["status"] == "FAIL"]
        assert fail == []

    def test_passes_without_score(self):
        data = _valid_adr()
        data["classification"]["complexity"] = "medium"
        issues = check_guard_003(data)
        fail = [i for i in issues if i["status"] == "FAIL"]
        assert fail == []

    def test_fails_invalid_complexity_value(self):
        data = _valid_adr()
        data["classification"]["complexity"] = "extreme"
        issues = check_guard_003(data)
        assert any("classification.complexity" in i["field"] for i in issues)

    def test_fails_score_not_integer(self):
        data = _valid_adr()
        data["classification"]["complexity"] = "low"
        data["metadata"]["complexity_score"] = "abc"
        issues = check_guard_003(data)
        assert any("metadata.complexity_score" in i["field"] for i in issues)

    def test_fails_score_out_of_range(self):
        data = _valid_adr()
        data["classification"]["complexity"] = "low"
        data["metadata"]["complexity_score"] = 99
        issues = check_guard_003(data)
        assert any("metadata.complexity_score" in i["field"] for i in issues)

    def test_warns_score_mismatch(self):
        data = _valid_adr()
        data["classification"]["complexity"] = "high"
        data["metadata"]["complexity_score"] = 0
        issues = check_guard_003(data)
        assert any("WARN" in i["status"] for i in issues)

    def test_score_mismatch_low_vs_high(self):
        data = _valid_adr()
        data["classification"]["complexity"] = "low"
        data["metadata"]["complexity_score"] = 3
        issues = check_guard_003(data)
        warns = [i for i in issues if i["status"] == "WARN"]
        assert len(warns) >= 1

    def test_zero_score_matches_low(self):
        data = _valid_adr()
        data["classification"]["complexity"] = "low"
        data["metadata"]["complexity_score"] = 0
        fail = [i for i in check_guard_003(data) if i["status"] == "FAIL"]
        warns = [i for i in check_guard_003(data) if i["status"] == "WARN"]
        assert fail == []
        assert warns == []

    def test_score_1_matches_medium(self):
        data = _valid_adr()
        data["classification"]["complexity"] = "medium"
        data["metadata"]["complexity_score"] = 1
        fail = [i for i in check_guard_003(data) if i["status"] == "FAIL"]
        warns = [i for i in check_guard_003(data) if i["status"] == "WARN"]
        assert fail == []
        assert warns == []

    def test_score_2_or_3_matches_high(self):
        for score in (2, 3):
            data = _valid_adr()
            data["classification"]["complexity"] = "high"
            data["metadata"]["complexity_score"] = score
            fail = [i for i in check_guard_003(data) if i["status"] == "FAIL"]
            warns = [i for i in check_guard_003(data) if i["status"] == "WARN"]
            assert fail == [], f"FAIL for score {score}"
            assert warns == [], f"WARN for score {score}"


# ===========================================================================
# GUARD-004: Status Validity
# ===========================================================================


class TestGuard004:
    def test_passes_valid_status(self):
        for status in ("proposed", "draft", "accepted", "deprecated", "superseded"):
            data = _valid_adr()
            data["metadata"]["status"] = status
            if status in ("superseded", "deprecated"):
                data["footer"]["references"] = ["ADR-001"]
            fail = [i for i in check_guard_004(data) if i["status"] == "FAIL"]
            assert not fail, f"Failed for status '{status}'"

    def test_fails_invalid_status(self):
        data = _valid_adr()
        data["metadata"]["status"] = "deleted"
        issues = check_guard_004(data)
        assert any("metadata.status" in i["field"] for i in issues)

    def test_fails_superseded_without_references(self):
        data = _valid_adr()
        data["metadata"]["status"] = "superseded"
        data["footer"]["references"] = []
        issues = check_guard_004(data)
        fail = [i for i in issues if i["status"] == "FAIL"]
        assert any("footer.references" in i["field"] for i in fail)

    def test_warns_deprecated_without_references(self):
        data = _valid_adr()
        data["metadata"]["status"] = "deprecated"
        data["footer"]["references"] = []
        issues = check_guard_004(data)
        warns = [i for i in issues if i["status"] == "WARN"]
        assert any("footer.references" in i["field"] for i in warns)

    def test_passes_superseded_with_references(self):
        data = _valid_adr()
        data["metadata"]["status"] = "superseded"
        data["footer"]["references"] = ["ADR-002"]
        fail = [i for i in check_guard_004(data) if i["status"] == "FAIL"]
        assert fail == []

    def test_passes_deprecated_with_references(self):
        data = _valid_adr()
        data["metadata"]["status"] = "deprecated"
        data["footer"]["references"] = ["ADR-002"]
        fail = [i for i in check_guard_004(data) if i["status"] == "FAIL"]
        warns = [i for i in check_guard_004(data) if i["status"] == "WARN"]
        assert fail == []
        assert warns == []


# ===========================================================================
# GUARD-005: Review Date
# ===========================================================================


class TestGuard005:
    def test_passes_with_review_date(self):
        data = _valid_adr()
        data["footer"]["review_date"] = "2026-10-03"
        data["metadata"]["date"] = "2026-07-05"
        fail = [i for i in check_guard_005(data) if i["status"] == "FAIL"]
        assert fail == []

    def test_fails_missing_review_date(self):
        data = _valid_adr()
        data["footer"]["review_date"] = ""
        issues = check_guard_005(data)
        assert any("footer.review_date" in i["field"] for i in issues)

    def test_fails_no_review_date_field(self):
        issues = check_guard_005({})
        assert any(i["status"] == "FAIL" for i in issues)

    def test_fails_invalid_date_format(self):
        data = _valid_adr()
        data["footer"]["review_date"] = "2026/10/03"
        issues = check_guard_005(data)
        assert any(i["status"] == "FAIL" for i in issues)

    def test_warns_review_too_far_from_created(self):
        data = _valid_adr()
        data["footer"]["review_date"] = "2027-01-01"
        data["metadata"]["date"] = "2026-07-05"
        issues = check_guard_005(data)
        warns = [i for i in issues if i["status"] == "WARN"]
        assert len(warns) >= 1
        assert any("90 days" in i["detail"] for i in warns)

    def test_passes_review_within_90_days(self):
        data = _valid_adr()
        data["footer"]["review_date"] = "2026-09-01"
        data["metadata"]["date"] = "2026-07-05"
        fail = [i for i in check_guard_005(data) if i["status"] == "FAIL"]
        warns = [i for i in check_guard_005(data) if i["status"] == "WARN"]
        assert fail == []
        assert not any("90 days" in i["detail"] for i in warns)

    def test_fails_value_error_on_semantically_invalid_date(self):
        """A date string matching YYYY-MM-DD format but semantically invalid
        (e.g. Feb 30) passes the regex check but raises ValueError from
        strptime → returns FAIL with 'Invalid date' in detail."""
        data = _valid_adr()
        # "2025-02-30" passes ^\d{4}-\d{2}-\d{2}$ regex but is not a real date
        data["footer"]["review_date"] = "2025-02-30"
        # Clear metadata.date so we don't accidentally trigger other branches
        data["metadata"]["date"] = ""
        issues = check_guard_005(data)
        fail = [i for i in issues if i["status"] == "FAIL"]
        assert any("Invalid date" in i["detail"] for i in fail)


# ===========================================================================
# GUARD-006: Cross-Reference Integrity
# ===========================================================================


class TestGuard006:
    def test_passes_no_references(self):
        data = _valid_adr()
        data["footer"]["references"] = []
        issues = check_guard_006(data)
        assert issues == []

    def test_passes_no_footer(self):
        issues = check_guard_006({})
        assert issues == []

    def test_fails_reference_to_nonexistent_adr(self):
        data = _valid_adr()
        data["footer"]["references"] = ["ADR-99999"]
        issues = check_guard_006(data)
        fail = [i for i in issues if i["status"] == "FAIL"]
        assert len(fail) == 1
        assert "ADR-99999" in fail[0]["field"]

    def test_fails_reference_to_nonexistent_rfc(self):
        data = _valid_adr()
        data["footer"]["references"] = ["RFC-99999"]
        issues = check_guard_006(data)
        fail = [i for i in issues if i["status"] == "FAIL"]
        assert len(fail) == 1
        assert "RFC-99999" in fail[0]["field"]

    def test_passes_ignores_non_adr_rfc_refs(self):
        data = _valid_adr()
        data["footer"]["references"] = ["https://example.com", "#internal-note"]
        issues = check_guard_006(data)
        assert issues == []

    def test_mixed_references(self):
        data = _valid_adr()
        data["footer"]["references"] = ["ADR-001", "RFC-99999", "ADR-99999"]
        issues = check_guard_006(data)
        fail = [i for i in issues if i["status"] == "FAIL"]
        # ADR-001 should exist, RFC-99999 and ADR-99999 should not
        failed_fields = [i["field"] for i in fail]
        assert any("RFC-99999" in f for f in failed_fields)
        assert any("ADR-99999" in f for f in failed_fields)
    