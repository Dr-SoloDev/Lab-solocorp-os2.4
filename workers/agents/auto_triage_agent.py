#!/usr/bin/env python3
"""
🤖 Auto-Triage Agent — SoloCorp OS
Phase 8.2: Auto-classify + route request, L1-L2 auto-execute, L3+ propose

Behavior:
  1. Poll bus/queue/ for new entries
  2. Classify: priority + department (via keyword match + LLM fallback)
  3. Check escalation level (L1-L5)
  4. L1-L2: auto-create dispatch + route
  5. L3+: create structured proposal, leave for CEO
  6. L5: flag for Owner
"""

import json, os, re, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE = Path(__file__).parent.parent.parent
QUEUE_DIR = BASE / "bus/queue"
DISPATCH_DIR = BASE / "bus/dispatch"
PROFILES_DIR = BASE / "profiles"
STATE_FILE = QUEUE_DIR / ".triage_offset.json"

# ── Routing Table (mirror of rules/01-receive.md) ──────────────────────
ROUTING_TABLE = [
    # P0 — Critical (check first, more specific)
    (r"security|threat|incident|breach|vulnerability|hack|cyber|exploit|ransomware|ระบบล่ม|down|outage|ล้ม|เสียหาย", "cybersec", "P0"),
    (r"vision|strategy|decision|urgent.*decide|เปลี่ยน.*ทิศทาง", "ceo", "P0"),
    
    # P1 — High
    (r"การเงิน|งบ|budget|cost|ราคา|ลงทุน|invoice|payment|รายงาน.*เงิน|ต้นทุน", "cfo", "P1"),
    (r"การตลาด|marketing|brand|content|social|post|โฆษณา|โปรโมท", "cmo", "P1"),
    (r"pipeline|orchestrat|workflow|process|handoff|dispatch", "orchestrator", "P1"),
    (r"architecture|architect|bus|routing|system.*design|ออกแบบ.*ระบบ", "architect", "P1"),
    (r"product|feature|PRD|roadmap|user.*story|requirement|product.*plan", "product", "P1"),
    (r"code|implement|backend|frontend|api|database|dev|develop|implement|พัฒนา|เขียน.*code|deploy", "engineering", "P1"),
    (r"ออกแบบ|design|ux|visual|wireframe|figma|ดีไซน์|ui.*design", "design", "P1"),
    (r"sales|deal|customer.*meet|pipeline|proposal|ขาย|ลูกค้า.*ใหม่", "sales", "P1"),
    
    # P2 — Normal
    (r"ui|component|interface|pixel|layout|css|หน้า.*user", "ui_designer", "P2"),
    (r"test|qa|quality|bug|regression|verify|บั๊ก|test.*case", "qa", "P2"),
    (r"support|customer.*help|issue|problem|complaint|ลูกค้า.*ปัญหา", "support", "P2"),
    (r"legal|compliance|nda|regulation|กฏหมาย|contract.*review|legal.*review", "legal", "P2"),
    (r"blockchain|web3|solana|smart.*contract|defi|nft|เหรียญ|token|crypto", "web3", "P2"),
    (r"content|caption|image|video|copy|write|campaign|เนื้อหา| caption", "content_creator", "P2"),
    (r"network|cdn|vpn|dns|infra|latency|带宽|เน็ต|network.*issue", "neteng", "P2"),
    (r"psychology|behavior|bias|research.*user|emotion|จิตวิทยา|พฤติกรรม", "psychology", "P2"),
    
    # P3 — Low
    (r"research|prototype|experiment|rd|explore|poc|วิจัย|ทดลอง", "rd_lab", "P3"),
]

# ── L1-L5 Escalation by Priority ───────────────────────────────────────
PRIORITY_TO_LEVEL = {
    "P0": "L5",  # → Owner
    "P1": "L3",  # → Department Head
    "P2": "L2",  # → Specialist
    "P3": "L1",  # → Auto / Loop Runner
}

DEPARTMENT_ALIASES = {
    "ceo": ["ceo", "turbo", "เทอโบ"],
    "cfo": ["cfo", "meetoo", "finance"],
    "cmo": ["cmo", "mark", "มาร์ค", "marketing"],
    "orchestrator": ["orchestrator", "wut", "พี่วุฒิ"],
    "architect": ["architect", "songsak", "พี่ทรงศักดิ์"],
    "product": ["product", "produck", "โปรดัค"],
    "engineering": ["engineering", "changful", "ช่างฟูล", "dev"],
    "design": ["design", "kreet", "ครีเอท"],
    "ui_designer": ["ui", "ui designer"],
    "qa": ["qa"],
    "sales": ["sales", "เซลส์"],
    "support": ["support", "ซัพพอร์ต"],
    "legal": ["legal", "tulya", "ตุลย์"],
    "web3": ["web3", "aywa", "อัยวา"],
    "content_creator": ["content", "sek", "เสก"],
    "neteng": ["neteng", "neet", "นีต"],
    "cybersec": ["cybersec", "sai", "ซาย"],
    "psychology": ["psychology", "jit", "จิต"],
    "rd_lab": ["rd", "rd lab"],
}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, Exception):
            pass
    return {"last_file": "", "last_line": 0}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def classify(text: str) -> tuple[Optional[str], str, str]:
    """
    Returns (department_id, priority, reason).
    Uses keyword match; returns None if no match.
    """
    text_lower = text.lower()
    for pattern, dept, pri in ROUTING_TABLE:
        if re.search(pattern, text_lower):
            return dept, pri, f"keyword match: {pattern}"
    return None, "P2", "unclassified — fallback to CEO"


