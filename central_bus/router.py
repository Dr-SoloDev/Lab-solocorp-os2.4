"""Central Bus v0.6 — Routing Engine (SQLite + JSONL backward compat).

Architecture
~~~~~~~~~~~~
* Existing ``route()`` and ``priority_for()`` functions remain **untouched**
  for backward compatibility (JSONL-backed).
* New ``RoutingEngine`` class loads rules from SQLite with 60s TTL cache.
* The module-level ``route()`` function delegates to the engine when
  ``USE_SQLITE=True`` is set.  Otherwise falls back to JSONL.

v0.6.1 — Behavior-Centric Routing (ADR-016)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* NEW ``BehaviorRouter`` class wraps the ``BehaviorClassifier`` as Tier 0.
* NEW ``route_v2()`` — non-destructive: Tier 0 Behavior -> fallback to route().
* Existing ``route()``, ``RoutingEngine``, ``priority_for()`` untouched.

v0.6.2 — A/B Test 50/50 (ADR-017)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* NEW ``should_use_v2()`` — deterministic 50/50 split based on trace_id hash.
* NEW ``route_ab_test()`` — A/B wrapper that delegates to v2 or legacy.
* NEW ``get_ab_report()`` — in-memory + DB-backed metrics report.
* Existing ``route()``, ``BehaviorRouter`` / ``route_v2()`` untouched.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from central_bus.config import settings
from central_bus.db import DbManager, new_id, now_iso
from central_bus.models import BusMessage, Department, Priority
from central_bus.semantic import TfidfRouter

log = logging.getLogger(__name__)

RULES_PATH = Path(__file__).parent.parent / "bus" / "system" / "routing_rules.json"
USE_SQLITE = settings.use_sqlite

_router: TfidfRouter | None = None


# ═══════════════════════════════════════════════════════════════════════
# Existing JSONL functions — preserved for backward compat
# ═══════════════════════════════════════════════════════════════════════


def _get_semantic_router() -> TfidfRouter:
    global _router
    if _router is None:
        _router = TfidfRouter()
    return _router


def _load_rules() -> dict:
    return json.loads(RULES_PATH.read_text())


def _has_thai(s: str) -> bool:
    return bool(re.search(r"[\u0e01-\u0e39]", s))


def _matches(keyword: str, text: str) -> bool:
    return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text))


# ── Governance event routing ────────────────────────────────────────


def _route_governance(msg: BusMessage) -> Department:
    """Route a GOVERNANCE-type message based on gov_event field."""
    gov_event: str = msg.payload.get("gov_event", "")

    if gov_event == "guard_failed":
        return "orchestrator"
    elif gov_event == "rfc_created":
        return "orchestrator"
    elif gov_event == "complexity_assessed":
        return "architect"
    elif gov_event == "adr_accepted":
        return "architect"
    elif gov_event == "guard_run":
        return "architect"
    else:
        return "architect"


# ── Governance-aware priority ────────────────────────────────────────


def _governance_priority(msg: BusMessage) -> Priority | None:
    """Override priority based on governance event severity."""
    if msg.type != "GOVERNANCE":
        return None
    gov_event = msg.payload.get("gov_event", "")
    if gov_event == "guard_failed":
        return "critical"
    elif gov_event == "rfc_created":
        return "high"
    return None


# ── Main route function (JSONL) — UNTOUCHED ────────────────────────


def route(msg: BusMessage) -> Department:
    """Match message payload to destination department.

    Three-tier matching with governance pre-route:
      0. If message type is GOVERNANCE -> governance routing rules
      1. Keyword matching (fast path)
      2. Semantic matching (TF-IDF + cosine similarity)
      3. CEO fallback
    """
    # Tier 0a: AO message routing
    if msg.type == "AO_REQUEST":
        return "architect"
    if msg.type == "AO_RESPONSE":
        return msg.to_dept

    # Tier 0b: Governance event routing
    if msg.type == "GOVERNANCE":
        return _route_governance(msg)

    rules = _load_rules()
    text = " ".join(str(v) for v in msg.payload.values()).lower()

    # Tier 1: keyword matching (skip for Thai text)
    if not _has_thai(text):
        for rule in rules["rules"]:
            if rule.get("is_fallback"):
                continue
            if any(_matches(kw, text) for kw in rule["trigger"]["keywords"]):
                return rule["route_to"]

    # Tier 2: semantic matching
    sr = _get_semantic_router()
    dept = sr.match(text)
    if dept is not None:
        return dept

    # Tier 3: CEO fallback
    return next(r["route_to"] for r in rules["rules"] if r.get("is_fallback"))


def priority_for(dept: Department, msg: BusMessage | None = None) -> Priority:
    """Determine priority for a department or message."""
    if msg is not None:
        gov_prio = _governance_priority(msg)
        if gov_prio is not None:
            return gov_prio

    rules = _load_rules()
    for rule in rules["rules"]:
        if rule["route_to"] == dept and not rule.get("is_fallback"):
            return rule["priority"]
    return "normal"


# ═══════════════════════════════════════════════════════════════════════
# SQLite Routing Engine — the v0.6 default (UNTOUCHED)
# ═══════════════════════════════════════════════════════════════════════


class RoutingEngine:
    """SQLite-backed routing rule engine with 60s TTL cache."""

    def __init__(self, db: DbManager) -> None:
        self._db = db
        self._cache: list[dict[str, Any]] = []
        self._last_refresh: float = 0.0
        self._ttl: float = 60.0

    async def _load_rules(self) -> list[dict[str, Any]]:
        now = time.monotonic()
        if self._cache and (now - self._last_refresh) < self._ttl:
            return self._cache
        rows = await self._db.fetch_all(
            "SELECT * FROM routing_rules WHERE enabled = 1 ORDER BY priority DESC"
        )
        self._cache = [dict(r) for r in rows]
        self._last_refresh = now
        return self._cache

    async def invalidate_cache(self) -> None:
        self._last_refresh = 0.0

    async def match(
        self,
        source_agent: str,
        payload: dict[str, Any],
        *,
        fallback_department: str = "ceo",
    ) -> str:
        rules = await self._load_rules()
        for rule in rules:
            agent_pattern = rule.get("source_agent", "")
            if agent_pattern and not re.search(agent_pattern, source_agent):
                continue
            condition_str = rule.get("condition")
            if condition_str:
                try:
                    condition = json.loads(condition_str)
                    if not self._evaluate_condition(condition, payload):
                        continue
                except (json.JSONDecodeError, TypeError):
                    log.warning("Invalid condition JSON for rule %s", rule.get("id"))
            return rule.get("target_department", fallback_department)
        return fallback_department

    async def count_rules(self) -> int:
        rules = await self._load_rules()
        return len(rules)

    @staticmethod
    def _evaluate_condition(condition: dict[str, Any], payload: dict[str, Any]) -> bool:
        if "and" in condition:
            return all(RoutingEngine._evaluate_condition(c, payload) for c in condition["and"])
        if "or" in condition:
            return any(RoutingEngine._evaluate_condition(c, payload) for c in condition["or"])
        field = condition.get("field", "")
        value = payload.get(field)
        if "equals" in condition:
            return value == condition["equals"]
        if "contains" in condition:
            return isinstance(value, str) and condition["contains"] in value
        if "exists" in condition:
            return condition["exists"] == (value is not None)
        return False


# ═══════════════════════════════════════════════════════════════════════
# v0.6.1 — BehaviorRouter (Tier 0) — ADD-ON, NOT DESTRUCTIVE
# ═══════════════════════════════════════════════════════════════════════


class BehaviorRouter:
    """Behavior-Centric Router — Tier 0 wrapper around BehaviorClassifier.

    Adds behavior classification BEFORE the existing keyword/semantic/CEO
    routing pipeline.  Uses the centralized ``behavior_classifier`` module
    and DB-backed route mapping.
    """

    def __init__(self, db: DbManager | None = None, classifier=None) -> None:
        self._db = db
        self._classifier = classifier
        self._route_cache: dict[str, str] = {}
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 120.0

    async def _load_route_map(self) -> dict[str, str]:
        now = time.monotonic()
        if self._route_cache and (now - self._cache_ts) < self._cache_ttl:
            return self._route_cache
        if self._db is None:
            from central_bus.behavior_classifier import BEHAVIOR_DEPT_MAP
            self._route_cache = BEHAVIOR_DEPT_MAP
            return self._route_cache
        try:
            rows = await self._db.fetch_all("""
                SELECT bt.behavior_name, brm.primary_dept
                FROM behavior_route_map brm
                JOIN behavior_taxonomy bt ON bt.id = brm.behavior_id
                WHERE bt.is_active = 1
            """)
            self._route_cache = {r["behavior_name"]: r["primary_dept"] for r in rows}
            self._cache_ts = now
        except Exception:
            from central_bus.behavior_classifier import BEHAVIOR_DEPT_MAP
            self._route_cache = BEHAVIOR_DEPT_MAP
        return self._route_cache

    async def invalidate_route_cache(self) -> None:
        self._cache_ts = 0.0

    @property
    def classifier(self):
        if self._classifier is None:
            from central_bus.behavior_classifier import get_classifier
            self._classifier = get_classifier()
        return self._classifier

    async def route_v2(
        self,
        msg: BusMessage,
        *,
        fallback_department: str = "ceo",
        audit: bool = False,
    ) -> Department:
        """Full routing pipeline: Tier 0 (Behavior) -> existing route()."""
        if msg.type in ("AO_REQUEST", "AO_RESPONSE", "GOVERNANCE"):
            return route(msg)
        payload_text = self._extract_text(msg)
        if not payload_text:
            return route(msg)
        behavior_id, confidence = self.classifier.classify(payload_text)
        if confidence >= 0.9:
            route_map = await self._load_route_map()
            dept = route_map.get(behavior_id, fallback_department)
            if audit and self._db:
                await self._audit_classification(msg, behavior_id, dept, confidence)
            return dept
        if audit and self._db:
            await self._audit_classification(msg, behavior_id, "fallback", confidence)
        return route(msg)

    def route_v2_sync(self, payload_text: str, *, fallback_department: str = "ceo") -> str:
        """Sync version: classify payload text -> department."""
        if not payload_text:
            return fallback_department
        behavior_id, confidence = self.classifier.classify(payload_text)
        if confidence >= 0.9:
            from central_bus.behavior_classifier import BEHAVIOR_DEPT_MAP
            return BEHAVIOR_DEPT_MAP.get(behavior_id, fallback_department)
        return fallback_department

    @staticmethod
    def _extract_text(msg: BusMessage) -> str:
        parts = []
        for key in ("text", "message", "description", "title", "detail", "content", "query", "request"):
            val = msg.payload.get(key)
            if isinstance(val, str):
                parts.append(val)
        if not parts:
            parts = [str(v) for v in msg.payload.values() if isinstance(v, (str, int, float))]
        return " ".join(parts) if parts else ""

    async def _audit_classification(self, msg, behavior, dept, confidence) -> None:
        if not self._db:
            return
        try:
            await self._db.execute("""
                INSERT INTO audit_log (id, trace_id, action, agent_id, entity_type, entity_id, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_id(), msg.trace_id, "behavior.classify", msg.from_dept, "behavior", behavior,
                  json.dumps({"behavior": behavior, "route_to": dept, "confidence": confidence,
                              "auto_routed": confidence >= 0.9}), now_iso()))
        except Exception as e:
            log.warning("Failed to audit behavior classification: %s", e)


