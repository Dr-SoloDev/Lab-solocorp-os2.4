"""Staleness detection for long-running MCP servers.

A server that loaded its modules before the last edit keeps answering from
the old code. On 2026-11-02 the qa MCP returned a "pending" seed that no
longer existed in `qa_mcp.py`, and nothing in the response said so. These
tests pin the signal that makes that visible.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from solocorp_mcp import runtime_freshness


@pytest.fixture()
def fake_sources(monkeypatch: pytest.MonkeyPatch):
    """Control the two facts freshness() reads: process start and file mtimes."""

    def configure(started: float | None, source_mtimes: list[float]) -> None:
        monkeypatch.setattr(
            runtime_freshness, "_process_start_epoch", lambda: started
        )
        monkeypatch.setattr(
            runtime_freshness,
            "_sources_by_mtime",
            lambda: sorted(
                [
                    (mtime, runtime_freshness.PACKAGE_ROOT / f"fake_{i}.py")
                    for i, mtime in enumerate(source_mtimes)
                ],
                key=lambda item: item[0],
                reverse=True,
            ),
        )

    return configure


def test_current_when_no_source_is_newer(fake_sources) -> None:
    now = time.time()
    fake_sources(now, [now - 600, now - 60])

    result = runtime_freshness.freshness()

    assert result["status"] == "current"
    assert result["restart_required"] is False
    assert result["newer_source_count"] == 0
    assert result["newer_sources"] == []


def test_stale_when_source_changed_after_start(fake_sources) -> None:
    now = time.time()
    # One file predates the process, one was edited after it started.
    fake_sources(now - 3600, [now - 7200, now])

    result = runtime_freshness.freshness()

    assert result["status"] == "stale"
    assert result["restart_required"] is True
    assert result["newer_source_count"] == 1
    assert result["newer_sources"][0].startswith("solocorp_mcp/")
    assert result["process_started_at"] and result["newest_source_at"]


def test_startup_touch_within_tolerance_is_not_stale(fake_sources) -> None:
    now = time.time()
    fake_sources(now, [now + runtime_freshness.STARTUP_TOLERANCE_SECONDS / 2])

    assert runtime_freshness.freshness()["status"] == "current"


def test_unknown_when_process_start_unavailable(fake_sources) -> None:
    fake_sources(None, [time.time()])

    result = runtime_freshness.freshness()

    assert result["status"] == "unknown"
    assert result["restart_required"] is False
    assert "platform" in result["reason"]


def test_reported_sources_are_capped(fake_sources) -> None:
    now = time.time()
    fake_sources(now - 3600, [now + i for i in range(20)])

    result = runtime_freshness.freshness()

    assert result["newer_source_count"] == 20
    assert len(result["newer_sources"]) == runtime_freshness.MAX_REPORTED_SOURCES


def test_with_freshness_preserves_payload(fake_sources) -> None:
    now = time.time()
    fake_sources(now, [now - 60])

    result = runtime_freshness.with_freshness({"status": "ok", "department": "qa"})

    assert result["department"] == "qa"
    assert result["runtime"]["status"] == "current"


@pytest.mark.parametrize(
    "module_name,info_name",
    [
        ("qa_mcp", "qa_department_info"),
        ("engineering_mcp", "engineering_department_info"),
        ("content_mcp", "content_department_info"),
    ],
)
def test_every_department_info_reports_runtime(module_name: str, info_name: str) -> None:
    """Every department must be able to answer 'are you current?'."""

    module = __import__(f"solocorp_mcp.departments.{module_name}", fromlist=[info_name])
    payload = json.loads(getattr(module, info_name)())

    assert "runtime" in payload
    assert payload["runtime"]["status"] in {"current", "stale", "unknown"}
    assert "restart_required" in payload["runtime"]


def test_real_freshness_on_this_process_is_answerable() -> None:
    """The live signal must resolve on the platform CI runs on."""

    result = runtime_freshness.freshness()

    assert result["status"] in {"current", "stale"}
    assert isinstance(result["restart_required"], bool)
    assert result["newest_source_at"] is not None