def resolve_head(department_id: str) -> str:
    """Get department head name from profile"""
    profile_path = PROFILES_DIR / f"*{department_id}*" / "SOUL.md"
    if not profile_path:
        # Try direct
        for p in sorted(PROFILES_DIR.iterdir()):
            if department_id in p.name:
                soul = p / "SOUL.md"
                if soul.exists():
                    for line in soul.read_text().split("\n"):
                        if "**ชื่อ:**" in line:
                            return line.split("**ชื่อ:**")[-1].strip()
    return department_id


def escalation_level(priority: str) -> str:
    return PRIORITY_TO_LEVEL.get(priority, "L2")


def poll_queue() -> list[dict]:
    """Read new entries from queue files since last offset"""
    state = load_state()
    new_entries = []
    
    for qfile in sorted(QUEUE_DIR.glob("*.jsonl")):
        fname = qfile.name
        # Skip if we've already processed this file and caught up
        if state["last_file"] and fname < state["last_file"]:
            continue
        
        lines = qfile.read_text().strip().split("\n")
        start_line = state["last_line"] if fname == state["last_file"] else 0
        
        for i in range(start_line, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entry["_source_file"] = fname
                entry["_line"] = i + 1
                new_entries.append(entry)
            except json.JSONDecodeError:
                continue
        
        state["last_file"] = fname
        state["last_line"] = len(lines)
    
    save_state(state)
    return new_entries


def auto_triage(entry: dict) -> dict:
    """
    Process a single queue entry.
    Returns action result.
    """
    content = json.dumps(entry)
    # Skip already-dispatched entries
    if entry.get("status") in ("dispatched", "completed", "done"):
        return {"dispatch_id": entry.get("dispatch_id", "?"), "status": "skipped", "reason": "already dispatched"}
    
    text = f"{entry.get('command', {}).get('title', '')} {entry.get('command', {}).get('description', '')} {entry.get('summary', '')}"
    if not text.strip():
        text = entry.get("dispatch_id", content)
    
    # 1. Classify
    dept, priority, reason = classify(text)
    
    # Check if already routed (entry has 'to' field)
    if not dept:
        dept = entry.get("to")
        if dept:
            # Resolve alias to canonical ID
            for canonical, aliases in DEPARTMENT_ALIASES.items():
                if dept.lower() in [a.lower() for a in aliases]:
                    dept = canonical
                    break
            reason = f"pre-routed to {dept}"
        else:
            dept = "ceo"
            reason = "fallback to CEO"
    
    # Preserve original priority if pre-routed
    if entry.get("to") and entry.get("priority"):
        priority = entry["priority"]
        reason += f" (priority from source: {priority})"
    
    # 2. Determine level
    level = escalation_level(priority)
    
    # 3. Build dispatch
    dispatch_id = entry.get("dispatch_id", f"TRIAGE-{uuid.uuid4().hex[:8]}")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # 4. Build action
    action = {
        "dispatch_id": dispatch_id,
        "source": entry.get("_source_file", "unknown"),
        "classified": {
            "department": dept,
            "priority": priority,
            "level": level,
            "reason": reason,
        },
        "status": "proposed" if level in ("L3", "L4", "L5") else "auto_dispatched",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # 5. For L1-L2 — auto-create dispatch file
    if level in ("L1", "L2"):
        dispatch_dir = DISPATCH_DIR / today
        dispatch_dir.mkdir(parents=True, exist_ok=True)
        dispatch_file = dispatch_dir / f"{dispatch_id}.json"
        
        dispatch_data = {
            "command": {
                "id": dispatch_id,
                "type": "AUTO_TRIAGE",
                "timestamp": action["timestamp"],
                "priority": priority,
                "from": "Auto-Triage Agent",
                "to": dept,
                "title": entry.get("command", {}).get("title", f"Auto-routed: {text[:60]}"),
                "context": f"Auto-triaged via {reason}",
                "tasks": entry.get("command", {}).get("tasks", []),
            },
            "status": "dispatched",
            "meta": action,
        }
        dispatch_file.write_text(json.dumps(dispatch_data, indent=2, ensure_ascii=False))
        action["dispatch_file"] = str(dispatch_file)
        action["status"] = "dispatched"
    
    # 6. For L3+ — create proposal
    if level in ("L3", "L4"):
        action["status"] = "proposed"
        action["proposal"] = (
            f"**Auto-Triage Proposal**\n"
            f"- Department: {dept}\n"
            f"- Priority: {priority} (Level: {level})\n"
            f"- Reason: {reason}\n"
            f"- Request: {text[:120]}\n"
            f"- **CEO approval needed** — auto-execute not authorized at L{level}"
        )
    
    # L5 — immediate flag for Owner
    if level == "L5":
        action["status"] = "owner_flag"
        action["owner_notice"] = f"🔴 **L5 ESCALATION — Owner needed**\n{text[:200]}"
    
    return action


def run_triage_cycle() -> list[dict]:
    """Run one triage cycle — poll + process all new entries"""
    entries = poll_queue()
    results = []
    for entry in entries:
        result = auto_triage(entry)
        results.append(result)
    return results


# ── CLI Mode ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    
    if "--watch" in sys.argv:
        print("🤖 Auto-Triage Agent — watching bus/queue/...")
        print("  Press Ctrl+C to stop")
        try:
            while True:
                results = run_triage_cycle()
                for r in results:
                    icon = {"dispatched": "✅", "proposed": "📋", "owner_flag": "🔴", "pending": "⏳"}.get(r["status"], "❓")
                    print(f"  {icon} {r['dispatch_id']} → {r['classified']['department']} [{r['classified']['level']}] — {r['status']}")
                time.sleep(30)
        except KeyboardInterrupt:
            print("\n👋 Auto-Triage Agent stopped")
    else:
        # One-shot
        results = run_triage_cycle()
        print(json.dumps(results, indent=2, ensure_ascii=False))
