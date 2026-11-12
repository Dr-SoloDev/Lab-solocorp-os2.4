# PR2.1 Live Hardening — Product Contract v1.0 (Spec อย่างเดียว ห้ามโค้ด)

> Owner: @product-produck (Head of Product) · Date: 2026-11-12
> Base: `main@c449702` Beta v1 PASS 10/10 · Target: PR2.1 hardening (Architect D1–D7)
> Status: **DRAFT for CEO Go** — ไฟล์นี้คือ contract ล็อกสเปก, ไม่ใช่ implementation

## 1. Baseline Beta v1 (ล็อกไว้ห้ามถอยหลังถกใหม่)

- Routes 4 ตัว: `GET /live` + `GET /api/sessions` + `GET /api/bus/queue` + `GET /api/live/status`
- `live.py`: sessions cache TTL **10s**, `CLI_TIMEOUT_S = 4.0s` (> poll 3s → เสี่ยง overlap), มี DB fallback (`_sessions_from_db` → `source=db`)
- `static/app.js` **291 บรรทัด** = 92 (modules poll `/api/modules` 5s) + 199 (live poll `/api/live/status` 3s) ต่อเติมในไฟล์เดียว
- `live_status()` คืน `session_source/session_error/queues/queue_total/modules/provider_state/updated_at` — ยังไม่มี `degraded/queue_source/cache_hit/tasks_summary`, cap, single-flight

## 2. PR2.1 Contract (ล็อก — เลือกอย่างเดียว ห้ามคลุมเครือ)

### 2.1 Routes: เหลือ 2 เท่านั้น

| Route | เก็บ | หมายเหตุ |
|:------|:----|:---------|
| `GET /live` (SSR page) | ✅ | server-render รอบแรกคือความจริง, poll ต่อด้วย `live.js` |
| `GET /api/live/status` (JSON เดียว) | ✅ | แหล่ง poll เดียวของหน้า /live ทุก 3s |
| `GET /api/sessions` | ❌ ลบ | เรียกแล้วต้อง **404** (ไม่ใช่ redirect/500) |
| `GET /api/bus/queue` | ❌ ลบ | เรียกแล้วต้อง **404** — queue ดูผ่าน `/api/live/status.queues` เท่านั้น |

ห้ามเพิ่ม route ใหม่ใน PR2.1 (healthz/modules/tasks/settings ไม่เกี่ยว ห้ามแตะ)

### 2.2 Schema `GET /api/live/status` (ล็อกคำตอบข้อคลุมเครือ)

**ตัดสินใจล็อก:** ต้องมีครบทั้ง 5 ฟิลด์ `degraded / queue_source / cache_hit / tasks_summary / updated_at`
และ **เก็บ `session_source / session_error / error` ไว้ร่วมด้วย (ไม่ใช่ทางเลือกแทน)** — แยก semantics ชัดเจนดังนี้ ห้ามใช้สลับกัน:

