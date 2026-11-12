# CEO Loop Sync — Phase 2 Design (D7)

| Field | Value |
|:--|:--|
| Status | Design only — **ห้าม implement** จนกว่า CEO จะสั่ง Go |
| Date | 2026-11-13 |
| Author | @architect-songsak (AXIS Architect) |
| Parent | `docs/plans/SOLOCORP-APP-LOCAL-RUNTIME-DESIGN-v0.1.md` D7 + §5.2 |
| Scope | `solocorp_app/runtime.py` · `axis_mcp/module_host.py` (271) · `axis_mcp/task_tracking.py` (153) · `solocorp_app/app.py` chat routes · `solocorp_app/templates/chat.html` |
| Safety | read-only + เขียนไฟล์ใหม่เท่านั้น — ไม่ commit/push, ไม่แตะ branch |

> หลักการ: **sync เท่านั้น, record ก่อน invoke, failed ชัดเจน, ไม่ลามไป Concat/MCP**

---

## 1. สิ่งที่อ่านแล้ว (ground truth + file:line)

| ชิ้น | สถานะจริง |
|:--|:--|
| `solocorp_app/runtime.py:190-198` `call_tool()` เป็น passthrough ไป `host.call_tool` — คอมเมนต์บอกเองว่า "kept on the same interface" สำหรับ Phase 2 loop, **ยังไม่มี `run_ceo_turn` / router / timeout budget** | ยังไม่มี loop |
| `solocorp_app/runtime.py:225-258` `tasks()` / `tasks_summary()` อ่าน `TaskTracker` อย่างเดียว, fail-open (`except OSError → []`, cap 200) — **single source of truth ฝั่ง task ถูกต้องแล้ว ห้ามเปลี่ยน** | ห้ามแตะพฤติกรรม |
| `axis_mcp/module_host.py:235-262` `call_tool(module_id, tool, args, timeout=60.0)` — auto-`connect()` ถ้ายังไม่ connected, `disabled → disconnect + raise ModuleHostError`, `MCPStdioError → ModuleHostError` | จุดคุม timeout หลัก |
| `axis_mcp/module_host.py:54-134` `connect()` — `disabled → raise`, `transport != stdio → raise`, `command` ว่าง → record `error` + return dict (ไม่ raise), success → record `connected` + `response_time_ms` | สัญญา connect ครบแล้ว |
| `axis_mcp/module_host.py:206-226` `health()` / `health_all()` — probe เฉพาะ connection ที่มีอยู่, disabled → disconnect | poller ปลอดภัยแล้ว |
| `axis_mcp/module_host.py:26-30` `startup_timeout=15.0, request_timeout=5.0` ; `axis_mcp/departments/mcp_stdio.py:88` `request(timeout=30)` ; `mcp_stdio.py:132` `call_tool(timeout=60)` | ค่า timeout ปัจจุบัน (ดู §3 ว่าทำไมไม่พอ) |
| `axis_mcp/departments/mcp_stdio.py:106-118` `request()` วน `while True` + `continue` เมื่อ `id` ไม่ตรง — **timeout รีเซ็ตทุกครั้งที่ได้บรรทัดผิด id → รอได้ไม่จำกัดถ้า module พ่น interleaved output** (จุดเสี่ยง Concat ค้าง 30 นาที) | ต้องแก้ด้วย budget รวม (§3) |
| `axis_mcp/departments/mcp_stdio.py:162-176` `close()` มี `wait 5s → terminate → wait 5s → kill` แล้ว — **ของดีที่มีอยู่, loop ต้องเรียกใช้ผ่าน `disconnect` เมื่อ timeout** | reuse ห้ามเขียน killer ใหม่ |
| `axis_mcp/task_tracking.py:55-80` `create(dept, module, brief, task_type)` — envelope มี `task_id/dept/module/task_type/status/brief/created_at/started_at/completed_at/result_ref/error_detail` **ยังไม่มี `route_reason / artifact_refs / app_version`** | F1 ต้องเพิ่มแบบ additive |
| `axis_mcp/task_tracking.py:119-148` `update_status(status, result_ref, error_detail)` — รับเฉพาะ 2 ฟิลด์, `status` ล็อกใน `VALID_STATUSES` (`task_tracking.py:30`) | F1 ต้องขยายโดยไม่หักของเดิม |
| `axis_mcp/task_tracking.py:94-117` `list_tasks(include_brief=False)` ตัด `brief` ออกเป็น default; `task_tracking.py:43-50` guard `task-<12hex>` กัน path traversal | สัญญา security ที่ต้องคงไว้ |
| `solocorp_app/app.py:259-271` `GET /chat` render `chat.html` อย่างเดียว (read-only) ; `solocorp_app/app.py:249-251` แยก `reads` / `writes(CSRF)` router | POST ต้องอยู่ฝั่ง `writes` (§5) |
| `solocorp_app/templates/chat.html:16-17` ข้อความ "Not wired yet" — placeholder ชัดเจน | F5 แทนที่ตรงนี้ |
| `solocorp_app/templates/tasks.html:37-42` **อ่าน `artifact_refs` ก่อน `result_ref` อยู่แล้ว** — template รองรับ envelope ใหม่ล่วงหน้า, ไม่ต้องแก้เพื่อ compat | หลักฐานว่า migration แบบ additive ปลอดภัย |
| `solocorp_app/__init__.py:15` `APP_VERSION = "0.1.0"` ; `solocorp_app/app.py:512` `/healthz` คืน `app_version` แล้ว | แหล่งเดียวของ version |
| `solocorp_app/live.py:19` `ห้าม import content_service / Concat / DB ใด ๆ เข้าไฟล์นี้ (R2/R3)` — precedent ของ boundary ที่ Phase 2 ต้องลอก | R1/R2 ตั้งตามบรรทัดนี้ |
| `docs/plans/SOLOCORP-APP-LOCAL-RUNTIME-DESIGN-v0.1.md:142-156` D7 สัญญา sync: `brief → route → TaskTracker.create → ModuleHost.call_tool (sync) → terminal + artifact_refs` — ไม่มี worker, ไม่มี "สำเร็จเทียม", module ไม่พร้อม → `failed` + บอกวิธีเปิด ห้าม route เงียบ | สัญญาที่ design นี้ขยาย ไม่ใช่เปลี่ยน |