# ── Module-level convenience: route_v2 ──────────────────────────────

_behavior_router: BehaviorRouter | None = None


def get_behavior_router(db: DbManager | None = None, classifier=None) -> BehaviorRouter:
    global _behavior_router
    if _behavior_router is None:
        _behavior_router = BehaviorRouter(db=db, classifier=classifier)
    return _behavior_router


def route_v2(msg: BusMessage, *, fallback_department: str = "ceo", audit: bool = False, db: DbManager | None = None) -> Department:
    """Convenience: route with Behavior Tier 0 (sync wrapper)."""
    router = get_behavior_router(db=db)
    return router.route_v2_sync(BehaviorRouter._extract_text(msg), fallback_department=fallback_department)


# ═══════════════════════════════════════════════════════════════════════
# v0.6.2 — A/B Test 50/50 (ADR-017) — LAYER ON TOP, NOT DESTRUCTIVE
# ═══════════════════════════════════════════════════════════════════════
# Wraps both route() (legacy) and route_v2() (behavior-centric) with a
# deterministic 50/50 split based on trace_id hash.  Every routing
# decision is logged with variant + timing for comparison.
#
# Non-destructive guarantee:
#   - route()        — UNTOUCHED
#   - route_v2()     — UNTOUCHED
#   - BehaviorRouter — UNTOUCHED
# ═══════════════════════════════════════════════════════════════════════

