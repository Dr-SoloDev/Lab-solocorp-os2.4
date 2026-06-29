import json
import subprocess
from datetime import timedelta
from pathlib import Path
from ..runner import Loop


def _finance(op: str) -> dict:
    r = subprocess.run(
        [str(Path.home() / ".local/bin/mcp-fallback-finance"), op],
        capture_output=True, text=True, timeout=10,
    )
    try:
        return json.loads(r.stdout) if r.returncode == 0 else {}
    except json.JSONDecodeError:
        return {}


class SubscriptionAuditLoop(Loop):
    loop_id = "subscription_audit"
    interval = timedelta(days=30)
    trust_level = 4  # L4 — auto-execute: ตัด unused >3 months
    model_hint = "glm-5.2"  # cron — pattern matching + report, no heavy reasoning

    def run(self) -> str:
        transactions = _finance("list_transactions")
        items = transactions.get("items", transactions.get("transactions", []))

        # Flag recurring expenses with no recent usage signal
        # (heuristic: transaction description contains sub/subscription/saas)
        suspects = [
            t for t in items
            if any(k in str(t).lower() for k in ("subscription", "monthly", "saas", "plan"))
        ]

        if not suspects:
            return "✅ Subscription audit: no suspects found"

        lines = ["## CFO Subscription Audit", f"Found {len(suspects)} recurring charges:"]
        for t in suspects[:10]:
            name = t.get("description") or t.get("name", "?")
            amount = t.get("amount", "?")
            lines.append(f"  - {name}: {amount}")
        lines.append("→ Review with meetoo (CFO)")
        return "\n".join(lines)
