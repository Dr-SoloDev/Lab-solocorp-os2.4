# Design Note: SoloCorp App — Local Runtime Architecture (Phase 0 Deliverable)

| Field | Value |
|:--|:--|
| Status | Phase 0 baseline closed; Phase 1 implementation in progress |
| Date | 2026-11-02 |
| Author | Software Architect (Buffy) |
| Reviewers | Engineering |
| Parent | [`PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md`](../prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md) |
| Related | ADR-030 (Content MCP open-core split) · ADR-029 (doc authority rank) · [`CONTENT-MCP-STRATEGY-v1.0.md`](CONTENT-MCP-STRATEGY-v1.0.md) |

> หลักการของเอกสารนี้ (ตาม rules ของสถาปนิก): **ทุกการตัดสินใจมีชื่อและ trade-off** —
> ไม่มี architecture astronautics, ของที่มีอยู่แล้วในโค้ดคือข้อเท็จจริง, สิ่งที่กลับได้ง่ายชนะสิ่งที่ "เหมาะสมที่สุด"

---

## 1. บริบทและข้อเท็จจริงจากโค้ดจริง (verified 2026-11-02)

PRD ระบุว่า *"first-party SoloCorp App/runtime and module registry are NOT implemented"* — **ถูกเฉพาะส่วน UI/app shell** แต่ inspection โค้ดพบว่า **substrate หลายชิ้นมีอยู่แล้วและดี:**

| ชิ้นส่วน | สถานะจริง | หลักฐาน |
|:--|:--|:--|
| Module registry (config/state split) | ✅ มี ใช้การได้ | `solocorp_mcp/module_registry.py` — config อยู่ `config/module-registry.json` (git), state อยู่ `central_bus/module-registry.state.json` (ไม่ track) — แยก lifetime ถูกต้องแล้ว |
| Task tracker (task envelope) | ✅ มี ครบ lifecycle | `solocorp_mcp/task_tracking.py` — `pending → running → completed/failed/cancelled`, guard path traversal, ซ่อน `brief` จาก list |
| Stdio MCP client | ✅ มี | `solocorp_mcp/departments/mcp_stdio.py` — JSON-RPC newline, initialize handshake, 182 บรรทัด |
| Artifact store | ✅ มี | `solocorp_mcp/bus_store.py` — submit/fetch/list ต่อ department |
| Central Bus daemon | ✅ มี (pre-release) | `central_bus/` — FastAPI :8099, queue SQLite+JSONL |
| **Web UI / app shell** | ❌ ไม่มี | — |
| **MCP host (connection manager หลายตัวพร้อมกัน)** | ✅ มี lifecycle/health polling ขั้นต้น | solocorp_mcp/module_host.py — persistent stdio process, connect/disconnect/health/call |
| **Model/provider adapter ของ app** | ❌ ไม่มี | provider call กระจายใน content_service ไม่ใช่ adapter ของ app |
| **CEO chat loop ใน app** | ❌ ไม่มี | — |

**ข้อสรุปเชิงสถาปัตยกรรม:** งาน Phase 1–2 ไม่ใช่ "สร้างระบบใหม่" แต่คือ **สร้างเปลือก (shell) + host ที่ประกอบชิ้นเดิมเข้าด้วยกัน** — ความเสี่ยงหลักจึงเป็นเรื่อง integration ไม่ใช่ invention

---

## 2. Goals / Non-Goals

**Goals (ตรง PRD §7 Must Have):**
- G1: app ผู้ใช้คนเดียว local — CEO chat, module screen, task history, provider settings
- G2: host จัดการ connect/disconnect/health ของ MCP modules
- G3: เส้นทาง task ครบวงจร: brief → route → record → invoke → terminal + artifacts
- G4: standalone ของ department ไม่ถูกทำลาย (แยก repo ตาม ADR-030 ได้โดยไม่ต้องแก้ app)

**Non-Goals (ตรง PRD §7 Out of Scope):** hosted/multi-user, billing, dynamic plugin install, worker pool, แผนกครบทั้ง 18, แทนที่ Central Bus

---

## 3. ภาพรวมสถาปัตยกรรม

