# Wave 3 — Runtime Visibility (2026-11-23)

Owner อนุมัติ **Option B** · งานเฉพาะส่วนที่ไม่แตะ `central_bus/health.py` (Wave 1/2 ถือกรรมสิทธิ์)

## ผลลัพธ์สรุป

| # | งาน | ผล |
|:-:|:----|:----|
| 1 | `scripts/mcp-diagnose.py` | **9 processes = 2 groups (ppid 5496 × 2 cwd), 0 duplicates** ตอนเริ่มงาน → หลังสร้าง worktree ของ Wave 3 เอง เครื่องมี **12 = 3 groups, 0 duplicates** (delta = MCP 3 ตัวของ worktree นี้) |
| 2 | Watchdog auto-triage | `check_orphaned_messages` **wire อยู่แล้วแต่ inert** (รายงานเฉย ๆ ไม่ตัดสินใจ) → เพิ่ม policy >24h alert / >7d fail, default report-only |
| 3 | Tests | 23 เทสต์ใหม่ผ่าน (17 triage + 6 diagnose) · full suite 1403 passed, 1 pre-existing failure (พิสูจน์บน origin/main) |
| 4 | Dry-run live DB | **0 routed ค้าง · 0 alert · 0 fail** (ตรงกับที่คาด) |

> **ทำไมมีสองตัวเลข (9 กับ 12):** ตัวเลข "11 ตัว" เดิมมาจาก `pgrep` ที่นับ shell ตัวเอง
> ตอนเริ่มงานตัวนับที่ถูกต้องได้ **9 = 2 groups** (`mcp-diagnose-0751-baseline.txt`)
> ระหว่างทางงานนี้สร้าง git worktree ใหม่ → OpenCode spawn MCP ชุดของ worktree นั้นเพิ่ม 3 ตัว
> → รันซ้ำได้ **12 = 3 groups** (`mcp-diagnose.txt/.json` ซึ่งเป็น live ล่าสุด)
> **ทั้งสองรอบมี 0 duplicates** และ delta คือ "module เดียวกันคนละ project root" — เคสที่ต้องไม่ถูก flag
> เป็น duplicate ซึ่งเป็นสิ่งที่เครื่องมือนี้แยกให้เห็น

## ไฟล์ในชุดหลักฐานนี้

| ไฟล์ | อะไร |
|:-----|:-----|
| `mcp-diagnose-0751-baseline.txt` | ผลจริงตอนเริ่มงาน (9 ตัว / 2 groups) — ก่อน worktree ของ Wave 3 จะ spawn MCP ของตัวเอง |
| `mcp-diagnose.txt` | ผลจริงล่าสุดบนเครื่องนี้ (12 ตัว / 3 groups — เพิ่ม worktree นี้ 3 ตัว) |
| `mcp-diagnose.json` | รูปแบบ machine-readable ของรอบล่าสุด (ใช้ตรวจซ้ำ/ทำ dashboard) |
| `watchdog-triage-dryrun.txt` | dry-run กับ **live DB** (read-only) |
| `watchdog-triage-dryrun.json` | dry-run แบบ JSON (นับ `checked/alert/fail/changed`) |
| `live-queue-before.txt` | snapshot queue ก่อนเปลี่ยน (pending 0 / routed 0 / failed 1) |
| `cron-baseline.txt` | crontab ปัจจุบัน — **หลักฐานว่าไม่ได้แก้** |
| `policy.md` | นโยบายฉบับเต็ม + idempotency + rollout + NOT done |
| `test-results.txt` | ผล full suite + หลักฐานว่า failure ที่เหลือเป็นของเดิม |

## วิธีรันซ้ำ

```bash
# ต้องมี venv ของ repo และรันจาก repo root
source .venv/bin/activate && export PYTHONPATH=.

# 1) MCP truth
python scripts/mcp-diagnose.py
python scripts/mcp-diagnose.py --json

# 2) triage — dry-run (ค่าเริ่มต้น ไม่เขียนอะไร)
python -m central_bus.watchdog_triage --db /data/projects/Lab-solocorp-os2.4/central_bus/bus.db

# 3) triage — เขียนจริง (อย่ารันกับ live จนกว่า Owner จะอนุมัติหลังดู report 1 สัปดาห์)
SOLOCORP_WATCHDOG_TRIAGE_APPLY=1   # สำหรับ cron path
python -m central_bus.watchdog_triage --db <path>/bus.db --apply

# 4) เทสต์
python -m pytest tests/test_watchdog_triage.py tests/test_mcp_diagnose.py -q
```

## สิ่งที่ **ไม่** ทำในรอบนี้ (ห้ามตีความเป็นเสร็จ)

- ไม่รัน `--apply` กับ live DB (พิสูจน์การเขียนบน temp DB 17 เทสต์แทน)
- ไม่แก้ crontab — พฤติกรรมใหม่จะเริ่มเมื่อ merge แล้ว canonical checkout pull เท่านั้น
- ไม่แตะ `central_bus/health.py`, routing, seed, `opencode.jsonc`
- ไม่ kill/respawn MCP process ใด ๆ (diagnose เป็น read-only)
- ไม่แก้ `tests/test_solocorp_app_live.py` ที่ fail อยู่ (pre-existing, พิสูจน์แล้ว)
