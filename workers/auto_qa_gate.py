#!/usr/bin/env python3
"""
Auto-QA Gate — SoloCorp OS Pipeline

ตรวจสอบ test coverage threshold ทุกครั้งที่รัน
Gate จะ:
  - รัน pytest + coverage
  - อ่านผล coverage จาก .coverage.json
  - เปรียบเทียบกับ threshold (default: 70%)
  - บันทึก evidence ไปยัง bus/evidence/
  - คืน exit code: 0=PASS, 1=FAIL

Usage:
    python3 workers/auto_qa_gate.py [--threshold=70] [--project-id=auto-qa-pipeline]

SOP Ref: SOP-04 (Deploy) — ต้องผ่าน gate นี้ก่อน deploy
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
EVIDENCE_DIR = REPO_ROOT / "bus" / "evidence"
DEFAULT_THRESHOLD = 70  # percent


def run_tests(test_path: str | None = None) -> dict:
    """Run pytest with coverage and return results."""
    cmd = [sys.executable, "-m", "pytest"]
    if test_path:
        cmd.extend(test_path.split())
    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )

    coverage_file = REPO_ROOT / ".coverage.json"
    coverage_data = {}
    if coverage_file.exists():
        try:
            coverage_data = json.loads(coverage_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "coverage_file": str(coverage_file) if coverage_file.exists() else None,
        "coverage_data": coverage_data,
    }


def extract_coverage_percent(coverage_data: dict) -> float | None:
    """Extract overall coverage percentage from coverage.json."""
    try:
        # pytest-cov json format: {"meta": ..., "files": {...}, "totals": {...}}
        totals = coverage_data.get("totals", {})
        percent_covered = totals.get("percent_covered")
        if percent_covered is not None:
            return float(percent_covered)

        # Alternative: sum covered / sum total statements
        covered = totals.get("covered_lines", 0)
        total = totals.get("num_statements", 0)
        if total and total > 0:
            return (covered / total) * 100.0
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return None


def record_evidence(
    project_id: str,
    result: dict,
    coverage_pct: float | None,
    threshold: int,
    passed: bool,
    trace_id: str,
) -> Path:
    """บันทึก evidence ไปยัง bus/evidence/"""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ev_dir = EVIDENCE_DIR / date_str
    ev_dir.mkdir(parents=True, exist_ok=True)

    evidence = {
        "event_id": f"qa-gate-{trace_id[:8]}",
        "event_type": "QA_GATE",
        "project_id": project_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gate_version": "v1.0",
        "threshold": threshold,
        "coverage_percent": coverage_pct,
        "passed": passed,
        "tests_returncode": result["returncode"],
        "tests_passed": "OK" if result["returncode"] == 0 else "FAILED",
        "evidence_type": "auto_qa_gate",
        "trace_id": trace_id,
    }

    # Attach test output summary (last 20 lines)
    stdout_lines = result.get("stdout", "").strip().splitlines()
    evidence["test_summary"] = "\n".join(stdout_lines[-20:]) if stdout_lines else ""

    ev_file = ev_dir / f"qa-gate-{trace_id[:8]}.json"
    ev_file.write_text(json.dumps(evidence, indent=2, ensure_ascii=False))
    return ev_file


def main():
    parser = argparse.ArgumentParser(description="Auto-QA Coverage Gate")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, help="Coverage threshold %%")
    parser.add_argument("--project-id", default="auto-qa-pipeline", help="Project identifier")
    parser.add_argument("--test-path", default=None, help="Specific test paths (space-separated, e.g. 'tests/test_config.py tests/test_adr.py')")
    args = parser.parse_args()

    trace_id = uuid.uuid4().hex[:12]
    project_id = args.project_id
    threshold = args.threshold

    print(f"\n🔍 Auto-QA Gate [{trace_id[:8]}]")
    print(f"   Project : {project_id}")
    print(f"   Threshold: {threshold}%")
    print(f"   Running pytest + coverage...\n")

    # Step 1: Run tests
    result = run_tests(args.test_path)

    # Step 2: Extract coverage
    coverage_pct = extract_coverage_percent(result.get("coverage_data", {}))

    # Step 3: Evaluate
    if coverage_pct is not None:
        passed = coverage_pct >= threshold and result["returncode"] == 0
        status = "🟢 PASS" if passed else "🔴 FAIL"
        print(f"\n{status}")
        print(f"   Coverage : {coverage_pct:.1f}% (threshold: {threshold}%)")
        print(f"   Tests    : {'✅ Passed' if result['returncode'] == 0 else '❌ Failed'}")
    else:
        passed = result["returncode"] == 0
        status = "🟢 PASS" if passed else "🔴 FAIL"
        print(f"\n{status}")
        print(f"   Coverage : N/A (could not extract)")
        print(f"   Tests    : {'✅ Passed' if result['returncode'] == 0 else '❌ Failed'}")

    # Step 4: Record evidence
    ev_file = record_evidence(project_id, result, coverage_pct, threshold, passed, trace_id)
    print(f"   Evidence : {ev_file}")

    # Step 5: Print summary
    stdout = result.get("stdout", "")
    if stdout:
        # Print last 5 lines of test output
        lines = stdout.strip().splitlines()
        print(f"\n📋 Test Summary (last {min(5, len(lines))} lines):")
        for line in lines[-5:]:
            print(f"   {line}")

    if result.get("stderr"):
        print(f"\n⚠️  Stderr:")
        for line in result["stderr"].strip().splitlines()[-3:]:
            print(f"   {line}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
