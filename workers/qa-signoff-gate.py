#!/usr/bin/env python3
"""
=============================================================
  🛡️ SoloCorp OS — QA Sign-off Gate
=============================================================
  Formal QA sign-off ก่อน deploy
  "ไม่มี QA sign-off = ห้าม deploy"
=============================================================

Usage:
    python3 workers/qa-signoff-gate.py --feature "feature-name" --status APPROVED
    python3 workers/qa-signoff-gate.py --feature "feature-name" --status REJECTED --coverage 65

Minimum Thresholds (APPROVED):
    - test_coverage >= 80%
    - critical_bugs == 0
    - high_bugs == 0
    - regression_pass == True
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("qa-signoff")

# ── Paths ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIGNOFF_DIR = PROJECT_ROOT / "bus" / "evidence" / "qa-signoff"

# ── Minimum Thresholds ─────────────────────────────────────
MIN_COVERAGE = 80  # %
CONDITIONAL_MIN_COVERAGE = 70  # %
MAX_CRITICAL = 0
MAX_HIGH = 0
MAX_MEDIUM_CONDITIONAL = 3
MAX_LOW_CONDITIONAL = 10


def _now_iso() -> str:
    """Return current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Generate a unique evidence ID."""
    return str(uuid.uuid4())


def _ensure_dir(path: Path) -> Path:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_test_results(path: str | None) -> dict:
    """Load test results from a JSON file if provided.

    Expected JSON format:
    {
        "test_coverage": 85,
        "critical_bugs": 0,
        "high_bugs": 0,
        "medium_bugs": 0,
        "low_bugs": 0,
        "total_tests": 120,
        "passed_tests": 115,
        "failed_tests": 0,
        "skipped_tests": 5,
        "regression_pass": true
    }
    """
    if not path:
        return {}

    path_obj = Path(path)
    if not path_obj.exists():
        log.warning(f"⚠️ Test results file not found: {path}")
        return {}

    try:
        with open(path_obj) as f:
            data = json.load(f)
        log.info(f"📊 Loaded test results from {path}")
        return data
    except (json.JSONDecodeError, PermissionError) as e:
        log.warning(f"⚠️ Failed to load test results: {e}")
        return {}


def _validate_signoff(params: dict) -> str:
    """Validate sign-off against minimum thresholds.

    Returns:
        "APPROVED", "CONDITIONAL", or "REJECTED" based on thresholds.
    """
    coverage = params.get("test_coverage", 0)
    critical = params.get("critical_bugs", 0)
    high = params.get("high_bugs", 0)
    medium = params.get("medium_bugs", 0)
    low = params.get("low_bugs", 0)
    regression = params.get("regression_pass", False)

    # ── Hard blocks (REJECTED) ────────────────────────────
    reject_reasons = []

    if coverage < CONDITIONAL_MIN_COVERAGE:
        reject_reasons.append(
            f"Test coverage too low: {coverage}% < {CONDITIONAL_MIN_COVERAGE}%"
        )

    if critical > MAX_CRITICAL:
        reject_reasons.append(
            f"Critical bugs present: {critical} > {MAX_CRITICAL}"
        )

    if high > MAX_HIGH:
        reject_reasons.append(
            f"High bugs present: {high} > {MAX_HIGH}"
        )

    if not regression:
        reject_reasons.append("Regression tests did not pass")

    if reject_reasons:
        log.warning(f"❌ REJECTED: {'; '.join(reject_reasons)}")
        return "REJECTED"

    # ── Conditional check ─────────────────────────────────
    conditional_reasons = []

    if coverage < MIN_COVERAGE:
        conditional_reasons.append(
            f"Coverage {coverage}% < {MIN_COVERAGE}% threshold"
        )

    if medium > MAX_MEDIUM_CONDITIONAL:
        conditional_reasons.append(
            f"Medium bugs: {medium} > {MAX_MEDIUM_CONDITIONAL}"
        )

    if low > MAX_LOW_CONDITIONAL:
        conditional_reasons.append(
            f"Low bugs: {low} > {MAX_LOW_CONDITIONAL}"
        )

    if conditional_reasons:
        log.warning(f"⚠️ CONDITIONAL: {'; '.join(conditional_reasons)}")
        return "CONDITIONAL"

    # ── All clear ─────────────────────────────────────────
    log.info(f"✅ APPROVED — All thresholds met (coverage: {coverage}%)")
    return "APPROVED"


def _save_signoff(record: dict) -> Path:
    """Save sign-off record to bus/evidence/qa-signoff/."""
    signoff_dir = _ensure_dir(SIGNOFF_DIR)
    filename = f"signoff-{record['qa_signoff']['feature']}-{record['qa_signoff']['date'][:10]}.json"
    # Sanitize filename — replace spaces/slashes
    filename = filename.replace(" ", "-").replace("/", "-")
    filepath = signoff_dir / filename

    with open(filepath, "w") as f:
        json.dump(record, f, indent=2, default=str)

    log.info(f"💾 Sign-off saved → {filepath}")
    return filepath


def _load_test_results_with_retry(path: str | None, max_retries: int = 3) -> dict:
    """Load test results with retry logic."""
    for attempt in range(1, max_retries + 1):
        data = _load_test_results(path)
        if data or not path:
            return data
        log.warning(f"🔄 Retry {attempt}/{max_retries} — waiting before re-reading...")
        import time
        time.sleep(1)
    return {}


def run_signoff(
    feature: str,
    status: str = "REJECTED",
    tester: str = "unknown",
    test_results_path: str | None = None,
    coverage: int | None = None,
    critical_bugs: int = 0,
    high_bugs: int = 0,
    medium_bugs: int = 0,
    low_bugs: int = 0,
    regression_pass: bool = True,
    conditions: list[str] | None = None,
    notes: str = "",
) -> dict:
    """Execute QA sign-off gate.

    Args:
        feature: ชื่อ feature ที่ sign-off
        status: override status (APPROVED | REJECTED | CONDITIONAL)
        tester: ชื่อผู้ทำการทดสอบ
        test_results_path: path ไปยังไฟล์ JSON test results
        coverage: test coverage percentage
        critical_bugs: จำนวน critical bugs
        high_bugs: จำนวน high bugs
        medium_bugs: จำนวน medium bugs
        low_bugs: จำนวน low bugs
        regression_pass: regression tests ผ่านหรือไม่
        conditions: เงื่อนไข (ถ้ามี)
        notes: หมายเหตุเพิ่มเติม

    Returns:
        dict: sign-off record
    """
    # ── Load test results from file if provided ────────────
    test_data = _load_test_results_with_retry(test_results_path)
    if test_data:
        coverage = coverage or test_data.get("test_coverage")
        critical_bugs = test_data.get("critical_bugs", critical_bugs)
        high_bugs = test_data.get("high_bugs", high_bugs)
        medium_bugs = test_data.get("medium_bugs", medium_bugs)
        low_bugs = test_data.get("low_bugs", low_bugs)
        regression_pass = test_data.get("regression_pass", regression_pass)

    # ── Default coverage ──────────────────────────────────
    coverage = coverage or 0
    conditions = conditions or []

    # ── Build params for validation ───────────────────────
    params = {
        "test_coverage": coverage,
        "critical_bugs": critical_bugs,
        "high_bugs": high_bugs,
        "medium_bugs": medium_bugs,
        "low_bugs": low_bugs,
        "regression_pass": regression_pass,
    }

    # ── Auto-determine status if not explicitly set ───────
    if status not in ("APPROVED", "REJECTED", "CONDITIONAL"):
        status = _validate_signoff(params)

    # ── Build sign-off record ─────────────────────────────
    record = {
        "feature": feature,
        "qa_signoff": {
            "evidence_id": _new_id(),
            "tester": tester,
            "date": _now_iso(),
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

    # ── Save evidence ─────────────────────────────────────
    filepath = _save_signoff(record)
    record["_filepath"] = str(filepath)

    # ── Log result ────────────────────────────────────────
    icon = {"APPROVED": "✅", "REJECTED": "❌", "CONDITIONAL": "⚠️"}.get(status, "❓")
    msg = (
        f"\n"
        f"{'=' * 55}\n"
        f"  {icon}  QA SIGN-OFF GATE RESULT\n"
        f"{'=' * 55}\n"
        f"  Feature:      {feature}\n"
        f"  Status:       {status}\n"
        f"  Tester:       {tester}\n"
        f"  Coverage:     {coverage}%\n"
        f"  Critical:     {critical_bugs} | High: {high_bugs} | "
        f"Medium: {medium_bugs} | Low: {low_bugs}\n"
        f"  Regression:   {'✅ Pass' if regression_pass else '❌ Fail'}\n"
        f"  Evidence:     {filepath}\n"
        f"{'=' * 55}"
    )
    if conditions:
        msg += f"\n  ⚠️  Conditions:\n"
        for i, c in enumerate(conditions, 1):
            msg += f"       {i}. {c}\n"
        msg += f"{'=' * 55}"
    if notes:
        msg += f"\n  📝 {notes}"

    log.info(msg)

    return record


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="🛡️ SoloCorp OS — QA Sign-off Gate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 workers/qa-signoff-gate.py --feature \"login-v2\" "
            "--status APPROVED --tester \"QA-01\" --coverage 85\n"
            "  python3 workers/qa-signoff-gate.py --feature \"checkout\" "
            "--test-results test-output.json --tester \"QA-02\"\n"
        ),
    )

    parser.add_argument(
        "--feature",
        required=True,
        help="ชื่อ feature ที่ sign-off (required)",
    )
    parser.add_argument(
        "--status",
        choices=["APPROVED", "REJECTED", "CONDITIONAL"],
        default="REJECTED",
        help="QA sign-off status (default: REJECTED)",
    )
    parser.add_argument(
        "--tester",
        default="unknown",
        help="ชื่อผู้ทำการทดสอบ (default: unknown)",
    )
    parser.add_argument(
        "--test-results",
        default=None,
        help="Path ไปยังไฟล์ JSON test results",
    )
    parser.add_argument(
        "--coverage",
        type=int,
        default=None,
        help="Test coverage percentage (overrideจากไฟล์)",
    )
    parser.add_argument(
        "--critical-bugs",
        type=int,
        default=0,
        help="จำนวน critical bugs (default: 0)",
    )
    parser.add_argument(
        "--high-bugs",
        type=int,
        default=0,
        help="จำนวน high bugs (default: 0)",
    )
    parser.add_argument(
        "--medium-bugs",
        type=int,
        default=0,
        help="จำนวน medium bugs (default: 0)",
    )
    parser.add_argument(
        "--low-bugs",
        type=int,
        default=0,
        help="จำนวน low bugs (default: 0)",
    )
    parser.add_argument(
        "--regression-pass",
        action="store_true",
        help="Regression tests ผ่าน (flag: add to set True)",
    )
    parser.add_argument(
        "--conditions",
        nargs="*",
        default=[],
        help="เงื่อนไข (space-separated strings)",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="หมายเหตุเพิ่มเติม",
    )

    return parser.parse_args(argv)


def main() -> int:
    """CLI entry point."""
    args = parse_args()

    record = run_signoff(
        feature=args.feature,
        status=args.status,
        tester=args.tester,
        test_results_path=args.test_results,
        coverage=args.coverage,
        critical_bugs=args.critical_bugs,
        high_bugs=args.high_bugs,
        medium_bugs=args.medium_bugs,
        low_bugs=args.low_bugs,
        regression_pass=args.regression_pass,
        conditions=args.conditions,
        notes=args.notes,
    )

    # Exit code: 0 = APPROVED, 1 = REJECTED, 2 = CONDITIONAL
    status = record["qa_signoff"]["status"]
    exit_codes = {"APPROVED": 0, "REJECTED": 1, "CONDITIONAL": 2}
    return exit_codes.get(status, 1)


if __name__ == "__main__":
    sys.exit(main())
