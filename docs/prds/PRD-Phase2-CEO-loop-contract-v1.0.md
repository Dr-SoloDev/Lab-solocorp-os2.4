# Phase 2 CEO Loop — Product Contract v1.0 (Spec อย่างเดียว ห้ามโค้ด)

> Owner: @product-produck (Head of Product) · Date: 2026-11-13
> Base: `main@10968b7` PR2.1 CLOSED · Target: Phase 2 เปิด CEO loop (PRD FR-03/04/05)
> Status: **DRAFT for CEO Go** — ไฟล์นี้คือ contract ล็อกสเปก, ไม่ใช่ implementation
> Parent: PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0 (§7 Must Have ข้อ 7–8, §11 Phase 2 gate) + Runtime Design D7

## 1. Baseline ที่ล็อกไว้ (ห้ามถกใหม่)

- `GET /chat` = หน้า SSR placeholder ("Not wired yet", `chat.html:16`) — Phase 2 เติมวงจรหลังบ้าน ไม่เปลี่ยนเลย์เอาต์หน้านี้เกินจำเป็น
- `runtime.call_tool` ปัจจุบันคือ passthrough ตรงไป `host.call_tool` (`runtime.py:190-198`) — ยังไม่มี record-before-invoke, ไม่มี route_reason, ไม่มี terminal guarantee
- Task envelope เก่า (`axis_mcp/task_tracking.py:create`): `task_id/dept/module/task_type/status/brief/created_at/started_at/completed_at/result_ref/error_detail` — `result_ref` ตัวเดียว (string|null), `error_detail` เป็น string อิสระ (ไม่มี code/hint)
- `tasks.html` อ่าน `artifact_refs[]` ก่อนแล้ว fallback `result_ref` — แต่ tracker ไม่เคยเขียน `artifact_refs` (UI รอของที่ไม่มีใครผลิต)
- `ModuleHost.call_tool` โยน `ModuleHostError("module X is disabled/unavailable")` เมื่อ disabled หรือ connect ล้มเหลว — Phase 2 ต้องแปลงเป็น task `failed` ที่มี hint ไม่ใช่ 500 เปล่า

## 2. Phase 2 Contract (ล็อก — เลือกอย่างเดียว ห้ามคลุมเครือ)

### 2.1 `POST /chat`: วงจรเดียว brief → terminal (D7 synchronous)

**Route:** `POST /chat` ใหม่บน `writes` router (ต้องผ่าน `require_csrf` เหมือน toggle/settings — ไม่ยกเว้น)

**Request (form หรือ JSON — รับทั้งคู่, ล็อกแค่นี้):**

| ฟิลด์ | type | กฎ |
|:------|:-----|:---|
| `brief` | string | trim แล้วต้องยาว 1–2000 ตัวอักษร; ว่าง/เกิน → **400 + ไม่สร้าง task** (ดู §2.4 `BRIEF_INVALID`) |

**ลำดับบังคับ (ห้ามสลับ ห้ามข้าม):**

```
1. validate brief                → ล้ม = 400, ไม่สร้าง task
2. resolve route                  → content-creator ตัวเดียวใน Phase 2 (§2.2)
3. TaskTracker.create(...)        → status=pending, เก็บ brief + route_reason + app_version ตั้งแต่เกิด
4. update running                 → started_at ประทับก่อน invoke เสมอ
5. runtime.call_tool(...)          → sync, timeout 60s (เท่า host default)
6. terminal write                 → completed หรือ failed + completed_at เสมอ (ห้ามค้าง pending/running หลัง response)
7. respond                        → redirect ไป /tasks?task=<id> (SSR) หรือ JSON envelope (API) — อย่างใดอย่างหนึ่งต้องมี task_id
```

**Response ล็อก 2 แบบ (server เลือกตาม Accept/Content-Type แต่ shape ต้องตรงนี้):**

- SSR: `303 → /tasks?task=<task_id>` (pattern เดียวกับ toggle/provider — reload ไม่ยิงซ้ำ)
- JSON: `200` พร้อม task envelope เต็ม (§2.3) — กรณี `failed` ก็ยัง `200` + envelope `status=failed` (failed คืองานที่จบแล้ว ไม่ใช่ HTTP error; HTTP 4xx/5xx ใช้เฉพาะ validate ล้มหรือ app พังเท่านั้น)

**ห้าม:** เปิดแชทที่สอง, spawn background worker/LLM session ของแผนก, silent fallback ไป model/แผนกอื่น (D5 + D7), คืน "สำเร็จเทียม" ก่อน invoke เสร็จ

### 2.2 Routing (FR-03 — ล็อกรูปแบบ Phase 2)

Phase 2 มีแผนกเดียวที่ route ได้: **`content-creator`**

