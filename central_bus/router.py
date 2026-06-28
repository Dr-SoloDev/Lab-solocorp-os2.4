import json
import re
from pathlib import Path
from .models import BusMessage, Department, Priority

RULES_PATH = Path(__file__).parent.parent / "bus" / "system" / "routing_rules.json"


def _load_rules() -> dict:
    return json.loads(RULES_PATH.read_text())


def _matches(keyword: str, text: str) -> bool:
    return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text))


def route(msg: BusMessage) -> Department:
    """Match message payload text to routing rules, return destination department."""
    rules = _load_rules()
    text = " ".join(str(v) for v in msg.payload.values()).lower()

    for rule in rules["rules"]:
        if rule.get("is_fallback"):
            continue
        if any(_matches(kw, text) for kw in rule["trigger"]["keywords"]):
            return rule["route_to"]

    # fallback
    return next(r["route_to"] for r in rules["rules"] if r.get("is_fallback"))


def priority_for(dept: Department) -> Priority:
    rules = _load_rules()
    for rule in rules["rules"]:
        if rule["route_to"] == dept and not rule.get("is_fallback"):
            return rule["priority"]
    return "normal"
