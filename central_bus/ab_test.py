"""Central Bus — A/B Test Experiment Layer (CMD-002-A).

Deploys a live 50/50 A/B test between two routing variants **on top of**
the existing routing engine (non-destructive):

* ``v1`` — legacy ``route()``        (JSONL keyword/semantic routing)
* ``v2`` — behavior-centric ``route_v2()`` (BehaviorClassifier Tier 0)

Endpoints
~~~~~~~~~
* ``GET /v1/route_v1``   — Variant-1 entry point: assigns a variant per
                           request (deterministic), routes through the
                           selected implementation, returns the selection.
* ``GET /v1/route_v2``   — Variant-2 entry point: same A/B experiment.
* ``GET /v1/ab-test/report`` — defined in ``central_bus.main``; merges this
                           module's experiment report (``get_all_reports()``).

Design
~~~~~~
* ``EXPERIMENTS`` registry — single source of truth for active experiments
  (name -> variants + weights).  Currently ``route_split``: v1/v2 @ 50/50.
* ``assign_variant()`` — deterministic split by request id: MD5 hash first
  nibble < 8 -> v2, >= 8 -> v1.  Reuses ``router.should_use_v2()`` so ids
  stay consistent with the existing route-level A/B machinery.  The same
  request id ALWAYS maps to the same variant — reproducible, debuggable,
  and exactly 50/50 by construction (8 of 16 MD5 buckets per variant).
* Metrics are in-memory (same pattern as ``router._AB_METRICS``) with a
  lock for thread safety.

Non-destructive guarantee:
  - router.route()    — UNTOUCHED
  - router.route_v2() — UNTOUCHED
  - router._AB_METRICS — UNTOUCHED (this module keeps its own counters)
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from collections import deque
from threading import Lock
from typing import Any, Optional

from fastapi import APIRouter, Request

from central_bus.models import BusMessage
from central_bus.router import route, route_v2, should_use_v2

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# Experiment registry — single source of truth
# ═══════════════════════════════════════════════════════════════════════

EXPERIMENTS: dict[str, dict[str, Any]] = {
    "route_split": {
        "description": (
            "Live 50/50 split: v1 (legacy route()) vs "
            "v2 (behavior-centric route_v2())"
        ),
        "variants": ["v1", "v2"],
        "weights": [50, 50],
        "split_method": "MD5 hash of request_id — first nibble < 8 -> v2, >= 8 -> v1",
        "status": "active",
    },
}

# ═══════════════════════════════════════════════════════════════════════
# In-memory metrics (per experiment) — same pattern as router._AB_METRICS
# ═══════════════════════════════════════════════════════════════════════

_METRICS: dict[str, dict[str, Any]] = {}
_METRICS_LOCK = Lock()
_SAMPLE_LIMIT = 50


def _ensure_experiment(experiment: str) -> None:
    if experiment not in EXPERIMENTS:
        raise KeyError(
            f"Unknown A/B experiment: {experiment!r}. Known: {sorted(EXPERIMENTS)}"
        )


def _init_metrics(experiment: str) -> dict[str, Any]:
    with _METRICS_LOCK:
        if experiment not in _METRICS:
            cfg = EXPERIMENTS[experiment]
            _METRICS[experiment] = {
                "counts": {v: 0 for v in cfg["variants"]},
                "samples": deque(maxlen=_SAMPLE_LIMIT),
                "started_at": time.time(),
            }
        return _METRICS[experiment]


# ═══════════════════════════════════════════════════════════════════════
# Deterministic 50/50 split
# ═══════════════════════════════════════════════════════════════════════


def assign_variant(experiment: str, request_id: str) -> str:
    """Deterministic variant assignment for a request id.

    For ``route_split`` this delegates to ``router.should_use_v2()``
    (MD5 first nibble < 8 -> v2) so the mapping is identical to the
    existing route-level A/B machinery.  Future experiments fall back to
    a generic weighted MD5 split over ``(experiment, request_id)``.

    Args:
        experiment: Name of a registered experiment (see ``EXPERIMENTS``).
        request_id: Unique identifier of the request (X-Request-Id /
                    ?request_id=).  Empty -> first variant.

    Returns:
        The selected variant name (e.g. ``"v1"`` or ``"v2"``).
    """
    _ensure_experiment(experiment)
    cfg = EXPERIMENTS[experiment]

    # Fast path — reuse the battle-tested split for route_split
    if cfg["variants"] == ["v1", "v2"] and cfg["weights"] == [50, 50]:
        return "v2" if should_use_v2(request_id) else "v1"

    # Generic weighted split for future experiments
    if not request_id:
        return cfg["variants"][0]
    h = hashlib.md5(f"{experiment}:{request_id}".encode("utf-8")).hexdigest()
    total = sum(cfg["weights"])
    bucket = int(h[:8], 16) % total
    acc = 0
    for variant, weight in zip(cfg["variants"], cfg["weights"]):
        acc += weight
        if bucket < acc:
            return variant
    return cfg["variants"][-1]


# ═══════════════════════════════════════════════════════════════════════
# Metrics recording
# ═══════════════════════════════════════════════════════════════════════


def record_decision(
    experiment: str,
    variant: str,
    request_id: str,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    """Record one A/B decision in the experiment's in-memory metrics."""
    _ensure_experiment(experiment)
    m = _init_metrics(experiment)
    with _METRICS_LOCK:
        m["counts"][variant] = m["counts"].get(variant, 0) + 1
        sample: dict[str, Any] = {
            "request_id": request_id,
            "variant": variant,
            "timestamp": time.time(),
        }
        if meta:
            sample["meta"] = meta
        m["samples"].append(sample)


