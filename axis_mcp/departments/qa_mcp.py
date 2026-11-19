"""QA department MCP server.

Department boundary for QA. Exposes test suite listing, test result recording,
and QA status summary through the head, keeping specialist implementation
details internal.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..runtime_freshness import freshness
from ..task_tracking import TaskTracker

ROOT = Path(__file__).resolve().parent.parent.parent
_task_tracker = TaskTracker()

# suite_id ต้องเป็นรูปแบบปลอดภัย ป้องกัน path traversal ผ่านชื่อไฟล์
_SUITE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

QA_RESULTS_ROOT = Path(
    os.environ.get(
        "SOLOCORP_QA_RESULTS_ROOT", ROOT / "central_bus" / "content" / "qa_results"
    )
)
QA_RESULTS_ROOT.mkdir(parents=True, exist_ok=True)

mcp = FastMCP(
    "qa",
    instructions=(
        "SoloCorp QA department. The head coordinates testing, quality, and "
        "evidence collection. Tools expose test suite status and result recording "
        "without revealing internal QA specialist internals. "
        "DEPRECATED (Wave 2 CTO flip-default 20261113): primary is now CTO (@cto); "
        "this server is read-only redirect — forward new QA work to CTO, "
        "evidence owner stays QA-ทีม, trace cto-mig-W2-20261112T224226Z."
    ),
)


def _error(exc: Exception) -> str:
    from ..bus_store import as_json

    return as_json(
        {"status": "error", "error": type(exc).__name__, "message": str(exc)}
    )


@mcp.tool()
def qa_department_info() -> str:
    """Return the head, specialists, scope, and data root for QA."""

    from ..bus_store import as_json

    return as_json(
        {
            "status": "ok",
            "department": "qa",
            "runtime": freshness(),
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
            "deprecated": True,
            "primary": "cto",
            "forward_to": "cto (@axis/cto/smoke-test, @cto pipeline; evidence owner stays QA-ทีม)",
            "trace_id": "cto-mig-W2-20261112T224226Z",
            "mode": "read-only redirect (1 release alias @qa preserved)",
        }
    )


@mcp.tool()
def qa_list_test_suites(limit: int = 10) -> str:
    """List recent QA test suites with status summary from stored evidence."""
    from ..bus_store import as_json

    suites: dict[str, dict[str, Any]] = {}
    if QA_RESULTS_ROOT.exists():
        for path in QA_RESULTS_ROOT.glob("qa-*.json"):
            try:
                evidence_bytes = path.read_bytes()
                payload = json.loads(evidence_bytes.decode("utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            except UnicodeError:
                continue
            suite_id = payload.get("suite_id")
            if not suite_id:
                continue
            recorded_at = payload.get("recorded_at", "")
            existing = suites.get(suite_id)
            if existing is None or recorded_at > existing.get("recorded_at", ""):
                suites[suite_id] = {
                    "suite_id": suite_id,
                    "status": payload.get("result", "unknown"),
                    "note": payload.get("note", ""),
                    "recorded_at": recorded_at,
                    "task_id": payload.get("task_id"),
                    "evidence_file": path.name,
                    "sha256": hashlib.sha256(evidence_bytes).hexdigest(),
                }

    test_suites = sorted(
        suites.values(), key=lambda s: s.get("recorded_at", ""), reverse=True
    )[:limit]

    return as_json(
        {
            "status": "ok",
            "department": "qa",
            "test_suites": test_suites,
            "count": len(test_suites),
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

    # suite_id ต้องเป็นรูปแบบปลอดภัย ป้องกัน path traversal ผ่านชื่อไฟล์
    if not isinstance(suite_id, str) or not _SUITE_ID_RE.fullmatch(suite_id):
        return as_json(
            {
                "status": "error",
                "error": "invalid_suite_id",
                "message": "suite_id must contain only letters, numbers, '_' or '-' and be 1-64 characters",
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
