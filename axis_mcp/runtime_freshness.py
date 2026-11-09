"""Is this running MCP server built from the code currently on disk?

An MCP server loads its modules once at startup. Every edit after that is
invisible to it until the process restarts, so a tool can answer confidently
from code that no longer exists. On 2026-11-02 the qa MCP answered with a
"pending" seed that had already been deleted from `qa_mcp.py` two hours
earlier — nothing in the response said so.

This module answers it in two facts, both of which the process already knows:

* when this process started (the directory /proc/self was created), and
* when any source file under ``axis_mcp/`` was last modified.

If a source file is newer than the process, the process is stale and must be
restarted. No git, no build stamp, no hash to compare — one boolean.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parent

# Filesystem timestamps are coarse; ignore edits within this window of startup
# so a touch during interpreter import does not raise a false alarm.
STARTUP_TOLERANCE_SECONDS = 1.0

# Keep responses small: the newest few offenders are enough to act on.
MAX_REPORTED_SOURCES = 5


def _process_start_epoch() -> float | None:
    """Return the epoch second this process started, or None if unavailable.

    ``/proc/<pid>`` is created at process start, and its mtime is that moment.
    Linux-only; callers get ``unknown`` elsewhere rather than a wrong answer.
    """

    try:
        return Path("/proc/self").stat().st_mtime
    except OSError:
        return None


def _iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def _sources_by_mtime() -> list[tuple[float, Path]]:
    found: list[tuple[float, Path]] = []
    for path in PACKAGE_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            found.append((path.stat().st_mtime, path))
        except OSError:
            continue
    found.sort(key=lambda item: item[0], reverse=True)
    return found


def freshness() -> dict[str, Any]:
    """Report whether this process is running the code that is on disk now."""

    started = _process_start_epoch()
    sources = _sources_by_mtime()
    newest = sources[0][0] if sources else None

    if started is None:
        return {
            "status": "unknown",
            "restart_required": False,
            "reason": "process start time unavailable on this platform",
            "process_started_at": None,
            "newest_source_at": _iso(newest),
            "newer_source_count": 0,
            "newer_sources": [],
        }

    newer = [
        (mtime, path)
        for mtime, path in sources
        if mtime > started + STARTUP_TOLERANCE_SECONDS
    ]

    if newer:
        names = [
            str(path.relative_to(PACKAGE_ROOT.parent))
            for _, path in newer[:MAX_REPORTED_SOURCES]
        ]
        return {
            "status": "stale",
            "restart_required": True,
            "reason": "source files changed after this process started",
            "process_started_at": _iso(started),
            "newest_source_at": _iso(newest),
            "newer_source_count": len(newer),
            "newer_sources": names,
        }

    return {
        "status": "current",
        "restart_required": False,
        "reason": "no source file is newer than this process",
        "process_started_at": _iso(started),
        "newest_source_at": _iso(newest),
        "newer_source_count": 0,
        "newer_sources": [],
    }


def with_freshness(payload: dict[str, Any]) -> dict[str, Any]:
    """Return ``payload`` plus a ``runtime`` block describing staleness."""

    return {**payload, "runtime": freshness()}