---

## 2. CEO loop — state machine (sync, D7)

### 2.1 ลำดับเดียว ไม่มีทางลัด

```
POST /chat (writes, CSRF)
  │ ① validate brief (ยาว/ว่าง/ชนิด)
  ├─► ② route (pure function, ไม่แตะ MCP) → (module_id, tool_name, args, route_reason)
  ├─► ③ TaskTracker.create → status=pending  (record ก่อน invoke เสมอ — D7)
  ├─► ④ TaskTracker.update_status(running)   (ประทับ started_at)
  ├─► ⑤ ModuleHost.call_tool(..., timeout=T)  (sync, มี budget รวม — §3)
  │     ├── ok   → ⑥a completed + artifact_refs (+ result_ref ตัวแรกเพื่อ compat)
  │     ├── fail → ⑥b failed + error_detail{code,message,hint}
  │     └── timeout/exit → ⑥b failed + disconnect module ทันที
  └─► ⑦ render chat.html (200 แม้ failed — failed คือข้อมูล, ไม่ใช่ 500)
```

* ไม่มี background thread / queue / retry อัตโนมัติใน Phase 2 — ตรง `SOLOCORP-APP-LOCAL-RUNTIME-DESIGN-v0.1.md:142-156`
* `cancelled` ไม่ใช่ terminal ของ loop นี้ — เก็บไว้ให้ operator/tool ในอนาคตเรียก `update_status("cancelled")` โดยตรง (สถานะมีอยู่แล้วใน `task_tracking.py:30`)
* ทุกก้าว ③–⑥ เขียนไฟล์ task เดิม (`task-<12hex>.json`) — ไม่สร้างไฟล์ที่สอง, ไม่เขียน bus queue

