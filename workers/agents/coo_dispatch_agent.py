#!/usr/bin/env python3
"""
COO Dispatch Agent — กิจ (Kit)
=================================
หน้าที่: รับ L1-L3 request → triage → assign → status report
Owner ไม่ต้องเห็น L1-L3 = ทำงานสำเร็จ

Flow:
  1. อ่าน current queue (bus/dispatch/)
  2. classify priority + department
  3. L1-L2 → auto-assign → department heads
  4. L3 → COO review → assign
  5. L4+ → escalate to CEO
  6. Generate daily ops status report
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DISPATCH_DIR = BASE_DIR / "bus" / "dispatch"
ROUTING_RULES = BASE_DIR / "bus" / "system" / "routing_rules.json"
LOG_FILE = BASE_DIR / "bus" / "logs" / "coo-dispatch.log"

# ── Department mapping ──
DEPT_MAP = {
    "cfo": "02-cfo",
    "cmo": "03-cmo",
    "orchestrator": "04-orchestrator",
    "architect": "05-architect",
    "product": "06-product",
    "engineering": "07-engineering",
    "design": "08-design",
    "ui_designer": "09-ui-designer",
    "qa": "10-qa",
    "sales": "11-sales",
    "support": "12-support",
    "legal": "13-legal",
    "web3": "14-web3",
    "content_creator": "15-content-creator",
    "coo": "02-coo",
    "ceo": "01-ceo",
}

# ── Priority mapping ──
PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}

LEVEL_MAP = {
    "L5": {"action": "🚩 Owner เท่านั้น", "auto": False},
    "L4": {"action": "📋 CEO ตัดสิน → รายงาน Owner", "auto": False},
    "L3": {"action": "👷 COO จัดการ → รายงาน CEO", "auto": False},
    "L2": {"action": "🏢 Department Heads → COO รับรู้", "auto": True},
    "L1": {"action": "🤖 Auto / Loop Runner", "auto": True},
}


def load_routing_rules():
    """โหลด routing rules"""
    with open(ROUTING_RULES) as f:
        return json.load(f)


# ── L5/L4 escalation keywords (ตรวจก่อน department match) ──
ESCALATION_KEYWORDS = {
    "L5": {
        "keywords": ["vision", "core product", "rewrite", "restructure org", "เปลี่ยน core product",
                     "pivot", "company direction", "mission change", "org structure"],
        "route_to": "ceo",
        "note": "L5 — Owner only",
    },
    "L4": {
        "keywords": ["budget approval", "อนุมัติ budget", "roadmap shift", "cross-dept strategy",
                     "季度策略", "annual plan", "strategic partnership"],
        "route_to": "ceo",
        "note": "L4 — CEO decide",
    },
}


def detect_level(text_lower: str) -> dict | None:
    """check L5/L4 escalation keywords ก่อน"""
    for level, cfg in ESCALATION_KEYWORDS.items():
        for kw in cfg["keywords"]:
            kw_lower = kw.lower()
            if " " in kw_lower:
                matched = kw_lower in text_lower
            else:
                matched = bool(re.search(r'\b' + re.escape(kw_lower) + r'\b', text_lower))
            if matched:
                return {
                    "route_to": cfg["route_to"],
                    "department": DEPT_MAP.get(cfg["route_to"], cfg["route_to"]),
                    "priority": "critical" if level == "L5" else "high",
                    "level": level,
                    "matched_keyword": kw,
                    "mirror_check": True,
                    "note": cfg["note"],
                }
    return None


def classify_request(text: str, rules: dict) -> dict:
    """classify request → route_to + priority + level"""
    text_lower = text.lower()

    # Step 1: Check L5/L4 escalation FIRST
    escalation = detect_level(text_lower)
    if escalation:
        return escalation

    # Step 2: Match department-level routing rules (L2-L3)
    for rule in rules["rules"]:
        rule_id = rule.get("rule_id", "")
        # Skip fallback, governance, and mirror-only rules
        if rule.get("is_fallback"):
            continue
        if rule_id.startswith("r_mirror_"):
            continue

        keywords = rule.get("trigger", {}).get("keywords", [])
        if not keywords:
            continue
        for kw in keywords:
            kw_lower = kw.lower()
            # Multi-word → substring match; single-word → word boundary match
            if " " in kw_lower:
                matched = kw_lower in text_lower
            else:
                matched = bool(re.search(r'\b' + re.escape(kw_lower) + r'\b', text_lower))
            if matched:
                route_to = rule["route_to"]
                priority = rule.get("priority", "normal")
                is_mirror = rule.get("mirror_check", False)

                # ถ้าเป็น COO keyword → COO triage (L3)
                if route_to == "coo":
                    return {
                        "route_to": route_to,
                        "department": DEPT_MAP.get(route_to, route_to),
                        "priority": priority,
                        "level": "L3",
                        "matched_keyword": kw,
                        "mirror_check": is_mirror,
                        "note": "COO triage",
                    }

                # Budget/Finance → CFO + report CEO
                if route_to in ["cfo"] and any(re.search(r'\b' + re.escape(w) + r'\b', text_lower) for w in ["budget", "อนุมัติ", "approve", "งบ"]):
                    return {
                        "route_to": "ceo",
                        "department": "01-ceo",
                        "priority": "high",
                        "level": "L4",
                        "matched_keyword": kw,
                        "mirror_check": True,
                        "note": "Budget → CEO approve",
                    }

                # Normal department match → L2
                return {
                    "route_to": route_to,
                    "department": DEPT_MAP.get(route_to, route_to),
                    "priority": priority,
                    "level": "L2",
                    "matched_keyword": kw,
                    "mirror_check": is_mirror,
                }

    # Step 3: Fallback — no rule matched
    return {
        "route_to": "coo",
        "department": "02-coo",
        "priority": "normal",
        "level": "L3",
        "matched_keyword": None,
        "mirror_check": False,
        "note": "Fallback — COO triage",
    }


def scan_dispatch_queue() -> list:
    """scan bus/dispatch/ for pending items"""
    items = []
    if not DISPATCH_DIR.exists():
        return items

    for f in sorted(DISPATCH_DIR.glob("*.json")):
        try:
            with open(f) as fh:
                data = json.load(fh)
            data["_file"] = f.name
            items.append(data)
        except (json.JSONDecodeError, OSError):
            pass

    return items


def triage_items(items: list, rules: dict) -> dict:
    """triage all pending items"""
    result = {
        "auto_assign": [],      # L1-L2 → auto
        "coo_review": [],       # L3 → COO review
        "escalate_ceo": [],     # L4+ → escalate
        "owner_only": [],       # L5 → flag Owner
        "timestamp": datetime.now().isoformat(),
    }

    for item in items:
        title = item.get("title", "") or item.get("description", "") or item.get("name", "")
        classification = classify_request(title, rules)
        level = classification["level"]

        entry = {
            "file": item.get("_file", "unknown"),
            "title": title,
            "classification": classification,
            "original": item,
        }

        if level == "L5":
            result["owner_only"].append(entry)
        elif level == "L4":
            result["escalate_ceo"].append(entry)
        elif level == "L3":
            result["coo_review"].append(entry)
        else:  # L1-L2
            result["auto_assign"].append(entry)

    return result


def log_dispatch(result: dict):
    """log to file"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    summary = (
        f"=== COO Dispatch [{result['timestamp']}] ===\n"
        f"Auto-Assign (L1-L2): {len(result['auto_assign'])}\n"
        f"COO Review (L3):     {len(result['coo_review'])}\n"
        f"Escalate CEO (L4):   {len(result['escalate_ceo'])}\n"
        f"Owner Only (L5):     {len(result['owner_only'])}\n"
        f"{'='*50}\n"
    )
    with open(LOG_FILE, "a") as f:
        f.write(summary)


