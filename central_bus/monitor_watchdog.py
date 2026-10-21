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
from datetime import datetime, timedelta, timezone
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


def check_model_health(use_cache: bool = True) -> dict:
    """ตรวจว่าโมเดลใน LLM fallback chain ยังมีอยู่จริงไหม

    โมเดลฟรีของ opencode ถูกเปลี่ยนชื่อ/ลบไปเรื่อย ๆ → ทุกโมเดลคืน
    "empty response" → agent 19 ตัว "ตาบอด" โดยไม่มี error ชัดเจน
    ตัวตรวจนี้กันไม่ให้เกิดซ้ำแบบเงียบ ๆ (ดู ADR-021)

    Returns:
        dict: ผลจาก workers.llm_provider.audit_models()
              + {"skipped": True, "error": str} เมื่อตรวจไม่ได้
    """
    try:
        from workers.llm_provider import audit_models
    except Exception as e:  # pragma: no cover
        return {"ok": True, "skipped": True, "error": f"import ไม่ได้: {e}"}

    try:
        report = audit_models(use_cache=use_cache)
    except Exception as e:  # pragma: no cover
        return {"ok": True, "skipped": True, "error": f"ตรวจไม่ได้: {e}"}

    return report


def check_dead_letters() -> list[dict]:
    """Check dead letter queue for stuck messages."""
    return list_dead_letters()


# ── Orphan detection (กัน "ตายเงียบ") ────────────────────────────────
# ข้อความที่ยัง pending/routed แต่ target_agent ไม่มีในรายชื่อที่ worker
# service ลงทะเบียนไว้ → ไม่มีใครมารับ → จะค้างตลอดไปโดยไม่มีใครรู้
# (เจอกรณีนี้จริง: skill dispatch เขียน target เป็น "ชื่อแผนก" ไม่ใช่ agent_id
#  → 19 ข้อความค้างเงียบ ๆ ตั้งแต่ ก.ค. — ดู ADR-019)

_ORPHAN_STUCK_MINUTES = 15


def _registered_agent_ids() -> set[str]:
    """รายชื่อ agent ที่ worker service ลงทะเบียนไว้ (consumer ตัวจริง)"""
    try:
        from workers.agent_worker_service import AGENT_IDS
        return set(AGENT_IDS)
    except Exception:
        return set()


def check_orphaned_messages(minutes: int = _ORPHAN_STUCK_MINUTES) -> list[dict]:
    """หาข้อความที่ค้างและไม่มีใครจะมารับ (silent failure guard)

    คืน list ของ dict: {id, agent_id, target_agent, status, age_minutes, reason}
    """
    import sqlite3

    from central_bus.config import settings

    db_file = Path(settings.db_path)
    if not db_file.is_absolute():
        db_file = Path(__file__).parent.parent / db_file
    if not db_file.exists():
        return []

    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=minutes)
    ).isoformat()

    try:
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(
            "SELECT id, agent_id, target_agent, status, created_at "
            "FROM queue WHERE status IN ('pending','routed') AND created_at < ? "
            "ORDER BY created_at ASC",
            (cutoff,),
        )]
        conn.close()
    except Exception as e:
        print(f"  ⚠️ orphan check failed: {e}", file=sys.stderr)
        return []

    known = _registered_agent_ids()
    orphans: list[dict] = []
    for r in rows:
        target = r.get("target_agent")
        age = 0
        try:
            created = datetime.fromisoformat(r.get("created_at", ""))
            age = int((datetime.now(timezone.utc) - created).total_seconds() // 60)
        except Exception:
            pass
        if not target:
            reason = "ไม่มี target_agent — ไม่มีใครรู้ว่าจะส่งให้ใคร"
        elif known and target not in known:
            reason = f"target_agent '{target}' ไม่มีในรายชื่อ agent ที่ลงทะเบียน"
        else:
            reason = (
                f"ค้างมา {age} นาที ยังไม่มี worker หยิบ "
                "(worker service ไม่ได้รัน?)"
            )
        orphans.append({
            "id": r["id"],
            "agent_id": r.get("agent_id"),
            "target_agent": target,
            "status": r.get("status"),
            "age_minutes": age,
            "reason": reason,
        })
    return orphans


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
