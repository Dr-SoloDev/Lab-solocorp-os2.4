#!/usr/bin/env python3
"""
QA Sign-off Gate
=================
Gate บังคับก่อน deploy — ทุก feature ต้องมี QA sign-off

Usage:
  python3 workers/qa_signoff_gate.py --feature "login-redesign" --status APPROVED --coverage 85 --tester "qa-team"
  python3 workers/qa_signoff_gate.py --feature "payment-fix" --status REJECTED --critical-bugs 2 --notes "2 critical bugs found"
  python3 workers/qa_signoff_gate.py --feature "nav-update" --status CONDITIONAL --notes "ต้องแก้ low bugs ก่อน"
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SIGNOFF_DIR = BASE_DIR / "bus" / "evidence" / "qa-signoff"

MIN_COVERAGE = 80        # minimum test coverage %
MAX_CRITICAL_BUGS = 0    # 0 critical bugs allowed
MAX_HIGH_BUGS = 0        # 0 high bugs allowed
MAX_MEDIUM_BUGS = 5      # up to 5 medium bugs allowed
MAX_LOW_BUGS = 20        # up to 20 low bugs allowed


def auto_evaluate(coverage: int,
                  critical_bugs: int,
                  high_bugs: int,
                  medium_bugs: int,
                  low_bugs: int,
                  regression_pass: bool) -> tuple[str, list[str]]:
    """auto-evaluate whether feature passes QA gate"""
    conditions = []

    if coverage < MIN_COVERAGE:
        conditions.append(f"Test coverage {coverage}% < minimum {MIN_COVERAGE}%")

    if critical_bugs > MAX_CRITICAL_BUGS:
        conditions.append(f"Critical bugs {critical_bugs} > {MAX_CRITICAL_BUGS}")
    if high_bugs > MAX_HIGH_BUGS:
        conditions.append(f"High bugs {high_bugs} > {MAX_HIGH_BUGS}")
    if medium_bugs > MAX_MEDIUM_BUGS:
        conditions.append(f"Medium bugs {medium_bugs} > {MAX_MEDIUM_BUGS}")
    if low_bugs > MAX_LOW_BUGS:
        conditions.append(f"Low bugs {low_bugs} > {MAX_LOW_BUGS}")
    if not regression_pass:
        conditions.append("Regression tests failed")

    if not conditions:
        return "APPROVED", []
    elif any(b > 0 for b in [critical_bugs, high_bugs]):
        return "REJECTED", conditions
    else:
        return "CONDITIONAL", conditions


def build_signoff(
    feature: str,
    status: str,
    coverage: int = 0,
    critical_bugs: int = 0,
    high_bugs: int = 0,
    medium_bugs: int = 0,
    low_bugs: int = 0,
    regression_pass: bool = True,
    tester: str = "qa-team",
    notes: str = "",
    auto: bool = False,
) -> dict:
    """build sign-off record"""
    conditions = []

    if auto:
        status, conditions = auto_evaluate(coverage, critical_bugs, high_bugs, medium_bugs, low_bugs, regression_pass)

    now = datetime.now(timezone.utc).isoformat()

    return {
        "feature": feature,
        "qa_signoff": {
            "tester": tester,
            "date": now,
            "test_coverage": f"{coverage}%",
            "critical_bugs": critical_bugs,
            "high_bugs": high_bugs,
            "medium_bugs": medium_bugs,
            "low_bugs": low_bugs,
            "regression_pass": regression_pass,
            "status": status,
            "conditions": conditions,
            "notes": notes,
        },
    }


def save_signoff(record: dict, dry_run: bool = False) -> Path | None:
    """save signoff record to disk"""
    if dry_run:
        return None

    SIGNOFF_DIR.mkdir(parents=True, exist_ok=True)
    ts = record["qa_signoff"]["date"].replace(":", "-").split(".")[0]
    fname = f"{record['feature']}-{record['qa_signoff']['status']}-{ts}.json"
    fpath = SIGNOFF_DIR / fname

    with open(fpath, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    return fpath


def main():
    parser = argparse.ArgumentParser(description="QA Sign-off Gate")
    parser.add_argument("--feature", required=True, help="ชื่อ feature")
    parser.add_argument("--status", choices=["APPROVED", "REJECTED", "CONDITIONAL", "AUTO"],
                        default="AUTO", help="สถานะ (AUTO = auto-evaluate)")
    parser.add_argument("--coverage", type=int, default=0, help="Test coverage %")
    parser.add_argument("--critical-bugs", type=int, default=0)
    parser.add_argument("--high-bugs", type=int, default=0)
    parser.add_argument("--medium-bugs", type=int, default=0)
    parser.add_argument("--low-bugs", type=int, default=0)
    parser.add_argument("--regression-pass", action="store_true", default=True)
    parser.add_argument("--no-regression", action="store_false", dest="regression_pass")
    parser.add_argument("--tester", default="qa-team", help="ชื่อผู้ทดสอบ")
    parser.add_argument("--notes", default="", help="หมายเหตุ")
    parser.add_argument("--dry-run", action="store_true", help="ทดสอบเท่านั้น")

    args = parser.parse_args()

    auto_mode = args.status == "AUTO"
    notes = args.notes

    record = build_signoff(
        feature=args.feature,
        status=args.status if not auto_mode else "PENDING",
        coverage=args.coverage,
        critical_bugs=args.critical_bugs,
        high_bugs=args.high_bugs,
        medium_bugs=args.medium_bugs,
        low_bugs=args.low_bugs,
        regression_pass=args.regression_pass,
        tester=args.tester,
        notes=notes,
        auto=auto_mode,
    )

    status = record["qa_signoff"]["status"]
    conditions = record["qa_signoff"]["conditions"]

    if args.dry_run:
        print(json.dumps(record, indent=2, ensure_ascii=False))
        return

    fpath = save_signoff(record, dry_run=args.dry_run)

    # Print report
    emoji = {"APPROVED": "✅", "REJECTED": "❌", "CONDITIONAL": "🟡", "PENDING": "⏳"}
    print(f"\n{'='*50}")
    print(f"🛡️  QA Sign-off Gate")
    print(f"{'='*50}")
    print(f"  Feature:     {record['feature']}")
    print(f"  Status:      {emoji.get(status, '❓')} {status}")
    print(f"  Tester:      {record['qa_signoff']['tester']}")
    print(f"  Coverage:    {record['qa_signoff']['test_coverage']}")
    print(f"  Critical:    {record['qa_signoff']['critical_bugs']}  High: {record['qa_signoff']['high_bugs']}")
    print(f"  Medium:      {record['qa_signoff']['medium_bugs']}  Low: {record['qa_signoff']['low_bugs']}")
    print(f"  Regression:  {'✅ Pass' if record['qa_signoff']['regression_pass'] else '❌ Fail'}")
    if conditions:
        print(f"\n  ⚠️  Conditions:")
        for c in conditions:
            print(f"      • {c}")
    if notes:
        print(f"\n  📝 Notes: {notes}")
    if fpath:
        print(f"\n  💾 Saved: {fpath}")
    print(f"{'='*50}\n")

    # Exit code for pipeline gates
    if status == "REJECTED":
        sys.exit(1)


if __name__ == "__main__":
    main()
