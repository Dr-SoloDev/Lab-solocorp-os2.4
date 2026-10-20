"""Watchdog cron — ตรวจสุขภาพคิวทุก 5 นาที

ตรวจ 3 อย่าง:
  1. ประมวลผลข้อความในคิว (watchdog_loop)
  2. dead letters (ข้อความตายจริง)
  3. orphaned messages — ข้อความที่ค้างและไม่มีใครจะมารับ (กันตายเงียบ)
"""
from central_bus.monitor_watchdog import (
    watchdog_loop,
    check_dead_letters,
    check_orphaned_messages,
)
import sys

processed = watchdog_loop(max_iterations=5)
stuck = check_dead_letters()
orphans = check_orphaned_messages()

if processed > 0:
    print(f"[OK] Watchdog processed {processed} messages")

if stuck:
    print(f"[WARN] Dead letters: {len(stuck)} stuck messages")
    for item in stuck[-3:]:
        print(f"   - {item.get('reason', 'unknown')}: "
              f"{item.get('message', {}).get('trace_id', '?')[:20]}")

if orphans:
    print(f"[WARN] Orphaned messages: {len(orphans)} ค้างและไม่มีใครรับ")
    for o in orphans[-5:]:
        print(f"   - {o['id'][:8]} status={o['status']} "
              f"target={o['target_agent']} — {o['reason']}")
    print("[WARN] แก้: ตั้ง target_agent ให้เป็น agent_id ที่ลงทะเบียน "
          "(ดู workers/agent_worker_service.py AGENT_IDS) หรือล้างด้วย "
          "scripts/purge-stale-queue.py")
    sys.exit(1)  # ให้ cron log เห็นเป็น error → เห็นง่ายขึ้น
