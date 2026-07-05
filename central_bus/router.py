import json
import re
from pathlib import Path
from .models import BusMessage, Department, Priority
from .semantic import TfidfRouter

RULES_PATH = Path(__file__).parent.parent / "bus" / "system" / "routing_rules.json"

_router: TfidfRouter | None = None


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
    """Route a GOVERNANCE-type message based on gov_event field.

    Rules:
        - ``guard_failed``    → orchestrator (needs escalation triage)
        - ``rfc_created``     → orchestrator (broadcast dispatch via orchestrator)
        - ``complexity_assessed`` → architect (score is an architectural artifact)
        - ``adr_accepted``    → architect (ADR is architect's domain)
        - ``guard_run``       → architect (guard execution is initiated by architect)
    """
    gov_event: str = msg.payload.get("gov_event", "")
    gov_detail: str = msg.payload.get("gov_detail", "")

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
        # Unknown governance event → architect as default
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


# ── Main route function ──────────────────────────────────────────────


def route(msg: BusMessage) -> Department:
    """Match message payload to destination department.

    Three-tier matching with governance pre-route:
      0. If message type is GOVERNANCE → governance routing rules (see _route_governance)
      1. Keyword matching (fast path) — exact word-boundary match
      2. Semantic matching (TF-IDF + cosine similarity) — fallback
      3. CEO fallback — ultimate fallback
    """
    # Tier 0a: AO message routing
    if msg.type == "AO_REQUEST":
        # AO_REQUEST from any dept → architect (to bridge to AO CLI)
        return "architect"
    if msg.type == "AO_RESPONSE":
        # AO_RESPONSE from architect → reply to original requester
        return msg.to_dept

    # Tier 0b: Governance event routing
    if msg.type == "GOVERNANCE":
        return _route_governance(msg)

    rules = _load_rules()
    text = " ".join(str(v) for v in msg.payload.values()).lower()

    # Tier 1: keyword matching (fast path) — skip for Thai text (no reliable word boundaries)
    if not _has_thai(text):
        for rule in rules["rules"]:
            if rule.get("is_fallback"):
                continue
            if any(_matches(kw, text) for kw in rule["trigger"]["keywords"]):
                return rule["route_to"]

    # Tier 2: semantic matching (works for both Thai and English via char n-grams)
    sr = _get_semantic_router()
    dept = sr.match(text)
    if dept is not None:
        return dept

    # Tier 3: CEO fallback
    return next(r["route_to"] for r in rules["rules"] if r.get("is_fallback"))


def priority_for(dept: Department, msg: BusMessage | None = None) -> Priority:
    """Determine priority for a department or message.

    If a BusMessage is provided, governance events can override the default priority.
    """
    if msg is not None:
        gov_prio = _governance_priority(msg)
        if gov_prio is not None:
            return gov_prio

    rules = _load_rules()
    for rule in rules["rules"]:
        if rule["route_to"] == dept and not rule.get("is_fallback"):
            return rule["priority"]
    return "normal"
