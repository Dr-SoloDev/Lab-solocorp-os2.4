"""QA department MCP server.

Department boundary for QA. Exposes test suite listing, test result recording,
and QA status summary through the head, keeping specialist implementation
details internal.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..module_registry import ModuleRegistry
from ..task_tracking import TaskTracker

ROOT = Path(__file__).resolve().parent.parent.parent
_module_registry = ModuleRegistry()
_task_tracker = TaskTracker()

QA_RESULTS_ROOT = Path(
    os.environ.get("SOLOCORP_QA_RESULTS_ROOT", ROOT / "central_bus" / "content" / "qa_results")
)
QA_RESULTS_ROOT.mkdir(parents=True, exist_ok=True)

mcp = FastMCP(
    "qa",
    instructions=(
        "SoloCorp QA department. The head coordinates testing, quality, and "
        "evidence collection. Tools expose test suite status and result recording "
        "without revealing internal QA specialist internals."
    ),
)


def _error(exc: Exception) -> str:
    from ..bus_store import as_json

    return as_json({"status": "error", "error": type(exc).__name__, "message": str(exc)})


@mcp.tool()
def qa_department_info() -> str:
    """Return the head, specialists, scope, and data root for QA."""

    from ..bus_store import as_json

    return as_json(
        {
            "status": "ok",
            "department": "qa",
            "head": {
                "id": "qa-tim",
                "name": "QA-ทีม",
                "role": "Head of QA",
                "profile": "profiles/10-qa/SOUL.md",
            },
            "specialists": [
                {
                    "id": "qa-automation",
                    "name": "ทดสอบอัตโนมัติ",
                    "role": "Test automation, CI/CD integration, regression suites",
                },
                {
                    "id": "qa-evidence",
                    "name": "เก็บหลักฐาน",
                    "role": "Quality evidence, bug tracking, test report validation",
                },
                {
                    "id": "qa-performance",
                    "name": "ทดสอบประสิทธิภาพ",
                    "role": "Performance testing, load testing, benchmark validation",
                },
            ],
            "control_rule": "Client ส่งงานผ่านหัวหน้า; specialist เป็น implementation ภายในแผนก",
            "data_root": "central_bus/content/",
        }
    )


@mcp.tool()
def qa_list_test_suites(limit: int = 10) -> str:
    """List recent QA test suites with status summary."""
    from ..bus_store import as_json

    return as_json(
        {
            "status": "ok",
            "department": "qa",
            "test_suites": [
                {
                    "suite_id": "qa-001",
                    "name": "Content MCP Tool Tests",
                    "status": "passed",
                    "owner": "qa-automation",
                },
                {
                    "suite_id": "qa-002",
                    "name": "Module Registry Tests",
                    "status": "pending",
                    "owner": "qa-automation",
                },
                {
                    "suite_id": "qa-003",
                    "name": "Task Tracking Workflow Tests",
                    "status": "passed",
                    "owner": "qa-evidence",
                },
            ][:limit],
            "count": 3,
        }
    )


@mcp.tool()
def qa_record_test_result(suite_id: str, status: str, note: str = "") -> str:
    """Record a test result for a QA suite with real evidence stored to disk."""

    from ..bus_store import as_json

    valid = {"passed", "failed", "skipped", "error"}
    if status not in valid:
        return as_json(
            {
                "status": "error",
                "error": "invalid_status",
                "message": f"status must be one of: {', '.join(sorted(valid))}",
            }
        )

    # Create a linked task record for traceability
    task_record = _task_tracker.create(
        dept="qa",
        module="qa",
        brief=f"QA test result: suite={suite_id} status={status} note={note}",
        task_type="qa_test",
    )
    task_id = task_record["task_id"]
    recorded_at = task_record["created_at"]

    # Persist evidence payload as JSON
    evidence = {
        "schema_version": 1,
        "task_id": task_id,
        "department": "qa",
        "suite_id": suite_id,
        "result": status,
        "note": note,
        "recorded_at": recorded_at,
        "recorded_by": "qa MCP tool call",
    }
    payload = json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    filename = f"qa-{suite_id}-{task_id[5:]}.json"
    result_path = QA_RESULTS_ROOT / filename
    result_path.write_text(payload, encoding="utf-8")

    return as_json(
        {
            "status": "ok",
            "department": "qa",
            "task_id": task_id,
            "suite_id": suite_id,
            "result": status,
            "note": note,
            "recorded_at": recorded_at,
            "result_path": str(result_path.relative_to(ROOT)),
            "sha256": digest,
            "evidence": "stored_to_disk",
        }
    )


if __name__ == "__main__":
    mcp.run()
