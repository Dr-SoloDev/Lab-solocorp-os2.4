#!/usr/bin/env python3
"""
SOP Compliance Checker
=======================
ตรวจสอบว่า SOP ครอบคลุมทุก workflow หรือไม่
และมี evidence ครบตาม checklist

Usage:
  python3 workers/sop_compliance_check.py              # Full scan
  python3 workers/sop_compliance_check.py --sop 01     # Single SOP
  python3 workers/sop_compliance_check.py --json       # Machine-readable
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SOP_DIR = BASE_DIR / "sop"
DISPATCH_DIR = BASE_DIR / "bus" / "dispatch"
EVIDENCE_DIR = BASE_DIR / "bus" / "evidence"
CONFIRM_DIR = DISPATCH_DIR / "confirmations"
QA_SIGNOFF_DIR = EVIDENCE_DIR / "qa-signoff"

SOPS = {
    "01": "SOP-01-dispatch.md",
    "02": "SOP-02-escalation.md",
    "03": "SOP-03-handoff.md",
    "04": "SOP-04-deploy.md",
    "05": "SOP-05-incident.md",
}


def count_checkboxes(content: str) -> tuple[int, int]:
    """count total checkboxes and checked ones"""
    total = len(re.findall(r'\[ \]', content))
    checked = len(re.findall(r'\[x\]', content, re.IGNORECASE))
    return total, checked


def has_section(content: str, section_name: str) -> bool:
    """check if SOP has a section"""
    return f"## {section_name}" in content or f"### {section_name}" in content


def check_sop(sop_id: str) -> dict:
    """check a single SOP"""
    fname = SOPS[sop_id]
    fpath = SOP_DIR / fname

    if not fpath.exists():
        return {"sop": sop_id, "file": fname, "status": "❌ Missing", "score": 0}

    content = fpath.read_text()
    total, checked = count_checkboxes(content)

    # Extract version
    version_match = re.search(r'\*\*Version:\*\* v?(\d+\.\d+)', content)
    version = version_match.group(1) if version_match else "unknown"

    findings = {
        "sop": sop_id,
        "file": fname,
        "version": version,
        "status": "✅ OK",
        "checkboxes": {"total": total, "checked": checked},
        "has_checklist": has_section(content, "Checklist") or has_section(content, "Verification"),
        "has_verification": has_section(content, "Verification"),
        "has_quality_gate": has_section(content, "Quality Gate"),
        "evidence_count": 0,
        "score": 0,
    }

    # Score calculation
    score = 0
    if version != "unknown" and version >= "1.1":
        score += 30
    elif version >= "1.0":
        score += 20

    if findings["has_checklist"]:
        score += 20
        if total > 0 and checked == total:
            score += 10  # all checked (template complete)

    if findings["has_verification"]:
        score += 20

    if findings["has_quality_gate"]:
        score += 20

    score += min(checked, 10)  # up to 10 bonus for actual checkboxes
    findings["score"] = min(score, 100)

    return findings


def count_evidence() -> dict:
    """count evidence files"""
    evidence = {}
    for d in [CONFIRM_DIR, QA_SIGNOFF_DIR, EVIDENCE_DIR]:
        if d.exists():
            count = len([f for f in d.glob("*.json") if f.name != ".gitkeep"])
            evidence[d.name] = count
        else:
            evidence[d.name] = 0
    return evidence


def generate_report(sop_results: list, evidence: dict) -> str:
    """generate human-readable report"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_score = sum(r["score"] for r in sop_results) // max(len(sop_results), 1)

    lines = [
        f"📋 SOP Compliance Report — {now}",
        f"{'='*50}",
        f"",
        f"📊 Overall SOP Health: {total_score}/100",
        f"",
    ]

    # Status bar
    emoji_map = {"✅ OK": "✅", "❌ Missing": "❌"}
    for r in sop_results:
        emoji = emoji_map.get(r["status"], "❓")
        cb = r["checkboxes"]
        lines.append(
            f"  {emoji} SOP-{r['sop']} ({r['file']}) v{r['version']}"
            f"  Score: {r['score']}/100"
        )
        lines.append(f"     Checklist: {cb['total']} items ({cb['checked']} checked)")
        lines.append(f"     Verification: {'✅' if r['has_verification'] else '❌'}")
        lines.append(f"     Quality Gate: {'✅' if r['has_quality_gate'] else '❌'}")

    lines.append("")
    lines.append(f"📦 Evidence Store")
    for name, count in evidence.items():
        lines.append(f"  {name}: {count} files")
    lines.append("")
    lines.append(f"{'='*50}")
    lines.append(f"COO: ทุก SOP ต้องมี checklist + verification + evidence")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="SOP Compliance Checker")
    parser.add_argument("--sop", choices=["01", "02", "03", "04", "05"], help="เฉพาะ SOP นี้")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    if args.sop:
        sop_ids = [args.sop]
    else:
        sop_ids = list(SOPS.keys())

    results = [check_sop(sid) for sid in sop_ids]
    evidence = count_evidence()

    if args.json:
        output = {"sops": results, "evidence": evidence, "timestamp": datetime.now().isoformat()}
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    print(generate_report(results, evidence))


if __name__ == "__main__":
    main()