| กรณี | route ไป | `route_reason` ที่บันทึก (ล็อก template) |
|:-----|:---------|:------------------------------------------|
| content-creator `enabled` + observation `connected`/`connecting` | `content-creator` | `"Phase2 single-candidate route: brief asks for content work; content-creator is the only enabled department"` |
| content-creator disabled / error / ไม่ต่อติด | **ไม่ route ไปไหน** → สร้าง task `failed` ตาม §2.4 (FR-04) | `"no enabled department available; content-creator is <state>"` — บันทึกใน task ที่ failed นั้น |

- `route_reason` เป็น **string บังคับ non-empty (≤500 ตัวอักษร)** ทุก task ที่สร้างจาก `POST /chat` — ไม่มีข้อยกเว้น
- การเลือกแผนกด้วย LLM หลายแผนก = **Phase 5** (out-of-scope §4) — Phase 2 ห้ามอ้าง "CEO ฉลาดเลือก" เป็นเกณฑ์ผ่าน
- Tool ที่ invoke: tool แรกของ Content MCP ที่ประกาศใน registry `capabilities` (Content กำหนดชื่อใน §5 handoff) — Product ไม่ล็อกชื่อ tool ตรงนี้ ให้ Content ส่งชื่อมาก่อน Engineering ลงมือ

### 2.3 Task envelope ใหม่ (FR-05 — แทน result_ref ตัวเดียว)

**Envelope v2 (writer ต้องเขียนครบ, reader ต้องอ่านได้):**

```jsonc
{
  "task_id": "task-<12hex>",
  "dept": "content",
  "module": "content-creator",
  "task_type": "content",
  "status": "pending|running|completed|failed|cancelled",
  "brief": "...",                       // มีตอน create; list_tasks ซ่อนตามเดิม
  "route_reason": "Phase2 single-candidate route: ...",  // ➕ บังคับ non-empty ทุก task จาก POST /chat
  "artifact_refs": ["content/..."],     // ➕ list แหล่งจริง — completed ต้อง non-empty
  "result_ref": "content/...|null",     // legacy mirror: เท่ากับ artifact_refs[0] หรือ null (คงไว้อ่านย้อนหลังเท่านั้น)
  "error": {"code": "MODULE_DISABLED", "message": "...", "hint": "..."} | null,  // ➕ struct (§2.4)
  "error_detail": "...|null",           // legacy mirror: เท่ากับ error.message หรือ null
  "app_version": "0.1.0",               // ➕ จาก solocorp_app.APP_VERSION ตอน create
  "created_at": "ISO8601", "started_at": "ISO8601|null", "completed_at": "ISO8601|null"
}
```

**กฎล็อก:**

1. `artifact_refs` เป็นแหล่งจริง (tasks.html อ่านตัวนี้ก่อนอยู่แล้ว) — `completed` ต้องมี ≥1 entry, `failed` ต้องมี `error` non-null
2. `result_ref` / `error_detail` เก่าเป็น **mirror อ่านย้อนหลังเท่านั้น** — writer เติมให้ตรง (`result_ref = artifact_refs[0]`, `error_detail = error.message`) ห้ามเขียนให้ขัดกัน
3. `error` เป็น struct เสมอ — ห้ามเขียน string เปลือยลง `error_detail` โดยไม่มี `error.code+hint`
4. terminal (`completed`/`failed`/`cancelled`) ต้องมี `completed_at` — POST /chat ห้าม return ขณะยัง `pending`/`running`
5. `app_version` ผูกตอน create — ห้ามย้อนแก้ของ task เก่า

**Migration จาก `result_ref` เก่า (ไม่ rewrite ประวัติ):**

| ของเก่า | พฤติกรรมที่สเปกบังคับ |
|:--------|:----------------------|
| task JSON มีแค่ `result_ref` ไม่มี `artifact_refs` | reader ต้อง normalize ตอนอ่าน: `artifact_refs = [result_ref]` ถ้า non-null ไม่งั้น `[]` — task เก่าต้องโชว์ใน tasks.html ได้โดยไม่แก้ไฟล์ |
| task JSON มีแค่ `error_detail` string ไม่มี `error` | reader normalize: `error = {"code":"UNKNOWN","message":error_detail,"hint":"ดู task นี้ใน tasks.html แล้วรัน brief ใหม่อีกครั้ง"}` |
| task ใหม่ที่ writer สร้าง | เขียนครบทั้ง v2 + mirror เก่า (§2.3 ข้อ 2) — ตรวจ DoD ข้อ 3 จับได้ถ้าขาดฟิลด์ใดฟิลด์หนึ่ง |
| ห้าม | backfill เขียนทับไฟล์ task เก่าทั้งกอง, เปลี่ยน `task_id`/timestamp เก่า, ลบ `brief` เก่าทิ้ง |

