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


def route(msg: BusMessage) -> Department:
    """Match message payload to destination department.

    Two-tier matching:
      1. Keyword matching (fast path) — exact word-boundary match
      2. Semantic matching (TF-IDF + cosine similarity) — fallback
      3. CEO fallback — ultimate fallback
    """
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


def priority_for(dept: Department) -> Priority:
    rules = _load_rules()
    for rule in rules["rules"]:
        if rule["route_to"] == dept and not rule.get("is_fallback"):
            return rule["priority"]
    return "normal"