### 2.2 State table (ใครเปลี่ยน, เมื่อไร)

| จาก → ไป | ใครเรียก | เงื่อนไข |
|:--|:--|:--|
| — → `pending` | `runtime.run_ceo_turn` → `tracker.create(...)` | brief ผ่าน validate + route ได้ module (แม้ module disabled ก็ create ก่อน แล้วค่อย failed — เพื่อให้มีหลักฐาน) |
| `pending` → `running` | `tracker.update_status(task_id, "running")` | ก่อน `host.call_tool` 1 บรรทัดเสมอ (ประทับ `started_at` ตาม `task_tracking.py:136-137`) |
| `running` → `completed` | `tracker.update_status(..., "completed", artifact_refs=[...])` | `call_tool` คืนค่าโดยไม่ raise (รวม tool ที่คืน `isError=false`) |
| `running` → `failed` | `tracker.update_status(..., "failed", error_detail={...})` | raise ใด ๆ / timeout / disabled / tool `isError` / response ผิดรูป |
| ใด ๆ → `cancelled` | **loop นี้ห้ามเรียก** — อนาคต operator เท่านั้น | คงสถานะไว้ตาม `VALID_STATUSES` ห้ามลบ |

### 2.3 Router Phase 2 — deterministic ก่อน LLM

* Phase 2a (ที่ออกแบบรอบนี้): **keyword router ล้วน** — `route_brief(brief, modules_view) -> (module_id, tool, args, route_reason)` อยู่ในไฟล์ใหม่ `solocorp_app/ceo_loop.py` (pure, ไม่มี I/O)
  * อ่านเฉพาะ `runtime.modules()` (intent `enabled` + observation จาก `runtime.py:62-98`) — ไม่ import department ใด ๆ (R1)
  * กติกา: brief ว่าง/เกิน cap → ไม่ route (400 ตั้งแต่ §5); module ที่ match แต่ `enabled==False` → ยังเลือกตัวนั้นแล้วให้ loop ล้มเป็น `failed` พร้อม hint "ไปเปิดที่ /modules" (ห้าม reroute เงียบ — D7); ไม่มี match → default `content-creator` ถ้า enabled มิฉะนั้น failed `no_route`
  * `route_reason` เป็นประโยคสั้นที่มนุษย์อ่านได้ เช่น `"matched 'สคริปต์' → content-creator.create_campaign"` — เก็บลง task ทุกครั้ง (FR-03)
* Phase 2b (เลื่อน): LLM router ผ่าน `ProviderStore` — ยังไม่ออกแบบรอบนี้เพราะจะดึง `provider.status()` (`provider.py:308-336`), secret handling และ no-silent-fallback เข้ามา ให้เป็น design doc ฉบับถัดไปเมื่อมี usage ว่า keyword ไม่พอ (risk §7 แถว 1)

### 2.4 Error mapping (MCP → task → UI คำเดียว)