| ฟิลด์ | type | ค่าที่อนุญาต | ความหมาย (ล็อก) |
|:------|:-----|:-------------|:----------------|
| `sessions` | list | session envelope (cap ตาม §2.5) | แถวที่ normalize แล้ว |
| `session_count` | int | `len(sessions)` | ห้ามไม่ตรงกัน |
| `session_source` | string | `"cli"` \| `"none"` เท่านั้น (**ตัด `"db"` ทิ้ง**) | ป้าย source ฝั่ง session |
| `session_error` | string\|null | ข้อความ ≤200 ตัวอักษร | เหตุผลฝั่ง session เท่านั้น (CLI fail ว่าอะไร) |
| `queues` | object | `{critical,high,normal,low,dead}` int | นับ JSONL (ops metric อย่างเดียว ไม่ใช่ task truth) |
| `queue_total` | int | sum(queues) | ห้ามไม่ตรงกัน |
| `queue_source` | string | `"files"` \| `"empty"` \| `"truncated"` \| `"unavailable"` | ป้าย source ฝั่ง queue (คู่กับ session_source = "ป้าย source คู่") |
| `queue_error` | string\|null | ≤200 ตัวอักษร | เหตุผลฝั่ง queue เท่านั้น |
| `cache_hit` | bool | true/false | true = เสิร์ฟจาก cache (sessions 15s / queue 5s), false = เรียก source สด |
| `degraded` | bool | true/false | สูตรล็อก §2.3 — UI ใช้ฟิลด์นี้ฟิลด์เดียวตัดสินป้ายเหลือง/แดง |
| `tasks_summary` | object | `{total, by_status, updated_at}` | **Single source of truth จาก `TaskTracker.list_tasks()` เท่านั้น** ห้ามนับจาก `bus/queue/*.jsonl` |
| `modules/module_states/provider_state/registry_valid` | คงเดิม Beta | — | ไม่เปลี่ยน shape ใน PR2.1 |
| `error` | string\|null | ≤200 ตัวอักษร | **runtime read fail เท่านั้น** ห้ามใช้แทน session/queue error |
| `updated_at` | string | ISO-8601 UTC seconds | เวลาตอบ envelope นี้ (cache envelope เก็บ `updated_at` ของรอบที่สร้าง ไม่ใช่เวลาขอ) |

ตัวอย่าง envelope ขั้นต่ำ (ฟิลด์อื่นคงเดิมได้):
```json
{
  "sessions": [], "session_count": 0,
  "session_source": "none", "session_error": "opencode CLI not found",
  "queues": {"critical":0,"high":0,"normal":0,"low":0,"dead":0}, "queue_total": 0,
  "queue_source": "empty", "queue_error": null,
  "cache_hit": false, "degraded": true,
  "tasks_summary": {"total": 3, "by_status": {"done": 2, "running": 1}, "updated_at": "2026-11-12T00:00:00+00:00"},
  "error": null, "updated_at": "2026-11-12T00:00:00+00:00"
}
```

### 2.3 สูตร `degraded` (ล็อก — ห้ามตีความหน้างาน)

`degraded = true` เมื่อ **ข้อใดข้อหนึ่ง** เป็นจริง:
1. `session_source == "none"`, หรือ
2. `queue_source in ("truncated","unavailable")`, หรือ
3. `error is not null`, หรือ
4. `provider_state in ("unknown","failed")` หรือ `registry_valid == false`

นอกนั้น `false`. ห้ามเพิ่มเงื่อนไขลับโดยไม่แก้ spec นี้

### 2.4 Cache / Concurrency / Timeout (ล็อกตัวเลข Architect D1–D7)

- **Sessions TTL 15s / Queue TTL 5s / Error TTL 5s** (ล็อกความหมาย "15s/5s": sessions 15s, queue 5s; ผลล้มเหลว `source=none`/`unavailable` cache ได้สูงสุด 5s — ห้าม cache ความว่าง 15s)
- **Single-flight:** poll ซ้อนกันต้องรวมเป็น CLI call เดียว (lock/event — ห้าม spawn ซ้ำขณะ in-flight)
- **`CLI_TIMEOUT_S = 1.5s`** (จาก 4.0s → สั้นกว่า poll 3s, กัน overlap; timeout นับเป็น `session_source=none` + `session_error` + `degraded=true`, ห้าม 500)
- `cache_hit` ต้องตอบตามจริงทุกครั้ง (test จับได้)

### 2.5 Cap กันบวม (ล็อก)

- อ่าน queue ไฟล์ละไม่เกิน **50,000 บรรทัด**, รวมทุกไฟล์ไม่เกิน **8MB**; เกิน → หยุดอ่าน + `queue_source="truncated"` + `queue_error="queue cap exceeded (50k lines / 8MB)"` + `degraded=true`
- `sessions` ถูกตัดที่ `limit` (default 30, max 100) เท่าเดิม ไม่เปลี่ยนใน PR2.1

### 2.6 ตัด DB ทิ้ง (ล็อก + เงื่อนไข ADR)

