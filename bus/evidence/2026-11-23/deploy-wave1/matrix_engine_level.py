#!/usr/bin/env python3
"""Engine-level routing matrix — Wave-1 deploy verification (2026-11-23).

⚠️  SCOPE LABEL: **engine-level**, NOT HTTP.
    There is no read-only routing HTTP endpoint in central_bus (every
    routing-adjacent route is a POST that writes). This script therefore drives
    the canonical `RoutingEngine` directly.

⚠️  ZERO-WRITE GUARANTEE for the live DB:
    1. the live DB is opened with a read-only URI (`mode=ro`);
    2. it is snapshotted with sqlite3 `.backup()` (consistent, includes WAL);
    3. the engine runs against the SNAPSHOT only — the live file is never
       written, and no test messages are injected into the live queue.

Run (canonical repo, project venv):
    cd /data/projects/Lab-solocorp-os2.4
    PYTHONPATH=. .venv/bin/python <this file> --json-out <path>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

LIVE_DB = Path("/data/projects/Lab-solocorp-os2.4/central_bus/bus.db")
RULES_JSON = Path("/data/projects/Lab-solocorp-os2.4/bus/system/routing_rules.json")

# The 11 canonical cases — mirrors central_bus/tests/test_routing_ssot.py::SEMANTIC_MATRIX
# (10 department expectations + the no-match SSoT-fallback case).
MATRIX = [
    ("review the quarterly budget and cost report", "cfo"),
    ("deploy the backend api hotfix", "engineering"),
    ("run regression test suite for quality", "qa"),
    ("our solana smart contract needs an audit", "web3"),
    ("customer support ticket escalation", "support"),
    ("GDPR compliance review for the contract", "legal"),
    ("marketing content plan for the brand", "cmo"),
    ("fix a bug in the server", "engineering"),
    ("daily ops routine admin", "coo"),
    ("ช่วยดูเรื่องการเงินกับงบประมาณให้หน่อย", "cfo"),
    ("hello there, nice weather", "coo"),  # r_fallback → coo (NOT hardcoded ceo)
]


def snapshot_live_db(dest: Path) -> dict:
    """Consistent read-only snapshot of the live DB (includes WAL content)."""
    src_uri = f"file:{LIVE_DB}?mode=ro"
    src = sqlite3.connect(src_uri, uri=True, timeout=10)
    try:
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)
        finally:
            dst.close()
        meta = {
            "live_db": str(LIVE_DB),
            "live_db_bytes": LIVE_DB.stat().st_size,
            "snapshot": str(dest),
            "snapshot_bytes": dest.stat().st_size,
            "opened_read_only_uri": src_uri,
            "queue_rows_in_snapshot": src.execute(
                "SELECT COUNT(*) FROM queue"
            ).fetchone()[0],
            "routing_rules_in_snapshot": src.execute(
                "SELECT COUNT(*) FROM routing_rules"
            ).fetchone()[0],
        }
    finally:
        src.close()
    return meta


async def run_matrix(snapshot: Path) -> dict:
    from central_bus.db import DbManager
    from central_bus.router import RoutingEngine
    from central_bus.routing_sync import load_rules_doc, transform_all

    manager = DbManager(db_path=str(snapshot))
    await manager.init()
    try:
        engine = RoutingEngine(manager)

        count = await engine.count_rules()
        enabled_rows = await manager.fetch_all(
            "SELECT id, target_department FROM routing_rules WHERE enabled = 1"
        )
        db_ids = {r["id"] for r in enabled_rows}

        # SSoT parity: DB rows must equal the JSON SSoT rule ids.
        ssot_ids = {r["id"] for r in transform_all(load_rules_doc(RULES_JSON))}
        parity = {
            "ssot_json_rules": len(ssot_ids),
            "db_enabled_rules": len(db_ids),
            "missing_in_db": sorted(ssot_ids - db_ids),
            "extra_in_db": sorted(db_ids - ssot_ids),
            "parity_ok": ssot_ids == db_ids,
        }

        results = []
        for idx, (text, expected) in enumerate(MATRIX, 1):
            actual = await engine.match("ceo", {"text": text})
            results.append(
                {
                    "n": idx,
                    "payload": text,
                    "expected": expected,
                    "actual": actual,
                    "pass": actual == expected,
                }
            )

        passed = sum(1 for r in results if r["pass"])
        return {
            "engine_level_not_http": True,
            "count_rules": count,
            "parity": parity,
            "results": results,
            "passed": passed,
            "total": len(results),
            "all_pass": passed == len(results) and parity["parity_ok"] and count == 22,
        }
    finally:
        await manager.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", type=str, default="")
    args = ap.parse_args()

    if not LIVE_DB.exists():
        print(f"FATAL: live DB not found: {LIVE_DB}", file=sys.stderr)
        return 2

    tmpdir = tempfile.mkdtemp(prefix="routing-matrix-")
    snapshot = Path(tmpdir) / "bus-snapshot.db"

    meta = snapshot_live_db(snapshot)
    result = asyncio.run(run_matrix(snapshot))
    payload = {"snapshot_meta": meta, **result}

    # ── human table ────────────────────────────────────────────────
    print("=" * 78)
    print("ENGINE-LEVEL ROUTING MATRIX (not HTTP) — canonical code, live-DB snapshot")
    print("=" * 78)
    print(f"live DB        : {meta['live_db']} ({meta['live_db_bytes']} bytes)")
    print(f"opened as      : {meta['opened_read_only_uri']}")
    print(f"snapshot       : {meta['snapshot']} ({meta['snapshot_bytes']} bytes)")
    print(
        f"queue rows     : {meta['queue_rows_in_snapshot']} (untouched, no injection)"
    )
    print(f"count_rules()  : {result['count_rules']} (expected 22)")
    print(
        f"SSoT parity    : {result['parity']['parity_ok']} "
        f"(json={result['parity']['ssot_json_rules']}, db={result['parity']['db_enabled_rules']})"
    )
    print("-" * 78)
    print(f"{'#':<3}{'expected':<14}{'actual':<14}{'res':<5}payload")
    print("-" * 78)
    for r in result["results"]:
        mark = "PASS" if r["pass"] else "FAIL"
        print(f"{r['n']:<3}{r['expected']:<14}{r['actual']:<14}{mark:<5}{r['payload']}")
    print("-" * 78)
    print(
        f"MATRIX: {result['passed']}/{result['total']} passed | "
        f"overall: {'PASS' if result['all_pass'] else 'FAIL'}"
    )
    print("=" * 78)

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"json → {args.json_out}")

    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
