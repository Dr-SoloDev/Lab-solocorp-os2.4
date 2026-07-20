#!/usr/bin/env python3
"""
=============================================================
  🧪 SoloCorp OS — QA Sign-off Gate Tests
=============================================================
  pytest suite สำหรับ QA sign-off gate validation
=============================================================
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from workers.qa_signoff_gate import (
    _now_iso,
    _ensure_dir,
    _load_test_results,
    _validate_signoff,
    _save_signoff,
    run_signoff,
    parse_args,
    MIN_COVERAGE,
    CONDITIONAL_MIN_COVERAGE,
    MAX_CRITICAL,
    MAX_HIGH,
    MAX_MEDIUM_CONDITIONAL,
    MAX_LOW_CONDITIONAL,
    SIGNOFF_DIR,
)


# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def sample_test_results() -> dict:
    return {
        "test_coverage": 85,
        "critical_bugs": 0,
        "high_bugs": 0,
        "medium_bugs": 1,
        "low_bugs": 3,
        "total_tests": 120,
        "passed_tests": 115,
        "failed_tests": 0,
        "skipped_tests": 5,
        "regression_pass": True,
    }


@pytest.fixture
def temp_test_file(sample_test_results) -> str:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(sample_test_results, f)
        return f.name


@pytest.fixture
def clean_signoff_dir():
    """Use temp dir instead of real signoff dir to avoid side effects."""
    original = os.environ.get("_TEST_SIGNOFF_DIR")
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["_TEST_SIGNOFF_DIR"] = tmpdir
        yield Path(tmpdir)
    if original:
        os.environ["_TEST_SIGNOFF_DIR"] = original
    else:
        os.environ.pop("_TEST_SIGNOFF_DIR", None)


# ═══════════════════════════════════════════════════════════
# Test: Constants
# ═══════════════════════════════════════════════════════════


def test_min_thresholds_are_sane():
    """Verify minimum thresholds are logically consistent."""
    assert MIN_COVERAGE == 80, "APPROVED coverage threshold should be 80%"
    assert CONDITIONAL_MIN_COVERAGE == 70, "CONDITIONAL coverage threshold should be 70%"
    assert CONDITIONAL_MIN_COVERAGE < MIN_COVERAGE, "CONDITIONAL threshold must be lower than APPROVED"
    assert MAX_CRITICAL == 0, "No critical bugs allowed"
    assert MAX_HIGH == 0, "No high bugs allowed"
    assert MAX_MEDIUM_CONDITIONAL >= 1, "Conditional medium bug threshold should exist"
    assert MAX_LOW_CONDITIONAL >= 1, "Conditional low bug threshold should exist"


def test_signoff_dir_path():
    """Signoff directory should be under bus/evidence/qa-signoff."""
    assert "qa-signoff" in str(SIGNOFF_DIR)
    assert "evidence" in str(SIGNOFF_DIR)


# ═══════════════════════════════════════════════════════════
# Test: _now_iso
# ═══════════════════════════════════════════════════════════


def test_now_iso_format():
    """ISO-8601 timestamp should include date and time."""
    ts = _now_iso()
    assert "T" in ts, "ISO-8601 must contain T separator"
    assert ts.endswith("+00:00") or "Z" in ts or "+" in ts, "Must include timezone"


# ═══════════════════════════════════════════════════════════
# Test: _ensure_dir
# ═══════════════════════════════════════════════════════════


def test_ensure_dir_creates(tmp_path):
    """Should create directory if it doesn't exist."""
    test_dir = tmp_path / "nested" / "dir" / "test"
    assert not test_dir.exists()
    result = _ensure_dir(test_dir)
    assert test_dir.exists()
    assert result == test_dir


def test_ensure_dir_exists(tmp_path):
    """Should not fail if directory already exists."""
    test_dir = tmp_path / "existing"
    test_dir.mkdir(parents=True)
    result = _ensure_dir(test_dir)
    assert result == test_dir


# ═══════════════════════════════════════════════════════════
# Test: _load_test_results
# ═══════════════════════════════════════════════════════════


def test_load_test_results_none():
    """Should return empty dict when no path provided."""
    assert _load_test_results(None) == {}


def test_load_test_results_not_found():
    """Should return empty dict when file not found."""
    assert _load_test_results("/nonexistent/path.json") == {}


def test_load_test_results_valid(temp_test_file, sample_test_results):
    """Should load valid JSON test results."""
    data = _load_test_results(temp_test_file)
    assert data.get("test_coverage") == sample_test_results["test_coverage"]
    assert data.get("critical_bugs") == sample_test_results["critical_bugs"]
    assert data.get("regression_pass") == sample_test_results["regression_pass"]