- ลบ `_sessions_from_db` path ทั้งหมด + `db_path` param + `source="db"` enum ออกจาก contract นี้
- **เงื่อนไข:** การลบมีผลได้ก็ต่อเมื่อมี **ADR ใหม่โดย Architect** (ให้เหตุผล + ผลกระทบ allowlist/`opencode.db`) — ถ้า ADR ยังไม่ออก ห้ามอ้างว่า "ตัด DB แล้ว" ใน DoD

### 2.7 แยก `live.js` + freeze `app.js` (ล็อกความหมาย "92+291 ห้ามแตะ")

- Beta `app.js` 291 บรรทัด = 92 (modules) + 199 (live) — ตรวจพบความขัดแย้งในคำสั่ง (แยกไฟล์ แต่ diff ว่าง) จึงล็อกแบบนี้:
- PR2.1 ทำ **ครั้งเดียว**: ย้ายบล็อก live (บรรทัด 94–291 เดิม, poll `/api/live/status` 3s + single-instance guard) ไป `static/live.js` ใหม่; `static/app.js` เหลือ **92 บรรทัด modules-only**; `live.html` เปลี่ยน script tag มาอ้าง `live.js` (ห้าม inline script/CSP แตก)
- หลัง split เสร็จ บันทึก SHA-256 ของทั้งสองไฟล์ไว้ใน PR description — **หลังจากนั้น freeze: DoD ข้อ 6 ตรวจ diff ว่างเทียบกับ hash นี้** (ไม่ใช่เทียบ Beta 291) ห้ามแตะ logic ใดๆ ทั้งสองไฟล์ตลอด PR2.1 verification

## 3. DoD PR2.1 (6 ข้อ — ไม่ผ่านข้อเดียว = ไม่ Go)

| # | ข้อ | วิธีตรวจ (ล็อกคำสั่ง/เกณฑ์) | ผ่านเมื่อ |
|:-:|:----|:---------------------------|:---------|
| 1 | Poll 10 นาที spawn ≤40 | รันหน้า /live poll 3s นาน 10 นาที (200 polls) นับ process spawn `opencode session list` (log counter/strace) | spawn ≤40 (600s/15s TTL) |
| 2 | ถอด CLI แล้ว 200 `source=none` | `PATH` ไม่มี opencode (หรือ binary คืน non-zero) แล้ว `GET /api/live/status` | 200 + `session_source="none"` + `session_error` มีข้อความ + `degraded=true` + หน้า /live render ได้ (ห้าม 500) |
| 3 | Queue ว่างแต่ tasks ขึ้น | ล้าง `bus/queue/*.jsonl` ให้ว่าง แต่ `TaskTracker` มี task ≥1 แล้ว `GET /api/live/status` | `queue_total==0` แต่ `tasks_summary.total>=1` (พิสูจน์แยก truth: tasks มาจาก tracker ไม่ใช่ queue) |
| 4 | Session ใหม่ ≤20s | สร้าง session ใหม่ 1 ตัว แล้วจับเวลาโผล่ใน `sessions` | ≤20s (TTL 15s + poll 3s + margin 2s) |
| 5 | Secret guard | grep secret (`api_key`, `sk-`, credential file content) ใน git diff/log/artifact + ตรวจ `provider.json` เก็บแค่ `api_key_ref` | ไม่พบ secret หลุด; ตรวจซ้ำหลัง split `live.js` |
| 6 | `app.js`/`live.js` diff ว่าง (frozen) | `git diff --stat static/app.js static/live.js` + เทียบ SHA-256 ที่บันทึกหลัง split | diff ว่าง + hash ตรง (ห้ามแตะหลัง freeze) |

## 4. Out-of-scope (ห้ามลากเข้า PR2.1)

1. **Phase 2 CEO loop** (`runtime.call_tool` / `host.call_tool` chain) — ห้ามขยาย scope
2. **Standalone / packaging / deploy** — ไม่นับใน DoD นี้
3. **Concat render / media pipeline** — ห้ามอ้างเป็นหลักฐานหรือเงื่อนไข
4. **การลบ DB path** ต้องมี ADR ใหม่โดย **Architect** ก่อน (§2.6) — Product ไม่เขียน ADR นี้เอง
5. ห้ามเปลี่ยน shape `modules/tasks/settings/healthz`, ห้ามแตะ provider/registry logic, ห้ามเพิ่ม dependency ใหม่