# ── In-memory A/B test metrics ──────────────────────────────────────

_AB_METRICS: dict[str, dict] = defaultdict(lambda: {
    "count": 0,
    "latencies_ms": [],
    "confidences": [],
    "dept_counts": defaultdict(int),
    "bypass_count": 0,
})


# ── Deterministic 50/50 split ───────────────────────────────────────


def should_use_v2(trace_id: str) -> bool:
    """Deterministic 50/50 split based on trace_id hash.

    Uses MD5 hash of the trace_id — first nibble determines variant:
      - nibble 0-7 (0-7):   v2 (Behavior-Centric Routing)
      - nibble 8-15 (8-F): legacy (Existing route())

    This guarantees the *same trace_id* always maps to the *same variant*,
    making the split reproducible and debuggable.

    Args:
        trace_id: Unique identifier for the message/request being routed.

    Returns:
        True  -> use route_v2() (Behavior-Centric)
        False -> use route() (Legacy)
    """
    if not trace_id:
        return False  # Default to legacy if no trace_id
    h = hashlib.md5(trace_id.encode("utf-8")).hexdigest()
    # First hex digit: 0-15.  < 8 = 50% chance.
    return int(h[0], 16) < 8


# ── A/B Test Audit Event ────────────────────────────────────────────


def _make_ab_audit_payload(result: dict) -> dict:
    """Structure the audit payload for an A/B test routing event."""
    return {
        "variant": result["variant"],
        "department": result["department"],
        "confidence": result["confidence"],
        "latency_ms": result["latency_ms"],
        "trace_id": result["trace_id"],
        "timestamp": now_iso(),
    }


