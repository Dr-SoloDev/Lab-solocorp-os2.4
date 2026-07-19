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
* NEW ``route_v2()`` — non-destructive: Tier 0 Behavior → fallback to route().
* Existing ``route()``, ``RoutingEngine``, ``priority_for()`` untouched.
"""

from __future__ import annotations

import json
import logging
import re
import time
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
    return bool(re.search(r"[ก-๙]", s))


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
    """SQLite-backed routing rule engine with 60s TTL cache.

    Loads routing rules from the ``routing_rules`` table and
    caches them in memory.  The cache is refreshed when ``_last_refresh``
    exceeds 60 seconds.
    """

    def __init__(self, db: DbManager) -> None:
        self._db = db
        self._cache: list[dict[str, Any]] = []
        self._last_refresh: float = 0.0
        self._ttl: float = 60.0

    # ── Cache management ──────────────────────────────────────────

    async def _load_rules(self) -> list[dict[str, Any]]:
        """Load rules from SQLite, refreshing cache if TTL expired."""
        now = time.monotonic()
        if self._cache and (now - self._last_refresh) < self._ttl:
            return self._cache

        rows = await self._db.fetch_all(
            "SELECT * FROM routing_rules WHERE enabled = 1 ORDER BY priority DESC"
        )
        self._cache = [dict(r) for r in rows]
        self._last_refresh = now
        log.debug("RoutingEngine: loaded %d rules (cache refresh)", len(self._cache))
        return self._cache

    async def invalidate_cache(self) -> None:
        """Force a cache refresh on the next call."""
        self._last_refresh = 0.0

    # ── Core matching ─────────────────────────────────────────────

    async def match(
        self,
        source_agent: str,
        payload: dict[str, Any],
        *,
        fallback_department: str = "ceo",
    ) -> str:
        """Match a message against routing rules.

        Matching priority:
          1. ``source_agent`` matches ``source_agent`` regex pattern
          2. If rule has a ``condition`` JSON predicate, evaluate it
             against payload
          3. Return ``target_department`` of the highest-priority matching
             rule
          4. If no rule matches, return ``fallback_department``
        """
        rules = await self._load_rules()

        for rule in rules:
            # Step 1: match source_agent regex
            agent_pattern = rule.get("source_agent", "")
            if agent_pattern and not re.search(agent_pattern, source_agent):
                continue

            # Step 2: evaluate condition predicate (if present)
            condition_str = rule.get("condition")
            if condition_str:
                try:
                    condition = json.loads(condition_str)
                    if not self._evaluate_condition(condition, payload):
                        continue
                except (json.JSONDecodeError, TypeError):
                    log.warning(
                        "Invalid condition JSON for rule %s", rule.get("id")
                    )

            # Match found
            return rule.get("target_department", fallback_department)

        # Fallback
        return fallback_department

    async def count_rules(self) -> int:
        """Return the number of enabled routing rules."""
        rules = await self._load_rules()
        return len(rules)

    # ── Admin helpers ─────────────────────────────────────────────

    @staticmethod
    def _evaluate_condition(
        condition: dict[str, Any],
        payload: dict[str, Any],
    ) -> bool:
        """Evaluate a simple condition predicate against payload.

        Supports:
          - ``{"field": "key", "equals": "value"}``
          - ``{"field": "key", "contains": "substring"}``
          - ``{"field": "key", "exists": true/false}``
          - ``{"and": [cond1, cond2, ...]}``
          - ``{"or": [cond1, cond2, ...]}``
        """
        if "and" in condition:
            return all(
                RoutingEngine._evaluate_condition(c, payload) for c in condition["and"]
            )
        if "or" in condition:
            return any(
                RoutingEngine._evaluate_condition(c, payload) for c in condition["or"]
            )

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
# Sits BEFORE existing route() — classifies intent into behavior,
# then routes to the matching department.
#
# Flow:
#   route_v2(msg):
#     1. AO/GOVERNANCE bypass → existing route()
#     2. BehaviorClassifier.classify(payload_text)
#        → confidence >= 0.9 → route to behavior's primary_dept
#        → confidence < 0.9 → fallback to route()
# ═══════════════════════════════════════════════════════════════════════


class BehaviorRouter:
    """Behavior-Centric Router — Tier 0 wrapper around BehaviorClassifier.

    Adds behavior classification BEFORE the existing keyword/semantic/CEO
    routing pipeline.  Uses the centralized ``behavior_classifier`` module
    and DB-backed route mapping.

    Usage::

        router = BehaviorRouter(db=db, classifier=classifier)
        dept = await router.route_v2(msg)          # async
        dept = router.route_v2_sync(payload_text)   # sync
    """

    def __init__(
        self,
        db: DbManager | None = None,
        classifier=None,
    ) -> None:
        self._db = db
        self._classifier = classifier
        self._route_cache: dict[str, str] = {}  # behavior_name -> dept
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 120.0

    # ── Route cache ──────────────────────────────────────────────

    async def _load_route_map(self) -> dict[str, str]:
        """Load behavior_name -> primary_dept from DB, with cache."""
        now = time.monotonic()
        if self._route_cache and (now - self._cache_ts) < self._cache_ttl:
            return self._route_cache

        if self._db is None:
            # Fallback to static BEHAVIOR_DEPT_MAP
            from central_bus.behavior_classifier import BEHAVIOR_DEPT_MAP
            self._route_cache = BEHAVIOR_DEPT_MAP
            return self._route_cache

        try:
            rows = await self._db.fetch_all(
                """
                SELECT bt.behavior_name, brm.primary_dept
                FROM behavior_route_map brm
                JOIN behavior_taxonomy bt ON bt.id = brm.behavior_id
                WHERE bt.is_active = 1
                """
            )
            self._route_cache = {r["behavior_name"]: r["primary_dept"] for r in rows}
            self._cache_ts = now
            log.debug("BehaviorRouter: loaded %d route mappings", len(self._route_cache))
        except Exception:
            log.warning("Failed to load route map from DB — using static map")
            from central_bus.behavior_classifier import BEHAVIOR_DEPT_MAP
            self._route_cache = BEHAVIOR_DEPT_MAP

        return self._route_cache

    async def invalidate_route_cache(self) -> None:
        """Force refresh of route map cache."""
        self._cache_ts = 0.0

    # ── Getters for classifier ───────────────────────────────────

    @property
    def classifier(self):
        """Lazy-load the BehaviorClassifier singleton."""
        if self._classifier is None:
            from central_bus.behavior_classifier import get_classifier
            self._classifier = get_classifier()
        return self._classifier

    # ── Async route_v2 (for SQLite RoutingEngine consumers) ──────

    async def route_v2(
        self,
        msg: BusMessage,
        *,
        fallback_department: str = "ceo",
        audit: bool = False,
    ) -> Department:
        """Full routing pipeline: Tier 0 (Behavior) → existing route().

        Args:
            msg: The BusMessage to route
            fallback_department: Fallback if nothing matches
            audit: If True, logs classification result to DB audit_log

        Returns:
            Department name (string)
        """
        # Bypass: AO/GOVERNANCE messages skip behavior classifier
        if msg.type in ("AO_REQUEST", "AO_RESPONSE", "GOVERNANCE"):
            return route(msg)

        # Extract text from payload for classification
        payload_text = self._extract_text(msg)
        if not payload_text:
            return route(msg)

        # Tier 0: Behavior Classification
        behavior_id, confidence = self.classifier.classify(payload_text)

        if confidence >= 0.9:
            # High confidence — route directly
            route_map = await self._load_route_map()
            dept = route_map.get(behavior_id, fallback_department)

            if audit and self._db:
                await self._audit_classification(msg, behavior_id, dept, confidence)

            log.debug(
                "BehaviorRouter: classified '%s' as '%s' (%.3f) → %s",
                payload_text[:60], behavior_id, confidence, dept,
            )
            return dept

        # Confidence < 0.9 — fallback to existing route()
        if audit and self._db:
            await self._audit_classification(
                msg, behavior_id, "fallback", confidence
            )

        log.debug(
            "BehaviorRouter: low confidence (%.3f) — falling back to route()",
            confidence,
        )
        return route(msg)

    # ── Sync route_v2 (for JSONL consumers) ──────────────────────

    def route_v2_sync(
        self,
        payload_text: str,
        *,
        fallback_department: str = "ceo",
    ) -> str:
        """Sync version: classify payload text → department.

        For use in synchronous code paths (e.g., test assertions).
        Falls back to a static department map (no DB dependency).
        """
        if not payload_text:
            return fallback_department

        behavior_id, confidence = self.classifier.classify(payload_text)

        if confidence >= 0.9:
            from central_bus.behavior_classifier import BEHAVIOR_DEPT_MAP
            return BEHAVIOR_DEPT_MAP.get(behavior_id, fallback_department)

        return fallback_department

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _extract_text(msg: BusMessage) -> str:
        """Extract plain text from a BusMessage payload for classification."""
        parts = []

        # Common fields to include
        for key in ("text", "message", "description", "title", "detail", "content", "query", "request"):
            val = msg.payload.get(key)
            if isinstance(val, str):
                parts.append(val)

        # If no structured text, serialize all payload values
        if not parts:
            parts = [str(v) for v in msg.payload.values() if isinstance(v, (str, int, float))]

        return " ".join(parts) if parts else ""

    async def _audit_classification(
        self,
        msg: BusMessage,
        behavior: str,
        dept: str,
        confidence: float,
    ) -> None:
        """Log behavior classification result to audit trail."""
        if not self._db:
            return
        try:
            await self._db.execute(
                """
                INSERT INTO audit_log (id, trace_id, action, agent_id, entity_type, entity_id, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id(),
                    msg.trace_id,
                    "behavior.classify",
                    msg.from_dept,
                    "behavior",
                    behavior,
                    json.dumps({
                        "behavior": behavior,
                        "route_to": dept,
                        "confidence": confidence,
                        "auto_routed": confidence >= 0.9,
                    }),
                    now_iso(),
                ),
            )
        except Exception as e:
            log.warning("Failed to audit behavior classification: %s", e)


# ── Module-level convenience: route_v2 ──────────────────────────────

_behavior_router: BehaviorRouter | None = None


def get_behavior_router(
    db: DbManager | None = None,
    classifier=None,
) -> BehaviorRouter:
    """Get or create the BehaviorRouter singleton."""
    global _behavior_router
    if _behavior_router is None:
        _behavior_router = BehaviorRouter(db=db, classifier=classifier)
    return _behavior_router


def route_v2(
    msg: BusMessage,
    *,
    fallback_department: str = "ceo",
    audit: bool = False,
    db: DbManager | None = None,
) -> Department:
    """Convenience: route with Behavior Tier 0 (sync wrapper).

    Uses default BehaviorRouter singleton.
    For async callers, use BehaviorRouter.route_v2() directly.
    """
    router = get_behavior_router(db=db)
    # Note: the audit log uses the sync path — no DB write in sync mode
    return router.route_v2_sync(
        BehaviorRouter._extract_text(msg),
        fallback_department=fallback_department,
    )


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
]