```
┌──────────────── Browser (loopback only) ────────────────┐
│  Web UI: CEO Chat · Modules · Task History · Settings   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (127.0.0.1)
┌──────────────────────▼──────────────────────────────────┐
│              SoloCorp App Runtime (1 process)           │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────┐  │
│  │ App API     │ │ CEO Agent    │ │ Module Host       │  │
│  │ (FastAPI)   │ │ Loop         │ │ (connection mgr)  │  │
│  └─────────────┘ └──────┬───────┘ └─────────┬─────────┘  │
│  ┌──────────────────────▼───────────────────▼─────────┐  │
│  │  Registry (config+state) · TaskTracker · BusStore  │  │
│  └──────────────────────┬─────────────────────────────┘  │
│  ┌──────────────────────▼─────────────────────────────┐  │
│  │  Model Adapter (user-configured provider, no       │  │
│  │  silent fallback)  ← provider creds: local config  │  │
│  └────────────────────────────────────────────────────┘  │
└──────────┬──────────────────┬──────────────────┬─────────┘
           │ stdio           │ stdio            │ (optional)
   ┌───────▼──────┐  ┌────────▼───────┐  ┌───────▼────────┐
   │ Content MCP  │  │ Core MCP       │  │ busd :8099     │
   │ (แผนกอื่นๆ)   │  │ (org/routing)  │  │ (ไม่บังคับ MVP)│
   └──────────────┘  └────────────────┘  └────────────────┘
```

**หลักการ compose:** App runtime เป็นผู้เริ่มและเป็นเจ้าของ connection ทั้งหมด (PRD §5 host-owned connections) — modules ไม่รู้จักกันและกัน ไม่รู้จัก app

---

## 4. การตัดสินใจเชิงสถาปัตยกรรม (D1–D7)

### D1: รูปทรง runtime — **Single local process** (แนะนำ)

| ตัวเลือก | ได้ | เสีย |
|:--|:--|:--|
| **(ก) process เดียว: FastAPI serve UI + app API + host ในตัว** ✅ | deploy = รันคำสั่งเดียว; state ใน memory เดียวกัน (ไม่ต้อง IPC); ตรงคำว่า "local app" ที่สุด | process เดียว = crash ครั้งเดียวตายหมด |
| (ข) daemon + static SPA แยก | scale ทีหลังง่าย | ต้องมี IPC/API contract ตั้งแต่วันแรก — ความซับซ้อนที่ MVP ยังไม่ต้องจ่าย |

**ตัดสินใจ: (ก)** — reversibility สูง (แยกทีหลังได้เสมอ) และ MVP เป็น single-user local ไม่มีอะไรต้อง scale แยก
**เพิ่มเติม:** host health polling + explicit reconnect path ช่วยให้ตรวจพบ module ที่ล้มและเชื่อมใหม่ได้โดยไม่ซ่อนการเปลี่ยนสถานะ

### D2: MCP host — **Adapter เหนือ client ที่มีอยู่** (ไม่ใช้ SDK ใหม่ตอนนี้)

| ตัวเลือก | ได้ | เสีย |
|:--|:--|:--|
| **(ก) `ModuleHost` ห่อ `MCPStdioClient` เดิม หลัง interface เดียว** ✅ | ไม่เพิ่ม dependency; client จริงผ่าน handshake มาแล้วในการ pilot | protocol coverage จำกัดเท่าที่มี (initialize/call) — ถ้าต้องการ full MCP spec ต้องขยายเอง |
| (ข) ย้ายไป official MCP Python SDK | spec compliance เต็ม, maintenance ให้ upstream | dependency ใหม่ + เขียน adapter ใหม่ + pilot ต้อง regression ทั้งหมด |

**ตัดสินใจ: (ก) ชั่วคราว + บันทึก exit condition:** เมื่อต้องการ capability ที่ client เดิมไม่มี (elicitation — ซึ่ง A2 ต้องการพอดี, streaming, OAuth) → กลับมาประเมิน (ข) **ทันที** นี่คือ ADR ที่ทบทวนได้ ไม่ใช่การล็อกถาวร
**Interface บังคับ:** `connect(module_id) / disconnect / health / call_tool(module_id, tool, args)` — ทุกอย่างนอก host เห็นแค่ interface นี้ (กันผูกกับ implementation)