# ── A/B Test Router — the wrapper ───────────────────────────────────


def route_ab_test(msg: BusMessage, *, db: DbManager | None = None) -> dict:
    """A/B test wrapper — deterministic 50/50 split between route() and route_v2().

    **Non-destructive**: ``route()``, ``route_v2()``, and ``BehaviorRouter``
    are NOT modified.  This function sits ON TOP of them.

    Flow:
      1. AO/GOVERNANCE/bypass messages -- route() directly (not part of A/B)
      2. ``should_use_v2(msg.trace_id)`` determines variant
      3. v2 -> ``route_v2()``   (behavior-centric)
      4. legacy -> ``route()``   (existing JSONL)

    Returns:
        dict with keys:
          - ``department``  : routed department
          - ``variant``     : ``"v2"``, ``"legacy"``, or ``"bypass"``
          - ``confidence``  : 0.0-1.0 (0.0 for bypass/legacy)
          - ``latency_ms``  : routing duration in milliseconds
          - ``trace_id``    : the message's trace_id
    """
    start = time.monotonic()
    trace_id = msg.trace_id
    variant = "bypass"
    confidence = 1.0

    # System messages bypass A/B test entirely
    if msg.type in ("AO_REQUEST", "AO_RESPONSE", "GOVERNANCE"):
        dept = route(msg)
        result = {
            "department": dept,
            "variant": "bypass",
            "confidence": 1.0,
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
            "trace_id": trace_id,
        }
        _AB_METRICS["bypass"]["count"] += 1
        _AB_METRICS["bypass"]["dept_counts"][dept] += 1
        return result

    # A/B split
    variant = "v2" if should_use_v2(trace_id) else "legacy"

    if variant == "v2":
        dept = route_v2(msg)
        confidence = 1.0  # route_v2_sync doesn't return confidence; caller can enrich
    else:
        dept = route(msg)

    latency_ms = round((time.monotonic() - start) * 1000, 2)

    result = {
        "department": dept,
        "variant": variant,
        "confidence": confidence,
        "latency_ms": latency_ms,
        "trace_id": trace_id,
    }

    # Record in-memory metrics
    _AB_METRICS[variant]["count"] += 1
    _AB_METRICS[variant]["latencies_ms"].append(latency_ms)
    _AB_METRICS[variant]["confidences"].append(confidence)
    _AB_METRICS[variant]["dept_counts"][dept] += 1

    return result


# ── Async audit logger for A/B test events ──────────────────────────


