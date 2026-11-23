# Wave 3 — Runtime Visibility (2026-11-23)

Owner อนุมัติ **Option B** · งานเฉพาะส่วนที่ไม่แตะ `central_bus/health.py` (Wave 1/2 ถือกรรมสิทธิ์)

## ผลลัพธ์สรุป

| # | งาน | ผล |
|:-:|:----|:----|
| 1 | `scripts/mcp-diagnose.py` | **9 processes = 2 groups (ppid 5496 × 2 cwd), 0 duplicates** — พิสูจน์บนเครื่องจริง |
| 2 | Watchdog auto-triage | `check_orphaned_messages` **wire อยู่แล้วแต่ inert** (รายงานเฉย ๆ ไม่ตัดสินใจ) → เพิ่ม policy >24h alert / >7d fail, default report-only |
| 3 | Tests | 23 เทสต์ใหม่ผ่าน (17 triage + 6 diagnose) · full suite 1403 passed, 1 pre-existing failure (พิสูจน์บน origin/main) |
| 4 | Dry-run live DB | **0 routed ค้าง · 0 alert · 0 fail** (ตรงกับที่คาด) |

## ไฟล์ในชุดหลักฐานนี้

| ไฟล์ | อะไร |
|:-----|:-----|
| `mcp-diagnose.txt` | ผลจริงจากการรันบนเครื่องนี้ (9 ตัว / 2 groups) |
| `mcp-diagnose.json` | รูปแบบ machine-readable (ใช้ตรวจซ้ำ/ทำ dashboard) |
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