### D3: Registry — **ใช้ของเดิม + extend schema ตาม PRD**

ของเดิมดีอยู่แล้ว (split config/state ถูกหลัก) สิ่งที่ต้องเพิ่มให้ครบ PRD FR-01/FR-03:

| Field | สถานะ | หมายเหตุ |
|:--|:--|:--|
| `id`, `transport`, `command`, `description`, `status` | มีแล้ว | คงเดิม |
| `version` | ➕ เพิ่ม | ต้องรู้ version ก่อนอ้างใน task record |
| `capabilities` | ➕ เพิ่ม | declared tools/resources — ให้ UI แสดง + CEO เลือก route |
| `dependencies` | ➕ เพิ่ม | เช่น "busd" / "ไม่มี" — ใช้ตอบ FR-04 |
| `permissions` | ➕ เพิ่ม | scope ที่ module ขอ (สอดคล้อง `SOLOCORP_API_KEY` scope ที่มีอยู่) |
| `entry_repo` | ➕ เพิ่ม | path/remote ของ repo โมดูล — **รองรับ ADR-030 split โดยไม่ต้องแก้ schema ใหม่** |

State file เดิม covers `connecting/connected/error` + `last_error` + `response_time_ms` อยู่แล้ว → FR-02 ได้เกือบทั้งหมด

### D4: Task store — **คง `TaskTracker` เป็น contract หลัก MVP**

| ตัวเลือก | ได้ เสีย |
|:--|:--|
| **(ก) TaskTracker (JSON ต่อ task ใต้ `central_bus/content/tasks/`)** ✅ | ✅ มีแล้ว, envelope ครบ (task_id/status/timestamps/result_ref/error_detail), เขียนอ่านง่าย, restart ไม่หาย (PRD NFR) ❌ ไม่มี transaction/queue semantics พร้อมกันหลาย writer |
| (ข) ย้ายเข้า busd queue (SQLite/JSONL) | ✅ queue, retry, dead-letter ❌ PRD สั่งเอง: *"replacing Central Bus before evaluating"* = out of scope; เพิ่ม daemon เป็น dependency ของ task พื้นฐาน |
| (ค) DB ใหม่ (SQLAlchemy/Postgres) | ✅ กรอง/aggregate ❌ ของใหม่หมด, local-first ไม่ต้องการ |

**ตัดสินใจ: (ก)** — ตอบ **FR-05** (task tracking: task_id/dept/status/timestamps/result/error มีครบใน envelope เดิม) + **การประเมิน (ข) เลื่อนไปหลัง Beta** เมื่อมี usage จริงว่าต้องการ queue semantics (cancel/retry ที่เป็น more than status flip)
**สิ่งที่ต้องเพิ่มเล็กน้อยใน envelope:** `artifact_refs` (list แทน result_ref ตัวเดียว — งาน content สร้างหลายไฟล์) และ `app_version` เพื่อ audit

### D5: Model adapter — **explicit config, no fallback (ตาม PRD)**

- ที่เก็บ: `config/provider.json` (tracked ถ้าไม่มี secret) + **credential ใน env/local file ที่ไม่ track** — ห้ามอยู่ใน task artifact (PRD NFR)
- ฟอร์แมต: `{provider, base_url?, model, api_key_ref}` — `api_key_ref` ชี้ชื่อ env var ไม่ใช่ค่าจริง
- **no silent fallback:** provider ล้ม → task `failed` + `error_detail` ชัดเจน — ห้ามเด้ง model เองโดยไม่บอกผู้ใช้
- adapter เป็น interface เดียวที่ CEO loop เรียก — content MCP ที่เรียก provider เอง (ElevenLabs ฯลฯ) คงอยู่ฝั่ง module ไม่ปน

### D6: Boundary กับ Content MCP ที่จะแยก (ADR-030)

- App **รู้จัก module ผ่าน registry เท่านั้น** — ไม่ import โค้ด module ตรงๆ (หลักการ module boundary อยู่แล้ว)
- เมื่อแยก repo: เปลี่ยนแค่ `command`/`entry_repo` ใน registry config → **app ไม่แก้บรรทัดเดียว**
- Core MCP (org/routing) เป็น optional module เช่นกัน — standalone dept ไม่ต้องพึ่ง (FR-07 สอดคล้อง)

