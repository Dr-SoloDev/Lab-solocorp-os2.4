#!/usr/bin/env python3
"""
🧠 Auto-Brain Summary — SoloCorp OS (Phase 8.5)
Auto-summarize session context สิ้น session
Usage:
    python scripts/session-bootstrap.py --summary
    # → generates structured summary + appends to session-log.md
"""

import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
BRAIN_DIR = BASE / "brain"
DISPATCH_DIR = BASE / "bus/dispatch"
STATE_DIR = BASE / "bus/state"

def _git(cmd):
    r = subprocess.run(["git", "-C", str(BASE)] + cmd, capture_output=True, text=True)
    return r.stdout.strip()

def auto_summary() -> dict:
    """Generate structured summary of current session"""
    
    commits = _git(["log", "--oneline", "-10"])
    dirty = _git(["status", "--porcelain"])
    
    # Check what changed
    changed = []
    if dirty:
        for line in dirty.split("\n"):
            line = line.strip()
            if line:
                changed.append(line)
    
    # Count active dispatches
    active_dispatch_files = 0
    if DISPATCH_DIR.exists():
        for date_dir in DISPATCH_DIR.iterdir():
            if date_dir.is_dir():
                active_dispatch_files += len(list(date_dir.glob("*.json")))
    
    # Check state files
    state_files = list(STATE_DIR.glob("*.json")) if STATE_DIR.exists() else []
    
    # Read last session
    last_mode = ""
    last_decisions = []
    log_file = BRAIN_DIR / "session-log.md"
    if log_file.exists():
        text = log_file.read_text()
        sessions = text.split("## Session #")
        if len(sessions) >= 2:
            latest = sessions[-1]
            for line in latest.split("\n"):
                if "**Mode:**" in line:
                    last_mode = line.split("**Mode:**")[-1].strip()
                if line.strip().startswith("|") and len(line.split("|")) >= 4:
                    parts = [p.strip() for p in line.split("|")]
                    if parts[1].isdigit() and len(parts) > 2:
                        last_decisions.append(parts[2])
    
    # Read pending from brain
    pending = []
    mem_file = BRAIN_DIR / "ceo-memory.json"
    if mem_file.exists():
        try:
            data = json.loads(mem_file.read_text())
            sessions = data.get("sessions", [])
            if sessions:
                pending = sessions[-1].get("pending_next", [])
        except (json.JSONDecodeError, IndexError, KeyError):
            pass
    
    summary = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "git": {
            "recent_commits": commits[:500],
            "uncommitted": len([c for c in changed if c]),
        },
        "state": {
            "active_dispatch_files": active_dispatch_files,
            "state_tracking_files": len(state_files),
        },
        "brain": {
            "last_mode": last_mode,
            "pending_items": pending,
        },
    }
    
    return summary


def format_summary(data: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"## Session Auto-Summary — {now}",
        "",
        "### Git",
        f"```",
        f"{data['git']['recent_commits']}",
        f"```",
        f"Uncommitted: {data['git']['uncommitted']} files",
        "",
        "### State",
        f"Active dispatch files: {data['state']['active_dispatch_files']}",
        f"State tracking files: {data['state']['state_tracking_files']}",
        "",
    ]
    
    pending = data['brain'].get('pending_items', [])
    if pending:
        lines.append("### Pending")
        lines.extend(f"- {p}" for p in pending)
    
    return "\n".join(lines)


if __name__ == "__main__":
    data = auto_summary()
    
    if "--json" in sys.argv:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif "--save" in sys.argv:
        # Append to session-log.md
        summary_text = format_summary(data)
        log_file = BRAIN_DIR / "session-log.md"
        with open(log_file, "a") as f:
            f.write("\n" + summary_text + "\n\n---\n")
        print(f"✅ Summary appended to {log_file}")
    else:
        print(format_summary(data))
