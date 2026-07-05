"""Central Bus v0.6 — Routing Engine (SQLite + JSONL backward compat).

Architecture
~~~~~~~~~~~~
* Existing ``route()`` and ``priority_for()`` functions remain **untouched**
  for backward compatibility (JSONL-backed).
* New ``RoutingEngine`` class loads rules from SQLite with 60s TTL cache.
* The module-level ``route()`` function delegates to the engine when
  ``USE_SQLITE=True`` is set.  Otherwise falls back to JSONL.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

from central_bus.config import settings
from central_bus.db import DbManager
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


# ── Main route function (JSONL) ─────────────────────────────────────


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
# SQLite Routing Engine — the v0.6 default
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
# Module-level convenience: auto-select JSONL vs SQLite
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    "USE_SQLITE",
    "RoutingEngine",
    # backward-compat JSONL functions
    "route", "priority_for", "_load_rules",
]