def test_load_test_results_invalid_json(tmp_path):
    """Should return empty dict for invalid JSON."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json")
    assert _load_test_results(str(bad_file)) == {}


# ═══════════════════════════════════════════════════════════
# Test: _validate_signoff
# ═══════════════════════════════════════════════════════════


class TestValidateSignoff:
    """Group validation tests."""

    def test_approve_high_coverage_no_bugs(self):
        """85% coverage, 0 bugs, regression pass → APPROVED."""
        result = _validate_signoff({
            "test_coverage": 85,
            "critical_bugs": 0,
            "high_bugs": 0,
            "medium_bugs": 0,
            "low_bugs": 0,
            "regression_pass": True,
        })
        assert result == "APPROVED"

    def test_approve_at_threshold(self):
        """80% coverage, 0 bugs, regression pass → APPROVED."""
        result = _validate_signoff({
            "test_coverage": 80,
            "critical_bugs": 0,
            "high_bugs": 0,
            "medium_bugs": 0,
            "low_bugs": 0,
            "regression_pass": True,
        })
        assert result == "APPROVED"

    def test_conditional_below_full_threshold(self):
        """75% coverage → CONDITIONAL."""
        result = _validate_signoff({
            "test_coverage": 75,
            "critical_bugs": 0,
            "high_bugs": 0,
            "medium_bugs": 0,
            "low_bugs": 0,
            "regression_pass": True,
        })
        assert result == "CONDITIONAL"

    def test_conditional_many_medium_bugs(self):
        """Medium bugs > 3 → CONDITIONAL."""
        result = _validate_signoff({
            "test_coverage": 85,
            "critical_bugs": 0,
            "high_bugs": 0,
            "medium_bugs": 5,
            "low_bugs": 0,
            "regression_pass": True,
        })
        assert result == "CONDITIONAL"

    def test_conditional_many_low_bugs(self):
        """Low bugs > 10 → CONDITIONAL."""
        result = _validate_signoff({
            "test_coverage": 85,
            "critical_bugs": 0,
            "high_bugs": 0,
            "medium_bugs": 0,
            "low_bugs": 15,
            "regression_pass": True,
        })
        assert result == "CONDITIONAL"

    def test_reject_critical_bugs(self):
        """Critical bugs > 0 → REJECTED."""
        result = _validate_signoff({
            "test_coverage": 85,
            "critical_bugs": 1,
            "high_bugs": 0,
            "medium_bugs": 0,
            "low_bugs": 0,
            "regression_pass": True,
        })
        assert result == "REJECTED"

    def test_reject_high_bugs(self):
        """High bugs > 0 → REJECTED."""
        result = _validate_signoff({
            "test_coverage": 85,
            "critical_bugs": 0,
            "high_bugs": 2,
            "medium_bugs": 0,
            "low_bugs": 0,
            "regression_pass": True,
        })
        assert result == "REJECTED"

    def test_reject_low_coverage(self):
        """Coverage < 70% → REJECTED."""
        result = _validate_signoff({
            "test_coverage": 50,
            "critical_bugs": 0,
            "high_bugs": 0,
            "medium_bugs": 0,
            "low_bugs": 0,
            "regression_pass": True,
        })
        assert result == "REJECTED"

    def test_reject_regression_fail(self):
        """Regression not passed → REJECTED."""
        result = _validate_signoff({
            "test_coverage": 85,
            "critical_bugs": 0,
            "high_bugs": 0,
            "medium_bugs": 0,
            "low_bugs": 0,
            "regression_pass": False,
        })
        assert result == "REJECTED"

    def test_reject_edge_coverage_zero(self):
        """Coverage 0% → REJECTED."""
        result = _validate_signoff({
            "test_coverage": 0,
            "critical_bugs": 0,
            "high_bugs": 0,
            "medium_bugs": 0,
            "low_bugs": 0,
            "regression_pass": True,
        })
        assert result == "REJECTED"

    def test_approve_boundary_coverage(self):
        """Coverage exactly at conditional boundary (70%) + no bugs → CONDITIONAL (since < 80)."""
        result = _validate_signoff({
            "test_coverage": 70,
            "critical_bugs": 0,
            "high_bugs": 0,
            "medium_bugs": 0,
            "low_bugs": 0,
            "regression_pass": True,
        })
        assert result == "CONDITIONAL"


# ═══════════════════════════════════════════════════════════
# Test: _save_signoff
# ═══════════════════════════════════════════════════════════


def test_save_signoff_creates_file(tmp_path):
    """Save should create a JSON file."""
    from workers.qa_signoff_gate import SIGNOFF_DIR

    record = {
        "feature": "test-feature",
        "qa_signoff": {
            "evidence_id": "test-id",
            "tester": "QA-01",
            "date": "2026-07-20T00:00:00+00:00",
            "test_coverage": "80%",
            "critical_bugs": 0,
            "high_bugs": 0,
            "medium_bugs": 0,
            "low_bugs": 0,
            "regression_pass": True,
            "status": "APPROVED",
            "conditions": [],
            "notes": "test",
        },
    }
    filepath = _save_signoff(record)
    assert filepath.exists()
    assert filepath.suffix == ".json"

    # Verify content
    with open(filepath) as f:
        saved = json.load(f)
    assert saved["feature"] == "test-feature"
    assert saved["qa_signoff"]["status"] == "APPROVED"


def test_save_signoff_valid_json(tmp_path):
    """Saved file should be valid JSON."""
    record = {
        "feature": "json-validity",
        "qa_signoff": {
            "evidence_id": "test-id-2",
            "tester": "QA-02",
            "date": "2026-07-20T00:00:00+00:00",
            "test_coverage": "99%",
            "critical_bugs": 0,
            "high_bugs": 0,
            "medium_bugs": 0,
            "low_bugs": 0,
            "regression_pass": True,
            "status": "APPROVED",
            "conditions": [],
            "notes": "",
        },
    }
    filepath = _save_signoff(record)
    with open(filepath) as f:
        loaded = json.load(f)
    assert loaded["qa_signoff"]["status"] == "APPROVED"


# ═══════════════════════════════════════════════════════════
# Test: run_signoff (integration)
# ═══════════════════════════════════════════════════════════


def test_run_signoff_approved():
    """Full integration: approved sign-off."""
    record = run_signoff(
        feature="integration-test",
        status="APPROVED",
        tester="QA-Bot",
        coverage=90,
        regression_pass=True,
    )
    assert record["feature"] == "integration-test"
    assert record["qa_signoff"]["status"] == "APPROVED"
    assert record["qa_signoff"]["test_coverage"] == "90%"
    assert "_filepath" in record


def test_run_signoff_rejected():
    """Full integration: rejected sign-off."""
    record = run_signoff(
        feature="bad-feature",
        status="REJECTED",
        tester="QA-Bot",
        coverage=40,
        critical_bugs=2,
        regression_pass=False,
    )
    assert record["qa_signoff"]["status"] == "REJECTED"


def test_run_signoff_conditional_with_conditions():
    """Full integration: conditional with documented conditions."""
    record = run_signoff(
        feature="partial-feature",
        status="CONDITIONAL",
        tester="QA-Bot",
        coverage=75,
        regression_pass=True,
        conditions=["Fix medium bug MB-42 before next deploy", "Add missing edge case tests"],
        notes="Approved with conditions",
    )
    assert record["qa_signoff"]["status"] == "CONDITIONAL"
    assert len(record["qa_signoff"]["conditions"]) == 2


def test_run_signoff_auto_determine_approve():
    """Auto determine status from parameters — should be APPROVED."""
    record = run_signoff(
        feature="auto-approve",
        tester="QA-Bot",
        coverage=88,
        regression_pass=True,
    )
    assert record["qa_signoff"]["status"] == "APPROVED"


def test_run_signoff_auto_determine_reject():
    """Auto determine status from parameters — should be REJECTED."""
    record = run_signoff(
        feature="auto-reject",
        tester="QA-Bot",
        coverage=30,
        regression_pass=True,
    )
    assert record["qa_signoff"]["status"] == "REJECTED"


def test_run_signoff_with_test_results_file(temp_test_file):
    """Load results from JSON file."""
    record = run_signoff(
        feature="file-based",
        tester="QA-Bot",
        test_results_path=temp_test_file,
    )
    assert record["qa_signoff"]["test_coverage"] == "85%"
    assert record["qa_signoff"]["status"] == "APPROVED"


def test_run_signoff_missing_test_file():
    """Missing test file should not crash."""
    record = run_signoff(
        feature="missing-file",
        tester="QA-Bot",
        test_results_path="/nonexistent/file.json",
        coverage=80,
        regression_pass=True,
    )
    assert record["qa_signoff"]["status"] == "APPROVED"


def test_run_signoff_saves_evidence():
    """Evidence file should be created on disk."""
    record = run_signoff(
        feature="evidence-check",
        status="APPROVED",
        tester="QA-Bot",
        coverage=95,
        regression_pass=True,
    )
    filepath = record.get("_filepath")
    assert filepath is not None
    assert os.path.exists(filepath), f"Evidence file not found: {filepath}"

    # Clean up
    os.unlink(filepath)


# ═══════════════════════════════════════════════════════════
# Test: parse_args
# ═══════════════════════════════════════════════════════════


def test_parse_args_minimal():
    """Minimal required args."""
    args = parse_args(["--feature", "my-feature"])
    assert args.feature == "my-feature"
    assert args.status == "REJECTED"  # default
    assert args.tester == "unknown"  # default


def test_parse_args_full():
    """All args provided."""
    args = parse_args([
        "--feature", "login-v2",
        "--status", "APPROVED",
        "--tester", "QA-01",
        "--coverage", "85",
        "--critical-bugs", "0",
        "--high-bugs", "0",
        "--medium-bugs", "2",
        "--low-bugs", "5",
        "--regression-pass",
        "--conditions", "fix-nits", "add-logging",
        "--notes", "All good",
    ])
    assert args.feature == "login-v2"
    assert args.status == "APPROVED"
    assert args.tester == "QA-01"
    assert args.coverage == 85
    assert args.critical_bugs == 0
    assert args.regression_pass is True
    assert len(args.conditions) == 2
    assert args.notes == "All good"


def test_parse_args_requires_feature():
    """Missing --feature should fail."""
    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_invalid_status():
    """Invalid status should fail."""
    with pytest.raises(SystemExit):
        parse_args(["--feature", "x", "--status", "INVALID"])


# ═══════════════════════════════════════════════════════════
# Test: record schema compliance
# ═══════════════════════════════════════════════════════════


def test_signoff_record_schema():
    """Verify sign-off record matches required schema."""
    record = run_signoff(
        feature="schema-test",
        status="APPROVED",
        tester="QA-Schema",
        coverage=85,
        regression_pass=True,
    )

    # Top-level key
    assert "feature" in record
    assert "qa_signoff" in record

    # qa_signoff fields
    qa = record["qa_signoff"]
    assert "tester" in qa
    assert "date" in qa
    assert "test_coverage" in qa
    assert "critical_bugs" in qa
    assert "high_bugs" in qa
    assert "medium_bugs" in qa
    assert "low_bugs" in qa
    assert "regression_pass" in qa
    assert "status" in qa
    assert "conditions" in qa
    assert "notes" in qa

    # Status values
    assert qa["status"] in ("APPROVED", "REJECTED", "CONDITIONAL")

    # Coverage format
    assert qa["test_coverage"].endswith("%")

    # Types
    assert isinstance(qa["critical_bugs"], int)
    assert isinstance(qa["regression_pass"], bool)
    assert isinstance(qa["conditions"], list)

    # Clean up
    filepath = record.get("_filepath")
    if filepath and os.path.exists(filepath):
        os.unlink(filepath)


# ═══════════════════════════════════════════════════════════
# Test: exit codes
# ═══════════════════════════════════════════════════════════


class TestExitCodes:
    """Test CLI exit codes match status."""

    def test_approved_exit(self, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            ["qa-signoff", "--feature", "exit-test", "--status", "APPROVED", "--tester", "t"],
        )
        from workers.qa_signoff_gate import main
        assert main() == 0

    def test_rejected_exit(self, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            ["qa-signoff", "--feature", "exit-test", "--status", "REJECTED", "--tester", "t"],
        )
        from workers.qa_signoff_gate import main
        assert main() == 1

    def test_conditional_exit(self, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            ["qa-signoff", "--feature", "exit-test", "--status", "CONDITIONAL", "--tester", "t"],
        )
        from workers.qa_signoff_gate import main
        assert main() == 2


# ═══════════════════════════════════════════════════════════
# Test: edge cases
# ═══════════════════════════════════════════════════════════


def test_edge_case_default_values():
    """Defaults should not cause errors."""
    record = run_signoff(feature="edge-defaults")
    assert record["qa_signoff"]["status"] == "REJECTED"
    assert record["qa_signoff"]["tester"] == "unknown"
    assert record["qa_signoff"]["test_coverage"] == "0%"
    assert record["qa_signoff"]["regression_pass"] is True
    # Clean up
    filepath = record.get("_filepath")
    if filepath and os.path.exists(filepath):
        os.unlink(filepath)


def test_edge_case_special_chars_feature(tmp_path):
    """Feature name with special chars should not break file saving."""
    from workers.qa_signoff_gate import SIGNOFF_DIR
    record = run_signoff(
        feature="test/slash:feature name",
        status="APPROVED",
        tester="QA-01",
        coverage=90,
        regression_pass=True,
    )
    filepath = record.get("_filepath")
    assert filepath is not None
    # Clean up
    if os.path.exists(filepath):
        os.unlink(filepath)


def test_all_status_values_accepted():
    """All three status values should produce correct records."""
    for status in ("APPROVED", "CONDITIONAL", "REJECTED"):
        record = run_signoff(
            feature=f"status-{status.lower()}",
            status=status,
            tester="QA-01",
            coverage=85,
            regression_pass=True,
        )
        assert record["qa_signoff"]["status"] == status
        # Clean up
        filepath = record.get("_filepath")
        if filepath and os.path.exists(filepath):
            os.unlink(filepath)
