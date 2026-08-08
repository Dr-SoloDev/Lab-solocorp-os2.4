#!/usr/bin/env python3
"""Run all due loops. Call from cron: */30 * * * * python3 -m loop_runner.main"""
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loop_runner.loops import ALL_LOOPS
from loop_runner.state import record


def heartbeat() -> str:
    """Write scheduler heartbeat to state.db and return log marker."""
    marker = f"[scheduler] {datetime.now().isoformat()} fired"
    try:
        record("__scheduler__", "fired", success=True)
    except Exception:
        pass  # heartbeat ห้ามทำลาย loop run
    return marker


def main() -> None:
    print(heartbeat())
    for loop in ALL_LOOPS:
        if not loop.should_run():
            continue
        try:
            result = loop.execute()
            if result:
                print(f"[{loop.loop_id}]\n{result}\n")
        except Exception as e:
            print(f"[{loop.loop_id}] SKIPPED: {e}")


if __name__ == "__main__":
    main()