| ต้นทาง | จับที่ | `error_detail` (`{code,message,hint}`) | UI |
|:--|:--|:--|:--|
| brief ว่าง / ไม่ใช่ str / ยาวเกิน cap (เช่น 2000 ตัวอักษร) | `app.py` ก่อน create | ไม่สร้าง task — render 400 `"brief must be 1–2000 characters"` | chat form error, ไม่แตะ tracker |
| ไม่เจอ module ที่ route / module ไม่มีใน registry | router / `UnknownModuleError` (`runtime.py:32-33`) | `no_route` + `"no enabled module matches — enable it on /modules"` | failed task + ลิงก์ /modules |
| module `disabled` | `ModuleHost.call_tool` raise `ModuleHostError` (`module_host.py:247-249`) | `module_disabled` + hint เปิด module | failed task |
| `connect()` ล้ม (bad command / transport / handshake) | dict `{"connected": False, "error": ...}` (`module_host.py:114-134`) | `connect_failed` + `last_error` ≤200 ตัวอักษร | failed task |
| `MCPStdioError: timed out / exited / malformed` (`mcp_stdio.py:110-124`) | `ModuleHostError` (`module_host.py:261-262`) | `timeout` / `module_exited` / `bad_response` + hint "ลองใหม่; ถ้าซ้ำดู /modules" | failed task + **disconnect ทันที** (§3) |
| tool คืน `isError` (`mcp_stdio.py:139-145`) | `MCPStdioError(detail)` | `tool_error` + detail ≤1200 ตัดเหลือ ~500 ใน task | failed task |
| `tracker` เขียนไม่ได้ (`OSError`) | `runtime` | ไม่ crash — render 500 เฉพาะเคสนี้ (tracker คือ source of truth, ปิดบังไม่ได้) | 500 + log |
| อย่างอื่น (`Exception`) | `runtime` catch-all | `internal` + `TypeName: msg` ≤200 (สไตล์เดียวกับ `runtime.py:214-219`, `live.py:425-432`) | failed task ถ้ามี task_id แล้ว, ไม่ 500 |

* `error_detail` เก็บเป็น **dict** `{code,message,hint}` — แต่ `tasks.html:44-48` render ด้วย `{{ task.error_detail }}` ตรง ๆ จึงรับได้ทั้ง str (ของเก่า) และ dict (ของใหม่) โดยไม่ต้องแก้ template
* HTTP: **terminal `failed` ยังตอบ 200** (งานจบแล้ว แค่ผลคือล้ม) — 4xx มีแค่ input ผิด, 5xx มีแค่ tracker เขียนไม่ได้ (PRD §9: ล้มเหลวต้องเป็นข้อมูล ไม่ใช่หน้าขาว)

---

## 3. Timeout — กัน Concat/stdio ค้าง 30 นาที

### 3.1 ทำไมค่าปัจจุบันไม่พอ

* `ModuleHost.__init__` (`module_host.py:29-30`) ตั้ง `startup=15s / request=5s` แต่ `call_tool(..., timeout=60.0)` (`module_host.py:241`) ส่ง 60s ต่อ — render ยาวเกิน 60s จะโดนตัดทั้งที่งานอาจเกือบเสร็จ ส่วน Concat ที่ค้างจริงจะกินเต็ม 60s ต่อครั้งโดยไม่มี budget รวมคุม
* `MCPStdioClient.request()` (`mcp_stdio.py:106-118`) รีเซ็ต `queue.get(timeout)` ทุกรอบเมื่อ `id` ไม่ตรง → ถ้า module พ่น log/interleave ลง stdout ต่อเนื่อง ลูปนี้รอได้ไม่จำกัด (bug รูปแบบเดียวกับ "Concat stdio ค้าง 30 นาที" ที่ CEO สั่งกัน)

### 3.2 Design (ไม่แก้ protocol, แก้แค่ budget + kill)