def generate_status_report(triage_result: dict) -> str:
    """generate glanceable status report (for COO dashboard)"""
    ts = triage_result["timestamp"][:19].replace("T", " ")

    lines = [
        f"👷 COO Status Report — {ts}",
        f"{'='*50}",
        "",
    ]

    # Summary bar
    total = sum(len(v) for k, v in triage_result.items() if k != "timestamp")
    lines.append(f"📊 Total Pending: {total}")
    lines.append(f"   🤖 Auto-Assign (L1-L2): {len(triage_result['auto_assign'])}")
    lines.append(f"   👷 COO Review (L3):     {len(triage_result['coo_review'])}")
    lines.append(f"   📋 Escalate CEO (L4):   {len(triage_result['escalate_ceo'])}")
    lines.append(f"   🚩 Owner Only (L5):     {len(triage_result['owner_only'])}")
    lines.append("")

    # Auto-assign details
    if triage_result["auto_assign"]:
        lines.append("🤖 Auto-Assigned:")
        for item in triage_result["auto_assign"]:
            c = item["classification"]
            lines.append(f"   → [{c['priority'].upper()}] {item['title'][:60]}")
            lines.append(f"     Route: @{c['route_to']} (L2)")
        lines.append("")

    # COO review details
    if triage_result["coo_review"]:
        lines.append("👷 COO Review Required:")
        for item in triage_result["coo_review"]:
            c = item["classification"]
            lines.append(f"   → [{c['priority'].upper()}] {item['title'][:60]}")
            lines.append(f"     Route: @{c['route_to']} (L3 — COO approve)")
        lines.append("")

    # Escalations
    if triage_result["escalate_ceo"]:
        lines.append("📋 Escalate to CEO:")
        for item in triage_result["escalate_ceo"]:
            c = item["classification"]
            lines.append(f"   → [{c['priority'].upper()}] {item['title'][:60]}")
        lines.append("")

    if triage_result["owner_only"]:
        lines.append("🚩 OWNER ONLY (L5):")
        for item in triage_result["owner_only"]:
            lines.append(f"   → {item['title'][:60]}")
        lines.append("")

    lines.append(f"{'='*50}")
    lines.append("✅ Owner ไม่เห็น L1-L3 = COO ทำงานสำเร็จ")

    return "\n".join(lines)


def main():
    rules = load_routing_rules()
    queue = scan_dispatch_queue()

    if not queue:
        print("📭 No pending items in dispatch queue.")
        return

    result = triage_items(queue, rules)
    log_dispatch(result)

    report = generate_status_report(result)
    print(report)


if __name__ == "__main__":
    main()
