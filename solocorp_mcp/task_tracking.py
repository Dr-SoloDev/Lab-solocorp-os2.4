"""Task tracking for SoloCorp department MCPs.

Tracks task lifecycle: created → running → completed/failed + timestamps,
error detail, and artifact references. Stored under Central Bus content
directory as one JSON file per task.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
TASKS_ROOT = Path(os.environ.get("SOLOCORP_TASKS_ROOT", ROOT / "central_bus" / "content" / "tasks"))

VALID_STATUSES = {"pending", "running", "completed", "failed", "cancelled"}


class TaskTracker:
    """Create, read, update task records in Central Bus."""

    def __init__(self, tasks_root: Path | None = None) -> None:
        self.root = tasks_root or TASKS_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def _task_path(self, task_id: str) -> Path:
        return self.root / f"{task_id}.json"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create(
        self,
        dept: str,
        module: str,
        brief: str,
        task_type: str = "content",
    ) -> dict[str, Any]:
        """Create a new task and return its record."""

        task_id = f"task-{uuid4().hex[:12]}"
        now = self._now()
        record = {
            "task_id": task_id,
            "dept": dept,
            "module": module,
            "task_type": task_type,
            "status": "pending",
            "brief": brief,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "result_ref": None,
            "error_detail": None,
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
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return None

    def list_tasks(self, dept: str | None = None) -> list[dict[str, Any]]:
        """List all tasks, optionally filtered by department."""

        results: list[dict[str, Any]] = []
        for path in self.root.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    record = json.load(handle)
                if dept is None or record.get("dept") == dept:
                    results.append(record)
            except (json.JSONDecodeError, OSError):
                continue
        results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return results

    def update_status(
        self,
        task_id: str,
        status: str,
        result_ref: str | None = None,
        error_detail: str | None = None,
    ) -> dict[str, Any] | None:
        """Update task status and optional result/error."""

        if status not in VALID_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")

        record = self.get(task_id)
        if record is None:
            return None

        now = self._now()
        if status == "running" and record.get("started_at") is None:
            record["started_at"] = now
        if status in {"completed", "failed", "cancelled"}:
            record["completed_at"] = now

        record["status"] = status
        if result_ref is not None:
            record["result_ref"] = result_ref
        if error_detail is not None:
            record["error_detail"] = error_detail

        self._write(task_id, record)
        return record

    def _write(self, task_id: str, record: dict[str, Any]) -> None:
        path = self._task_path(task_id)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2)