1. **Deadline รวมต่อ 1 CEO turn**: `CEO_TURN_BUDGET_S = 180.0` (3 นาที) — นับจากก่อน `update_status(running)` ถึงหลัง `call_tool` คืน/raise ครอบทั้ง auto-`connect()` ภายใน (`module_host.py:250-255`) ด้วย
2. **Per-tool ceiling**: `TOOL_TIMEOUTS = {"default": 60.0, "render_*": 150.0, "tools/list": 5.0}` — `timeout = min(ceiling(tool), budget_remaining)` ส่งต่อเป็นอาร์กิวเมนต์ `timeout=` เดิมของ `host.call_tool` / `client.call_tool` ไม่เพิ่มพารามิเตอร์ใหม่ฝั่ง protocol
3. **แก้ `request()` แบบ minimal (F6)**: จำ `deadline = monotonic() + timeout` ก่อนลูป, ทุกรอบคำนวณ `remaining` แล้ว `get(timeout=remaining)` — `remaining <= 0 → raise MCPStdioError("MCP request timed out: {method}")` เดิม (`mcp_stdio.py:110`) เปลี่ยนแค่ให้ id-mismatch ไม่รีเซ็ตเวลา
4. **Timeout แล้วต้อง kill**: `except (timeout) → host.disconnect(module_id)` ทันที (ใช้ `_disconnect_locked → _close_client → close()` สาย `mcp_stdio.py:162-176` ที่มี `terminate/kill` อยู่แล้ว) แล้วค่อย `update_status(failed, code=timeout)` — ห้ามค้าง connection ที่ตายไว้ให้ poller เจอทีหลัง
5. **ห้าม retry อัตโนมัติ** — timeout 1 ครั้ง = 1 failed task ผู้ใช้กดส่งใหม่เอง (กันคูณเวลาค้างเป็น 30 นาที)
6. **HTTP ไม่รอเกิน budget**: FastAPI route เป็น `def` (sync) ตามไฟล์ปัจจุบัน (`app.py:259-271` ใช้ `def`) — ให้รัน `run_ceo_turn` ตรง ๆ ใน request thread (สอดคล้อง D1 single process) เพราะ budget สูงสุด 180s ยังอยู่ในขอบเขต local single-user; ห้ามย้ายไป background ใน Phase 2 (R3)

---

## 4. Envelope migration — backward compat 100%

### 4.1 ฟิลด์ใหม่ (additive เท่านั้น)

```jsonc
{
  "task_id": "task-<12hex>",            // เดิม — ห้ามเปลี่ยน (task_tracking.py:48-50)
  "dept": "content", "module": "content-creator", "task_type": "content",
  "status": "pending|running|completed|failed|cancelled",  // เดิม (task_tracking.py:30)
  "brief": "...",                        // เดิม — list ตัดออกเหมือนเดิม (task_tracking.py:113-114)
  "route_reason": "matched 'สคริปต์' → content-creator",  // ➕ str|None
  "artifact_refs": ["content/a.md"],     // ➕ list[str] — ของใหม่หลัก
  "result_ref": "content/a.md",          // เดิม — คงไว้, เขียนค่าตัวแรกของ artifact_refs ซ้ำเพื่อ reader เก่า
  "error_detail": {"code":"...","message":"...","hint":"..."}, // ➕ dict — reader เก่าที่เคยเก็บ str ยังอ่านได้ (template ไม่ cast)
  "app_version": "0.1.0",                // ➕ str — runtime ส่ง APP_VERSION (__init__.py:15) เข้า create()
  "created_at|started_at|completed_at": "ISO8601"          // เดิม
}
```

### 4.2 กฎ migration (F1)

* `create(..., route_reason=None, artifact_refs=None, app_version=None)` — kwargs ใหม่มี default หมด, positional เดิม 4 ตัวห้ามสลับ → โค้ดเก่าเรียกได้โดยไม่แก้
* `update_status(..., artifact_refs=None)` เพิ่ม 1 kwarg; ถ้าส่งมาให้ตั้ง `record["artifact_refs"] = list(...)` **และ** `record["result_ref"] = artifact_refs[0]` (ถ้ามี) เพื่อให้ reader เก่าเห็นค่าล่าสุด
* reader ทุกตัวใช้ `.get()` + fallback: `artifact_refs = record.get("artifact_refs") or ([record["result_ref"]] if record.get("result_ref") else [])` — สูตรเดียวกับที่ `tasks.html:37-42` ทำอยู่แล้ว
* `_write()` คง `json.dump(..., ensure_ascii=False, indent=2)` (`task_tracking.py:150-153`) และห้าม drop unknown keys (round-trip ไฟล์เก่า→ใหม่ต้องไม่เสียข้อมูล)
* ไม่ backfill ไฟล์เก่าใน `central_bus/content/tasks/` — ปล่อยให้เป็น legacy ที่อ่านได้ (append-only ประวัติห้าม rewrite ตามกฎ brain/session-log เดียวกัน)

