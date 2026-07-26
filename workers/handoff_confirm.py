#!/usr/bin/env python3
"""
=============================================================
  🏛️ SoloCorp OS — Handoff Confirmation
=============================================================
  สร้าง confirmation record สำหรับทุก handoff ระหว่าง department
  ตาม SOP-03-handoff.md Step 5a — Confirmation Record

  CLI Usage:
    python3 workers/handoff_confirm.py --handoff HANDOFF-001 --to architect-songsak --status acknowledged
    python3 workers/handoff_confirm.py --handoff HANDOFF-001 --to engineering --status need_clarify --notes "ขอ clarification เรื่อง API contract"
    python3 workers/handoff_confirm.py --handoff HANDOFF-001 --to ceo --status rejected --notes "context ไม่ครบ ไม่มี deadline"
=============================================================
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("handoff-confirm")

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIRMATIONS_DIR = os.path.join(PROJECT_ROOT, "bus", "dispatch", "confirmations")
DISPATCH_DIR = os.path.join(PROJECT_ROOT, "bus", "dispatch")

VALID_STATUSES = {"acknowledged", "rejected", "need_clarify"}


# ── Helpers ────────────────────────────────────────────────────────────


def _now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _timestamp_slug() -> str:
    """Compact timestamp for filenames: YYYYMMDDTHHMMSS"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


def _ensure_confirmations_dir() -> str:
    """Create confirmations directory if it doesn't exist."""
    os.makedirs(CONFIRMATIONS_DIR, exist_ok=True)
    return CONFIRMATIONS_DIR


