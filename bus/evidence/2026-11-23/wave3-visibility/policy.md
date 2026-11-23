# Wave 3 — Runtime Visibility: Watchdog Auto-Triage Policy

วันที่: 2026-11-23 · เจ้าของงาน: Orchestrator (พี่วุฒิ) · ผู้อนุมัติ: Owner (Option B)
ขอบเขต: ไม่แตะ `central_bus/health.py` (Wave 1/2), routing, seed, `opencode.jsonc`, campaigns

---

## 1. สิ่งที่ตรวจพบ (ข้อเท็จจริง ไม่ใช่การคาดเดา)

| # | คำถาม | ผลตรวจ |
|:-:|:------|:-------|
| 1 | `check_orphaned_messages` ถูก wire เข้า cron path จริงไหม? | **ใช่ แต่ "inert"** — `scripts/_watchdog_run.py:55` เรียกจริง และพิมพ์ผล แต่ไม่เคย *ตัดสินใจ* อะไรกับข้อความนั้น → ข้อความค้างต่อไม่จำกัด (เคสจริงค้าง 14 วัน) |
| 2 | worker หยิบงานแบบไหน? | `workers/agent_worker_service.py` poll เฉพาะ `status='routed'` → `pending`/`routed` ที่ไม่มีใครหยิบจะค้างตลอดกาล |
| 3 | cron ที่เกี่ยวข้องมีจริงไหม? | มี: `*/5` `scripts/_watchdog_run.py`, `*/5` `agent_worker_service --once`, `*/30` `loop_runner` (ดู `cron-baseline.txt`) |
| 4 | queue ค้างอยู่กี่ตัว? | `pending` = 0, `routed` = 0, `failed` = 1 (ซาก `watchdog-model-health-1793325601`, สร้าง 2026-10-30, mark failed 2026-11-13 ด้วย `W1-20261113:`) |
| 5 | MCP process กี่ตัวจริง? | **9 ตัว = 2 groups (ppid 5496 × 2 cwd), 0 duplicates** ตอนเริ่มงาน — "11 ตัว" เดิมมาจาก `pgrep` นับ shell ตัวเอง · หลังสร้าง worktree ของงานนี้เอง: **12 = 3 groups, 0 duplicates** (delta = MCP 3 ตัวของ worktree) |

> หมายเหตุสำคัญ: `/v1/observe` มี guard `action=report_back` ที่ปิดสถานะเป็น `completed` แล้ว
> (central_bus/main.py) — แถวที่ค้างเป็นของก่อน guard นั้นมีผล ดังนั้นช่องโหว่ที่เหลือคือ
> ข้อความ `routed` ที่ **ไม่ใช่** report_back และไม่มีใครหยิบ

---

## 2. Policy

| อายุของข้อความ (`status IN ('routed')`) | การกระทำ | ปลายทาง |
|:----------------------------------------|:---------|:--------|
| ≤ 24 ชั่วโมง | ไม่ทำอะไร | — |
| > 24 ชั่วโมง | **ALERT** | `ceo_alerts` (id = `triage-<message_id>-24h`) |
| > 7 วัน (168 ชม.) | **ALERT + FAIL** | `queue.status='failed'` + `error_log` entry `AUTO-TRIAGE: routed stale >7d ...` |
| `completed` / `failed` / `dead` | **ไม่แตะเด็ดขาด** | — |

- เกณฑ์เป็น *cumulative*: ข้อความ >7d จะได้ alert ด้วย (ถ้ายังไม่มี) แล้วจึง fail
- ไม่ย้ายเข้า `dead_letter_queue` — คงรูปเดียวกับ precedent `W1-20261113` เพื่อให้ CEO เห็นและ ack จากที่เดียว
- `attempt: 0` ใน error_log = ระบบเป็นคนตัดสิน ไม่ใช่ retry ของ agent (ไม่ทำให้ `retry_count` เพิ่ม)
- `pending` อยู่นอกขอบเขตโดยค่าเริ่มต้น (worker ไม่หยิบ `pending` อยู่แล้ว และ `check_orphaned_messages` คุมอยู่) — เปิดได้ด้วย `--statuses routed,pending` ถ้าต้องการ

---

## 3. Idempotency (กัน alert ท่วมทุก 5 นาที)

| กลไก | รายละเอียด |
|:-----|:-----------|
| Alert id deterministic | `INSERT OR IGNORE` ด้วย id `triage-<message_id>-24h` → รอบถัดไปไม่สร้างซ้ำ |
| Marker ใน error_log | มี entry `auto_triage: true` แล้ว (ยังไม่ resolved) → ไม่ append ซ้ำ |
| Resolved = หยุด | entry ที่ `resolved: true` → ข้ามถาวร ("คนแก้แล้ว ไม่แตะ") |
| Optimistic update | `UPDATE ... WHERE id=? AND status IN ('routed','pending') AND IFNULL(error_log,'')=IFNULL(<ค่าที่อ่านมา>,'')` → ถ้ามีคนแก้ระหว่างทาง จะไม่ทับ (rowcount = 0 = ข้าม) |
| Terminal status | คัดเฉพาะ `routed` ตั้งแต่ query → `completed` ไม่ถูกแตะเชิงโครงสร้าง |

---

## 4. Safety / Rollout

| ข้อ | สถานะ |
|:----|:------|
| default = **report-only (dry-run)** | ✅ ไม่เขียน DB เลยถ้าไม่ใส่ `--apply` |
| เปิดเขียนจริง | `SOLOCORP_WATCHDOG_TRIAGE_APPLY=1` (env ตอนสั่งรัน) หรือ `python -m central_bus.watchdog_triage --apply` |
| แก้ crontab | ❌ **ไม่แก้** — cron เดิมเรียกสคริปต์เดิม; พฤติกรรมใหม่มาพร้อมโค้ดที่ merge แล้วเท่านั้น |
| apply กับ live ในรอบนี้ | ❌ **ไม่ทำ** — Owner ดู report 1 สัปดาห์ก่อน |
| ลบ/แก้ข้อมูลเดิม | ❌ ไม่มี — แถว `failed` เดิม (W1) ไม่ถูกแตะ |

Rollout: merge → canonical checkout (`/data/projects/Lab-solocorp-os2.4`) pull → cron เริ่มพิมพ์
triage report ทุก 5 นาที (ไม่มี candidate = ไม่มี output) → Owner ดู 1 สัปดาห์ →
ถ้าเห็นด้วย ตั้ง `SOLOCORP_WATCHDOG_TRIAGE_APPLY=1` ใน cron **แยกการตัดสินใจอีกรอบ**

---

## 5. Dry-run บน live DB (2026-11-23)

```
ตรวจ 0 แถว · alert 0 · fail 0 · เปลี่ยนสถานะ 0 · เขียน alert 0
✅ ไม่มีข้อความ routed ค้างเกินเกณฑ์
```

คาดการณ์ไว้ 0 routed ค้าง — ตรงกับผลจริง (`pending`=0, `routed`=0)

---

## 6. NOT done (ห้ามรายงานว่าเสร็จ)

- ไม่ได้รัน `--apply` กับ live DB — ไม่มีหลักฐานว่าการเขียนจริงบน live ทำงาน (พิสูจน์บน temp DB แทน 17 เทสต์)
- ไม่ได้แก้ `central_bus/health.py` — surface ของ health ยังไม่โชว์ triage state (งาน Wave 1/2)
- ไม่ได้แตะ `/v1/observe`, routing, seed, `opencode.jsonc`
- ไม่ได้แก้ crontab
- ไม่ได้ kill/respawn MCP process ใด ๆ (diagnose เป็น read-only)
