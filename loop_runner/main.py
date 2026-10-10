#!/usr/bin/env python3
"""Run all due loops. Call from cron: */30 * * * * python3 -m loop_runner.main"""
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loop_runner.loops import ALL_LOOPS
from loop_runner.state import record
from loop_runner.verdict_log import append_verdict


def heartbeat() -> str:
    """Write scheduler heartbeat to state.db and return log marker."""
    marker = f"[scheduler] {datetime.now().isoformat()} fired"
    try:
        record("__scheduler__", "fired", success=True)
    except Exception:
        pass  # heartbeat ห้ามทำลาย loop run
    return marker


def main(dry_run: bool = False) -> None:
    import fcntl

    # Single-flight: กัน cron รอบซ้อน (forum-20260927-004)
    lock_path = Path(__file__).parent / ".main.lock"
    with open(lock_path, "w") as lock_f:
        try:
            fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print("[scheduler] SKIP: another run in progress (locked)")
            return
        print(heartbeat())
        for loop in ALL_LOOPS:
            if not loop.should_run():
                if not dry_run:
                    append_verdict(loop.loop_id, "NOT_DUE")  # per-gate heartbeat
                continue
            if dry_run:
                print(f"[{loop.loop_id}] DRY-RUN: due — would execute")
                continue
            try:
                result = loop.execute()
                if result:
                    print(f"[{loop.loop_id}]\n{result}\n")
            except Exception as e:
                print(f"[{loop.loop_id}] SKIPPED: {e}")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
