#!/usr/bin/env python3
"""📊 รายงาน token/quota — "วันนี้ทั้ง org กินเท่าไร ใครกิน"

ต่างจาก ledger ตรงไหน
─────────────────────
  · ledger (bus/system/token-ledger.jsonl) = เฉพาะ call ที่ `workers/` ยิง
  · DB report (สคริปต์นี้)                = ทุก session ในเครื่อง รวม desktop/CEO
    → ตัวเลขที่ควรใช้ตัดสินใจเรื่องโควตา/เงิน คือตัว DB

ตัวอย่าง
────────
  python scripts/token-report.py                 # วันนี้
  python scripts/token-report.py --days 3        # 3 วันย้อนหลัง
  python scripts/token-report.py --sessions 5    # ใครกินโควตามากสุด 5 อันดับ
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workers import token_ledger as tl  # noqa: E402


def _k(n: float) -> str:
    n = float(n or 0)
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if abs(n) >= 1000:
        return f"{n/1000:.1f}k"
    return f"{int(n)}"


def main() -> int:
    ap = argparse.ArgumentParser(description="รายงาน token/quota ของ SoloCorp OS")
    ap.add_argument("--days", type=int, default=1, help="ย้อนหลังกี่วัน (default 1)")
    ap.add_argument("--sessions", type=int, default=5, help="แสดง top N session (0=ปิด)")
    args = ap.parse_args()

    now = datetime.now().astimezone()
    # --days 1 = วันนี้ทั้งวัน, --days 3 = 3 วันรวมวันนี้
    start = (now - timedelta(days=max(0, args.days - 1))).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start_ms = int(start.timestamp() * 1000)

    print(f"=== SoloCorp token report · {start.date()} → {now.date()} ===")

    q = tl.quota_status()
    if q["locked"]:
        print(f"🔒 quota lock: {q['reason']} ถึง {q['until']} (~{q['remaining_s']//60} นาที)")
    else:
        print("🔓 quota: ไม่ถูกล็อก")

    led = tl.today_totals()
    att = tl.today_attempts()
    print(
        f"\nledger (call ที่ workers ยิงเอง):  {tl.format_usage(led)}"
        f"  · ยิง {att['ok']} สำเร็จ / {att['failed']} ล้ม"
    )

    db = tl.read_db_usage(start_ms)
    if db.get("error"):
        print(f"⚠️ อ่าน opencode.db ไม่ได้: {db['error']}")
    else:
        print(f"db (ทุก session ในเครื่อง):      {tl.format_usage(db)}")
        print(f"   requests สำเร็จ {db['requests']} · ล้ม/ถูกปฏิเสธ {db['failed']}")

    if args.sessions:
        rows = tl.read_db_usage_by_session(start_ms, limit=args.sessions)
        if rows:
            print(f"\n{'session':28s} {'req':>5s} {'out':>8s} {'reason':>8s} {'cache':>9s}")
            for r in rows:
                print(
                    f"{r['session_id'][:28]:28s} {r['requests']:5d} "
                    f"{_k(r['output']):>8s} {_k(r['reasoning']):>8s} {_k(r['cache_read']):>9s}"
                )

    lim = tl.budget_limits()
    b = tl.check_budget(led, lim)
    state = "OK" if b["ok"] else "เกิน"
    if b["warn"]:
        state = "ใกล้เต็ม"
    print(
        f"\nbudget วันนี้: {state} — requests {led['requests']}/{lim['requests']} · "
        f"output {_k(led['output'])}/{_k(lim['output_tokens'])} · "
        f"${float(led['cost']):.4f}/${lim['cost_usd']:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
