"""Task tracking for SoloCorp department MCPs.

Tracks task lifecycle: created → running → completed/failed + timestamps,
error detail, and artifact references. Stored under Central Bus content
directory as one JSON file per task.

Security notes:
- ``task_id`` is strictly validated (``task-<12 hex chars>``) to prevent
  path traversal through ``../`` sequences.
- ``list_tasks()`` excludes ``brief`` by default to avoid leaking
  potentially sensitive content. Set ``include_brief=True`` only when the
  caller genuinely needs the brief text.
- ``update_status()`` should be gated by ``_check_scope("team")`` at the
  MCP adapter layer (see ``axis_mcp.server``).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
TASKS_ROOT = Path(
    os.environ.get("SOLOCORP_TASKS_ROOT", ROOT / "central_bus" / "content" / "tasks")
)

VALID_STATUSES = {"pending", "running", "completed", "failed", "cancelled"}

# task_id ต้องเป็นรูปแบบ task-<12 hex ตัวอักษร> ป้องกัน path traversal
_TASK_ID_RE = re.compile(r"^task-[a-f0-9]{12}$")


class TaskTracker:
    """Create, read, update task records in Central Bus."""

    def __init__(self, tasks_root: Path | None = None) -> None:
        self.root = tasks_root or TASKS_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def _validate_task_id(self, task_id: str) -> None:
        """ป้องกัน path traversal: ยอมรับเฉพาะ task_id ที่สร้างโดยระบบเท่านั้น."""
        if not isinstance(task_id, str) or not _TASK_ID_RE.fullmatch(task_id):
            raise ValueError(f"invalid task_id: {task_id!r}")

    def _task_path(self, task_id: str) -> Path:
        self._validate_task_id(task_id)
        return self.root / f"{task_id}.json"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create(
        self,
        dept: str,
        module: str,
        brief: str,
        task_type: str = "content",
        *,
        route_reason: str | None = None,
        artifact_refs: list[str] | None = None,
        app_version: str | None = None,
    ) -> dict[str, Any]:
        """Create a new task and return its record."""

        task_id = f"task-{uuid4().hex[:12]}"
        now = self._now()
        artifacts = list(artifact_refs) if artifact_refs is not None else []
        record = {
            "task_id": task_id,
            "dept": dept,
            "module": module,
            "task_type": task_type,
            "status": "pending",
            "brief": brief,
            "route_reason": route_reason,
            "artifact_refs": artifacts,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "result_ref": artifacts[0] if artifacts else None,
            "error": None,
            "error_detail": None,
            "app_version": app_version,
        }
        self._write(task_id, record)
        return record

    def get(self, task_id: str) -> dict[str, Any] | None:
        """Return task record by ID, or None if not found."""

        path = self._task_path(task_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                record = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return None
        return _normalize_record(record)

    def list_tasks(
        self, dept: str | None = None, include_brief: bool = False
    ) -> list[dict[str, Any]]:
        """List all tasks, optionally filtered by department.

        By default ``brief`` is excluded to avoid leaking potentially
        sensitive content in list responses. Set ``include_brief=True``
        only when the caller genuinely needs the brief text.
        """

        results: list[dict[str, Any]] = []
        for path in self.root.glob("task-*.json"):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    record = json.load(handle)
            except (json.JSONDecodeError, OSError):
                continue
            if dept is not None and record.get("dept") != dept:
                continue
            record = _normalize_record(record)
            if not include_brief:
                record = {k: v for k, v in record.items() if k != "brief"}
            results.append(record)
        results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return results

    def update_status(
        self,
        task_id: str,
        status: str,
        result_ref: str | None = None,
        error_detail: str | dict[str, Any] | None = None,
        *,
        artifact_refs: list[str] | None = None,
        error: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Update task status and optional result/error."""

        if status not in VALID_STATUSES:
            raise ValueError(
                f"status must be one of: {', '.join(sorted(VALID_STATUSES))}"
            )

        path = self._task_path(task_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                record = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return None
        if not isinstance(record, dict):
            return None

        now = self._now()
        if status == "running" and record.get("started_at") is None:
            record["started_at"] = now
        if status in {"completed", "failed", "cancelled"}:
            record["completed_at"] = now

        record["status"] = status
        if artifact_refs is not None:
            record["artifact_refs"] = list(artifact_refs)
            if artifact_refs:
                record["result_ref"] = artifact_refs[0]
            elif result_ref is None:
                record["result_ref"] = None
        if result_ref is not None:
            record["result_ref"] = result_ref
            if artifact_refs is None:
                record["artifact_refs"] = [result_ref] if result_ref else []
        if error is not None:
            record["error"] = error
            record["error_detail"] = (
                error.get("message") if isinstance(error, dict) else str(error)
            )
        elif error_detail is not None:
            if isinstance(error_detail, dict):
                record["error"] = error_detail
                record["error_detail"] = error_detail.get("message")
            else:
                record["error_detail"] = error_detail
                record["error"] = {
                    "code": "UNKNOWN",
                    "message": error_detail,
                    "hint": "ดู task นี้ใน tasks.html แล้วรัน brief ใหม่อีกครั้ง",
                }

        self._write(task_id, record)
        return _normalize_record(record)

    def _write(self, task_id: str, record: dict[str, Any]) -> None:
        path = self._task_path(task_id)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2)


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize a task record for readers without touching disk.

    Backward compat (PRD §2.3 migration, additive only):
    - old files with only ``result_ref`` get ``artifact_refs=[result_ref]``;
    - old files with only string ``error_detail`` get
      ``error={"code":"UNKNOWN",...}``;
    - new files keep ``result_ref == artifact_refs[0]`` and
      ``error_detail == error.message`` mirrors.
    """

    if not isinstance(record, dict):
        return record
    normalized = dict(record)
    artifacts = normalized.get("artifact_refs")
    if not isinstance(artifacts, list):
        result_ref = normalized.get("result_ref")
        normalized["artifact_refs"] = [result_ref] if result_ref else []
    if "route_reason" not in normalized:
        normalized["route_reason"] = None
    if "app_version" not in normalized:
        normalized["app_version"] = None
    if "error" not in normalized:
        normalized["error"] = None
    error = normalized.get("error")
    error_detail = normalized.get("error_detail")
    if error is None and isinstance(error_detail, str) and error_detail:
        normalized["error"] = {
            "code": "UNKNOWN",
            "message": error_detail,
            "hint": "ดู task นี้ใน tasks.html แล้วรัน brief ใหม่อีกครั้ง",
        }
    elif error is None and isinstance(error_detail, dict):
        normalized["error"] = error_detail
    elif isinstance(error, dict) and error_detail is None:
        normalized["error_detail"] = error.get("message")
    return normalized
