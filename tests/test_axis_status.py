"""Deterministic tests for the AXIS unified status layer (C1 / D2).

Every probe is injected: no live network, no busd, no browse, no git mutation.
The only real probe exercised is ``probe_git`` (read-only, always available in
this repo).
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

import pytest

from axis_mcp.status import aggregator, sources


@pytest.fixture(autouse=True)
def _clear_cache():
    aggregator.reset_cache()
    yield
    aggregator.reset_cache()


def make_probe(status="ok", fresh=True, detail=None, warning=None, delay=0.0):
    def probe():
        if delay:
            time.sleep(delay)
        return {
            "status": status,
            "fresh": fresh,
            "detail": dict(detail or {}),
            "warning": warning,
        }

    return probe


def probes_with(**overrides):
    return {
        source_id: overrides.get(source_id, make_probe())
        for source_id in aggregator.SOURCE_IDS
    }


def row(payload, source_id):
    return next(item for item in payload["sources"] if item["id"] == source_id)


def test_schema_and_seven_sources():
    payload = aggregator.aggregate(force=True, probes=probes_with())

    assert payload["schema"] == "axis.status/1"
    assert [item["id"] for item in payload["sources"]] == list(aggregator.SOURCE_IDS)
    assert len(payload["sources"]) == 7
    assert payload["overall"] == {"status": "healthy", "score": 100, "color": "green"}
    assert payload["warnings"] == []
    assert payload["meta"]["cache"] == "fresh"
    assert payload["meta"]["tool_version"] == "1.0.0"
    assert isinstance(payload["meta"]["duration_ms"], int)
    assert datetime.fromisoformat(payload["generated_at"]).utcoffset() is not None

    for item in payload["sources"]:
        assert item["status"] == "ok"
        assert item["fresh"] is True
        assert isinstance(item["latency_ms"], int) and item["latency_ms"] >= 0
        assert isinstance(item["detail"], dict)
        assert item["warning"] is None


def test_weighted_score_uses_contract_weights():
    payload = aggregator.aggregate(
        force=True, probes=probes_with(cto=make_probe("degraded", warning="db slow"))
    )

    # cto carries 20 of 100 weight at half value -> exactly 90.
    assert payload["overall"] == {"status": "healthy", "score": 90, "color": "green"}
    assert row(payload, "cto")["warning"] == "db slow"


def test_unknown_is_excluded_and_renormalized():
    payload = aggregator.aggregate(
        force=True,
        probes=probes_with(codegraph=make_probe("unknown", fresh=False)),
    )

    item = row(payload, "codegraph")
    assert item["status"] == "unknown"
    assert item["fresh"] is False
    assert item["warning"]
    assert any("codegraph" in warning for warning in payload["warnings"])
    # 5 weight removed, the rest still scores 100.
    assert payload["overall"] == {"status": "healthy", "score": 100, "color": "green"}


def test_critical_down_forces_overall_down():
    payload = aggregator.aggregate(
        force=True, probes=probes_with(busd=make_probe("down", fresh=False))
    )

    assert payload["overall"] == {"status": "down", "score": 75, "color": "red"}


def test_non_critical_down_bands():
    degraded = aggregator.aggregate(
        force=True,
        probes=probes_with(
            git=make_probe("down", fresh=False),
            browse=make_probe("down", fresh=False),
            codegraph=make_probe("down", fresh=False),
        ),
    )
    assert degraded["overall"] == {"status": "degraded", "score": 75, "color": "amber"}

    aggregator.reset_cache()
    down = aggregator.aggregate(
        force=True,
        probes=probes_with(
            cto=make_probe("down", fresh=False),
            content=make_probe("down", fresh=False),
        ),
    )
    assert down["overall"] == {"status": "down", "score": 65, "color": "red"}


def test_slow_probe_is_cut_and_partial_result_returned():
    started = time.monotonic()
    payload = aggregator.aggregate(
        force=True, probes=probes_with(browse=make_probe(delay=1.35))
    )
    elapsed = time.monotonic() - started

    item = row(payload, "browse")
    assert item["status"] == "down"
    assert item["fresh"] is False
    assert "timed out" in item["warning"]
    assert len(payload["sources"]) == 7
    assert row(payload, "busd")["status"] == "ok"
    assert elapsed < aggregator.TOTAL_BUDGET_MS / 1000 + 0.3


def test_probes_run_in_parallel():
    started = time.monotonic()
    aggregator.aggregate(
        force=True,
        probes=probes_with(
            cto=make_probe(delay=0.3),
            content=make_probe(delay=0.3),
            git=make_probe(delay=0.3),
        ),
    )
    elapsed = time.monotonic() - started

    assert elapsed < 0.75


def test_cache_hit_and_force_bypass():
    calls = {"count": 0}

    def counting_probe():
        calls["count"] += 1
        return {"status": "ok", "fresh": True, "detail": {}, "warning": None}

    probes = probes_with(busd=counting_probe)

    first = aggregator.aggregate(force=True, probes=probes)
    assert first["meta"]["cache"] == "fresh"
    assert calls["count"] == 1

    second = aggregator.aggregate(probes=probes)
    assert second["meta"]["cache"] == "cached"
    assert calls["count"] == 1
    assert second["generated_at"] == first["generated_at"]

    third = aggregator.aggregate(force=True, probes=probes)
    assert third["meta"]["cache"] == "fresh"
    assert calls["count"] == 2


def test_probe_exception_is_isolated():
    def boom():
        raise RuntimeError("kaboom")

    payload = aggregator.aggregate(force=True, probes=probes_with(cto=boom))

    item = row(payload, "cto")
    assert item["status"] == "down"
    assert "RuntimeError" in item["warning"]
    assert item["detail"] == {"error": "RuntimeError"}
    assert row(payload, "busd")["status"] == "ok"
    assert "Traceback" not in json.dumps(payload)


def test_invalid_probe_status_is_down():
    probes = probes_with(
        git=lambda: {"status": "bogus", "fresh": True, "detail": {}, "warning": None}
    )
    payload = aggregator.aggregate(force=True, probes=probes)
    item = row(payload, "git")

    assert item["status"] == "down"
    assert item["fresh"] is False
    assert "no valid status" in item["warning"]


def test_non_boolean_fresh_is_down():
    probes = probes_with(
        git=lambda: {"status": "ok", "fresh": "false", "detail": {}, "warning": None}
    )
    payload = aggregator.aggregate(force=True, probes=probes)
    item = row(payload, "git")

    assert item["status"] == "down"
    assert item["fresh"] is False
    assert "non-boolean" in item["warning"]
    assert payload["overall"]["score"] == 90


def test_secret_never_appears_in_output(monkeypatch):
    canary = "sk-live-CANARY-0123456789"
    monkeypatch.setenv("SOLOCORP_API_KEY", canary)

    payload = aggregator.aggregate(
        force=True,
        probes=probes_with(
            busd=make_probe(
                "down",
                fresh=False,
                detail={"echo": f"header X-API-Key: {canary}"},
                warning=f"request failed with {canary}",
            )
        ),
    )

    text = json.dumps(payload)
    assert canary not in text
    assert "[redacted]" in text


def test_non_ok_sources_always_carry_warning():
    payload = aggregator.aggregate(
        force=True,
        probes=probes_with(
            busd=make_probe("degraded"),
            cto=make_probe("down", fresh=False),
            content=make_probe("unknown", fresh=False),
        ),
    )

    for item in payload["sources"]:
        if item["status"] == "ok":
            continue
        assert item["warning"]
        assert any(item["id"] in warning for warning in payload["warnings"])


def test_ok_with_stale_data_is_demoted():
    payload = aggregator.aggregate(
        force=True, probes=probes_with(git=make_probe("ok", fresh=False))
    )

    item = row(payload, "git")
    assert item["status"] == "degraded"
    assert item["fresh"] is False
    assert item["warning"]


def test_ok_with_warning_is_demoted():
    payload = aggregator.aggregate(
        force=True, probes=probes_with(git=make_probe("ok", warning="odd but true"))
    )

    item = row(payload, "git")
    assert item["status"] == "degraded"
    assert item["warning"] == "odd but true"
    assert payload["overall"]["score"] == 95


def test_all_unknown_is_not_healthy():
    probes = {
        source_id: make_probe("unknown", fresh=False)
        for source_id in aggregator.SOURCE_IDS
    }
    payload = aggregator.aggregate(force=True, probes=probes)

    assert payload["overall"] == {"status": "down", "score": 0, "color": "red"}
    assert any("not healthy" in warning for warning in payload["warnings"])


def test_freshness_tolerance_matches_runtime_rule():
    assert sources.STARTUP_TOLERANCE_SECONDS == 1.0
    # Stale iff newest mtime > process start + 1 s (runtime_freshness.py).
    assert sources.is_fresh(1000.0, 1001.0) is True
    assert sources.is_fresh(1000.0, 1001.01) is False
    assert sources.is_fresh(1000.0, 900.0) is True
    assert sources.is_fresh(None, 1000.0) is False
    assert sources.is_fresh(1000.0, None) is False


def test_newest_source_survives_relative_to_failure(monkeypatch):
    monkeypatch.setattr(sources, "PROJECT_ROOT", Path("/not-a-parent-of-axis-mcp"))

    mtime, name = sources._newest_source()

    assert mtime is not None
    assert name and "/" not in name


def test_content_process_absent_is_down(monkeypatch):
    monkeypatch.setattr(sources, "_mcp_processes", lambda: [])
    result = sources.probe_content()

    assert result["status"] == "down"
    assert result["fresh"] is False
    assert "not running" in result["warning"]

    payload = aggregator.aggregate(
        force=True, probes=probes_with(content=lambda: result)
    )
    # content carries 15 of 100 weight at zero -> exactly 85, amber.
    assert payload["overall"] == {"status": "degraded", "score": 85, "color": "amber"}


def test_cto_db_unreadable_is_down(tmp_path, monkeypatch):
    db_dir = tmp_path / "central_bus"
    db_dir.mkdir()
    (db_dir / "cto.db").write_text("not a sqlite database", encoding="utf-8")
    monkeypatch.setattr(sources, "PROJECT_ROOT", tmp_path)

    result = sources.probe_cto()
    assert result["status"] == "down"
    assert result["fresh"] is False
    assert result["detail"]["error"] in ("DatabaseError", "OperationalError")

    payload = aggregator.aggregate(force=True, probes=probes_with(cto=lambda: result))
    # cto carries 20 of 100 weight at zero -> exactly 80, amber.
    assert payload["overall"] == {"status": "degraded", "score": 80, "color": "amber"}


def test_cto_schema_drift_is_down(tmp_path, monkeypatch):
    db_dir = tmp_path / "central_bus"
    db_dir.mkdir()
    (db_dir / "cto.db").write_bytes(b"")
    monkeypatch.setattr(sources, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        sources,
        "_mcp_processes",
        lambda: [{"pid": 1, "module": "axis_mcp.cto.server", "started_at": 1.0}],
    )

    result = sources.probe_cto()
    assert result["status"] == "down"
    assert result["fresh"] is False
    assert result["detail"]["missing_tables"] == [
        "build_artifacts",
        "qa_evidence",
        "tool_calls",
    ]
    assert "missing required table" in result["warning"]

    payload = aggregator.aggregate(force=True, probes=probes_with(cto=lambda: result))
    # cto carries 20 of 100 weight at zero -> exactly 80, amber.
    assert payload["overall"] == {"status": "degraded", "score": 80, "color": "amber"}


def test_missing_probe_is_unknown_and_excluded():
    probes = probes_with()
    probes.pop("codegraph")

    payload = aggregator.aggregate(force=True, probes=probes)
    item = row(payload, "codegraph")

    assert item["status"] == "unknown"
    assert item["warning"] and "no probe" in item["warning"]
    # The 5-point weight is excluded and the rest renormalizes to 100.
    assert payload["overall"] == {"status": "healthy", "score": 100, "color": "green"}


def test_critical_unknown_forces_overall_down():
    probes = probes_with()
    probes.pop("busd")

    payload = aggregator.aggregate(force=True, probes=probes)
    item = row(payload, "busd")

    assert item["status"] == "unknown"
    assert item["warning"]
    assert payload["overall"]["status"] == "down"
    assert payload["overall"]["color"] == "red"
    assert any("critical source" in w for w in payload["warnings"])


def test_git_probe_failure_is_down(monkeypatch):
    def boom(*args):
        raise OSError("git missing")

    monkeypatch.setattr(sources, "_git", boom)
    result = sources.probe_git()

    assert result["status"] == "down"
    assert result["fresh"] is False
    assert "git probe failed" in result["warning"]


def test_git_branch_failure_is_down(monkeypatch):
    def fake(*args):
        code, out = 0, ""
        if args[0] == "rev-parse":
            out = "abc1234\n"
        elif args[0] == "branch":
            code = 128
        return subprocess.CompletedProcess(args, code, out, "")

    monkeypatch.setattr(sources, "_git", fake)
    result = sources.probe_git()

    assert result["status"] == "down"
    assert result["fresh"] is False
    assert "branch" in result["warning"]


def test_browse_cli_failure_is_down(monkeypatch):
    def boom(*args, **kwargs):
        raise subprocess.TimeoutExpired("browse", 1)

    monkeypatch.setattr(sources.subprocess, "run", boom)
    monkeypatch.setattr(sources, "_port_open", lambda *args, **kwargs: False)
    result = sources.probe_browse()

    assert result["status"] == "down"
    assert result["fresh"] is False
    assert result["detail"]["cli_error"] == "TimeoutExpired"


def test_codegraph_db_error_is_down(tmp_path, monkeypatch):
    db_path = tmp_path / ".codegraph" / "codegraph.db"
    db_path.parent.mkdir()
    db_path.write_text("not a sqlite database", encoding="utf-8")
    monkeypatch.setattr(sources, "PROJECT_ROOT", tmp_path)

    result = sources.probe_codegraph()

    assert result["status"] == "down"
    assert result["fresh"] is False
    assert result["detail"]["error"] in ("DatabaseError", "OperationalError")


def test_server_exposes_exactly_one_tool():
    from axis_mcp.status import server

    tools = asyncio.run(server.mcp.list_tools())

    assert [tool.name for tool in tools] == ["axis_status"]


def test_git_probe_reads_repo_without_mutating():
    result = sources.probe_git()

    assert result["status"] in ("ok", "degraded")
    assert result["detail"]["head"]
    assert isinstance(result["detail"]["dirty_count"], int)