---

## 5. `POST /chat` ควรอยู่ใน `app.py` อย่างไร

* อยู่ใน `_register_routes` (`app.py:249-251`) ฝั่ง **`writes = APIRouter(dependencies=[Depends(require_csrf)])`** (`app.py:251`) — ไม่สร้าง router ใหม่, ไม่แตะ `LoopbackBoundary` (`app.py:106-153`)
* ลายเซ็นตามสไตล์ไฟล์ (sync `def` เหมือน `chat_page` ใน `app.py:259-271`, toggle/check ใน `app.py:288-320`):

```python
@writes.post("/chat", include_in_schema=False)
def submit_chat(request: Request):
    # 1. form = await request.form()  — แต่ route เป็น def จึงใช้ await ไม่ได้:
    #    เปลี่ยนเป็น `async def` เฉพาะ route นี้ (Starlette รองรับผสม def/async
    #    ใน router เดียวกัน — toggle/check เป็น async อยู่แล้ว app.py:289,309)
    # 2. brief = str(form.get("brief","")).strip()[:2000] → ว่าง/เกิน → _render 400
    # 3. turn = runtime.run_ceo_turn(brief)   # F3 — sync, budget §3, ไม่ raise (ยกเว้น OSError tracker)
    # 4. return _render(request, "chat.html", active_page="chat",
    #        extra={"modules":..., "counts":..., "provider":..., "turn": turn, "brief": brief})
    #    - turn = {"task": task_dict, "route_reason":..., "result":...|None, "error":...|None}
    #    - failed ก็ 200 (ดู §2.4); มีแค่ OSError tracker → 500
```

* `GET /chat` (`app.py:259-271`) คงเดิมทุกอย่าง เพิ่มแค่ `extra={"turn": None}` เพื่อให้ template เดิม render ได้โดยไม่ `UndefinedError`
* ไม่เพิ่ม `/api/chat` JSON ใน Phase 2 — ลด surface ตาม precedent PR2.1 ที่ตัด `/api/sessions + /api/bus/queue` ออก (`app.py:347-349`)
* CSRF: ใช้ของเดิมล้วน ๆ (`security.py:135-159` + hidden field) — chat form ส่ง `csrf_token` แบบเดียวกับ settings form (`app.py:384-416`)

---

## 6. Checklist เรียงไฟล์ (F1–Fn) — ส่งต่อ implementer