### 2.4 FR-04: disabled → `failed` + hint (ห้าม route เงียบ — ล็อก vocabulary)

เมื่อ content-creator ใช้ไม่ได้ (disabled / observation error / connect ล้ม / tool โยน `ModuleHostError`) ต้องสร้าง task `failed` ใบเดียวจบ แล้วตอบแบบเดียวกับวงจรปกติ (303/200 + envelope) — **ห้าม 500, ห้าม route ไปแผนกอื่นเงียบๆ, ห้ามไม่สร้าง task**

**`error.code` vocabulary (มีแค่นี้ใน Phase 2):**

| code | เมื่อไหร่ | message template | hint template (ต้องชี้วิธีเปิด) |
|:-----|:----------|:-----------------|:--------------------------------|
| `MODULE_DISABLED` | registry intent = disabled | `"content-creator is disabled"` | `"ไปที่ Modules → Enable content-creator แล้วส่ง brief ใหม่อีกครั้ง"` |
| `MODULE_DISCONNECTED` | enabled แต่ host ไม่มี connection / health ไม่ใช่ connected | `"content-creator is not connected (<observation>)"` | `"ไปที่ Modules → กด Check ที่ content-creator; ถ้ายัง error ดู last_error ในหน้า Modules"` |
| `MODULE_ERROR` | connect/probe ล้ม (state error) | `"content-creator unavailable: <last_error ≤120 ตัวอักษร>"` | `"ดู last_error ในหน้า Modules แล้วกด Check อีกครั้ง; ถ้ายังล้มให้เก็บ log มาส่ง feedback"` |
| `TOOL_FAILED` | call_tool โยน error หลังต่อติด | `"content tool failed: <detail ≤120 ตัวอักษร>"` | `"ลอง brief ใหม่อีกครั้ง; ถ้ายังล้มให้ย่อ brief ให้สั้นลงแล้วส่งใหม่"` |
| `BRIEF_INVALID` | brief ว่าง/เกิน 2000 | `"brief must be 1-2000 characters"` | `"พิมพ์ brief 1–2000 ตัวอักษรแล้วส่งใหม่"` (เคสนี้ 400 + **ไม่สร้าง task**) |
| `INTERNAL` | อื่นๆ ที่ไม่ใช่ข้างบน | `"internal error: <ExcName>"` (ห้ามใส่ secret/path) | `"ลองใหม่; ถ้ายังล้มให้บันทึกเวลา + task_id (ถ้ามี) ส่ง feedback"` |

- `message` ≤200 ตัวอักษร, `hint` ต้องมีทุก `failed` (ว่างไม่ได้)
- `UNKNOWN` อนุญาตเฉพาะ normalize งานเก่า (§2.3) — task ใหม่ห้ามใช้

### 2.5 สิ่งที่ Phase 2 ไม่เปลี่ยน (ล็อกกัน scope creep)

- Status vocabulary 3 ชั้นเท่า design note §5.3 (module `enabled/disabled/connecting/connected/error`, task 5 สถานะ, provider 3 สถานะ) — ไม่เพิ่มคำใหม่
- `POST /chat` ไม่แตะ provider/settings logic — provider `unconfigured`/`failed` ให้ Tool แปลงเป็น `failed` ด้วย code `INTERNAL` + hint ชี้ไป `/settings` (ไม่เพิ่ม code ใหม่ใน Phase 2)
- CSRF + loopback boundary คงเดิม — `POST /chat` อยู่ใต้ `writes` + `require_csrf` อยู่แล้ว

## 3. DoD Phase 2 (6 ข้อ — ไม่ผ่านข้อเดียว = ไม่ Go)

