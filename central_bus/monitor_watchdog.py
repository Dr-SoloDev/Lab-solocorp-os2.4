"""
Monitor Watchdog — Real-time Event Listener
พี่ทรงศักดิ์ (Orchestrator) · Step 2 of Event-Driven Architecture

Replaces: cron polling (loop-runner every 30min)
With:     real-time queue consumption + routing.yaml-based notifications

Architecture:
  Central Bus Queue → Monitor Watchdog → routing.yaml → Notify Department
                                              │
                          ┌───────────────────┼───────────────────┐
                          ↓                   ↓                   ↓
                       🧪 QA              📋 Product          👑 CEO
                   "有新代码"           "PR needs review"   "Deploy done"

Key difference from old cron:
  OLD: Loop Runner polls state.json every 30 min → reads all → decides action
  NEW: Watchdog consumes queue events as they arrive → immediate routing
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from .models import BusMessage, Department, Priority
from .queue import dequeue, drain, requeue, list_dead_letters

# Notification channels
NOTIFY_VIA = ["hermes_cron", "stdout"]


def load_routing_yaml() -> dict:
    """Load routing.yaml for department notification rules."""
    paths = [
        Path(__file__).parent.parent / "bus" / "system" / "routing_events.json",
        Path.home() / ".hermes" / "profiles" / "04-orchestrator" / "routing.yaml",
    ]
    for p in paths:
        if p.exists():
            if p.suffix == ".json":
                return json.loads(p.read_text())
    # Default routing
    return {
        "engineering": {"notify": ["qa", "product"], "on": ["push", "pr_merged"]},
        "qa": {"notify": ["engineering", "ceo"], "on": ["gate_pass", "gate_fail"]},
        "deploy": {"notify": ["ceo", "cmo"], "on": ["deployed"]},
    }


def _resolve_skills_dir() -> Path:
    """Find Hermes skills directory."""
    candidates = [
        Path.home() / ".hermes" / "skills",
        Path(__file__).parent.parent / "skills",
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path.home() / ".hermes" / "skills"


def notify_department(dept: Department, msg: BusMessage, action: str) -> bool:
    """Notify a department about a Central Bus event.

    Writes to department's notification channel:
    - Hermes cron output file (picked up by next cron tick)
    - stdout (for immediate CLI visibility)
    - Future: Telegram/Discord via Hermes Gateway API
    """
    notification = {
        "event": "central_bus_notification",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from_dept": msg.from_dept,
        "to_dept": msg.to_dept,
        "action": action,
        "project": msg.project_id,
        "phase": msg.phase,
        "summary": msg.payload.get("text", ""),
        "trace_id": msg.trace_id,
        "priority": msg.priority,
    }

    # Channel 1: stdout (immediate visibility)
    if "stdout" in NOTIFY_VIA:
        icon = {"qa": "🧪", "product": "📋", "ceo": "👑", "cmo": "📢", "engineering": "🔧"}.get(dept, "📨")
        print(f"  {icon} [{dept.upper()}] {action}: {notification['summary'][:100]}", file=sys.stderr)

    # Channel 2: Hermes cron output file
    if "hermes_cron" in NOTIFY_VIA:
        cron_dir = Path.home() / ".hermes" / "cron" / "output"
        cron_dir.mkdir(parents=True, exist_ok=True)
        notify_file = cron_dir / f"watchdog_{dept}.jsonl"
        with open(notify_file, "a") as f:
            f.write(json.dumps(notification, ensure_ascii=False) + "\n")

    return True


def process_queue(max_messages: int = 10) -> int:
    """Consume Central Bus queue and route notifications.

    Priority order: critical → high → normal → low
    Returns: number of messages processed
    """
    routing = load_routing_yaml()
    processed = 0

    for priority in ["critical", "high", "normal", "low"]:
        msgs = drain(priority)  # type: ignore[arg-type]
        for msg in msgs:
            # Route to target department
            target = msg.to_dept if msg.to_dept else "qa"  # default: QA

            # Determine action from payload
            event = msg.payload.get("event", "")
            if "push" in event:
                action = "code_committed"
            elif "merged" in event:
                action = "pr_merged"
            elif "pull_request" in event:
                action = "pr_opened"
            else:
                action = "check_queue"

            # Notify target department + any routing.yaml subscribers
            subscribers = routing.get(msg.from_dept, {}).get("notify", [target])
            for dept in set([target] + list(subscribers)):
                notify_department(dept, msg, action)  # type: ignore[arg-type]

            processed += 1

    return processed


def check_dead_letters() -> list[dict]:
    """Check dead letter queue for stuck messages."""
    return list_dead_letters()


def watchdog_loop(max_iterations: int = 10):
    """Main watchdog loop — consume and route continuously.

    For production, this runs as:
      - Hermes cron: watchdog cron job (every 1 min)
      - Standalone:  python -m central_bus.monitor_watchdog
    """
    total = 0
    for _ in range(max_iterations):
        processed = process_queue(max_messages=5)
        if processed == 0:
            break
        total += processed

    # Check dead letters (stuck messages)
    stuck = check_dead_letters()
    if stuck:
        print(f"  ⚠️  Dead letters: {len(stuck)}", file=sys.stderr)
        for item in stuck[-3:]:  # Show last 3
            print(f"     - {item.get('reason', 'unknown')}: {item.get('message', {}).get('trace_id', '?')[:20]}", file=sys.stderr)

    return total


if __name__ == "__main__":
    processed = watchdog_loop()
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] Watchdog processed {processed} messages", file=sys.stderr)