| # | ไฟล์ | งาน (design scope) | Exit |
|:--|:--|:--|:--|
| F1 | `axis_mcp/task_tracking.py` | `create()` +3 kwargs (`route_reason, artifact_refs, app_version`), `update_status()` +1 (`artifact_refs` + mirror `result_ref`), normalize `error_detail` dict/str, คง `VALID_STATUSES` + guard + brief-strip เดิม (`task_tracking.py:30,43-50,94-117`) | test เก่าเขียว + ไฟล์เก่าอ่านได้ |
| F2 | `solocorp_app/ceo_loop.py` **(ใหม่)** | pure router `route_brief()` + `TOOL_TIMEOUTS` + `CEO_TURN_BUDGET_S` + `map_error()` — **ห้าม import `axis_mcp.departments.*`, `content_service`, `Concat`, `busd`, FastAPI** (R1/R2) | unit test ไม่ต้องมี MCP process |
| F3 | `solocorp_app/runtime.py` | เพิ่ม `run_ceo_turn(brief) -> dict` ตัวเดียว: validate cap → route (F2) → `tracker.create` (+`app_version=APP_VERSION`) → `running` → `host.call_tool(timeout=min(...))` → `completed/failed` + timeout-disconnect (§3.2-4); คง `call_tool` passthrough (`runtime.py:190-198`) ไว้เพื่อ compat | D7 loop ครบโดยไม่แตะ `tasks()/tasks_summary()` |
| F4 | `solocorp_app/app.py` | เพิ่ม `POST /chat` ใน `writes` router + `GET /chat` ส่ง `turn=None`; reuse `_render/_notice/_module_id_or_error` (`app.py:202-246`) | CSRF + loopback ผ่านเหมือน toggle |
| F5 | `solocorp_app/templates/chat.html` | แทน "Not wired" (`chat.html:16-17`) ด้วย `<form method=post action=/chat>` + hidden `csrf_token` + แสดง `turn.task/route_reason/result/error` + ลิงก์ `/tasks` | ไม่มี inline script (CSP `security.py:42-45`) |
| F6 | `axis_mcp/module_host.py` + `axis_mcp/departments/mcp_stdio.py` | **minimal**: `request()` ใช้ deadline รวม (แก้ `mcp_stdio.py:106-118` ไม่เกิน 5 บรรทัด) + `call_tool` ส่ง timeout ผ่านเหมือนเดิม (`module_host.py:260`) | handshake/connect test เดิมเขียว |
| F7 | `tests/test_solocorp_app_ceo_loop.py` **(ใหม่)** | ใช้ `FakeClient` แบบ `test_solocorp_app_runtime.py:29-46` ครอบ: happy path, disabled→failed, timeout→failed+disconnected, tool isError→failed, brief 400, ไฟล์ task เก่า (ไม่มี 3 ฟิลด์) อ่านได้ | ≥6 เคส, ไม่ spawn process จริง |
| F8 | `docs/runbooks/SOLOCORP-APP-SHELL.md` (append สั้น) | บันทึก budget/timeout + error codes + วิธีดู task file | ไม่แก้ contract เก่า |

*ลำดับบังคับ F1 → F2 → F3 → F4/F5 → F6 → F7 → F8 (envelope ก่อน loop, loop ก่อน route, route ก่อน template)*

---

## 7. Constraints (R1–Rn) — กัน Concat/MCP ลาม

| # | ข้อห้าม | ตรวจอย่างไร |
|:--|:--|:--|
| R1 | **ห้าม `import axis_mcp.departments.*` / `content_service` / engine ใด ๆ จาก `solocorp_app/`** — คุยผ่าน `ModuleHost` + `TaskTracker` เท่านั้น (precedent `live.py:19`) | `grep -rn "departments\.\|content_service\|concat" solocorp_app/` ต้องว่าง (ยกเว้นคอมเมนต์) |
| R2 | **ห้ามแตะ Concat / local-media / ffmpeg path จาก CEO loop** — render หนักเป็น Phase 3, loop นี้เรียกแค่ tool ที่ registry ประกาศ | F2 import-list ไม่มี `concat/render/local_media/ffmpeg` |
| R3 | **ห้าม background thread/worker/queue ใน Phase 2** — sync ใน request thread ภายใต้ budget 180s (D7 `SOLOCORP-APP-LOCAL-RUNTIME-DESIGN-v0.1.md:142-156`, `runtime.py:55-58` pool มีไว้แค่ connect ไม่ใช่ CEO) | ไม่มี `ThreadPool/subprocess/busd` ใหม่ใน F2–F4 |
| R4 | **ห้าม reroute เงียบ / fallback model เงียบ** (D5 `provider.py:11-15`) — disabled/unavailable = failed + hint เท่านั้น | test: disable content-creator แล้ว brief เดิมต้อง failed ไม่ใช่ไปลง engineering |
| R5 | **timeout/exit ต้อง `disconnect` ทันที** (`module_host.py:149-155` + `mcp_stdio.py:162-176`) ห้ามปล่อย zombie ให้ poller เก็บทีหลัง | test: FakeClient timeout แล้ว `host._connection(id) is None` |
| R6 | **ห้าม leak `brief`** — `list_tasks` default ตัด brief (`task_tracking.py:94-117`), `tasks_summary` นับอย่างเดียว (`runtime.py:234-258`), `/tasks` ไม่แสดง brief | `grep brief solocorp_app/templates/tasks.html` ต้องว่าง |
| R7 | **ห้าม 500 แทน failed** — terminal ทุกแบบตอบ 200 + task `failed` (PRD §9); 500 มีแค่ tracker `OSError` | F7 assert `failed → status 200` |
| R8 | **timeout มีเพดาน**: per-tool ≤150s, turn ≤180s, `request()` deadline รวม (ปิดช่อง `while True` `mcp_stdio.py:106-118`) | code review ดู `monotonic()+remaining` |
| R9 | **envelope additive เท่านั้น** — ห้าม rename/remove `result_ref`, ห้ามเปลี่ยน `task_id` regex/positional args | ไฟล์ task เก่าเปิดด้วย F7 ผ่าน |
| R10 | **security surface เดิม** — loopback (`app.py:106-153`) + CSRF `writes` (`app.py:251` + `security.py:135-159`) + brief cap 2000 + `MODULE_ID_PATTERN` (`app.py:42`) ไม่เพิ่ม auth/cookie ใหม่ | ZAP/CSRF test เดิมเขียว |

