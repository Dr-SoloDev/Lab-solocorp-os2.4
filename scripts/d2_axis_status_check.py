#!/usr/bin/env python3
"""D2 evidence harness for the AXIS status layer (C1).

Calls the real ``axis_status`` tool, validates ``axis.status/1``, prints
PASS/FAIL per check and exits non-zero on failure. One run writes both
``tool-calls.jsonl`` and ``harness.log``.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from axis_mcp.status import sources  # noqa: E402
from axis_mcp.status.aggregator import CRITICAL_SOURCES  # noqa: E402
from axis_mcp.status.aggregator import SOURCE_IDS, TOOL_VERSION  # noqa: E402
from axis_mcp.status.aggregator import WEIGHTS, aggregate  # noqa: E402
from axis_mcp.status.server import axis_status  # noqa: E402

CALL_LOG = ROOT / "bus/evidence/2026-11-23/d2-axis-status/tool-calls.jsonl"
LOG_PATH = ROOT / "bus/evidence/2026-11-23/d2-axis-status/harness.log"
LINES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    line = f"{'PASS' if ok else 'FAIL'} {name}"
    if detail and not ok:
        line += f" — {detail}"
    LINES.append(line)
    print(line)


def main() -> int:
    started = time.monotonic()
    payload = axis_status(force=True)
    elapsed = int((time.monotonic() - started) * 1000)
    rows = payload.get("sources") or []
    check("schema is axis.status/1", payload.get("schema") == "axis.status/1")
    check("7 sources in order", [r.get("id") for r in rows] == list(SOURCE_IDS))
    fields = all(
        r.get("status") in ("ok", "degraded", "down", "unknown")
        and isinstance(r.get("latency_ms"), int)
        and r["latency_ms"] >= 0
        and isinstance(r.get("fresh"), bool)
        and isinstance(r.get("detail"), dict)
        and (r.get("warning") is None or isinstance(r.get("warning"), str))
        for r in rows
    )
    check("every source has contract fields", fields)
    fresh_ok = all(
        (r["fresh"] and r["warning"] is None)
        if r["status"] == "ok"
        else bool(r["warning"])
        for r in rows
    )
    check("ok is fresh, non-ok warns", fresh_ok)
    listed = all(
        any(r["id"] in w for w in payload["warnings"])
        for r in rows
        if r["status"] != "ok"
    )
    check("non-ok sources appear in warnings", listed)
    values = {"ok": 1.0, "degraded": 0.5, "down": 0.0}
    measured = [r for r in rows if r["status"] in values]
    total = sum(WEIGHTS[r["id"]] for r in measured) or 1
    score = int(
        sum(WEIGHTS[r["id"]] * values[r["status"]] for r in measured) / total * 100
        + 0.5
    )
    overall = payload["overall"]
    critical_down = any(
        r["status"] in ("down", "unknown") and r["id"] in CRITICAL_SOURCES for r in rows
    )
    expected = (
        "down"
        if critical_down
        else ("healthy" if score >= 90 else "degraded" if score >= 70 else "down")
    )
    colors = {"healthy": "green", "degraded": "amber", "down": "red"}
    check(
        "overall score and bands",
        overall["score"] == score
        and overall["status"] == expected
        and overall["color"] == colors[expected],
    )
    meta = payload["meta"]
    meta_ok = (
        isinstance(meta["duration_ms"], int)
        and meta["cache"] in ("fresh", "cached")
        and meta["tool_version"] == TOOL_VERSION
    )
    check("meta fields and 2000 ms budget", meta_ok and elapsed <= 2000)
    try:
        datetime.fromisoformat(payload["generated_at"])
        check("generated_at is ISO-8601", True)
    except (KeyError, ValueError) as exc:
        check("generated_at is ISO-8601", False, str(exc))
    secret = (os.environ.get("SOLOCORP_API_KEY") or "").strip()
    text = json.dumps(payload)
    check(
        "no API key or headers",
        (not secret or secret not in text) and "X-API-Key:" not in text,
    )
    cached = axis_status(force=False)
    check(
        "cache hit keeps generated_at, force bypasses",
        cached["meta"]["cache"] == "cached"
        and cached["generated_at"] == payload["generated_at"]
        and axis_status(force=True)["meta"]["cache"] == "fresh",
    )
    probe_pass = aggregate(force=True)
    CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CALL_LOG.open("w", encoding="utf-8") as handle:
        for row in probe_pass["sources"]:
            record = {
                "source": row["id"],
                "status": row["status"],
                "method": sources.PROBE_METHODS[row["id"]],
                "latency_ms": row["latency_ms"],
                "at": probe_pass["generated_at"],
            }
            handle.write(json.dumps(record) + "\n")
    lines = [json.loads(x) for x in CALL_LOG.read_text().splitlines() if x]
    check(
        "tool-calls.jsonl has one complete line per source",
        sorted(x["source"] for x in lines) == sorted(SOURCE_IDS)
        and all(
            x["method"] and isinstance(x["latency_ms"], int) and x["status"]
            for x in lines
        ),
    )
    failed = sum(line.startswith("FAIL") for line in LINES)
    summary = f"\n{len(LINES) - failed}/{len(LINES)} checks passed · {elapsed} ms"
    smoke = "SMOKE: " + " · ".join(f"{r['id']}={r['status']}" for r in rows)
    print(summary)
    print(smoke)
    LOG_PATH.write_text("\n".join([*LINES, summary, smoke]) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
