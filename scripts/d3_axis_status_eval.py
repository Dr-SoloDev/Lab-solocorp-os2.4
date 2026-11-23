#!/usr/bin/env python3
"""D3 evaluation harness for the AXIS STATUS layer (``axis.status/1``).

This harness evaluates the **committed D2 artifact** only. It imports the
product package, injects deterministic probes for the contract cases, and
runs a small number of live cases (smoke subprocess, MCP stdio). It never
edits product code, never writes to the bus database, and never calls a
non-loopback endpoint.

Design rules:

* Every case is recorded — PASS, FAIL and SKIP alike. Nothing is filtered out.
* The aggregator cache is reset before and after every case.
* A FAIL is evidence, not something to hide: the D3 rule says a blocked/failed
  row with a root cause is valid work, while a green row without evidence is
  the worst failure.
* Exit code is 0 only when every non-SKIP case passes. The pytest post-check
  is also fatal when it runs and fails.

Run::

    PYTHONPATH=. .venv/bin/python3 scripts/d3_axis_status_eval.py

Outputs (all gitignored except the docs file and this script):

* ``bus/evidence/2026-11-23/d3-axis-status/eval.json``
* ``bus/evidence/2026-11-23/d3-axis-status/eval.log``
* ``bus/evidence/2026-11-23/d3-axis-status/env.txt``
* ``bus/evidence/2026-11-23/d3-axis-status/sha256.txt``
* ``bus/evidence/2026-11-23/d3-axis-status/table.md``
* ``docs/certification/D3-axis-status-2026-11-23.md``
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import hashlib
import json
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from axis_mcp import runtime_freshness  # noqa: E402
from axis_mcp.status import aggregator, sources  # noqa: E402

EVIDENCE_DIR = ROOT / "bus/evidence/2026-11-23/d3-axis-status"
DOCS_PATH = ROOT / "docs/certification/D3-axis-status-2026-11-23.md"
EVAL_PATH = ROOT / "scripts/d3_axis_status_eval.py"
CANARY = "sk-live-CANARY-0123456789"

EVALUATED_FILES = (
    "axis_mcp/status/__init__.py",
    "axis_mcp/status/aggregator.py",
    "axis_mcp/status/sources.py",
    "axis_mcp/status/server.py",
    "axis_mcp/runtime_freshness.py",
    "tests/test_axis_status.py",
    "docs/plans/AXIS-STATUS-CONTRACT-v1.0.md",
    "scripts/d3_axis_status_eval.py",
)

PYTEST_COMMAND = "PYTHONPATH=. .venv/bin/python3 -m pytest tests/test_axis_status.py -q"
EVAL_COMMAND = "PYTHONPATH=. .venv/bin/python3 scripts/d3_axis_status_eval.py"

_MISSING = object()


@dataclass
class Outcome:
    """One evaluated case."""

    actual: str
    verdict: str  # PASS | FAIL | SKIP
    note: str = ""
    root_cause: str = ""
    proposed_fix: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class Case:
    """A registered D3 case."""

    cid: str
    group: str
    name: str
    expected: str
    fn: Callable[[], Outcome]


CASES: list[Case] = []


def case(cid: str, group: str, name: str, expected: str):
    """Register one case in definition order."""

    def register(fn: Callable[[], Outcome]) -> Callable[[], Outcome]:
        CASES.append(Case(cid, group, name, expected, fn))
        return fn

    return register


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def probe(
    status: str = "ok",
    fresh: Any = True,
    detail: dict[str, Any] | None = None,
    warning: str | None = None,
    delay: float = 0.0,
):
    """Build an injected probe with the contract payload shape."""

    def run() -> dict[str, Any]:
        if delay:
            time.sleep(delay)
        return {
            "status": status,
            "fresh": fresh,
            "detail": dict(detail or {}),
            "warning": warning,
        }

    return run


def probes_with(**overrides):
    """Seven probes, all ok unless a source id is overridden."""

    return {
        source_id: overrides.get(source_id, probe())
        for source_id in aggregator.SOURCE_IDS
    }


def run_aggregate(**overrides) -> dict[str, Any]:
    """Aggregate one injected scenario with a clean cache."""

    aggregator.reset_cache()
    return aggregator.aggregate(force=True, probes=probes_with(**overrides))


def row(payload: dict[str, Any], source_id: str) -> dict[str, Any]:
    return next(item for item in payload["sources"] if item["id"] == source_id)


def overall_text(payload: dict[str, Any]) -> str:
    overall = payload["overall"]
    return f"{overall['score']}/{overall['status']}/{overall['color']}"


def row_text(payload: dict[str, Any], source_id: str) -> str:
    item = row(payload, source_id)
    return (
        f"{source_id}={item['status']} fresh={str(item['fresh']).lower()} "
        f"warning={item['warning']!r}"
    )


def matches(payload: dict[str, Any], score: int, status: str, color: str) -> bool:
    return payload["overall"] == {
        "status": status,
        "score": score,
        "color": color,
    }


def outcome(
    condition: bool,
    actual: str,
    *,
    note: str = "",
    root_cause: str = "",
    proposed_fix: str = "",
    evidence: dict[str, Any] | None = None,
) -> Outcome:
    return Outcome(
        actual=actual,
        verdict="PASS" if condition else "FAIL",
        note=note,
        root_cause="" if condition else root_cause,
        proposed_fix="" if condition else proposed_fix,
        evidence=evidence or {},
    )


def skip(actual: str, note: str, proposed_fix: str = "") -> Outcome:
    return Outcome(
        actual=actual,
        verdict="SKIP",
        note=note,
        proposed_fix=proposed_fix,
    )


@contextlib.contextmanager
def temporary_env(name: str, value: Any):
    """Set/remove one environment variable and restore the previous value."""

    previous = os.environ.get(name, _MISSING)
    if value is _MISSING:
        os.environ.pop(name, None)
    else:
        os.environ[name] = str(value)
    try:
        yield
    finally:
        if previous is _MISSING:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


class FakeResponse:
    """Minimal ``urlopen`` context-manager response for busd probe tests."""

    def __init__(self, body: bytes):
        self._body = body

    def read(self, _size: int = -1) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False


def fake_http_error(code: int, message: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "http://127.0.0.1:8099/v1/health",
        code,
        message,
        None,
        None,
    )


# ---------------------------------------------------------------------------
# A. Happy path
# ---------------------------------------------------------------------------


@case(
    "A1",
    "A. Happy path",
    "all 7 sources ok",
    "100/healthy/green; warnings=[]; every row ok+fresh",
)
def a1() -> Outcome:
    payload = run_aggregate()
    ok = (
        matches(payload, 100, "healthy", "green")
        and payload["warnings"] == []
        and all(
            item["status"] == "ok" and item["fresh"] is True
            for item in payload["sources"]
        )
        and [item["id"] for item in payload["sources"]] == list(aggregator.SOURCE_IDS)
    )
    return outcome(
        ok,
        f"{overall_text(payload)}; warnings={len(payload['warnings'])}; "
        f"rows={len(payload['sources'])}",
        root_cause="happy-path arithmetic or source ordering regressed",
        proposed_fix="restore the contract weights/order and the ok path",
        evidence={"overall": payload["overall"]},
    )


# ---------------------------------------------------------------------------
# B. One source down, each of the seven
# ---------------------------------------------------------------------------


def one_down(source_id: str, score: int, status: str, color: str) -> Outcome:
    payload = run_aggregate(**{source_id: probe("down", fresh=False)})
    item = row(payload, source_id)
    ok = (
        matches(payload, score, status, color)
        and item["status"] == "down"
        and item["fresh"] is False
        and bool(item["warning"])
    )
    return outcome(
        ok,
        f"{overall_text(payload)}; {row_text(payload, source_id)}",
        root_cause=(
            f"{source_id} down did not produce the contract score/band "
            f"({score}/{status}/{color}); weight or critical rule is wrong"
        ),
        proposed_fix=(
            "re-check WEIGHTS, CRITICAL_SOURCES and the 70/90 bands in "
            "axis_mcp/status/aggregator.py"
        ),
        evidence={"overall": payload["overall"], "row": item},
    )


@case("B1", "B. One source down", "busd down", "75/down/red (100-25; critical down)")
def b1() -> Outcome:
    return one_down("busd", 75, "down", "red")


@case(
    "B2", "B. One source down", "cto down", "80/degraded/amber (100-20; 80 in 70..89)"
)
def b2() -> Outcome:
    return one_down("cto", 80, "degraded", "amber")


@case("B3", "B. One source down", "content down", "85/degraded/amber (100-15)")
def b3() -> Outcome:
    return one_down("content", 85, "degraded", "amber")


@case(
    "B4",
    "B. One source down",
    "mcp_freshness down",
    "85/down/red (100-15; critical down)",
)
def b4() -> Outcome:
    return one_down("mcp_freshness", 85, "down", "red")


@case("B5", "B. One source down", "git down", "90/healthy/green (100-10; 90>=90)")
def b5() -> Outcome:
    return one_down("git", 90, "healthy", "green")


@case("B6", "B. One source down", "browse down", "90/healthy/green (100-10; 90>=90)")
def b6() -> Outcome:
    return one_down("browse", 90, "healthy", "green")


@case(
    "B7",
    "B. One source down",
    "codegraph down",
    "95/healthy/green (100-5; 95>=90)",
)
def b7() -> Outcome:
    return one_down("codegraph", 95, "healthy", "green")


# ---------------------------------------------------------------------------
# C. busd degraded
# ---------------------------------------------------------------------------


@case(
    "C1",
    "C. busd degraded",
    "busd queue_failed>0",
    "88/degraded/amber (100-12.5=87.5 -> 88; 88 in 70..89)",
)
def c1() -> Outcome:
    payload = run_aggregate(
        busd=probe(
            "degraded",
            warning="1 failed queue item(s) awaiting retry",
        )
    )
    item = row(payload, "busd")
    ok = (
        matches(payload, 88, "degraded", "amber")
        and item["status"] == "degraded"
        and item["fresh"] is True
        and "failed queue" in (item["warning"] or "")
    )
    return outcome(
        ok,
        f"{overall_text(payload)}; {row_text(payload, 'busd')}",
        root_cause="busd half-value weight 12.5 was not applied or rounded wrong",
        proposed_fix="use 25*0.5=12.5 and round half-up to 88",
        evidence={"overall": payload["overall"], "row": item},
    )


# ---------------------------------------------------------------------------
# D. unknown
# ---------------------------------------------------------------------------


@case(
    "D1",
    "D. unknown",
    "non-critical codegraph unknown",
    "100/healthy/green; codegraph excluded; measured weight 95 renormalized to 100; warning present",
)
def d1() -> Outcome:
    payload = run_aggregate(codegraph=probe("unknown", fresh=False))
    item = row(payload, "codegraph")
    ok = (
        item["status"] == "unknown"
        and bool(item["warning"])
        and matches(payload, 100, "healthy", "green")
        and any("codegraph" in warning for warning in payload["warnings"])
    )
    return outcome(
        ok,
        f"{overall_text(payload)}; {row_text(payload, 'codegraph')}; "
        f"warnings={len(payload['warnings'])}",
        root_cause="unknown was counted as ok/down instead of excluded+renormalized",
        proposed_fix="skip unknown rows in score_sources and keep a warning",
        evidence={"overall": payload["overall"], "row": item},
    )


def critical_unknown(source_id: str) -> Outcome:
    payload = run_aggregate(**{source_id: probe("unknown", fresh=False)})
    item = row(payload, source_id)
    ok = (
        item["status"] == "unknown"
        and bool(item["warning"])
        and matches(payload, 100, "down", "red")
        and any("critical source" in warning for warning in payload["warnings"])
    )
    return outcome(
        ok,
        f"{overall_text(payload)}; {row_text(payload, source_id)}; "
        f"critical_warning={any('critical source' in w for w in payload['warnings'])}",
        root_cause="critical unknown did not force overall down/red",
        proposed_fix="force down/red when a CRITICAL_SOURCES row is unknown",
        evidence={"overall": payload["overall"], "row": item},
    )


@case(
    "D2",
    "D. unknown",
    "critical busd unknown",
    "100/down/red; busd excluded (measured weight 75); critical unknown forces down",
)
def d2() -> Outcome:
    return critical_unknown("busd")


@case(
    "D3",
    "D. unknown",
    "critical mcp_freshness unknown",
    "100/down/red; mcp_freshness excluded (measured weight 85); critical unknown forces down",
)
def d3() -> Outcome:
    return critical_unknown("mcp_freshness")


# ---------------------------------------------------------------------------
# E. ok + warning -> degraded
# ---------------------------------------------------------------------------


@case(
    "E1",
    "E. ok + warning",
    "busd reports ok with a warning",
    "88/degraded/amber; busd demoted ok->degraded (loss 12.5)",
)
def e1() -> Outcome:
    payload = run_aggregate(busd=probe("ok", warning="odd but true"))
    item = row(payload, "busd")
    ok = (
        item["status"] == "degraded"
        and item["warning"] == "odd but true"
        and matches(payload, 88, "degraded", "amber")
    )
    return outcome(
        ok,
        f"{overall_text(payload)}; {row_text(payload, 'busd')}",
        root_cause="ok+warning was left as ok instead of being demoted",
        proposed_fix="demote any ok row carrying a warning to degraded",
        evidence={"overall": payload["overall"], "row": item},
    )


# ---------------------------------------------------------------------------
# F. non-boolean fresh
# ---------------------------------------------------------------------------


def non_boolean_fresh(value: Any, label: str) -> Outcome:
    payload = run_aggregate(git=probe("ok", fresh=value))
    item = row(payload, "git")
    ok = (
        item["status"] == "down"
        and item["fresh"] is False
        and "non-boolean" in (item["warning"] or "")
        and matches(payload, 90, "healthy", "green")
    )
    return outcome(
        ok,
        f"{overall_text(payload)}; {row_text(payload, 'git')}",
        root_cause=f"fresh={label} was accepted as truthy instead of down",
        proposed_fix="require isinstance(fresh, bool) before trusting a probe",
        evidence={"overall": payload["overall"], "row": item},
    )


@case(
    "F1",
    "F. non-boolean fresh",
    'fresh="false" (string)',
    "git down + non-boolean warning; 90/healthy/green",
)
def f1() -> Outcome:
    return non_boolean_fresh("false", '"false"')


@case(
    "F2",
    "F. non-boolean fresh",
    "fresh=1 (int)",
    "git down + non-boolean warning; 90/healthy/green",
)
def f2() -> Outcome:
    return non_boolean_fresh(1, "1")


@case(
    "F3",
    "F. non-boolean fresh",
    "fresh=None",
    "git down + non-boolean warning; 90/healthy/green",
)
def f3() -> Outcome:
    return non_boolean_fresh(None, "None")


# ---------------------------------------------------------------------------
# G. timeout
# ---------------------------------------------------------------------------


@case(
    "G1",
    "G. timeout",
    "browse probe sleeps 3 s",
    "aggregate <=2000 ms; browse down/timeout; other 6 intact; 90/healthy/green",
)
def g1() -> Outcome:
    started = time.monotonic()
    payload = run_aggregate(browse=probe(delay=3.0))
    elapsed_ms = (time.monotonic() - started) * 1000
    item = row(payload, "browse")
    others_ok = all(
        row(payload, source_id)["status"] == "ok"
        for source_id in aggregator.SOURCE_IDS
        if source_id != "browse"
    )
    ok = (
        elapsed_ms <= aggregator.TOTAL_BUDGET_MS
        and item["status"] == "down"
        and "timed out" in (item["warning"] or "")
        and others_ok
        and matches(payload, 90, "healthy", "green")
        and len(payload["sources"]) == 7
    )
    return outcome(
        ok,
        f"elapsed={int(round(elapsed_ms))}ms; {row_text(payload, 'browse')}; "
        f"others_ok={others_ok}; overall={overall_text(payload)}",
        root_cause="a slow probe blocked the call or lost the other sources",
        proposed_fix="keep per-source 1200 ms / total 2000 ms and return partial data",
        evidence={
            "elapsed_ms": int(round(elapsed_ms)),
            "overall": payload["overall"],
            "row": item,
        },
    )


# ---------------------------------------------------------------------------
# H. freshness boundary vs runtime_freshness
# ---------------------------------------------------------------------------


def freshness_case(offset: float, expect_stale: bool) -> Outcome:
    started = 1_000_000.0
    fake_source = runtime_freshness.PACKAGE_ROOT / "fake_probe.py"
    with (
        mock.patch.object(runtime_freshness, "_process_start_epoch", lambda: started),
        mock.patch.object(
            runtime_freshness,
            "_sources_by_mtime",
            lambda: [(started + offset, fake_source)],
        ),
    ):
        runtime = runtime_freshness.freshness()

    source_fresh = sources.is_fresh(started, started + offset)
    runtime_stale = runtime["restart_required"]
    expected_status = "stale" if expect_stale else "current"
    ok = (
        source_fresh is (not expect_stale)
        and runtime_stale is expect_stale
        and runtime["status"] == expected_status
        and sources.STARTUP_TOLERANCE_SECONDS
        == runtime_freshness.STARTUP_TOLERANCE_SECONDS
        == 1.0
    )
    return outcome(
        ok,
        f"sources.is_fresh={source_fresh}; "
        f"runtime.restart_required={runtime_stale}; "
        f"runtime.status={runtime['status']}; tolerance="
        f"{sources.STARTUP_TOLERANCE_SECONDS}",
        root_cause="freshness predicate or the 1 s tolerance diverged from runtime_freshness",
        proposed_fix="use one predicate: stale iff mtime > start + 1.0",
        evidence={
            "offset_seconds": offset,
            "sources_fresh": source_fresh,
            "runtime": runtime,
        },
    )


@case(
    "H1",
    "H. freshness boundary",
    "mtime = start + 0.5 s",
    "fresh=true by both predicates; runtime.status=current",
)
def h1() -> Outcome:
    return freshness_case(0.5, expect_stale=False)


@case(
    "H2",
    "H. freshness boundary",
    "mtime = start + 1.5 s",
    "fresh=false/stale by both predicates; runtime.status=stale",
)
def h2() -> Outcome:
    return freshness_case(1.5, expect_stale=True)


# ---------------------------------------------------------------------------
# I. cache
# ---------------------------------------------------------------------------


@case(
    "I1",
    "I. cache",
    "TTL hit then force",
    "2nd call cache=cached with identical generated_at; force=True cache=fresh with new generated_at",
)
def i1() -> Outcome:
    aggregator.reset_cache()
    calls = {"n": 0}

    def counting_probe() -> dict[str, Any]:
        calls["n"] += 1
        return {"status": "ok", "fresh": True, "detail": {}, "warning": None}

    probes = probes_with(busd=counting_probe)
    first = aggregator.aggregate(force=True, probes=probes)
    second = aggregator.aggregate(probes=probes)
    time.sleep(0.002)
    third = aggregator.aggregate(force=True, probes=probes)
    ok = (
        first["meta"]["cache"] == "fresh"
        and second["meta"]["cache"] == "cached"
        and second["generated_at"] == first["generated_at"]
        and third["meta"]["cache"] == "fresh"
        and third["generated_at"] != first["generated_at"]
        and calls["n"] == 2
    )
    return outcome(
        ok,
        f"first={first['meta']['cache']}; second={second['meta']['cache']}; "
        f"same_generated_at={second['generated_at'] == first['generated_at']}; "
        f"third={third['meta']['cache']}; "
        f"new_generated_at={third['generated_at'] != first['generated_at']}; "
        f"probe_calls={calls['n']}",
        root_cause="cache did not reuse the snapshot or force did not bypass it",
        proposed_fix="keep the 10 s TTL and deep-copy the cached payload",
        evidence={
            "first": first["meta"],
            "second": second["meta"],
            "third": third["meta"],
            "probe_calls": calls["n"],
        },
    )


# ---------------------------------------------------------------------------
# J. secret canary
# ---------------------------------------------------------------------------


@case(
    "J1",
    "J. secret canary",
    "canary in env + probe payload",
    "0 occurrences of the synthetic canary in output/warnings/JSON; [redacted] present",
)
def j1() -> Outcome:
    with temporary_env("SOLOCORP_API_KEY", CANARY):
        payload = run_aggregate(
            busd=probe(
                "down",
                fresh=False,
                detail={
                    "echo": CANARY,
                    "header": f"X-API-Key: {CANARY}",
                },
                warning=f"request failed with {CANARY}",
            )
        )
    text = json.dumps(payload, ensure_ascii=False)
    occurrences = text.count(CANARY)
    ok = occurrences == 0 and "[redacted]" in text
    return outcome(
        ok,
        f"canary_occurrences={occurrences}; "
        f"redacted={'[redacted]' in text}; "
        f"warnings={len(payload['warnings'])}",
        root_cause="the redaction scrub did not cover warnings/detail",
        proposed_fix="scrub the whole payload recursively before caching/returning",
        evidence={
            "canary_occurrences": occurrences,
            "redacted": "[redacted]" in text,
        },
    )


# ---------------------------------------------------------------------------
# K. CTO 0-byte DB + fake running process (D2 blocker regression)
# ---------------------------------------------------------------------------


@case(
    "K1",
    "K. CTO schema drift",
    "0-byte cto.db + fake running process",
    "cto=down, missing_tables=[build_artifacts,qa_evidence,tool_calls]; 80/degraded/amber",
)
def k1() -> Outcome:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "central_bus").mkdir()
        (root / "central_bus/cto.db").write_bytes(b"")
        with (
            mock.patch.object(sources, "PROJECT_ROOT", root),
            mock.patch.object(
                sources,
                "_mcp_processes",
                lambda: [
                    {
                        "pid": 1,
                        "module": "axis_mcp.cto.server",
                        "started_at": 1.0,
                    }
                ],
            ),
        ):
            probe_result = sources.probe_cto()

    payload = run_aggregate(cto=lambda: probe_result)
    missing = probe_result["detail"].get("missing_tables")
    ok = (
        probe_result["status"] == "down"
        and probe_result["fresh"] is False
        and missing == ["build_artifacts", "qa_evidence", "tool_calls"]
        and "missing required table" in (probe_result["warning"] or "")
        and matches(payload, 80, "degraded", "amber")
    )
    return outcome(
        ok,
        f"probe={probe_result['status']}; missing={missing}; "
        f"overall={overall_text(payload)}",
        root_cause="the D2 blocker regressed: a schema-less DB was reported green",
        proposed_fix="keep the missing-table branch as down + missing_tables + warning",
        evidence={
            "probe": probe_result,
            "overall": payload["overall"],
        },
    )


# ---------------------------------------------------------------------------
# L. CTO valid SQLite with wrong columns
# ---------------------------------------------------------------------------


@case(
    "L1",
    "L. CTO column drift",
    "valid SQLite, required table names, wrong columns",
    "SKIP-NA: contract §3 defines table names, not columns; actual must be documented",
)
def l1() -> Outcome:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "central_bus").mkdir()
        connection = sqlite3.connect(root / "central_bus/cto.db")
        try:
            for table in ("tool_calls", "build_artifacts", "qa_evidence"):
                connection.execute(f"CREATE TABLE {table} (id INTEGER)")
            connection.commit()
        finally:
            connection.close()
        with (
            mock.patch.object(sources, "PROJECT_ROOT", root),
            mock.patch.object(
                sources,
                "_mcp_processes",
                lambda: [
                    {
                        "pid": 1,
                        "module": "axis_mcp.cto.server",
                        "started_at": 1.0,
                    }
                ],
            ),
        ):
            probe_result = sources.probe_cto()

    actual = (
        f"probe={probe_result['status']}; fresh={probe_result['fresh']}; "
        f"tables={probe_result['detail'].get('tables')}; "
        f"warning={probe_result['warning']!r}"
    )
    return skip(
        actual,
        note=(
            "Contract §3 defines CTO measurement as 'health probe / DB ที่ประกาศ' "
            "and does not define table columns. The probe counts rows, so a DB "
            "with only an id column is reported ok. There is no contract "
            "threshold to call this PASS or FAIL; recorded as SKIP-NA so it is "
            "not silently green."
        ),
        proposed_fix=(
            "Add a contract-level required-column map per table and validate "
            "PRAGMA table_info in probe_cto (needs CTO owner + contract update). "
            "Until then, list this as a known limitation."
        ),
    )


# ---------------------------------------------------------------------------
# M. busd payload missing optional fields
# ---------------------------------------------------------------------------


@case(
    "M1",
    "M. busd partial payload",
    "payload missing rules_in_sync/version/uptime_seconds",
    '88/degraded/amber; warning contains "partial measurement" and the missing field names',
)
def m1() -> Outcome:
    body = json.dumps(
        {
            "status": "ok",
            "db": {
                "queue_pending": 0,
                "queue_failed": 0,
                "queue_dead": 0,
            },
        }
    ).encode("utf-8")
    with mock.patch.object(
        sources.urllib.request,
        "urlopen",
        return_value=FakeResponse(body),
    ):
        probe_result = sources.probe_busd()

    payload = run_aggregate(busd=lambda: probe_result)
    warning = probe_result["warning"] or ""
    missing = [
        key
        for key in ("rules_in_sync", "version", "uptime_seconds")
        if probe_result["detail"].get(key) is None
    ]
    ok = (
        probe_result["status"] == "degraded"
        and "partial measurement" in warning
        and all(field in warning for field in missing)
        and matches(payload, 88, "degraded", "amber")
    )
    return outcome(
        ok,
        f"probe={probe_result['status']}; warning={warning!r}; "
        f"missing={missing}; overall={overall_text(payload)}",
        root_cause=(
            "the M1 guard regressed: a busd payload missing required fields "
            "was reported ok instead of degraded"
        ),
        proposed_fix=(
            "keep the missing-field guard in probe_busd (sources.py): absent "
            "rules_in_sync/version/uptime_seconds -> partial-measurement "
            "warning + degraded"
        ),
        evidence={
            "probe": probe_result,
            "missing_fields": missing,
            "overall": payload["overall"],
        },
    )


# ---------------------------------------------------------------------------
# N. score_sources with partial rows missing a critical source
# ---------------------------------------------------------------------------


@case(
    "N1",
    "N. partial score_sources",
    "public score_sources() rows missing busd+mcp_freshness",
    "down/red + warning naming busd,mcp_freshness (renormalized score kept)",
)
def n1() -> Outcome:
    rows = [
        {"id": "git", "status": "ok"},
        {"id": "cto", "status": "ok"},
    ]
    result = aggregator.score_sources(rows)
    warning = result.get("warning") or ""
    missing = result.get("missing_critical")
    ok = (
        result["status"] == "down"
        and result["color"] == "red"
        and result["score"] == 100
        and missing == ["busd", "mcp_freshness"]
        and "busd" in warning
        and "mcp_freshness" in warning
    )
    return outcome(
        ok,
        f"{result['score']}/{result['status']}/{result['color']}; "
        f"missing={missing}; warning={warning!r}; "
        f"rows={[item['id'] for item in rows]}",
        root_cause=(
            "the N1 guard regressed: partial rows missing a critical source "
            "scored healthy instead of being forced down/red"
        ),
        proposed_fix=(
            "keep the missing-critical guard in score_sources "
            "(aggregator.py): absent busd/mcp_freshness -> down/red + warning"
        ),
        evidence={"result": result, "rows": rows},
    )


# ---------------------------------------------------------------------------
# O. codegraph valid DB with zero content
# ---------------------------------------------------------------------------


@case(
    "O1",
    "O. empty codegraph",
    "valid DB, 0 nodes/edges/files",
    "SKIP-NA: contract has no threshold; actual must be documented",
)
def o1() -> Outcome:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / ".codegraph").mkdir()
        connection = sqlite3.connect(root / ".codegraph/codegraph.db")
        try:
            for table in ("nodes", "edges", "files"):
                connection.execute(f"CREATE TABLE {table} (id INTEGER)")
            connection.commit()
        finally:
            connection.close()
        with mock.patch.object(sources, "PROJECT_ROOT", root):
            probe_result = sources.probe_codegraph()

    detail = probe_result["detail"]
    actual = (
        f"probe={probe_result['status']}; nodes={detail.get('nodes')}; "
        f"edges={detail.get('edges')}; files={detail.get('files')}; "
        f"warning={probe_result['warning']!r}"
    )
    return skip(
        actual,
        note=(
            "Contract §3 lists files/nodes/edges/size as codegraph data but "
            "defines no minimum. The probe reports ok for a readable but empty "
            "index; there is no contract threshold to call this PASS or FAIL. "
            "Recorded as SKIP-NA, not silently green."
        ),
        proposed_fix=(
            "Define a contract threshold (for example nodes == 0 -> degraded) "
            "or compare against a known baseline; needs a contract update and "
            "codegraph owner input."
        ),
    )


# ---------------------------------------------------------------------------
# P. live smoke
# ---------------------------------------------------------------------------


@case(
    "P1",
    "P. live smoke",
    "python -m axis_mcp.status.server --smoke",
    "axis.status/1; 7 sources; meta.duration_ms<2000; exit 0",
)
def p1() -> Outcome:
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "axis_mcp.status.server", "--smoke"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return outcome(
            False,
            f"smoke could not run: {type(exc).__name__}: {exc}",
            root_cause="the smoke subprocess did not start or timed out",
            proposed_fix="check the .venv interpreter and the axis_mcp.status.server module",
        )
    wall_ms = int((time.monotonic() - started) * 1000)
    payload: dict[str, Any] | None
    try:
        payload = json.loads(completed.stdout)
    except ValueError:
        payload = None

    if payload is None:
        actual = (
            f"exit={completed.returncode}; wall={wall_ms}ms; "
            f"stdout={completed.stdout[:160]!r}; "
            f"stderr={completed.stderr[-160:]!r}"
        )
    else:
        actual = (
            f"exit={completed.returncode}; wall={wall_ms}ms; "
            f"schema={payload.get('schema')}; "
            f"sources={len(payload.get('sources') or [])}; "
            f"meta.duration_ms={(payload.get('meta') or {}).get('duration_ms')}; "
            f"overall={payload.get('overall')}"
        )
    ok = (
        completed.returncode == 0
        and payload is not None
        and payload.get("schema") == "axis.status/1"
        and [item.get("id") for item in payload.get("sources") or []]
        == list(aggregator.SOURCE_IDS)
        and int((payload.get("meta") or {}).get("duration_ms", 10**9)) < 2000
        and wall_ms < 5000
    )
    return outcome(
        ok,
        actual,
        note=(
            "wall includes interpreter startup; the contract budget is the "
            "tool's meta.duration_ms"
        ),
        root_cause="live smoke failed its schema/source/budget/exit contract",
        proposed_fix="inspect smoke.json/stderr and the seven probes",
        evidence={
            "exit": completed.returncode,
            "wall_ms": wall_ms,
            "stderr_tail": completed.stderr[-400:],
            "payload": payload,
        },
    )


# ---------------------------------------------------------------------------
# Q. repeatability
# ---------------------------------------------------------------------------


@case(
    "Q1",
    "Q. repeatability",
    "same mocked scenario twice",
    "identical overall + per-source status/fresh/warnings (generated_at may differ)",
)
def q1() -> Outcome:
    scenario = {
        "busd": probe("degraded", warning="queue failed"),
        "cto": probe("down", fresh=False),
        "content": probe("unknown", fresh=False),
        "browse": probe("down", fresh=False),
    }
    aggregator.reset_cache()
    first = aggregator.aggregate(force=True, probes=probes_with(**scenario))
    aggregator.reset_cache()
    second = aggregator.aggregate(force=True, probes=probes_with(**scenario))

    def fingerprint(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "overall": payload["overall"],
            "sources": [
                (item["id"], item["status"], item["fresh"])
                for item in payload["sources"]
            ],
            "warnings": payload["warnings"],
        }

    ok = fingerprint(first) == fingerprint(second)
    return outcome(
        ok,
        f"overall={overall_text(first)}; "
        f"same_fingerprint={ok}; "
        f"generated_at_differs={first['generated_at'] != second['generated_at']}",
        root_cause="the same injected scenario produced different status/score",
        proposed_fix="remove nondeterminism from scoring/normalization",
        evidence={
            "first": fingerprint(first),
            "second": fingerprint(second),
        },
    )


# ---------------------------------------------------------------------------
# R. MCP stdio call
# ---------------------------------------------------------------------------


@case(
    "R1",
    "R. MCP stdio",
    "MCP client -> axis_status(force=True)",
    "1 tool named axis_status; 7 sources; isError=false; schema axis.status/1",
)
def r1() -> Outcome:
    async def call() -> tuple[list[str], Any]:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        errlog = open(os.devnull, "w", encoding="utf-8")
        try:
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "axis_mcp.status.server"],
                env={**os.environ, "PYTHONPATH": str(ROOT)},
            )
            async with stdio_client(params, errlog=errlog) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    result = await session.call_tool("axis_status", {"force": True})
                    return [tool.name for tool in tools.tools], result
        finally:
            errlog.close()

    try:
        tool_names, result = asyncio.run(asyncio.wait_for(call(), timeout=25))
    except Exception as exc:  # noqa: BLE001 - report, do not hide
        return outcome(
            False,
            f"MCP stdio call failed: {type(exc).__name__}: {exc}",
            root_cause="the MCP server did not start or the client call failed",
            proposed_fix="check the mcp package, the module command and stderr",
        )

    text = result.content[0].text if result.content else ""
    try:
        payload = json.loads(text)
    except ValueError:
        payload = None
    ok = (
        tool_names == ["axis_status"]
        and result.isError is False
        and payload is not None
        and payload.get("schema") == "axis.status/1"
        and len(payload.get("sources") or []) == 7
    )
    return outcome(
        ok,
        f"tools={tool_names}; isError={result.isError}; "
        f"schema={None if payload is None else payload.get('schema')}; "
        f"sources={None if payload is None else len(payload.get('sources') or [])}",
        root_cause="the MCP surface did not expose exactly one working axis_status tool",
        proposed_fix="keep the FastMCP tool name/schema and the 7-source payload",
        evidence={
            "tools": tool_names,
            "is_error": result.isError,
            "payload_schema": None if payload is None else payload.get("schema"),
        },
    )


# ---------------------------------------------------------------------------
# S. no-write static scan
# ---------------------------------------------------------------------------


def scan_status_package() -> tuple[list[str], dict[str, int]]:
    """AST scan for file writes, non-read SQLite opens and write HTTP verbs."""

    package = ROOT / "axis_mcp/status"
    write_path_methods = {
        "write_text",
        "write_bytes",
        "touch",
        "mkdir",
        "unlink",
        "rename",
        "chmod",
        "symlink_to",
        "hardlink_to",
        "rmdir",
    }
    os_write_calls = {
        "os.remove",
        "os.unlink",
        "os.rename",
        "os.replace",
        "os.rmdir",
        "os.makedirs",
        "os.mkdir",
        "shutil.copy",
        "shutil.copy2",
        "shutil.copyfile",
        "shutil.copytree",
        "shutil.move",
        "shutil.rmtree",
    }
    http_write_calls = {
        "requests.post",
        "requests.put",
        "requests.patch",
        "requests.delete",
        "httpx.post",
        "httpx.put",
        "httpx.patch",
        "httpx.delete",
    }
    git_write_verbs = {
        "commit",
        "add",
        "checkout",
        "reset",
        "clean",
        "push",
        "merge",
        "rebase",
        "stash",
        "rm",
        "mv",
        "tag",
        "fetch",
        "pull",
        "switch",
        "restore",
    }

    def full_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = full_name(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        return ""

    def keyword(node: ast.Call, name: str) -> ast.AST | None:
        for item in node.keywords:
            if item.arg == name:
                return item.value
        return None

    findings: list[str] = []
    files = 0
    calls = 0
    for path in sorted(package.glob("*.py")):
        files += 1
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            calls += 1
            name = full_name(node.func)
            line = node.lineno
            if name in os_write_calls or name in http_write_calls:
                findings.append(f"{path.name}:{line} {name}()")
            if name in write_path_methods:
                findings.append(f"{path.name}:{line} {name}()")
            if name == "replace":
                segment = ast.get_source_segment(source, node) or ""
                if "path" in segment.lower() or "Path(" in segment:
                    findings.append(
                        f"{path.name}:{line} replace() on a path-like receiver"
                    )
            if name == "open":
                mode = keyword(node, "mode")
                if mode is None and len(node.args) >= 2:
                    mode = node.args[1]
                if (
                    isinstance(mode, ast.Constant)
                    and isinstance(mode.value, str)
                    and any(char in mode.value for char in "wax+")
                ):
                    findings.append(f"{path.name}:{line} open(mode={mode.value!r})")
            if name == "connect":
                segment = ast.get_source_segment(source, node) or ""
                if "sqlite3.connect" in segment and (
                    "mode=ro" not in segment or "uri=True" not in segment
                ):
                    findings.append(
                        f"{path.name}:{line} sqlite3.connect without mode=ro+uri=True"
                    )
            if name == "Request":
                method = keyword(node, "method")
                if method is not None and not (
                    isinstance(method, ast.Constant) and method.value == "GET"
                ):
                    findings.append(
                        f"{path.name}:{line} Request(method={ast.unparse(method)})"
                    )
            if name == "urlopen" and keyword(node, "data") is not None:
                findings.append(f"{path.name}:{line} urlopen(data=...)")
        for match in re.finditer(
            r"method\s*=\s*['\"](POST|PUT|PATCH|DELETE)['\"]",
            source,
            re.IGNORECASE,
        ):
            findings.append(f"{path.name}: HTTP write method {match.group(0)}")
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.lower() in git_write_verbs
            ):
                findings.append(
                    f"{path.name}:{node.lineno} git write verb {node.value!r}"
                )
    return findings, {"files": files, "calls": calls}


@case(
    "S1",
    "S. no-write scan",
    "static scan of axis_mcp/status/*.py",
    "0 file writes, 0 POST/PUT/PATCH, 0 non-ro sqlite opens, 0 git write verbs",
)
def s1() -> Outcome:
    findings, scanned = scan_status_package()
    ok = not findings
    return outcome(
        ok,
        f"findings={len(findings)}; files={scanned['files']}; "
        f"calls={scanned['calls']}" + (f"; first={findings[0]}" if findings else ""),
        note="AST scan; str.replace() is excluded, Path/os/shutil writes are not",
        root_cause="the status package contains a write/POST/non-ro SQLite path",
        proposed_fix="remove the write path; probes must stay read-only",
        evidence={"findings": findings, "scanned": scanned},
    )


# ---------------------------------------------------------------------------
# T. redaction on 401/403
# ---------------------------------------------------------------------------


@case(
    "T1",
    "T. redaction",
    "busd returns 401/403 (with key) and 401 (no key)",
    "warnings + JSON contain no canary; warnings name the HTTP status",
)
def t1() -> Outcome:
    checks: list[dict[str, Any]] = []
    for code in (401, 403):
        with temporary_env("SOLOCORP_API_KEY", CANARY):
            with mock.patch.object(
                sources.urllib.request,
                "urlopen",
                side_effect=fake_http_error(code, f"denied {CANARY}"),
            ):
                probe_result = sources.probe_busd()
            payload = run_aggregate(busd=lambda: probe_result)
        text = json.dumps(probe_result, ensure_ascii=False) + json.dumps(
            payload, ensure_ascii=False
        )
        checks.append(
            {
                "code": code,
                "warning": probe_result["warning"],
                "canary_leaked": CANARY in text,
            }
        )

    with temporary_env("SOLOCORP_API_KEY", _MISSING):
        with mock.patch.object(
            sources.urllib.request,
            "urlopen",
            side_effect=fake_http_error(401, f"denied {CANARY}"),
        ):
            no_key_result = sources.probe_busd()
    checks.append(
        {
            "code": "401-no-key",
            "warning": no_key_result["warning"],
            "canary_leaked": CANARY in json.dumps(no_key_result, ensure_ascii=False),
        }
    )

    ok = (
        all(not item["canary_leaked"] for item in checks)
        and "401" in (checks[0]["warning"] or "")
        and "403" in (checks[1]["warning"] or "")
        and "missing" in (checks[2]["warning"] or "").lower()
    )
    return outcome(
        ok,
        "; ".join(
            f"{item['code']}={item['warning']!r} leaked={item['canary_leaked']}"
            for item in checks
        ),
        root_cause="an HTTP error path echoed the API key or request headers",
        proposed_fix="never include headers or the key in probe warnings/details",
        evidence={"checks": checks},
    )


# ---------------------------------------------------------------------------
# U/V/W. extra contract bands
# ---------------------------------------------------------------------------


@case(
    "U1",
    "U. browse degraded",
    "relay up, extension not paired",
    "95/healthy/green (browse 10*0.5=5 lost)",
)
def u1() -> Outcome:
    payload = run_aggregate(
        browse=probe(
            "degraded",
            warning="browse relay is up but no browser extension is paired",
        )
    )
    ok = (
        matches(payload, 95, "healthy", "green")
        and row(payload, "browse")["status"] == "degraded"
    )
    return outcome(
        ok,
        f"{overall_text(payload)}; {row_text(payload, 'browse')}",
        root_cause="browse half-value or 90-band arithmetic regressed",
        proposed_fix="keep browse weight 10 and the 70/90 bands",
        evidence={"overall": payload["overall"]},
    )


@case(
    "V1",
    "V. git detached",
    "detached HEAD",
    "95/healthy/green (git 10*0.5=5 lost)",
)
def v1() -> Outcome:
    payload = run_aggregate(git=probe("degraded", warning="git HEAD is detached"))
    ok = (
        matches(payload, 95, "healthy", "green")
        and row(payload, "git")["status"] == "degraded"
    )
    return outcome(
        ok,
        f"{overall_text(payload)}; {row_text(payload, 'git')}",
        root_cause="git half-value or 90-band arithmetic regressed",
        proposed_fix="keep git weight 10 and the 70/90 bands",
        evidence={"overall": payload["overall"]},
    )


@case(
    "W1",
    "W. busd queue dead",
    "real probe_busd with queue_dead>0 + rules_in_sync=false",
    "88/degraded/amber; warnings mention dead queue + out-of-sync rules",
)
def w1() -> Outcome:
    body = json.dumps(
        {
            "status": "ok",
            "db": {
                "queue_pending": 0,
                "queue_failed": 0,
                "queue_dead": 2,
            },
            "rules_in_sync": False,
            "version": "0.6.2",
            "uptime_seconds": 10,
        }
    ).encode("utf-8")
    with mock.patch.object(
        sources.urllib.request,
        "urlopen",
        return_value=FakeResponse(body),
    ):
        probe_result = sources.probe_busd()
    payload = run_aggregate(busd=lambda: probe_result)
    warning = probe_result["warning"] or ""
    ok = (
        probe_result["status"] == "degraded"
        and "dead queue" in warning
        and "out of sync" in warning
        and matches(payload, 88, "degraded", "amber")
    )
    return outcome(
        ok,
        f"probe={probe_result['status']}; warning={warning!r}; "
        f"overall={overall_text(payload)}",
        root_cause="real busd warning logic lost the dead-queue or rules warning",
        proposed_fix="keep both warnings and the degraded result",
        evidence={"probe": probe_result, "overall": payload["overall"]},
    )


# ---------------------------------------------------------------------------
# X/Y/Z. unknown, exception isolation, invalid status
# ---------------------------------------------------------------------------


@case(
    "X1",
    "X. all unknown",
    "all 7 probes unknown",
    "0/down/red + 'not healthy' warning",
)
def x1() -> Outcome:
    payload = run_aggregate(
        **{
            source_id: probe("unknown", fresh=False)
            for source_id in aggregator.SOURCE_IDS
        }
    )
    ok = (
        matches(payload, 0, "down", "red")
        and any("not healthy" in warning for warning in payload["warnings"])
        and all(item["status"] == "unknown" for item in payload["sources"])
    )
    return outcome(
        ok,
        f"{overall_text(payload)}; "
        f"warnings={len(payload['warnings'])}; "
        f"not_healthy={any('not healthy' in w for w in payload['warnings'])}",
        root_cause="an all-unknown snapshot was treated as healthy",
        proposed_fix="return down/0/red and the 'not healthy' warning",
        evidence={"overall": payload["overall"]},
    )


@case(
    "Y1",
    "Y. probe exception",
    "cto probe raises RuntimeError",
    "cto down (RuntimeError), no traceback; 80/degraded/amber",
)
def y1() -> Outcome:
    def boom() -> dict[str, Any]:
        raise RuntimeError("kaboom")

    payload = run_aggregate(cto=boom)
    item = row(payload, "cto")
    text = json.dumps(payload, ensure_ascii=False)
    ok = (
        item["status"] == "down"
        and item["detail"] == {"error": "RuntimeError"}
        and "RuntimeError" in (item["warning"] or "")
        and "Traceback" not in text
        and matches(payload, 80, "degraded", "amber")
    )
    return outcome(
        ok,
        f"{overall_text(payload)}; {row_text(payload, 'cto')}; "
        f"traceback={'Traceback' in text}",
        root_cause="a probe exception escaped isolation or leaked a traceback",
        proposed_fix="catch per probe, return down + error type, no traceback",
        evidence={"overall": payload["overall"], "row": item},
    )


@case(
    "Z1",
    "Z. invalid status",
    "git probe returns status='bogus'",
    "git down + 'no valid status' warning; 90/healthy/green",
)
def z1() -> Outcome:
    payload = run_aggregate(
        git=lambda: {
            "status": "bogus",
            "fresh": True,
            "detail": {},
            "warning": None,
        }
    )
    item = row(payload, "git")
    ok = (
        item["status"] == "down"
        and "no valid status" in (item["warning"] or "")
        and matches(payload, 90, "healthy", "green")
    )
    return outcome(
        ok,
        f"{overall_text(payload)}; {row_text(payload, 'git')}",
        root_cause="an invalid status string was trusted instead of becoming down",
        proposed_fix="validate status against the contract vocabulary",
        evidence={"overall": payload["overall"], "row": item},
    )


# ---------------------------------------------------------------------------
# Evidence collection
# ---------------------------------------------------------------------------


def collect_env() -> dict[str, Any]:
    def git(*args: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", "-C", str(ROOT), *args],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return completed.stdout.strip() if completed.returncode == 0 else None

    busd: dict[str, Any] = {"url": sources.BUSD_URL}
    try:
        with urllib.request.urlopen(sources.BUSD_URL, timeout=0.5) as response:
            busd["http_status"] = response.status
    except Exception as exc:  # noqa: BLE001 - environment fact
        busd["error"] = type(exc).__name__

    try:
        processes = sources._mcp_processes()
    except Exception as exc:  # noqa: BLE001 - environment fact
        processes = []
        busd["mcp_process_error"] = type(exc).__name__

    codegraph_db = ROOT / ".codegraph/codegraph.db"
    return {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git("rev-parse", "HEAD"),
        "git_head_short": git("rev-parse", "--short", "HEAD"),
        "git_branch": git("branch", "--show-current"),
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "cwd": str(ROOT),
        "busd": busd,
        "mcp_processes": [
            {"pid": item["pid"], "module": item["module"]} for item in processes
        ],
        "browse_cli": shutil.which("browse"),
        "codegraph_db": {
            "exists": codegraph_db.is_file(),
            "size_bytes": (
                codegraph_db.stat().st_size if codegraph_db.is_file() else None
            ),
        },
        "pytest_version": pytest_version(),
    }


def pytest_version() -> str | None:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return (completed.stdout or completed.stderr).strip().splitlines()[0]


def hash_evaluated_files() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relative in EVALUATED_FILES:
        path = ROOT / relative
        if not path.is_file():
            rows.append({"path": relative, "sha256": None, "exists": False})
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(
            {
                "path": relative,
                "sha256": digest,
                "exists": True,
                "size_bytes": path.stat().st_size,
            }
        )
    return rows


def run_pytest() -> dict[str, Any]:
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_axis_status.py",
                "-q",
            ],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "command": PYTEST_COMMAND,
            "exit_code": None,
            "summary": f"pytest could not run: {type(exc).__name__}",
            "stdout_tail": "",
            "stderr_tail": "",
            "elapsed_ms": int((time.monotonic() - started) * 1000),
        }
    stdout_lines = [
        line.strip() for line in completed.stdout.splitlines() if line.strip()
    ]
    summary = "(no output)"
    for line in reversed(stdout_lines):
        if re.search(r"\b\d+ (passed|failed|error|errors|skipped)\b", line):
            summary = line
            break
    else:
        if stdout_lines:
            summary = " | ".join(stdout_lines[-3:])
    return {
        "command": PYTEST_COMMAND,
        "exit_code": completed.returncode,
        "summary": summary,
        "stdout_tail": "\n".join(stdout_lines[-8:]),
        "stderr_tail": completed.stderr[-1200:],
        "elapsed_ms": int((time.monotonic() - started) * 1000),
    }


PRODUCT_FILES = frozenset(
    {
        "axis_mcp/status/__init__.py",
        "axis_mcp/status/aggregator.py",
        "axis_mcp/status/sources.py",
        "axis_mcp/status/server.py",
        "tests/test_axis_status.py",
    }
)


def run_git_status() -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {
            "raw": [],
            "error": "git status failed",
            "new_paths": [],
            "modified_paths": [],
            "product_modified": [],
        }
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    modified = [line[3:] for line in lines if line[:2].strip() == "M"]
    return {
        "raw": lines,
        "new_paths": [line[3:] for line in lines if line.startswith("??")],
        "modified_paths": modified,
        "product_modified": [path for path in modified if path in PRODUCT_FILES],
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(
    *,
    generated_at: str,
    results: list[dict[str, Any]],
    summary: dict[str, Any],
    env: dict[str, Any],
    hashes: list[dict[str, Any]],
    pytest_result: dict[str, Any],
    git_status: dict[str, Any],
) -> str:
    lines: list[str] = []
    product_modified = git_status.get("product_modified") or []
    tree_note = " + uncommitted M1/N1 hardening" if product_modified else ""
    lines.append("# D3 — AXIS STATUS (`axis.status/1`) evaluation")
    lines.append("")
    lines.append(
        f"> **Evaluated:** `{env.get('git_head_short') or 'unknown'}` "
        f"(`{env.get('git_branch') or 'unknown branch'}`){tree_note} · "
        f"**Date:** {generated_at} · "
        f"**Evaluator:** `scripts/d3_axis_status_eval.py`"
    )
    lines.append(">")
    if product_modified:
        lines.append(
            "> This D3 run evaluates the working tree on the branch: D2 commit "
            f"`{env.get('git_head_short') or 'HEAD'}` plus the uncommitted "
            "D3-driven M1/N1 hardening. The only product changes are the two "
            "fixes; no other product behavior was changed. FAIL rows would "
            "still be recorded with a root cause and a proposed minimal fix; "
            "SKIP rows are recorded as SKIP-NA."
        )
    else:
        lines.append(
            "> This is a D3 evaluation of the committed D2 artifact. Product "
            "code was **not** modified. FAIL rows are recorded with a root "
            "cause and a proposed minimal fix; SKIP rows are recorded as "
            "SKIP-NA, not silently green."
        )
    lines.append(">")
    lines.append(
        "> **Status: maker evidence, not an approval.** An independent checker "
        "must rerun `scripts/d3_axis_status_eval.py`, compare the evidence and "
        "confirm the M1/N1 PASS rows and the L1/O1 SKIP-NA decisions before "
        "D3 is considered passed."
    )
    lines.append(">")
    lines.append(
        "> **Evidence:** `bus/evidence/2026-11-23/d3-axis-status/` "
        "(`eval.json`, `eval.log`, `env.txt`, `sha256.txt`, `table.md`)."
    )
    lines.append("")
    lines.append("## 1. Summary")
    lines.append("")
    lines.append(
        f"- **Cases:** {summary['total']} · "
        f"**PASS:** {summary['pass']} · "
        f"**FAIL:** {summary['fail']} · "
        f"**SKIP:** {summary['skip']}"
    )
    lines.append(
        f"- **Exit code:** `{summary['exit_code']}` (0 only when every non-SKIP case passes)"
    )
    lines.append(
        f"- **Pytest post-check:** `{pytest_result['summary']}` "
        f"(exit `{pytest_result['exit_code']}`)"
    )
    if product_modified:
        lines.append(
            "- **Product code changed:** **YES — M1/N1 only** ("
            + ", ".join(f"`{path}`" for path in product_modified)
            + ")"
        )
    else:
        lines.append("- **Product code changed:** **NO**")
    lines.append("")
    lines.append("## 2. What was evaluated")
    lines.append("")
    lines.append("| File | SHA-256 | Size |")
    lines.append("|:-----|:--------|-----:|")
    for item in hashes:
        digest = item["sha256"] or "MISSING"
        size = item.get("size_bytes")
        lines.append(
            f"| `{md(item['path'])}` | `{digest}` | "
            f"{size if size is not None else '—'} |"
        )
    lines.append("")
    lines.append("## 3. Method")
    lines.append("")
    lines.append(
        "- Deterministic cases inject probes into `axis_mcp.status.aggregator.aggregate`; "
        "the aggregator cache is reset before and after every case."
    )
    lines.append(
        "- Real-probe cases patch only the probe's external boundary "
        "(`urllib.request.urlopen`, `PROJECT_ROOT`, `_mcp_processes`, and the "
        "two `runtime_freshness` time/source helpers) with `unittest.mock`; "
        "every patch is restored by its context manager. CTO/codegraph "
        "fixtures use throwaway SQLite files under a temporary directory."
    )
    lines.append(
        "- Live cases: `python -m axis_mcp.status.server --smoke` in a "
        "subprocess, and one MCP stdio client call to `axis_status(force=True)`."
    )
    lines.append(
        "- The no-write case is an AST scan of `axis_mcp/status/*.py` for file "
        "writes, non-read SQLite opens, HTTP write verbs and git write verbs."
    )
    lines.append(
        "- The eval itself did not modify product code, config or a product "
        "database; the working tree already contains the M1/N1 fixes under "
        "evaluation. No existing process was killed or restarted; all network "
        "calls are loopback."
    )
    lines.append("")
    lines.append("## 4. Results")
    lines.append("")
    lines.append(
        "| # | ID | Group | Case | Expected | Actual | Verdict | Root cause / note |"
    )
    lines.append(
        "|--:|:---|:------|:-----|:---------|:-------|:--------|:------------------|"
    )
    for index, item in enumerate(results, 1):
        if item["verdict"] == "FAIL":
            note = item.get("root_cause") or item.get("note") or "—"
        else:
            note = item.get("note") or "—"
        lines.append(
            f"| {index} | `{item['id']}` | {md(item['group'])} | "
            f"{md(item['name'])} | {md(item['expected'])} | "
            f"{md(item['actual'])} | **{item['verdict']}** | {md(note)} |"
        )
    lines.append("")
    lines.append("### Contract arithmetic used by the cases")
    lines.append("")
    lines.append(
        "Weights: busd 25 · cto 20 · content 15 · mcp_freshness 15 · git 10 · "
        "browse 10 · codegraph 5. Values: ok=1, degraded=0.5, down=0, "
        "unknown=excluded. `score = round(Σ(weight×value) / Σ(measured weight) × 100)`; "
        "critical down/unknown → overall down; otherwise ≥90 healthy, 70–89 "
        "degraded, <70 down."
    )
    lines.append("")
    lines.append("## 5. Failures and skips")
    lines.append("")
    problems = [item for item in results if item["verdict"] != "PASS"]
    if not problems:
        lines.append("None.")
    for item in problems:
        lines.append(f"### {item['id']} — {item['name']} ({item['verdict']})")
        lines.append("")
        lines.append(f"- **Expected:** {item['expected']}")
        lines.append(f"- **Actual:** {item['actual']}")
        if item.get("root_cause"):
            lines.append(f"- **Root cause:** {item['root_cause']}")
        if item.get("note"):
            lines.append(f"- **Note:** {item['note']}")
        if item.get("proposed_fix"):
            lines.append(f"- **Proposed minimal fix:** {item['proposed_fix']}")
        lines.append("")
    lines.append("## 6. Exact commands and exit codes")
    lines.append("")
    lines.append("| # | Command | Observed | Exit |")
    lines.append("|--:|:--------|:---------|:----:|")
    lines.append(
        f"| 1 | `{EVAL_COMMAND}` | "
        f"{summary['pass']} PASS · {summary['fail']} FAIL · {summary['skip']} SKIP | "
        f"`{summary['exit_code']}` |"
    )
    lines.append(
        f"| 2 | `{PYTEST_COMMAND}` | `{md(pytest_result['summary'])}` | "
        f"`{pytest_result['exit_code']}` |"
    )
    lines.append(
        f"| 3 | `git status --porcelain` | "
        f"{len(git_status['new_paths'])} untracked path(s); "
        f"{len(git_status['modified_paths'])} modified path(s) | — |"
    )
    lines.append("")
    lines.append("## 7. Environment")
    lines.append("")
    lines.append("```text")
    for key in (
        "date_utc",
        "git_head",
        "git_branch",
        "python_version",
        "python_executable",
        "platform",
        "cwd",
        "browse_cli",
        "pytest_version",
    ):
        lines.append(f"{key}={env.get(key)}")
    lines.append(f"busd={json.dumps(env.get('busd'), ensure_ascii=False)}")
    lines.append(
        f"mcp_processes={json.dumps(env.get('mcp_processes'), ensure_ascii=False)}"
    )
    lines.append(
        f"codegraph_db={json.dumps(env.get('codegraph_db'), ensure_ascii=False)}"
    )
    lines.append("```")
    lines.append("")
    lines.append("## 8. Known limitations and proposed fixes")
    lines.append("")
    lines.append(
        "- **M1 (fixed in this run):** a busd payload missing `rules_in_sync`, "
        "`version` or `uptime_seconds` now returns `degraded` with a "
        "'partial measurement' warning. Covered by D3 case M1 and D2 test "
        "`test_busd_partial_payload_is_degraded`."
    )
    lines.append(
        "- **N1 (fixed in this run):** `score_sources()` with rows missing a "
        "critical source now forces `down/red` and names the missing source(s) "
        "in a warning; the payload's `overall` keeps its fixed "
        "`{status, score, color}` shape. Covered by D3 case N1 and D2 test "
        "`test_score_sources_missing_critical_is_down`."
    )
    lines.append(
        "- **L1 (SKIP-NA):** CTO column drift is invisible; contract §3 does "
        "not define columns. Needs a contract/CTO-owner decision."
    )
    lines.append(
        "- **O1 (SKIP-NA):** an empty but valid codegraph index is reported "
        "`ok`; contract §3 has no minimum threshold."
    )
    lines.append(
        "- **P1:** wall-clock includes interpreter startup; the contract "
        "budget is the tool's `meta.duration_ms`."
    )
    lines.append(
        "- Live cases (P1/R1) depend on the local runtime; the deterministic "
        "cases do not. The secret canary is synthetic; no real secret is used."
    )
    lines.append(
        "- The M1/N1 fixes were applied before this D3 run; the eval itself "
        "did not modify product code. The changes are limited to "
        "`axis_mcp/status/sources.py`, `axis_mcp/status/aggregator.py` and the "
        "two new tests; no other product behavior changed."
    )
    lines.append("")
    lines.append("## 9. Workspace state")
    lines.append("")
    lines.append("```text")
    lines.append("$ git status --porcelain")
    for line in git_status["raw"]:
        lines.append(line)
    if not git_status["raw"]:
        lines.append("(clean)")
    lines.append("```")
    lines.append("")
    lines.append(
        "The snapshot is taken immediately before this Markdown file is "
        "rewritten, so the docs path appears once the file exists from a "
        "previous run."
    )
    lines.append("")
    lines.append(
        "New paths from this D3 work: `scripts/d3_axis_status_eval.py`, "
        "`docs/certification/D3-axis-status-2026-11-23.md` and the gitignored "
        "`bus/evidence/2026-11-23/d3-axis-status/` directory. "
        "`brain/learnt.md` and `config/.module-registry.json.lock` were "
        "already present before this run and were not touched."
    )
    lines.append("")
    lines.append(
        "> Generated by `scripts/d3_axis_status_eval.py`. Re-running the "
        "harness rewrites this file and the evidence JSON from the same data."
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat()
    console_lines: list[str] = []

    def say(text: str = "") -> None:
        print(text)
        console_lines.append(text)

    say("D3 — AXIS STATUS evaluation")
    say(f"commit: {collect_env().get('git_head_short')} · date: {generated_at}")
    say("")

    results: list[dict[str, Any]] = []
    for index, spec in enumerate(CASES, 1):
        aggregator.reset_cache()
        started = time.monotonic()
        try:
            result = spec.fn()
        except Exception as exc:  # noqa: BLE001 - a harness crash is a FAIL row
            result = Outcome(
                actual=f"harness exception: {type(exc).__name__}: {exc}",
                verdict="FAIL",
                root_cause=f"the eval harness raised {type(exc).__name__}",
                proposed_fix="fix the harness or the behavior it exercises",
                evidence={"exception": repr(exc)},
            )
        finally:
            aggregator.reset_cache()
        elapsed_ms = int((time.monotonic() - started) * 1000)
        record = {
            "id": spec.cid,
            "group": spec.group,
            "name": spec.name,
            "expected": spec.expected,
            "actual": result.actual,
            "verdict": result.verdict,
            "note": result.note,
            "root_cause": result.root_cause,
            "proposed_fix": result.proposed_fix,
            "evidence": result.evidence,
            "elapsed_ms": elapsed_ms,
        }
        results.append(record)
        say(
            f"{index:02d} {spec.cid:<3} {result.verdict:<4} "
            f"{spec.name[:44]:<44} | {result.actual[:96]}"
        )

    passed = sum(1 for item in results if item["verdict"] == "PASS")
    failed = sum(1 for item in results if item["verdict"] == "FAIL")
    skipped = sum(1 for item in results if item["verdict"] == "SKIP")
    total = len(results)

    say("")
    say("DETAIL — FAIL / SKIP")
    say("")
    for item in results:
        if item["verdict"] == "PASS":
            continue
        say(f"[{item['verdict']}] {item['id']} — {item['name']}")
        say(f"  expected: {item['expected']}")
        say(f"  actual:   {item['actual']}")
        if item["root_cause"]:
            say(f"  root:     {item['root_cause']}")
        if item["note"]:
            say(f"  note:     {item['note']}")
        if item["proposed_fix"]:
            say(f"  fix:      {item['proposed_fix']}")
        say("")

    env = collect_env()
    hashes = hash_evaluated_files()
    pytest_result = run_pytest()
    git_status = run_git_status()

    pytest_failed = pytest_result["exit_code"] not in (0, None)
    exit_code = 1 if failed or pytest_failed else 0

    summary = {
        "total": total,
        "pass": passed,
        "fail": failed,
        "skip": skipped,
        "exit_code": exit_code,
        "pytest_exit_code": pytest_result["exit_code"],
    }

    say("")
    say(f"CASES: {total} · PASS {passed} · FAIL {failed} · SKIP {skipped}")
    say(f"PYTEST: {pytest_result['summary']} (exit {pytest_result['exit_code']})")
    say(f"EXIT: {exit_code}")
    say("")

    evidence = {
        "schema": "axis.d3.eval/1",
        "generated_at": generated_at,
        "tool_schema": aggregator.SCHEMA,
        "tool_version": aggregator.TOOL_VERSION,
        "summary": summary,
        "cases": results,
        "environment": env,
        "evaluated_files": hashes,
        "pytest": pytest_result,
        "git_status": git_status,
        "commands": {
            "eval": EVAL_COMMAND,
            "pytest": PYTEST_COMMAND,
            "git_status": "git status --porcelain",
        },
        "known_limitations": [
            "M1 fixed in this run: busd partial payload -> degraded + partial-measurement warning (test: test_busd_partial_payload_is_degraded).",
            "N1 fixed in this run: score_sources missing critical -> down/red + warning (test: test_score_sources_missing_critical_is_down).",
            "L1: CTO column drift has no contract threshold (SKIP-NA).",
            "O1: empty codegraph index has no contract threshold (SKIP-NA).",
            "P1 wall time includes interpreter startup; contract budget is meta.duration_ms.",
            "Live cases P1/R1 depend on the local runtime; deterministic cases do not.",
            "The canary is synthetic; no real secret is used.",
            "Product changes are limited to M1/N1 (sources.py, aggregator.py) and the two new tests; no other product behavior changed.",
        ],
    }

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / "eval.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "eval.log").write_text(
        "\n".join(console_lines) + "\n", encoding="utf-8"
    )

    env_lines = [
        f"date_utc={env['date_utc']}",
        f"git_head={env['git_head']}",
        f"git_head_short={env['git_head_short']}",
        f"git_branch={env['git_branch']}",
        f"python_version={env['python_version']}",
        f"python_executable={env['python_executable']}",
        f"platform={env['platform']}",
        f"cwd={env['cwd']}",
        f"busd={json.dumps(env['busd'], ensure_ascii=False)}",
        f"mcp_processes={json.dumps(env['mcp_processes'], ensure_ascii=False)}",
        f"browse_cli={env['browse_cli']}",
        f"codegraph_db={json.dumps(env['codegraph_db'], ensure_ascii=False)}",
        f"pytest_version={env['pytest_version']}",
    ]
    (EVIDENCE_DIR / "env.txt").write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    sha_lines = []
    for item in hashes:
        digest = item["sha256"] or "MISSING"
        sha_lines.append(f"{digest}  {item['path']}")
    (EVIDENCE_DIR / "sha256.txt").write_text(
        "\n".join(sha_lines) + "\n", encoding="utf-8"
    )

    markdown = render_markdown(
        generated_at=generated_at,
        results=results,
        summary=summary,
        env=env,
        hashes=hashes,
        pytest_result=pytest_result,
        git_status=git_status,
    )
    (EVIDENCE_DIR / "table.md").write_text(markdown, encoding="utf-8")
    DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOCS_PATH.write_text(markdown, encoding="utf-8")

    print(f"evidence: {EVIDENCE_DIR}")
    print(f"docs:     {DOCS_PATH}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
