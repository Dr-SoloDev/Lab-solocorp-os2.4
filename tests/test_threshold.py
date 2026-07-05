"""Threshold engine unit tests — pure functions + CLI integration."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from govctl_cli.threshold import (
    COMPLEXITY_QUESTIONS,
    THRESHOLD_DECISIONS,
    THRESHOLD_MAP,
    assess_complexity,
    threshold_for_score,
)
from govctl_cli.cli import app

runner = CliRunner()

# ===========================================================================
# threshold_for_score
# ===========================================================================


class TestThresholdForScore:
    def test_score_0_returns_direct_adr(self):
        assert threshold_for_score(0) == "direct_adr"

    def test_score_1_returns_rfc(self):
        assert threshold_for_score(1) == "rfc"

    def test_score_2_returns_full_review(self):
        assert threshold_for_score(2) == "full_review"

    def test_score_3_returns_full_review(self):
        assert threshold_for_score(3) == "full_review"

    def test_raises_on_negative_one(self):
        with pytest.raises(ValueError, match="Score must be 0-3"):
            threshold_for_score(-1)

    def test_raises_on_four(self):
        with pytest.raises(ValueError, match="Score must be 0-3"):
            threshold_for_score(4)


# ===========================================================================
# assess_complexity — all 8 combinations of 3 binary questions
# ===========================================================================

_KEYS = ["scope_impact", "reversibility", "resource_commitment"]
_LABELS = {q["key"]: q["label"] for q in COMPLEXITY_QUESTIONS}


def _answers(*, scope_impact=False, reversibility=False, resource_commitment=False):
    return {
        "scope_impact": scope_impact,
        "reversibility": reversibility,
        "resource_commitment": resource_commitment,
    }


def _check_common(result, expected_score, expected_threshold):
    assert result["score"] == expected_score
    assert result["threshold"] == expected_threshold
    assert result["decision"] == THRESHOLD_DECISIONS[expected_threshold]
    assert result["all_clear"] == (expected_score == 0)
    assert len(result["details"]) == 3
    for d in result["details"]:
        assert d["key"] in _KEYS
        assert d["label"] == _LABELS[d["key"]]
        assert d["weight"] == (1 if d["answer"] else 0)


class TestAssessComplexityAllClear:
    """All three flags False → score 0, threshold direct_adr."""

    def test_all_false(self):
        result = assess_complexity(_answers())
        _check_common(result, 0, "direct_adr")
        for d in result["details"]:
            assert d["answer"] is False


class TestAssessComplexitySingleTrue:
    """Each flag alone → score 1, threshold rfc."""

    def test_only_scope_impact(self):
        result = assess_complexity(_answers(scope_impact=True))
        _check_common(result, 1, "rfc")
        assert result["details"][0]["answer"] is True
        assert result["details"][1]["answer"] is False
        assert result["details"][2]["answer"] is False

    def test_only_reversibility(self):
        result = assess_complexity(_answers(reversibility=True))
        _check_common(result, 1, "rfc")
        assert result["details"][0]["answer"] is False
        assert result["details"][1]["answer"] is True
        assert result["details"][2]["answer"] is False

    def test_only_resource_commitment(self):
        result = assess_complexity(_answers(resource_commitment=True))
        _check_common(result, 1, "rfc")
        assert result["details"][0]["answer"] is False
        assert result["details"][1]["answer"] is False
        assert result["details"][2]["answer"] is True


class TestAssessComplexityTwoTrue:
    """Two flags True → score 2, threshold full_review."""

    def test_scope_and_reversibility(self):
        result = assess_complexity(_answers(scope_impact=True, reversibility=True))
        _check_common(result, 2, "full_review")
        answers = [d["answer"] for d in result["details"]]
        assert answers == [True, True, False]

    def test_scope_and_resource(self):
        result = assess_complexity(_answers(scope_impact=True, resource_commitment=True))
        _check_common(result, 2, "full_review")
        answers = [d["answer"] for d in result["details"]]
        assert answers == [True, False, True]

    def test_reversibility_and_resource(self):
        result = assess_complexity(_answers(reversibility=True, resource_commitment=True))
        _check_common(result, 2, "full_review")
        answers = [d["answer"] for d in result["details"]]
        assert answers == [False, True, True]


class TestAssessComplexityAllTrue:
    """All three flags True → score 3, threshold full_review."""

    def test_all_true(self):
        result = assess_complexity(_answers(scope_impact=True, reversibility=True, resource_commitment=True))
        _check_common(result, 3, "full_review")
        for d in result["details"]:
            assert d["answer"] is True


# ===========================================================================
# CLI — threshold assess
# ===========================================================================


class TestCliAssess:
    def test_no_flags_score_0_direct_adr(self):
        result = runner.invoke(app, ["threshold", "assess"])
        assert result.exit_code == 0
        assert "Score:  0/3" in result.stdout
        assert "DIRECT ADR" in result.stdout

    def test_scope_impact_flag_score_1_rfc(self):
        result = runner.invoke(app, ["threshold", "assess", "-s"])
        assert result.exit_code == 0
        assert "Score:  1/3" in result.stdout
        assert "RFC" in result.stdout

    def test_scope_and_reversibility_score_2_full_review(self):
        result = runner.invoke(app, ["threshold", "assess", "-s", "-r"])
        assert result.exit_code == 0
        assert "Score:  2/3" in result.stdout
        assert "FULL REVIEW" in result.stdout

    def test_all_flags_with_verbose_score_3_details(self):
        result = runner.invoke(app, ["threshold", "assess", "-s", "-r", "-c", "-v"])
        assert result.exit_code == 0
        assert "Score:  3/3" in result.stdout
        assert "FULL REVIEW" in result.stdout
        assert "Scope Impact" in result.stdout
        assert "Reversibility" in result.stdout
        assert "Resource Commitment" in result.stdout


# ===========================================================================
# CLI — threshold info
# ===========================================================================


class TestCliInfo:
    def test_info_shows_rfc_001_table(self):
        result = runner.invoke(app, ["threshold", "info"])
        assert result.exit_code == 0
        assert "RFC-001" in result.stdout
        assert "Complexity Matrix" in result.stdout
        assert "Scope Impact" in result.stdout
        assert "Reversibility" in result.stdout
        assert "Resource Commitment" in result.stdout


# ===========================================================================
# CLI — threshold batch
# ===========================================================================


class TestCliBatch:
    def test_batch_with_json_file(self):
        tasks = [
            {"name": "quick task", "scope_impact": False, "reversibility": False, "resource_commitment": False},
            {"name": "big change", "scope_impact": True, "reversibility": True, "resource_commitment": True},
            {"name": "needs rfc", "scope_impact": True, "reversibility": False, "resource_commitment": False},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(tasks, f)
            tmp_path = f.name

        try:
            result = runner.invoke(app, ["threshold", "batch", "--file", tmp_path])
            assert result.exit_code == 0
            assert "quick task" in result.stdout
            assert "big change" in result.stdout
            assert "needs rfc" in result.stdout
            assert "score 0" in result.stdout
            assert "score 3" in result.stdout
            assert "score 1" in result.stdout
            assert "direct_adr" in result.stdout
            assert "full_review" in result.stdout
            assert "rfc" in result.stdout
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_batch_missing_file_shows_error(self):
        result = runner.invoke(app, ["threshold", "batch", "--file", "/tmp/nonexistent_batch_test.json"])
        assert result.exit_code == 1
        assert "Failed to load" in result.stdout

    def test_batch_no_file_flag_shows_error(self):
        result = runner.invoke(app, ["threshold", "batch"])
        assert result.exit_code == 1
        assert "Provide --file" in result.stdout
