"""Fan-out, scoring and cache for the AXIS status layer.

Seven probes run in parallel threads. A slow probe is cut at 1200 ms and the
remaining snapshot is still returned: partial data beats a failed call. The
whole call is cached for 10 s unless ``force`` is set.
"""

from __future__ import annotations

import copy
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from . import sources

SCHEMA = "axis.status/1"
TOOL_VERSION = "1.0.0"

SOURCE_IDS = (
    "busd",
    "cto",
    "content",
    "mcp_freshness",
    "git",
    "browse",
    "codegraph",
)

WEIGHTS = {
    "busd": 25,
    "cto": 20,
    "content": 15,
    "mcp_freshness": 15,
    "git": 10,
    "browse": 10,
    "codegraph": 5,
}

CRITICAL_SOURCES = frozenset({"busd", "mcp_freshness"})

# ok=1, degraded=0.5, down=0; unknown is excluded and the weights renormalize.
STATUS_VALUE = {"ok": 1.0, "degraded": 0.5, "down": 0.0}

PER_SOURCE_TIMEOUT_MS = 1200
TOTAL_BUDGET_MS = 2000
CACHE_TTL_SECONDS = 10.0

_COLORS = {"healthy": "green", "degraded": "amber", "down": "red"}

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {"at": 0.0, "payload": None}


def reset_cache() -> None:
    """Drop the cached snapshot (tests and ``force`` rely on this)."""

    with _CACHE_LOCK:
        _CACHE["at"] = 0.0
        _CACHE["payload"] = None


def _call_probe(probe: Callable[[], dict[str, Any]]) -> tuple[dict[str, Any], float]:
    started = time.monotonic()
    try:
        payload = probe()
    except Exception as exc:  # noqa: BLE001 - one bad probe must not kill the call
        payload = {
            "status": "down",
            "fresh": False,
            "detail": {"error": type(exc).__name__},
            "warning": f"probe raised {type(exc).__name__}",
        }
    return payload, (time.monotonic() - started) * 1000


def _normalize(source_id: str, payload: Any, elapsed_ms: float) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    status = data.get("status")
    if status not in STATUS_VALUE and status != "unknown":
        status = "down"
        data = {
            **data,
            "warning": data.get("warning")
            or "probe returned no valid status — measurement failed",
        }

    detail = data.get("detail")
    if not isinstance(detail, dict):
        detail = {}
    warning = data.get("warning")
    if warning is not None:
        warning = str(warning)

    if elapsed_ms > PER_SOURCE_TIMEOUT_MS:
        return {
            "id": source_id,
            "status": "down",
            "latency_ms": max(0, int(round(elapsed_ms))),
            "fresh": False,
            "detail": detail,
            "warning": (
                f"timed out after {int(round(elapsed_ms))} ms "
                f"(per-source limit {PER_SOURCE_TIMEOUT_MS} ms)"
            ),
        }

    fresh_value = data.get("fresh")
    if not isinstance(fresh_value, bool):
        return {
            "id": source_id,
            "status": "down",
            "latency_ms": max(0, int(round(elapsed_ms))),
            "fresh": False,
            "detail": detail,
            "warning": (
                "probe returned a non-boolean fresh value — measurement failed"
            ),
        }

    fresh = fresh_value and status in ("ok", "degraded")
    if status == "ok" and not fresh:
        status = "degraded"
        warning = warning or "source reports ok but its data is not fresh"
    if status == "ok" and warning:
        status = "degraded"
    if status != "ok" and not warning:
        warning = {
            "degraded": "source reports a degraded state",
            "down": "source did not respond",
            "unknown": "source could not be measured",
        }[status]

    return {
        "id": source_id,
        "status": status,
        "latency_ms": max(0, int(round(elapsed_ms))),
        "fresh": fresh,
        "detail": detail,
        "warning": warning,
    }


def _timeout_row(source_id: str) -> dict[str, Any]:
    return {
        "id": source_id,
        "status": "down",
        "latency_ms": PER_SOURCE_TIMEOUT_MS,
        "fresh": False,
        "detail": {},
        "warning": (
            f"timed out after {PER_SOURCE_TIMEOUT_MS} ms "
            f"(per-source limit {PER_SOURCE_TIMEOUT_MS} ms)"
        ),
    }


def _run_probes(
    probes: Mapping[str, Callable[[], dict[str, Any]]],
) -> list[dict[str, Any]]:
    started = time.monotonic()
    executor = ThreadPoolExecutor(
        max_workers=max(1, len(SOURCE_IDS)), thread_name_prefix="axis-status"
    )
    rows: dict[str, dict[str, Any]] = {}
    try:
        futures = {}
        for source_id in SOURCE_IDS:
            probe = probes.get(source_id)
            if probe is None:
                rows[source_id] = _normalize(
                    source_id,
                    {
                        "status": "unknown",
                        "fresh": False,
                        "detail": {},
                        "warning": "no probe registered for this source",
                    },
                    0.0,
                )
                continue
            futures[executor.submit(_call_probe, probe)] = source_id

        per_source = PER_SOURCE_TIMEOUT_MS / 1000
        total_budget = TOTAL_BUDGET_MS / 1000
        remaining = total_budget - (time.monotonic() - started)
        done, pending = wait(futures, timeout=max(0.0, min(per_source, remaining)))
        for future in done:
            payload, elapsed_ms = future.result()
            rows[futures[future]] = _normalize(futures[future], payload, elapsed_ms)
        for future in pending:
            future.cancel()
            rows[futures[future]] = _timeout_row(futures[future])
    finally:
        # Never block the caller on a probe that blew its deadline.
        executor.shutdown(wait=False, cancel_futures=True)

    return [rows[source_id] for source_id in SOURCE_IDS]