| # | ข้อ | วิธีตรวจ (ล็อกคำสั่ง/เกณฑ์) | ผ่านเมื่อ |
|:-:|:----|:---------------------------|:---------|
| 1 | Brief จบวงจร 1 ครั้ง (D7) | เปิด content-creator ให้ connected แล้ว `curl -X POST /chat` พร้อม CSRF + brief จริง 1 ครั้ง → ตาม `task_id` ที่ตอบกลับ | task ใบนั้น `status=completed` + `completed_at` มี + `artifact_refs` non-empty + เปิดดู artifact ได้จริง (ไม่ใช่แค่ชื่อ) |
| 2 | Disable → failed + hint (FR-04) | disable content-creator แล้ว `POST /chat` ซ้ำ brief เดิม | ได้ task ใหม่ `status=failed` + `error.code=MODULE_DISABLED` + `hint` มีคำว่า Modules/Enable + **ไม่มี** task ใดถูก route ไป module อื่น + HTTP ไม่ใช่ 500 |
| 3 | Envelope v2 ครบ + mirror ตรง | `GET` ไฟล์ task JSON จากข้อ 1–2 แล้ว assert schema | มีครบ `route_reason` non-empty + `artifact_refs` list + `app_version` ตรง `APP_VERSION` + `error` struct (failed) + `result_ref==artifact_refs[0]` + `error_detail==error.message` |
| 4 | งานเก่าไม่หาย (migration) | เก็บ task JSON เก่า (มีแค่ `result_ref`/`error_detail`) ไว้ 1 ใบ แล้วเปิด `/tasks` + `runtime.tasks()` | งานเก่าโชว์ artifact ได้ (normalize) + ไฟล์เก่าบนดิสก์ไม่ถูก rewrite (mtime/hash ไม่เปลี่ยน) |
| 5 | ไม่ค้าง pending/running | หลังข้อ 1–2 รัน `runtime.tasks()` / เปิด `/tasks` | ทุก task ที่ `POST /chat` สร้างมี `completed_at` + ไม่มีใบใดค้าง `pending`/`running` เกิน 70s หลัง POST return (timeout 60s + margin 10s) |
| 6 | Secret guard + scope ไม่บวม | `grep -riE 'sk-|api_key.{0,20}[A-Za-z0-9]{16}'` ใน diff/log/artifact + `git diff --stat` เทียบ base | ไม่พบ secret หลุด + diff ไม่มีไฟล์ standalone/packaging (`axis_mcp/departments/content_mcp` split), ไม่มีไฟล์ Concat/media pipeline, ไม่มีไฟล์ billing/subscription |

## 4. Out-of-scope (ห้ามลากเข้า Phase 2)

1. **Standalone / packaging / deploy** — ไม่พิสูจน์ external client ใน Phase 2 (นั่นคือ Phase 3 gate)
2. **Concat render / media pipeline** — ห้ามอ้างเป็นหลักฐานหรือเงื่อนไขผ่าน Phase 2
3. **Billing / subscription / marketplace / hosted multi-user** — งาน Phase 6 ตาม PRD
4. **LLM multi-department routing** — Phase 2 route ตัวเดียวตาม §2.2; การเลือกหลายแผนกด้วย model คือ Phase 5
5. **Background worker pool / autonomous agent team** — D7 ล็อกแล้ว: sync orchestration เท่านั้น
6. **Feedback flow (FR-08)** — งาน Phase 4 Closed Beta ไม่ใช่ dependency ของ gate นี้
7. ห้ามเปลี่ยน shape `/live`, `/api/live/status`, `/modules`, `/settings`, `/healthz` เพื่อ Phase 2 — ถ้าต้องแตะให้กลับมาแก้ spec นี้ก่อน

## 5. Handoff กลับ CEO: เจ้าของงานแต่ละชิ้น

- **→ CEO:** ขอ Go Phase 2 ตาม contract นี้ (POST /chat วงจรเดียว + envelope v2 + DoD 6 ข้อ); ถ้าไม่เห็นด้วยกับข้อใดข้อหนึ่ง ส่งกลับ Product ก่อนสั่ง Architect/Engineering ลงมือ — Product งานจบที่ spec นี้ **ไม่เขียนโค้ด ไม่แก้ test เอง ไม่ commit**
- **→ Architect (@songsak):** ออกแบบ route resolve + terminal guarantee + timeout 60s + error-code mapping (§2.1–2.4) ให้อยู่ใน D7 synchronous ไม่ใช่ worker; ถ้าจำเป็นออก ADR เสริมเรื่อง normalize-on-read (§2.3)
- **→ Content (@content-creator-sek):** ส่งชื่อ tool + args mapping ที่ `POST /chat` ต้องเรียก (registry `capabilities` ตัวแรกคืออะไร, brief → arguments แปลงอย่างไร, artifact ที่คืนมามี path แบบไหนให้ใส่ `artifact_refs`)
- **→ Engineering (@changful):** ทำ `POST /chat` (writes+CSRF), `TaskTracker` extend (v2 + mirror + normalize-on-read), ผูก `runtime.call_tool` เข้าวงจร record-before-invoke → terminal; ห้ามแตะไฟล์ scope §4
- **→ QA:** เขียน test ใหม่สำหรับ DoD ข้อ 1–5 (E2E brief จริง, disabled→failed, schema assert, legacy fixture, no-pending-leak) + หลักฐานเก็บ `bus/evidence/` ตาม SOP-06; เกณฑ์เขียว = รันชุด CI เดิม (`pytest tests/ central_bus/tests/ --tb=short ... -q`) ไม่ cherry-pick
