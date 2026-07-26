#!/usr/bin/env python3
"""
Department Proposal System
===========================
ให้ Department Heads เสนอโอกาส/ไอเดียแบบ proactive

Owner vision: "เห็นโอกาสแล้วเดินเข้าไปเสนอ = ทีมที่ดี"
วัด proactivity: ≥ 1 proposal/dept/week

Usage:
  # สร้าง proposal ใหม่
  python3 workers/dept_proposal.py --dept engineering --title "Migrate CI/CD to GitHub Actions" --impact "ลด deploy time 50%"

  # ดู proposals ทั้งหมด
  python3 workers/dept_proposal.py --list

  # COO review proposal
  python3 workers/dept_proposal.py --review PROP-003 --status approved --notes "ส่ง CEO พิจารณา"

  # Weekly report
  python3 workers/dept_proposal.py --report
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROPOSAL_DIR = BASE_DIR / "bus" / "proposals"

# Departments
DEPARTMENTS = [
    "coo", "cfo", "cmo", "orchestrator", "architect",
    "product", "engineering", "design", "ui-designer", "qa",
    "sales", "support", "legal", "web3", "content-creator",
    "neteng", "cybersec", "psychology", "rd-lab",
]

VALID_STATUSES = ["draft", "submitted", "reviewed", "approved", "rejected", "implemented"]


def next_id() -> str:
    """generate next proposal ID"""
    PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(PROPOSAL_DIR.glob("PROP-*.json"))
    nums = []
    for f in existing:
        m = re.match(r"PROP-(\d+)", f.stem)
        if m:
            nums.append(int(m.group(1)))
    next_num = max(nums) + 1 if nums else 1
    return f"PROP-{next_num:04d}"


def create_proposal(
    dept: str,
    title: str,
    problem: str = "",
    impact: str = "",
    effort: str = "M",
    category: str = "improvement",
) -> dict:
    """create a new proposal"""
    prop_id = next_id()
    now = datetime.now(timezone.utc).isoformat()

    proposal = {
        "id": prop_id,
        "department": dept,
        "title": title,
        "problem": problem,
        "impact": impact,
        "effort": effort.upper(),  # XS / S / M / L / XL
        "category": category,       # improvement / new-feature / research / fix / experiment
        "status": "submitted",
        "created_at": now,
        "updated_at": now,
        "review_history": [],
        "notes": "",
    }

    fpath = PROPOSAL_DIR / f"{prop_id}.json"
    with open(fpath, "w") as f:
        json.dump(proposal, f, indent=2, ensure_ascii=False)

    return proposal


def list_proposals(status_filter: str | None = None) -> list[dict]:
    """list all proposals"""
    PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)
    proposals = []
    for f in sorted(PROPOSAL_DIR.glob("PROP-*.json")):
        try:
            with open(f) as fh:
                p = json.load(fh)
            if status_filter and p.get("status") != status_filter:
                continue
            proposals.append(p)
        except (json.JSONDecodeError, OSError):
            pass
    return proposals


def review_proposal(prop_id: str, status: str, notes: str = "") -> dict | None:
    """COO review a proposal"""
    fpath = PROPOSAL_DIR / f"{prop_id}.json"
    if not fpath.exists():
        return None

    with open(fpath) as f:
        proposal = json.load(f)

    now = datetime.now(timezone.utc).isoformat()
    review_entry = {
        "reviewed_at": now,
        "old_status": proposal["status"],
        "new_status": status,
        "notes": notes,
    }

    proposal["status"] = status
    proposal["updated_at"] = now
    proposal["review_history"].append(review_entry)
    if notes:
        proposal["notes"] = notes

    with open(fpath, "w") as f:
        json.dump(proposal, f, indent=2, ensure_ascii=False)

    return proposal


def generate_weekly_report() -> str:
    """generate weekly proposal health report"""
    proposals = list_proposals()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Stats
    total = len(proposals)
    this_week = [p for p in proposals if datetime.fromisoformat(p["created_at"]) > week_ago]
    by_dept = defaultdict(list)
    for p in proposals:
        by_dept[p["department"]].append(p)

    by_status = defaultdict(int)
    for p in proposals:
        by_status[p["status"]] += 1

    lines = [
        f"📋 Department Proposals — Weekly Report",
        f"{'='*50}",
        f"",
        f"📊 Period: {week_ago.strftime('%Y-%m-%d')} → {now.strftime('%Y-%m-%d')}",
        f"",
        f"Total Proposals:     {total}",
        f"  This Week:         {len(this_week)}",
        f"",
        f"By Status:",
    ]
    for s in ["submitted", "reviewed", "approved", "rejected", "implemented"]:
        if by_status[s]:
            lines.append(f"  {s.capitalize()}: {by_status[s]}")

    lines.append("")
    lines.append("By Department:")
    for dept in DEPARTMENTS:
        dept_props = by_dept.get(dept, [])
        recent = sum(1 for p in dept_props if datetime.fromisoformat(p["created_at"]) > week_ago)
        accepted = sum(1 for p in dept_props if p["status"] in ["approved", "implemented"])
        status_emoji = "🟢" if recent >= 1 else "🟡" if recent == 0 and dept_props else "🔴"
        lines.append(f"  {status_emoji} {dept:<15}  Total: {len(dept_props):<3}  This week: {recent}  Accepted: {accepted}")

    lines.append("")
    lines.append("Recent Proposals:")
    recent_props = sorted(this_week, key=lambda p: p["created_at"], reverse=True)[:5]
    for p in recent_props:
        status_emoji = {"submitted": "🆕", "reviewed": "👀", "approved": "✅", "rejected": "❌", "implemented": "🎉", "draft": "📝"}
        lines.append(f"  {status_emoji.get(p['status'], '❓')} {p['id']} [{p['department']}] {p['title'][:50]}")

    lines.append("")
    lines.append(f"{'='*50}")
    lines.append("Goal: ≥ 1 proposal/dept/week — วัด proactivity")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Department Proposal System")
    parser.add_argument("--dept", choices=DEPARTMENTS, help="Department")
    parser.add_argument("--title", help="Proposal title")
    parser.add_argument("--problem", default="", help="Problem or opportunity")
    parser.add_argument("--impact", default="", help="Expected impact")
    parser.add_argument("--effort", choices=["XS", "S", "M", "L", "XL"], default="M", help="Effort estimate")
    parser.add_argument("--category", choices=["improvement", "new-feature", "research", "fix", "experiment"],
                        default="improvement", help="Category")
    parser.add_argument("--list", action="store_true", help="List all proposals")
    parser.add_argument("--status", choices=VALID_STATUSES, help="Filter by status")
    parser.add_argument("--review", metavar="PROP-ID", help="Review a proposal")
    parser.add_argument("--notes", default="", help="Review notes")
    parser.add_argument("--report", action="store_true", help="Weekly report")

    args = parser.parse_args()

    if args.report:
        print(generate_weekly_report())
        return

    if args.list:
        proposals = list_proposals(args.status)
        if not proposals:
            print("📭 No proposals found.")
            return
        for p in proposals:
            status_emoji = {"submitted": "🆕", "reviewed": "👀", "approved": "✅", "rejected": "❌", "implemented": "🎉", "draft": "📝"}
            print(f"  {status_emoji.get(p['status'], '❓')} {p['id']} [{p['department']}] {p['title'][:60]}")
            print(f"     Status: {p['status']} | Effort: {p['effort']} | Created: {p['created_at'][:10]}")
        return

    if args.review:
        if not args.status:
            print("❌ --status required for review")
            sys.exit(1)
        result = review_proposal(args.review, args.status, args.notes)
        if not result:
            print(f"❌ Proposal {args.review} not found")
            sys.exit(1)
        print(f"✅ {args.review} → {args.status}")
        return

    if args.dept and args.title:
        prop = create_proposal(args.dept, args.title, args.problem, args.impact, args.effort, args.category)
        print(f"\n{'='*50}")
        print(f"📋 New Proposal: {prop['id']}")
        print(f"{'='*50}")
        print(f"  Department: {prop['department']}")
        print(f"  Title:      {prop['title']}")
        print(f"  Problem:    {prop['problem'] or '(not specified)'}")
        print(f"  Impact:     {prop['impact'] or '(not specified)'}")
        print(f"  Effort:     {prop['effort']}")
        print(f"  Status:     {prop['status']}")
        print(f"{'='*50}\n")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