## 5. Handoff กลับ CEO: test เดิมต้องแก้อย่างไร (ล็อกแนวทางให้ QA/Architect)

ไฟล์ `tests/test_solocorp_app_live.py` (190 บรรทัด, เขียนบนสมมติ Beta 4 routes + DB fail-open) **ต้องแก้ก่อนอ้าง DoD** ดังนี้:

| ของเดิม (Beta) | ปัญหาใน PR2.1 | ต้องแก้เป็น |
|:---------------|:--------------|:------------|
| `test_api_sessions_is_fail_open_json` (เรียก `/api/sessions`, ยอมรับ `source in (cli,db,none)`) | route ถูกลบ + enum `db` ถูกตัด | **ลบ test นี้** แล้วแทนด้วย `test_removed_routes_are_404` (assert `/api/sessions` + `/api/bus/queue` → 404) |
| `test_api_bus_queue_counts_jsonl_lines` (เรียก `/api/bus/queue` ตรง) | route ถูกลบ | **ย้าย assertion ลง `/api/live/status`**: เขียน high/normal jsonl แล้ว assert `payload["queues"]` + `payload["queue_source"]=="files"` ผ่าน status endpoint แทน |
| `test_api_live_status_combines_everything` (assert ชุดฟิลด์ Beta) | ขาด 5 ฟิลด์ใหม่ | **ขยาย assert**: `{"degraded","queue_source","cache_hit","tasks_summary","updated_at","session_source","queue_error"}` + `session_source in ("cli","none")` (ห้าม `"db"`) + `tasks_summary.total/by_status` |
| `test_live_endpoints_need_no_csrf...` (loop 4 paths) | 2 paths ไม่มีแล้ว | **เหลือ loop 2 paths** (`/live`, `/api/live/status`) + เพิ่ม loop 404 สำหรับ 2 paths ที่ลบ |
| `test_list_sessions_fail_open...` + `queue_cli/db_path` params, `test_list_sessions_with_fake_cli` | DB fallback ยังอยู่ | **ลบ `db_path` ทุกจุด**; fail-open test ใช้ CLI-missing อย่างเดียว → assert `source=="none"`; เพิ่ม `test_cache_hit_and_singleflight` (เรียกซ้ำใน TTL → `cache_hit=true` + spawn 1 ครั้ง) และ `test_queue_cap_truncated` (ไฟล์เกิน cap → `queue_source=="truncated"` + `degraded=true`) |
| `test_live_page_renders...` assert `"3s"` | ยังใช้ได้ | คงไว้ + เพิ่ม assert ว่า page อ้าง `live.js` (ไม่ใช่ inline live logic ใน `app.js`) |

เกณฑ์: แก้ test แล้วต้องรันชุดเดิมคำสั่ง CI (`pytest tests/ central_bus/tests/ --tb=short ... -q`) เขียวเต็มก่อนอ้าง PASS — ห้าม cherry-pick

## 6. Handoff

- **→ CEO:** ขอ Go PR2.1 ตาม contract นี้ (2 routes + schema 5 ฟิลด์ + DoD 6 ข้อ); ถ้าไม่เห็นด้วยกับข้อใดข้อหนึ่ง ส่งกลับ Product ก่อนสั่ง Architect ลงมือ
- **→ Architect (@songsak):** ขอ ADR ใหม่เรื่องตัด DB (เงื่อนไข §2.6) + ออกแบบ single-flight/cache/cap/timeout ตามตัวเลข §2.4–2.5
- **→ QA:** แก้ `test_solocorp_app_live.py` ตามตาราง §5 ก่อนรัน DoD; หลักฐานเก็บ `bus/evidence/` ตาม SOP-06
- Product งานจบที่ spec นี้ — **ไม่เขียนโค้ด ไม่แก้ test เอง ไม่ commit**
