#!/usr/bin/env python3
"""Run all due loops. Call from cron: */30 * * * * python3 -m loop_runner.main"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loop_runner.loops import ALL_LOOPS

for loop in ALL_LOOPS:
    if not loop.should_run():
        continue
    try:
        result = loop.execute()
        if result:
            print(f"[{loop.loop_id}]\n{result}\n")
    except Exception as e:
        print(f"[{loop.loop_id}] SKIPPED: {e}")