def reset_metrics(experiment: Optional[str] = None) -> None:
    """Clear in-memory metrics.  Useful for test isolation.

    Args:
        experiment: If given, only that experiment is cleared; otherwise
                    all experiments are cleared.
    """
    with _METRICS_LOCK:
        if experiment is None:
            _METRICS.clear()
        else:
            _METRICS.pop(experiment, None)


# ═══════════════════════════════════════════════════════════════════════
# Report
# ═══════════════════════════════════════════════════════════════════════


def get_report(experiment: str) -> dict[str, Any]:
    """Counts per variant + split ratio for one experiment."""
    _ensure_experiment(experiment)
    cfg = EXPERIMENTS[experiment]
    m = _init_metrics(experiment)
    counts = dict(m["counts"])
    total = sum(counts.values())

    variants: dict[str, dict[str, Any]] = {}
    for v in cfg["variants"]:
        c = counts.get(v, 0)
        variants[v] = {
            "count": c,
            "percentage": round(c / total * 100, 1) if total else 0.0,
        }

    report: dict[str, Any] = {
        "experiment": experiment,
        "description": cfg["description"],
        "status": cfg["status"],
        "split_ratio": f"{cfg['weights'][0]}/{cfg['weights'][1]}",
        "split_method": cfg["split_method"],
        "total": total,
        "variants": variants,
    }

    if total:
        first = cfg["variants"][0]
        first_pct = variants[first]["percentage"]
        report["split_balance"] = {
            f"{first}_percent": first_pct,
            "other_percent": round(100 - first_pct, 1),
            "is_balanced": abs(first_pct - 50) < 5,  # within 5% of 50/50
        }

    report["recent_samples"] = list(m["samples"])[-10:]
    return report


def get_all_reports() -> dict[str, dict[str, Any]]:
    """Report for every registered experiment, keyed by name."""
    return {name: get_report(name) for name in EXPERIMENTS}


# ═══════════════════════════════════════════════════════════════════════
# Variant routing endpoints
# ═══════════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/v1", tags=["ab-test"])

_ROUTING_IMPLS = {
    "v1": "route() (legacy JSONL keyword/semantic)",
    "v2": "route_v2() (behavior-centric, Tier 0)",
}

_DEFAULT_TEXT = "Need to fix a login bug in the auth page"


def _request_id_from(request: Request) -> str:
    rid = request.headers.get("X-Request-Id") or request.query_params.get("request_id")
    return rid or str(uuid.uuid4())


def _execute_variant(variant: str, request_id: str, text: str) -> str:
    """Actually route through the selected variant's implementation."""
    msg = BusMessage(
        from_dept="engineering",
        to_dept="",
        type="HANDOFF",
        project_id="ab-test",
        phase="live",
        payload={"text": text},
        trace_id=request_id,
    )
    if variant == "v2":
        return route_v2(msg)
    return route(msg)


async def _handle_route_request(request: Request, endpoint: str) -> dict[str, Any]:
    """Shared handler — A/B experiment decides the variant, then routes."""
    experiment = "route_split"
    request_id = _request_id_from(request)
    text = request.query_params.get("text", _DEFAULT_TEXT)

    # Optional QA override (force=v1|v2); default = deterministic split
    force = request.query_params.get("force")
    if force in ("v1", "v2"):
        variant = force
    else:
        variant = assign_variant(experiment, request_id)

    start = time.monotonic()
    try:
        dept = _execute_variant(variant, request_id, text)
    except Exception as e:  # routing failure must not break the endpoint
        log.warning("A/B route execution failed (variant=%s): %s", variant, e)
        dept = "ceo"
    latency_ms = round((time.monotonic() - start) * 1000, 2)

    record_decision(experiment, variant, request_id, meta={
        "endpoint": endpoint,
        "route_to": dept,
        "latency_ms": latency_ms,
        "forced": bool(force in ("v1", "v2")),
    })

    return {
        "experiment": experiment,
        "variant": variant,
        "request_id": request_id,
        "endpoint": endpoint,
        "route_to": dept,
        "routing_impl": _ROUTING_IMPLS[variant],
        "latency_ms": latency_ms,
        "split_ratio": "50/50",
    }


@router.get("/route_v1")
async def route_v1_endpoint(request: Request):
    """A/B route entry — variant v1 side (legacy ``route()``).

    The returned variant is selected deterministically from the request id
    (``X-Request-Id`` header or ``?request_id=``), NOT forced by this path.
    Pass ``?force=v1`` / ``?force=v2`` for targeted QA.
    """
    return await _handle_route_request(request, "/v1/route_v1")


@router.get("/route_v2")
async def route_v2_endpoint(request: Request):
    """A/B route entry — variant v2 side (behavior-centric ``route_v2()``).

    Same experiment as ``/v1/route_v1``: the variant returned is the one
    selected deterministically for this request id.
    """
    return await _handle_route_request(request, "/v1/route_v2")


# ═══════════════════════════════════════════════════════════════════════
# Module-level exports
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    "EXPERIMENTS",
    "router",
    "assign_variant",
    "record_decision",
    "reset_metrics",
    "get_report",
    "get_all_reports",
]
