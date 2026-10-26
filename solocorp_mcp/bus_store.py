"""Shared, protocol-neutral storage for SoloCorp department payloads.

MCP servers use this module instead of calling one another.  A client can
therefore connect to a single department server and still get a working data
layer, while ``bus_mcp`` exposes the same contract for direct inspection.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BUS_ROOT = Path(os.environ.get("SOLOCORP_BUS_ROOT", ROOT / "central_bus"))
MAX_PAYLOAD_BYTES = 2 * 1024 * 1024
_COMPONENT_RE = re.compile(r"^[\w-]{1,64}$", re.UNICODE)
_EXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,15}$")


class BusStoreError(ValueError):
    """A user-correctable bus storage request error."""


def _validate_component(value: str, label: str) -> str:
    value = str(value or "").strip()
    if not _COMPONENT_RE.fullmatch(value):
        raise BusStoreError(
            f"{label} must contain only letters, numbers, '_' or '-' and be 1-64 characters"
        )
    return value


def _validate_extension(value: str) -> str:
    value = str(value or "").strip().lstrip(".").lower()
    if not _EXT_RE.fullmatch(value):
        raise BusStoreError("file_type must be a safe extension of 1-16 characters")
    return value


def _department_dir(dept: str) -> Path:
    name = _validate_component(dept, "dept")
    root = BUS_ROOT.resolve()
    directory = (root / name).resolve()
    if not directory.is_relative_to(root):
        raise BusStoreError("department path escapes the bus root")
    return directory


def _safe_filename(filename: str) -> str:
    filename = str(filename or "").strip()
    if not filename or Path(filename).name != filename or filename in {".", ".."}:
        raise BusStoreError("filename must be a single safe file name")
    if any(ord(ch) < 32 for ch in filename):
        raise BusStoreError("filename contains a control character")
    return filename


def _relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        # Tests and isolated deployments may point SOLOCORP_BUS_ROOT outside
        # the repository. Keep the manifest portable without exposing a host
        # path by making it relative to that configured bus root.
        return resolved.relative_to(BUS_ROOT.resolve()).as_posix()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def submit_to_bus(
    dept: str,
    task_id: str,
    payload_content: str,
    file_type: str = "md",
) -> dict[str, Any]:
    """Atomically write a payload and return a compact artifact manifest."""

    directory = _department_dir(dept)
    task = _validate_component(task_id, "task_id")
    extension = _validate_extension(file_type)
    if not isinstance(payload_content, str):
        raise BusStoreError("payload_content must be text")
    encoded = payload_content.encode("utf-8")
    if len(encoded) > MAX_PAYLOAD_BYTES:
        raise BusStoreError(f"payload exceeds {MAX_PAYLOAD_BYTES} bytes")

    created = _now()
    filename = f"{task}_{created.strftime('%Y%m%dT%H%M%S%fZ')}.{extension}"
    directory.mkdir(parents=True, exist_ok=True)
    destination = (directory / filename).resolve()
    if not destination.is_relative_to(directory.resolve()):
        raise BusStoreError("destination escapes the department bus")

    # NamedTemporaryFile in the same directory makes replace() atomic on the
    # same filesystem and avoids partially-written artifacts being listed.
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=directory, prefix=f".{filename}.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(destination)

    return {
        "status": "submitted",
        "dept": str(dept),
        "task_id": task,
        "filename": filename,
        "path": _relative(destination),
        "bytes": len(encoded),
        "created_at": created.isoformat(),
    }


def fetch_from_bus(dept: str, filename: str) -> dict[str, Any]:
    """Read one payload after enforcing department and filename boundaries."""

    directory = _department_dir(dept)
    safe_name = _safe_filename(filename)
    path = (directory / safe_name).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise BusStoreError("file path escapes the department bus")
    if not path.is_file():
        raise FileNotFoundError(f"artifact not found: {dept}/{safe_name}")
    size = path.stat().st_size
    if size > MAX_PAYLOAD_BYTES:
        raise BusStoreError(f"artifact exceeds {MAX_PAYLOAD_BYTES} bytes")
    content = path.read_text(encoding="utf-8")
    return {
        "status": "fetched",
        "dept": str(dept),
        "filename": safe_name,
        "path": _relative(path),
        "bytes": size,
        "content": content,
    }


def list_department_bus(dept: str) -> dict[str, Any]:
    """List regular files in one department's bus directory."""

    directory = _department_dir(dept)
    if not directory.exists():
        return {"status": "ok", "dept": str(dept), "count": 0, "files": []}
    files = [p for p in directory.iterdir() if p.is_file() and not p.name.startswith(".")]
    files.sort(key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
    return {
        "status": "ok",
        "dept": str(dept),
        "count": len(files),
        "files": [
            {
                "filename": p.name,
                "path": _relative(p),
                "bytes": p.stat().st_size,
                "modified_at": datetime.fromtimestamp(
                    p.stat().st_mtime, timezone.utc
                ).isoformat(),
            }
            for p in files
        ],
    }


def as_json(value: dict[str, Any]) -> str:
    """Stable JSON encoding used by MCP tool adapters."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True)