def score_sources(rows: list[dict[str, Any]]) -> dict[str, Any]:
    # A critical source that is absent from the rows is unmeasured, not healthy.
    # The aggregator always supplies all seven rows, so this guard only matters
    # to direct callers of this public helper (D3 NIT-4).
    present = {row["id"] for row in rows}
    missing_critical = sorted(CRITICAL_SOURCES - present)

    earned = 0.0
    measured = 0
    for row in rows:
        weight = WEIGHTS.get(row["id"], 0)
        value = STATUS_VALUE.get(row["status"])
        if value is None:
            continue
        earned += weight * value
        measured += weight

    if measured == 0:
        result: dict[str, Any] = {"status": "down", "score": 0, "color": "red"}
        if missing_critical:
            result["missing_critical"] = missing_critical
            result["warning"] = (
                "critical source(s) missing from the score: "
                f"{', '.join(missing_critical)} — overall forced down"
            )
        return result

    score = int(math.floor(earned / measured * 100 + 0.5))
    critical_down = any(
        row["status"] == "down" and row["id"] in CRITICAL_SOURCES for row in rows
    )
    critical_unknown = any(
        row["status"] == "unknown" and row["id"] in CRITICAL_SOURCES for row in rows
    )
    if critical_down or critical_unknown or missing_critical:
        status = "down"
    elif score >= 90:
        status = "healthy"
    elif score >= 70:
        status = "degraded"
    else:
        status = "down"
    result = {"status": status, "score": score, "color": _COLORS[status]}
    if missing_critical:
        result["missing_critical"] = missing_critical
        result["warning"] = (
            "critical source(s) missing from the score: "
            f"{', '.join(missing_critical)} — overall forced down"
        )
    return result


def _secret() -> str:
    return (os.environ.get("SOLOCORP_API_KEY") or "").strip()


def _scrub(value: Any, secret: str) -> Any:
    if isinstance(value, dict):
        return {key: _scrub(item, secret) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub(item, secret) for item in value]
    if isinstance(value, str) and secret and secret in value:
        return value.replace(secret, "[redacted]")
    return value


def _build_payload(rows: list[dict[str, Any]], duration_ms: float) -> dict[str, Any]:
    overall = score_sources(rows)
    # score_sources may annotate a partial-row result with missing-critical
    # context. The payload's overall object stays the contract's fixed
    # {status, score, color} shape; the warning moves to the top-level list.
    overall_warning = overall.pop("warning", None)
    overall.pop("missing_critical", None)
    warnings = [f"{row['id']}: {row['warning']}" for row in rows if row["warning"]]
    if overall_warning:
        warnings.append(overall_warning)
    unverified = [
        row["id"]
        for row in rows
        if row["status"] == "unknown" and row["id"] in CRITICAL_SOURCES
    ]
    if unverified:
        warnings.append(
            "critical source(s) "
            f"{', '.join(unverified)} could not be measured — overall forced down"
        )
    if all(row["status"] == "unknown" for row in rows):
        warnings.append("no source could be measured — status is unknown, not healthy")
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "sources": rows,
        "warnings": warnings,
        "meta": {
            "duration_ms": max(0, int(round(duration_ms))),
            "cache": "fresh",
            "tool_version": TOOL_VERSION,
        },
    }


def aggregate(
    force: bool = False,
    probes: Mapping[str, Callable[[], dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Return the unified status snapshot.

    ``force`` bypasses the 10 s cache. ``probes`` exists for tests and for the
    evidence harness; production callers leave it unset.
    """

    started = time.monotonic()

    if not force:
        with _CACHE_LOCK:
            cached = _CACHE["payload"]
            age = time.monotonic() - _CACHE["at"]
        if cached is not None and age <= CACHE_TTL_SECONDS:
            payload = copy.deepcopy(cached)
            payload["meta"]["cache"] = "cached"
            payload["meta"]["duration_ms"] = max(
                0, int(round((time.monotonic() - started) * 1000))
            )
            return payload

    selected = sources.DEFAULT_PROBES if probes is None else probes
    rows = _run_probes(selected)
    payload = _build_payload(rows, (time.monotonic() - started) * 1000)
    payload = _scrub(payload, _secret())

    with _CACHE_LOCK:
        _CACHE["at"] = time.monotonic()
        _CACHE["payload"] = copy.deepcopy(payload)
    return payload
