from __future__ import annotations

import hashlib
import inspect
import json

import pytest

from axis_mcp.departments import qa_mcp
from axis_mcp.task_tracking import TaskTracker


@pytest.fixture
def isolated_qa(tmp_path, monkeypatch):
    results_root = tmp_path / "central_bus" / "content" / "qa_results"
    results_root.mkdir(parents=True)
    monkeypatch.setattr(qa_mcp, "ROOT", tmp_path)
    monkeypatch.setattr(qa_mcp, "QA_RESULTS_ROOT", results_root)
    monkeypatch.setattr(qa_mcp, "_task_tracker", TaskTracker(tmp_path / "tasks"))
    return results_root


def test_qa_suite_list_computes_hash_from_evidence_bytes(isolated_qa):
    recorded = json.loads(qa_mcp.qa_record_test_result("unit-suite", "passed", "all good"))
    evidence_path = isolated_qa / recorded["result_path"].split("/")[-1]
    expected_hash = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

    listed = json.loads(qa_mcp.qa_list_test_suites())

    assert listed["test_suites"][0]["suite_id"] == "unit-suite"
    assert listed["test_suites"][0]["sha256"] == expected_hash
    assert listed["test_suites"][0]["sha256"] == recorded["sha256"]


def test_qa_record_timestamp_is_generated_by_the_server():
    parameters = inspect.signature(qa_mcp.qa_record_test_result).parameters
    assert "recorded_at" not in parameters
    with pytest.raises(TypeError):
        qa_mcp.qa_record_test_result("unit-suite", "passed", recorded_at="2000-01-01T00:00:00Z")
