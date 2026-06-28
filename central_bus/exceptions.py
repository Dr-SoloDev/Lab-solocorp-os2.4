import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Any
from .models import BusMessage

Severity = str  # "LOW" | "MED" | "HIGH" | "CRITICAL"

ESCALATION_LOG = Path(__file__).parent.parent / "bus" / "system" / "escalations.jsonl"

_SEVERITY_KEYWORDS = {
    "CRITICAL": ["crash", "data loss", "security", "production down", "critical"],
    "HIGH":     ["failed", "error", "timeout", "exception", "high"],
    "MED":      ["warning", "degraded", "slow", "retry", "med"],
}

RETRY_DELAYS = [1, 5, 30]  # seconds


def classify(msg: BusMessage) -> Severity:
    text = " ".join(str(v) for v in msg.payload.values()).lower()
    for level in ("CRITICAL", "HIGH", "MED"):
        if any(kw in text for kw in _SEVERITY_KEYWORDS[level]):
            return level
    return "LOW"


def handle(msg: BusMessage, fn: Callable[[BusMessage], Any]) -> Any:
    """Execute fn(msg) with retry on failure. Escalates if all retries fail."""
    last_err = None
    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            return fn(msg)
        except Exception as exc:
            last_err = exc
            if attempt < len(RETRY_DELAYS):
                time.sleep(delay)
    # all retries exhausted
    severity = classify(msg)
    escalate(msg, severity, reason=str(last_err))
    raise last_err


def escalate(msg: BusMessage, severity: Severity, reason: str = "") -> None:
    """Log escalation. CRITICAL also triggers CEO notification."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "severity": severity,
        "message_id": msg.id,
        "trace_id": msg.trace_id,
        "project_id": msg.project_id,
        "from": msg.from_dept,
        "to": msg.to_dept,
        "reason": reason,
    }
    ESCALATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ESCALATION_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if severity == "CRITICAL":
        _notify_ceo(entry)


def _notify_ceo(entry: dict) -> None:
    """Write CEO alert to dedicated file (Telegram MCP hook reads this)."""
    alert_path = Path(__file__).parent.parent / "bus" / "system" / "ceo_alerts.jsonl"
    with open(alert_path, "a") as f:
        f.write(json.dumps({"alert": "CRITICAL", **entry}) + "\n")


def read_escalations() -> list[dict]:
    if not ESCALATION_LOG.exists():
        return []
    return [json.loads(l) for l in ESCALATION_LOG.read_text().splitlines() if l]