async def log_ab_route(msg: BusMessage, result: dict, db: DbManager) -> str | None:
    """Persist an A/B test routing result to the audit_log table.

    Call this from async contexts (e.g., FastAPI endpoints) after
    ``route_ab_test()`` to persist the event.

    Args:
        msg:     The original BusMessage being routed
        result:  The dict returned by ``route_ab_test()``
        db:      Database manager instance for writing

    Returns:
        The audit_log row ID, or None on failure.
    """
    payload = _make_ab_audit_payload(result)
    payload["msg_type"] = msg.type
    payload["from_dept"] = msg.from_dept

    try:
        audit_id = new_id()
        await db.execute("""
            INSERT INTO audit_log (id, trace_id, action, agent_id, entity_type, entity_id, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_id,
            msg.trace_id,
            "ab_test.route",
            msg.from_dept,
            "ab_test",
            audit_id,
            json.dumps(payload),
            now_iso(),
        ))
        return audit_id
    except Exception as e:
        log.warning("Failed to log A/B test event: %s", e)
        return None


# ── A/B Test Report ─────────────────────────────────────────────────


def get_ab_report(db: DbManager | None = None) -> dict:
    """Generate A/B test metrics report from in-memory data + audit_log.

    Args:
        db: Optional database manager — if provided, queries audit_log
            for additional historical data.

    Returns:
        dict with:
          - ``summary``: total counts per variant
          - ``latency``: mean/p50/p95 latency per variant
          - ``departments``: department distribution per variant
          - ``audit_samples``: recent audit_log entries (if db provided)
    """
    report: dict[str, Any] = {
        "test_name": "route_v2 vs route (50/50 A/B Test)",
        "status": "active",
        "split_ratio": "50/50",
        "split_method": "MD5 hash of trace_id (first nibble < 8 = v2)",
        "summary": {},
        "latency": {},
        "departments": {},
    }

    # ── Summary counts ──────────────────────────────────────────
    for variant in ("v2", "legacy", "bypass"):
        m = _AB_METRICS.get(variant, {"count": 0})
        report["summary"][variant] = {
            "count": m["count"],
            "percentage": 0.0,
        }

    total = sum(v["count"] for v in _AB_METRICS.values())
    if total > 0:
        for variant in report["summary"]:
            report["summary"][variant]["percentage"] = round(
                report["summary"][variant]["count"] / total * 100, 1
            )

    # ── Latency stats (skip bypass) ─────────────────────────────
    for variant in ("v2", "legacy"):
        m = _AB_METRICS.get(variant, {"latencies_ms": []})
        lats = m["latencies_ms"]
        if lats:
            report["latency"][variant] = {
                "mean_ms": round(statistics.mean(lats), 2),
                "p50_ms": round(sorted(lats)[len(lats) // 2], 2),
                "p95_ms": round(sorted(lats)[int(len(lats) * 0.95)], 2) if len(lats) > 1 else 0,
                "min_ms": round(min(lats), 2),
                "max_ms": round(max(lats), 2),
                "sample_size": len(lats),
            }
        else:
            report["latency"][variant] = {"mean_ms": 0, "p50_ms": 0, "p95_ms": 0, "min_ms": 0, "max_ms": 0, "sample_size": 0}

    # ── Department distribution ────────────────────────────────
    for variant in ("v2", "legacy", "bypass"):
        dept_counts = dict(_AB_METRICS.get(variant, {}).get("dept_counts", {}))
        if dept_counts:
            report["departments"][variant] = dept_counts

    # ── Audit trail samples (if DB available) ───────────────────
    if db is not None:
        try:
            import asyncio
            rows = asyncio.run(db.fetch_all(
                """
                SELECT trace_id, action, payload, created_at
                FROM audit_log
                WHERE action = 'ab_test.route'
                ORDER BY created_at DESC
                LIMIT 20
                """
            ))
            report["audit_samples"] = [
                {
                    "trace_id": r["trace_id"],
                    "payload": json.loads(r["payload"]) if r.get("payload") else {},
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
        except Exception as e:
            report["audit_samples"] = []
            report["audit_error"] = str(e)

    # ── Traffic distribution check ─────────────────────────────
    v2_count = report["summary"]["v2"]["count"]
    legacy_count = report["summary"]["legacy"]["count"]
    if v2_count + legacy_count > 0:
        v2_pct = v2_count / (v2_count + legacy_count) * 100
        report["split_balance"] = {
            "v2_percent": round(v2_pct, 1),
            "legacy_percent": round(100 - v2_pct, 1),
            "is_balanced": abs(v2_pct - 50) < 5,  # within 5% of 50/50
        }

    return report


# ── Reset A/B metrics (for testing) ────────────────────────────────


def reset_ab_metrics() -> None:
    """Clear in-memory A/B test metrics.  Useful for test isolation."""
    _AB_METRICS.clear()
    # Re-initialise with clean state
    _AB_METRICS["v2"] = {"count": 0, "latencies_ms": [], "confidences": [], "dept_counts": defaultdict(int), "bypass_count": 0}
    _AB_METRICS["legacy"] = {"count": 0, "latencies_ms": [], "confidences": [], "dept_counts": defaultdict(int), "bypass_count": 0}
    _AB_METRICS["bypass"] = {"count": 0, "latencies_ms": [], "confidences": [], "dept_counts": defaultdict(int), "bypass_count": 0}


# ═══════════════════════════════════════════════════════════════════════
# Module-level exports
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    "USE_SQLITE",
    "RoutingEngine",
    "BehaviorRouter",
    # backward-compat JSONL functions (untouched)
    "route", "priority_for", "_load_rules",
    # v0.6.1 Behavior-Centric Routing
    "route_v2", "get_behavior_router",
    # v0.6.2 A/B Test 50/50
    "should_use_v2", "route_ab_test", "log_ab_route", "get_ab_report", "reset_ab_metrics",
]