def _find_handoff_file(handoff_id: str) -> str | None:
    """Search for a handoff/dispatch file by ID across all date subdirectories.

    Looks for files in:
      - bus/dispatch/YYYY-MM-DD/{handoff_id}.json
      - bus/dispatch/YYYY-MM-DD/*.json (content search)
    """
    if not os.path.isdir(DISPATCH_DIR):
        return None

    # Search across date subdirectories
    for entry in os.listdir(DISPATCH_DIR):
        date_dir = os.path.join(DISPATCH_DIR, entry)
        if not os.path.isdir(date_dir):
            continue

        # Direct match: {handoff_id}.json
        direct = os.path.join(date_dir, f"{handoff_id}.json")
        if os.path.isfile(direct):
            return direct

        # Content search: scan JSON files for matching handoff id
        for fname in os.listdir(date_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(date_dir, fname)
            try:
                with open(fpath, "r") as f:
                    data = json.load(f)
                # Check both handoff.id and command.id patterns
                if "handoff" in data and data["handoff"].get("id") == handoff_id:
                    return fpath
                if "command" in data and data["command"].get("id") == handoff_id:
                    return fpath
            except (json.JSONDecodeError, IOError):
                continue

    return None


def _read_handoff_metadata(handoff_id: str) -> dict[str, Any]:
    """Read handoff file and extract from/to/work_item metadata.

    Returns default placeholder values if file is not found, since
    the confirmation record should still be creatable.
    """
    filepath = _find_handoff_file(handoff_id)
    if filepath is None:
        return {
            "from": "unknown",
            "to": "unknown",
            "work_item": handoff_id,
        }

    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {
            "from": "unknown",
            "to": "unknown",
            "work_item": handoff_id,
        }

    # Handle both handoff format (SOP-03) and command format (dispatch)
    if "handoff" in data:
        h = data["handoff"]
        return {
            "from": h.get("from", "unknown"),
            "to": h.get("to", "unknown"),
            "work_item": h.get("work_item", handoff_id),
        }
    elif "command" in data:
        c = data["command"]
        return {
            "from": c.get("from", "unknown"),
            "to": c.get("to", "unknown"),
            "work_item": c.get("title", handoff_id),
        }
    else:
        return {
            "from": data.get("from", "unknown"),
            "to": data.get("to", "unknown"),
            "work_item": data.get("work_item", handoff_id),
        }


def build_confirmation(
    handoff_id: str,
    to_dept: str,
    status: str,
    *,
    from_dept: str | None = None,
    work_item: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Build a handoff confirmation record dictionary.

    Args:
        handoff_id: Handoff identifier (e.g. HANDOFF-001)
        to_dept: Receiving department ID
        status: One of: acknowledged, rejected, need_clarify
        from_dept: Sending department ID (auto-resolved if None)
        work_item: Work item name (auto-resolved if None)
        notes: Optional notes or clarification request

    Returns:
        Confirmation record dict ready for serialization
    """
    # Auto-resolve metadata from handoff file if not provided
    if from_dept is None or work_item is None:
        meta = _read_handoff_metadata(handoff_id)
        if from_dept is None:
            from_dept = meta["from"]
        if work_item is None:
            work_item = meta["work_item"]

    # Derive three-part confirmation booleans from status
    acknowledge_context = status == "acknowledged" or status == "need_clarify"
    understand_pending = status == "acknowledged"
    take_over = status == "acknowledged"

    record = {
        "handoff_id": handoff_id,
        "from": from_dept,
        "to": to_dept,
        "work_item": work_item,
        "confirmed_by": to_dept,
        "confirmed_at": _now_iso(),
        "status": status,
        "acknowledge_context": acknowledge_context,
        "understand_pending": understand_pending,
        "take_over": take_over,
        "notes": notes,
    }

    return record


def save_confirmation(record: dict[str, Any], *, dry_run: bool = False) -> str:
    """Save confirmation record to bus/dispatch/confirmations/.

    Args:
        record: Confirmation record dict
        dry_run: If True, just return the path without writing

    Returns:
        Path to the saved file
    """
    handoff_id = record["handoff_id"]
    status = record["status"]
    ts = _timestamp_slug()
    filename = f"{handoff_id}-{status}-{ts}.json"

    confirm_dir = _ensure_confirmations_dir()
    filepath = os.path.join(confirm_dir, filename)

    if not dry_run:
        with open(filepath, "w") as f:
            json.dump(record, f, indent=2, default=str)
        log.info(f"✅ Confirmation saved -> {filepath}")

    return filepath


def validate_status(status: str) -> None:
    """Validate that status is one of the allowed values."""
    if status not in VALID_STATUSES:
        valid_list = ", ".join(sorted(VALID_STATUSES))
        raise ValueError(
            f"Invalid status: '{status}'. Must be one of: {valid_list}"
        )


def print_record(record: dict[str, Any]) -> None:
    """Print confirmation record to stdout in a human-readable format."""
    status_icon = {
        "acknowledged": "✅",
        "rejected": "❌",
        "need_clarify": "❓",
    }.get(record["status"], "📋")

    print()
    print("=" * 60)
    print(f"  {status_icon}  Handoff Confirmation Record")
    print("=" * 60)
    print(f"  HANDOFF ID  : {record['handoff_id']}")
    print(f"  FROM        : {record['from']}")
    print(f"  TO          : {record['to']}")
    print(f"  WORK ITEM   : {record['work_item']}")
    print(f"  STATUS      : {record['status']}")
    print(f"  CONFIRMED   : {record['confirmed_at']}")
    print(f"  CONFIRMED BY: {record['confirmed_by']}")
    print()
    print("  -- Confirmation Checklist --")
    print(f"  [x] รับทราบ context    : {'yes' if record['acknowledge_context'] else 'no'}")
    print(f"  [x] เข้าใจ pending     : {'yes' if record['understand_pending'] else 'no'}")
    print(f"  [x] รับช่วงต่อ         : {'yes' if record['take_over'] else 'no'}")
    if record["notes"]:
        print()
        print(f"  Notes: {record['notes']}")
    print("=" * 60)
    print()


# ── CLI ────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="handoff-confirm",
        description="SoloCorp OS -- สร้าง Handoff Confirmation Record",
        epilog="ข้อกำหนด: SOP-03-handoff.md Step 5a -- ทุก handoff ต้องมี confirmation",
    )

    parser.add_argument(
        "--handoff",
        required=True,
        help="Handoff ID (e.g. HANDOFF-001, CMD-001)",
    )
    parser.add_argument(
        "--to",
        required=True,
        dest="to_dept",
        help="Department ID ที่รับช่วง (e.g. architect-songsak, engineering, ceo)",
    )
    parser.add_argument(
        "--from-department",
        dest="from_dept",
        default=None,
        help="Department ID ที่ส่งต่อ (ถ้าไม่ระบุจะอ่านจาก handoff file)",
    )
    parser.add_argument(
        "--work-item",
        default=None,
        help="ชื่องาน (ถ้าไม่ระบุจะอ่านจาก handoff file)",
    )
    parser.add_argument(
        "--status",
        required=True,
        choices=sorted(VALID_STATUSES),
        help=f"สถานะการยืนยัน: {', '.join(sorted(VALID_STATUSES))}",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="หมายเหตุเพิ่มเติม (เช่น เหตุผลที่ reject หรือขอ clarification)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="จำลองการสร้าง -- ไม่บันทึกไฟล์",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="แสดงเฉพาะ confirmation record (ไม่แสดง log)",
    )

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Setup logging
    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s")

    try:
        # Validate
        validate_status(args.status)

        # Build confirmation record
        record = build_confirmation(
            handoff_id=args.handoff,
            to_dept=args.to_dept,
            from_dept=args.from_dept,
            work_item=args.work_item,
            status=args.status,
            notes=args.notes,
        )

        # Save
        filepath = save_confirmation(record, dry_run=args.dry_run)

        # Print
        if not args.quiet:
            print_record(record)
            if args.dry_run:
                print(f"  Dry-run: would write -> {filepath}")
            else:
                print(f"  Saved -> {filepath}")

        # Machine-readable output for pipeline consumption
        print(f"CONFIRMED={record['status']}")
        print(f"FILE={filepath}")

    except ValueError as e:
        log.error(f"ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        log.error(f"ERROR: Unexpected error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