### D7: CEO loop ใน MVP — **synchronous orchestration ไม่ใช่ autonomous agent**

ตรง PRD "MVP Execution Boundary" ชัดเจน:

```
user brief → CEO (model adapter) ตัดสินใจ route (tool call เท่านั้น)
  → TaskTracker.create(dept, module, brief)          # record ก่อน invoke
  → ModuleHost.call_tool(...)                         # sync
  → terminal status + artifact_refs หรือ error        # ไม่มี intermediate "สำเร็จเทียม"
```

- **ไม่มี** background worker, ไม่มี LLM session ของแผนกใน MVP
- CEO เรียก tool ของ department ที่เปิดอยู่ **ใน chat session เดียวกัน** ไม่ต้องเปิดแชทที่สอง → **FR-06**
- Module ไม่พร้อม → หยุดที่ record + `failed` + ข้อความบอก module ไหนขาด + วิธีเปิด (FR-04) — **ห้าม route ไปแผนกอื่นเงียบๆ** (PRD §6.2)

---

## 5. Contract ที่ปิดสำหรับ Phase 0

### 5.1 Module manifest (extend จากของเดิม)

```jsonc
{
  "content-creator": {
    "status": "enabled",              // enabled | disabled (config)
    "transport": "stdio",
    "command": [".venv/bin/python3", "-m", "solocorp_mcp.departments.content_mcp"],
    "entry_repo": "internal",         // internal | <path> | <url> — ADR-030 split ready
    "version": "0.3.0",               // ➕
    "capabilities": ["tools", "resources"],   // ➕ declared
    "dependencies": [],               // ➕ ["busd"] ถ้ามี — ใช้ตอบ FR-04
    "permissions": ["team"],          // ➕ scope ที่ขอ
    "description": "Content Creator Department"
  }
}
// state (separate file): connecting|connected|error + last_checked + response_time_ms + last_error
```

### 5.2 Task envelope (extend จาก `task_tracking.py`)

```jsonc
{
  "task_id": "task-<12hex>",
  "dept": "content", "module": "content-creator", "task_type": "content",
  "status": "pending|running|completed|failed|cancelled",
  "brief": "...",                       // เขียนตอน create; list ไม่ return (มีอยู่แล้ว)
  "route_reason": "user asked for video script",   // ➕ FR-03: CEO บอกเหตุผลที่เลือกแผนก
  "artifact_refs": ["content/..."],     // ➕ list — แทน result_ref ตัวเดียว (เก่าคงไว้อ่านย้อนหลัง)
  "error_detail": null,                 // struct: {code, message, hint} — ➕ hint = วิธีแก้ (FR-04)
  "app_version": "0.1.0",               // ➕
  "created_at|started_at|completed_at": "ISO8601"
}
```

### 5.3 Status model (หน้าเดียว ห้ามมีชุดคำที่สอง)

| ชั้น | ค่า | ที่อยู่ |
|:--|:--|:--|
| Module | `enabled/disabled` (intent) · `connecting/connected/error` (observation) | registry config / state |
| Task | `pending/running/completed/failed/cancelled` | task envelope |
| Provider | `configured/unconfigured/failed` | provider config |

---

## 6. แผนประกอบร่าง (Phase 1 → 2 build order)

| # | ชิ้น | อาศัย | Exit gate (PRD) |
|:-:|:--|:--|:--|
| 1 | ModuleHost (D2 interface) + health polling entrypoint | MCPStdioClient เดิม | connect/disconnect/health ผ่าน live MCP stdio smoke test |
| 2 | Registry schema extension (D3) + validator | `module_registry.py` เดิม | manifest ใหม่ validate + state ไม่玷เมนต์ tracked file |
| 3 | Provider settings + adapter (D5) | — | configure model ครั้งเดียว + error ชัดเมื่อ fail |
| 4 | App API (FastAPI) + Web UI 4 หน้า (D1) | 1–3 | **Phase 1 gate:** config model + เปิด/ปิด content module ได้ |
| 5 | CEO loop + task path (D7, D4 extend) | 1–4 | **Phase 2 gate:** brief จบวงจร 1 ครั้ง; disable module → unavailable ชัด |
| 6 | Standalone proof (repo split ตาม ADR-030) | 4–5 นิ่งแล้ว | **Phase 3 gate:** external client ใช้ content MCP โดยไม่มี Core |

