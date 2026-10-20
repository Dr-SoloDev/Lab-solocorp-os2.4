#!/usr/bin/env python3
"""ล้างข้อความค้างใน Central Bus queue (SQLite) — archive ก่อนลบเสมอ

ทำไมต้องมี: skill dispatch เขียนลง SQLite แต่ไม่มี consumer รับ
→ ข้อความค้างเป็น 'pending' นิรนัย (ดู ADR-019)

ใช้:
  python scripts/purge-stale-queue.py --dry-run          # ดูก่อน ไม่ลบ
  python scripts/purge-stale-queue.py --older-than 24h    # ล้างที่ค้างเกิน 24 ชม.
  python scripts/purge-stale-queue.py --status pending --agent-prefix "skill:"
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from central_bus.config import settings  # noqa: E402

ARCHIVE_DIR = ROOT / "bus" / "queue" / "archive"


def parse_age(text: str) -> timedelta:
    """'24h' / '7d' / '90m' → timedelta"""
    t = text.strip().lower()
    num = int("".join(ch for ch in t if ch.isdigit()) or 0)
    unit = t[-1] if t and t[-1].isalpha() else "h"
    mult = {"h": 1, "d": 24, "m": 1 / 60}.get(unit, 1)
    return timedelta(hours=num * mult)


def main() -> int:
    ap = argparse.ArgumentParser(description="Purge stale messages from the Bus queue")
    ap.add_argument("--db", default=None, help="path to bus.db")
    ap.add_argument("--status", default="pending",
                    help="status to purge (default: pending)")
    ap.add_argument("--agent-prefix", default=None,
                    help="only purge rows whose agent_id starts with this")
    ap.add_argument("--older-than", default="24h",
                    help="only purge rows created longer ago than this (default 24h)")
    ap.add_argument("--dry-run", action="store_true", help="show what would be purged")
    ap.add_argument("--yes", action="store_true", help="actually purge")
    args = ap.parse_args()

    db_path = Path(args.db) if args.db else Path(settings.db_path)
    if not db_path.is_absolute():
        db_path = ROOT / db_path
    if not db_path.exists():
        print(f"❌ ไม่พบ DB: {db_path}")
        return 1

    cutoff = (datetime.now(timezone.utc) - parse_age(args.older_than)).isoformat()

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    sql = "SELECT * FROM queue WHERE status = ? AND created_at < ?"
    params: list = [args.status, cutoff]
    if args.agent_prefix:
        sql += " AND agent_id LIKE ?"
        params.append(f"{args.agent_prefix}%")
    sql += " ORDER BY created_at ASC"
    rows = [dict(r) for r in conn.execute(sql, tuple(params))]
    conn.close()

    print(f"📂 DB: {db_path}")
    print(f"🔎 status={args.status} · created_at < {cutoff}"
          + (f" · agent_id LIKE '{args.agent_prefix}%'" if args.agent_prefix else ""))
    print(f"📋 พบ {len(rows)} ข้อความ")

    if not rows:
        print("✅ ไม่มีอะไรให้ล้าง")
        return 0

    for r in rows[:10]:
        print(f"   - {r['id'][:8]} {r['status']:8} {r.get('agent_id', '')[:40]:42} "
              f"{r.get('created_at', '')[:19]}")
    if len(rows) > 10:
        print(f"   ... และอีก {len(rows) - 10} ข้อความ")

    if args.dry_run or not args.yes:
        print("\n🔎 DRY RUN — ไม่ได้ลบ (ใช้ --yes เพื่อล้างจริง)")
        return 0

    # ── Archive ก่อนลบเสมอ ──
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    archive_file = ARCHIVE_DIR / f"purged-{args.status}-{stamp}.jsonl"
    with archive_file.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"💾 archive: {archive_file.relative_to(ROOT)} ({len(rows)} แถว)")

    ids = [r["id"] for r in rows]
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("BEGIN")
        for mid in ids:
            conn.execute("DELETE FROM queue WHERE id = ?", (mid,))
        conn.commit()
    finally:
        conn.close()

    print(f"🗑️ ลบ {len(ids)} ข้อความออกจาก queue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