---

## 8. ความเสี่ยงส่ง CEO

| # | ความเสี่ยง | ระดับ | รับมือใน design นี้ |
|:--|:--|:--|
| 1 | keyword router เลือกแผนกผิด (brief กำกวม) | สูง/สูง | `route_reason` บังคับทุก task (§2.3) ตรวจย้อนได้ + fallback ให้ผู้ใช้พิมพ์ชื่อแผนกตรง ๆ; เลื่อน LLM router เป็น Phase 2b แยกฉบับ |
| 2 | render จริงเกิน 150s → failed ทั้งที่งานเกือบเสร็จ | กลาง/กลาง | ceiling แยก per-tool (§3.2) + `artifact_refs` รองรับ partial (tool คืน path ที่เสร็จก่อน timeout ได้ถ้า implement ภายหลัง); ไม่ retry อัตโนมัติ |
| 3 | `request()` id-mismatch starvation (Concat พ่น log ลง stdout) | กลาง/สูง | deadline รวม F6 (§3.2-3) — ปิดช่องค้างไม่จำกัดโดยไม่เปลี่ยน protocol |
| 4 | HTTP worker ถูกยึด 180s ต่อ 1 chat (single-user ok, แต่กดซ้ำ = ซ้อน) | ต่ำ/กลาง | single-user local รับได้ (D1); กันกดซ้ำฝั่ง template (disable button on submit, ไม่ต้องมี JS — ใช้ `disabled` attr) + ไม่ทำ single-flight ในรอบนี้ |
| 5 | envelope dict `error_detail` ทำให้ tool เก่าที่คาด str พัง | ต่ำ/กลาง | dual-read (`tasks.html:37-42` รับทั้งคู่แล้ว) + mirror `result_ref` (F1); test ไฟล์เก่าใน F7 |
| 6 | implementer ลาก Concat/LLM เข้ามาใน loop | กลาง/สูง | R1–R3 + F2 import ban + รีวิวล็อก `grep` (§7) — ผิด R ใดคือตีกลับทั้ง PR |

---

## 9. สิ่งที่ design นี้ **ไม่** ครอบ (กัน scope creep)

* LLM routing / provider call / streaming / multi-turn memory — Phase 2b แยกฉบับ
* retry / cancel UI / worker pool / busd queue semantics — เลื่อนตาม `SOLOCORP-APP-LOCAL-RUNTIME-DESIGN-v0.1.md:124` (ประเมินหลัง Beta)
* Concat render proof / local-media fallback — ไม่แตะ (R2)
* `/api/chat` JSON / SSE / SPA — ไม่เพิ่ม (ลด surface ตาม `app.py:347-349`)

---

*จบ design — รอ CEO Go ก่อน implement ใด ๆ (ไฟล์ต่อไปคือ F1 ตาม §6)*