**ความเสี่ยงหลัก + mitigation:**

| Risk | Likelihood | Impact | Mitigation |
|:--|:-:|:-:|:--|
| CEO route แม่นไม่พอ (model เลือกแผนกผิด) | สูง | สูง | route เป็น tool call ที่บันทึก `route_reason` — ตรวจจาก task record ได้; fallback = ผู้ใช้ @mention แผนกตรง |
| stdio client ขาด protocol capability (elicitation/A2) | กลาง | กลาง | D2 มี exit condition ย้าย SDK — ประเมินตอนทำ A2 |
| เอกสารเก่า (PROJECT.md) ขัดกับของจริง | สูง | กลาง | เช่นเดิม: PRD = truth — งานด้านเอกสารค้างอยู่ (banner legacy) |
| busd ไม่เริ่ม → feature บางตัวพัง | กลาง | ต่ำ | MVP task path ไม่พึ่ง busd (D4) — busd เป็น optional module |

---

## 7. Defaults ที่ใช้เริ่ม Phase 1

- **UI:** ใช้ FastAPI กับ server-rendered Jinja templates; ไม่เพิ่ม SPA framework ใน MVP
- **Local binding:** bind เฉพาะ 127.0.0.1, default port 8766, override ผ่าน environment; ถ้าพอร์ตถูกใช้ให้ startup ล้มพร้อม error ชัดเจน ไม่สุ่มพอร์ตเงียบ ๆ
- **Browser request boundary:** ตรวจ Host และ same-origin สำหรับ mutation พร้อม CSRF token; MVP single-user ไม่มี account login
- **Feedback (FR-08):** ทำให้ครบก่อน Closed Beta ใน Phase 4 ตาม PRD; ไม่ดึงเข้ามาเป็น dependency ของ Phase 1–2
- **Artifacts:** artifact_refs เป็น list ของ reference ที่สัมพันธ์กับ Bus; campaign bundle เก็บหลาย reference ได้ และคง result_ref ไว้เพื่ออ่าน task เก่า

ค่าเหล่านี้เป็น implementation defaults ที่ย้อนกลับได้และไม่ขยาย MVP scope; ยังไม่ใช่การอ้างว่า Owner อนุมัติรายละเอียดเหล่านี้แยกเป็น L5 decisions

---

## 8. สิ่งที่เอกสารนี้ปิด (Phase 0 exit gate)

- [x] Module manifest contract — §5.1
- [x] Task envelope contract — §5.2 + status model §5.3
- [x] Local runtime design — §3 + D1–D7
- [x] MVP boundaries สอด PRD §7 (non-goals §2)
- [x] Traceability: FR-01→08 อ้างครบใน D1–D7 (FR-01/02=D3, FR-03/04=D7+§5.2, FR-05=D4, FR-06=D7, FR-07=D6, FR-08=Phase 4 Closed Beta)
- [x] Reversible implementation defaults for Phase 1 are recorded in §7

---

## 9. สถานะการทำงาน

- Phase 0: ปิดแล้ว — architecture, contracts และลำดับงานสอดคล้องกับ PRD
- Phase 1: กำลังทำ — ModuleHost รองรับ connect/disconnect/health polling/call tool และบันทึก runtime state แยกจาก config
- ยังไม่ผ่าน Phase 1 gate: App API, provider settings, UI และการเปิด/ปิด Content module จากหน้าจอยังไม่ครบ
- health_all() เป็น polling entrypoint; การตั้งรอบ background จะผูกกับ FastAPI lifespan เมื่อสร้าง app runtime

---

## References

- PRD §5 (target architecture) · §6 (usage modes) · §7 (MVP scope) · §9 (NFR) · §11 (phases)
- Code facts: `solocorp_mcp/module_registry.py` · `task_tracking.py` · `departments/mcp_stdio.py` · `bus_store.py` · `config/module-registry.json`
- ADR-030 (accepted open-core boundary — entry_repo รองรับการ split ที่ Phase 3) · ADR-029 (rank: ADR ใหม่ > SOP > rules)
