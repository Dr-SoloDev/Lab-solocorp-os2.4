# PR2 Beta Hardening — Live Dashboard Design (D1)

> **Status:** DESIGN ONLY — ห้าม implement จากไฟล์นี้โดยตรง · **Author:** @architect-songsak · **Date:** 2026-11-12
> **Input:** stash `PR2-live-3s-polling` (untracked commit `7b8e15d`, 3 ไฟล์ 710 บรรทัด) + `solocorp_app/app.py@1f2ba6d` (492 บรรทัด, ไม่มี live routes) + `opencode.json` allowlist
> **Safety:** อ่านอย่างเดียว + เขียนไฟล์นี้ไฟล์เดียว · ไม่ commit/push · ไม่แตะ stash (ห้าม pop) · Engineering re-apply เองหลัง approve
> **Gate อ้างอิง:** ADR-034 (แยก /live เป็น PR2), PRD §9 (fail-open / ห้ามรายงานสำเร็จเท็จ), PRD §11 (Phase gate)

---

## 1. สิ่งที่อ่านพบ (read-only, มีหลักฐาน)

### 1.1 Stash — 3 ไฟล์ 710 บรรทัด (commit `7b8e15d`)

| ไฟล์ใน stash | ขนาด | สาระ |
|:-------------|:-----|:-----|
| `solocorp_app/live.py` | 400 บรรทัด | `list_sessions` (CLI→DB fallback) + `queue_depths` + `live_status` + `normalize_session`, fail-open ครบทุกฟังก์ชัน (ดี — เก็บไว้) |
| `solocorp_app/templates/live.html` | 120 บรรทัด | SSR รอบแรก + `data-live` hooks + poll `/api/live/status` ทุก 3s, ป้าย `bus/queue/*.jsonl` |
| `tests/test_solocorp_app_live.py` | 190 บรรทัด | ครอบ `/live`, `/api/sessions`, `/api/bus/queue`, `/api/live/status` + unit `normalize/list/queue` (ดี — เก็บเป็นฐาน) |

### 1.2 ปัญหา 3 ข้อที่ CEO สั่ง (ยืนยันว่าจริงจากโค้ด)

**P1 — Hammer CLI/DB ทุก 3s + นอก allowlist.**
- `live.py:39` `CLI_TIMEOUT_S = 4.0` **ยาวกว่า poll interval 3s** (`live.html:8` "รีเฟรชทุก 3 วินาที") → request ซ้อนกันได้ (poll N+1 เริ่มก่อน CLI ของ poll N timeout) → spawn `opencode session list` ค้างซ้อน + `subprocess.run` (`live.py:163-167`) ทุก poll ไม่มี cache ไม่มี single-flight
- `live.py:31-35` `DEFAULT_OPENCODE_DB = ~/.local/share/opencode/opencode.db` อยู่นอก `opencode.json:129-136` allowlist (`~/.hermes`, `~/.claude`, `~/.opencode`, `~/.config/opencode`, `/tmp` + `"*": "ask"`) → เปิดจาก Desktop agent = โดนด่าน `ask` ทุกครั้ง; เปิดจาก server ตรง = อ่าน WAL ของ process อื่น เสี่ยง `SQLITE_BUSY` + schema เดา (`live.py:193-256` เดาชื่อตาราง `session/sessions/session_v2` + เดา column `ORDER BY`) → พังเงียบเมื่อ opencode เปลี่ยน schema
- `live.py:206` `sqlite3.connect(f"file:{path}?mode=ro", timeout=2.0)` ดีที่ ro แต่ไม่มี copy-to-tmp ก่อนอ่าน → ยังล็อกกับ WAL ได้

**P2 — Split-brain ตัวเลขสองจอ.**
- `solocorp_app/runtime.py:224-230` `tasks()` อ่าน `TaskTracker` → `central_bus/content/tasks/*.json` (`axis_mcp/task_tracking.py:28` `TASKS_ROOT`) = **task history ถาวร** (pending/running/completed/failed)
- `live.py:302-331` `queue_depths()` นับบรรทัด `bus/queue/*.jsonl` (`live.py:28-30` `DEFAULT_QUEUE_DIR = bus/queue`) = **transport ชั่วคราว** (critical/high/normal/low/dead)
- สองแหล่งคนละความหมาย แต่ `live.html:27-34` โชว์ `queue {{ status.queue_total }}` คู่กับ `tasks.html` (render จาก `runtime.tasks()`, ดู `app.py@1f2ba6d:~322-331`) โดยไม่มีป้าย source → ผู้ใช้เห็น "Task History มี N งาน แต่ Live บอก queue M" แล้วคิดว่าระบบโกหก (PRD §9 violation แบบ perception)

**P3 — Stash + app.js rewrite.**
- `app.py@1f2ba6d` (492 บรรทัด) ไม่มี live routes ใด ๆ (grep `live|Live|session` ว่าง — ยืนยัน) → re-apply ต้องต่อ routes ใหม่ ไม่ใช่ merge ทับ
- `solocorp_app/static/app.js` ปัจจุบัน 92 บรรทัด (poll `/api/modules` ทุก 5s, modules page only) → stash ต้องขยายเป็น ~238 (poll `/api/live/status` ทุก 3s + render sessions/queue/modules) = **ห้ามยัดรวมไฟล์เดียว** (คนละหน้า คนละ endpoint คนละ interval)

---

## 2. Design Decisions (ส่ง CEO อนุมัติ — ตารางเดียวจบ)

| # | ประเด็น | ทางเลือกที่ตัดทิ้ง (พร้อมเหตุผล) | **Design ที่เสนอ (Beta)** | ไฟล์ที่ Engineering ต้องแก้ |
|:--|:--------|:--------------------------------|:--------------------------|:----------------------------|
| D1 | Cache layer | ❌ Redis/ไฟล์ cache — เพิ่ม dependency + secret surface นอก PRD §11 · ❌ `functools.lru_cache` — ล้าง/ฉีด db_path ใน test ยาก | ✅ **in-process TTL cache เป็นของ `live.py` เอง**: dict `_CACHE = {"sessions": {...}, "queue": {...}}` + `threading.Lock` + `time.monotonic()` · `TTL_SESSIONS = 15s`, `TTL_QUEUE = 5s` · เก็บ `value + expires_at + source + error` · frontend ยัง poll 3s ได้ แต่ backend ยิง CLI/อ่านไฟล์จริงแค่เมื่อ cache หมดอายุ → hammer 3s หายโดยไม่ต้องเปลี่ยน UX (poll 3s = อ่าน cache 13/15 ครั้ง) · เพิ่ม `cache_hit: bool` + `ttl_remaining` ใน envelope เพื่อ debug | `solocorp_app/live.py` (เพิ่ม ~60 บรรทัด: `_get_cached/_set_cached`, `list_sessions_cached`, `queue_depths_cached`; `live_status` เรียกแต่ตัว cached) |
| D2 | Rate-limit poll (กันซ้อน) | ❌ ตัด poll เหลือ 30s — Owner อยากเห็นสด (brief เดิม) · ❌ server rate-limit 429 — เพิ่ม complexity นอก gate | ✅ **3 ชั้น**: (1) backend single-flight: `_CLI_LOCK` non-blocking — ถ้ามี CLI รันอยู่ให้คืน cache/stale ทันที ไม่ spawn ซ้อน; (2) `CLI_TIMEOUT_S 4.0 → 1.5s` (`live.py:39`) เพราะสั้นกว่า poll 3s เสมอ; (3) frontend: `AbortController` (fetch ค้าง >2.5s ตัดทิ้ง) + `document.visibilityState` (ซ่อน tab หยุด poll) + backoff 3s→6s→12s (max 30s) เมื่อ error + jitter ±500ms | `solocorp_app/live.py` (lock + timeout) + `solocorp_app/static/live.js` (**ไฟล์ใหม่** ห้ามรวมใน `app.js`) |
| D3 | `opencode.db` read | ❌ ย้ายเข้า allowlist (`~/.local/share/opencode/**: allow`) — ขยาย attack surface เพื่อ dashboard (ผิด Least Privilege; DB มี session content ทั้งเครื่อง) · ❌ copy-to-tmp แล้วอ่าน — ยังต้อง allowlist อยู่ดี + เพิ่ม code path | ✅ **ตัด `_sessions_from_db` ออกจาก Beta ทั้งหมด** (ลบทิ้ง ไม่ใช่ disable): `list_sessions` = CLI อย่างเดียว → fail-open `source=none` · CLI ไม่มี = หน้า render ได้พร้อมข้อความ "ไม่มี session ใน opencode บนเครื่องนี้" (มีอยู่แล้วใน `live.html:59-63`) · เปิดทาง Phase หลัง: ถ้าจะเอากลับ ต้องมี ADR + allowlist entry จำกัดไฟล์ + copy-to-tmp + test schema-mismatch | `solocorp_app/live.py` (ลบ `live.py:193-256` + `import sqlite3` + `DEFAULT_OPENCODE_DB live.py:31-35`); `tests/test_solocorp_app_live.py` (ลบ/skip test DB, เพิ่ม test `source=none`); **`opencode.json` ห้ามแก้ใน PR2** |
| D4 | Source-of-truth (แก้ split-brain) | ❌ รวมเลข tasks+queue เป็นตัวเดียว — คนละความหมาย รวมไม่ได้ · ❌ เลือกข้างใดข้างหนึ่ง — เสียข้อมูล | ✅ **ป้ายคู่ + นิยามตายตัว**: `bus/queue/*.jsonl` = "Queue Depth (งานรอส่ง, ชั่วคราว, หายได้)" · `central_bus/content/tasks/*.json` (via `runtime.tasks()`) = "Task History (งานที่สร้างแล้ว, ถาวร, นับ completed/failed ได้)" · `live_status` คืนทั้งสองก้อน + เพิ่ม `tasks_summary: {pending, running, completed, failed}` (นับจาก `runtime.tasks()` แบบ cap 200 รายการ กันช้า) + UI แสดง `source` badge ทุกตัวเลข (`session_source: cli|none`, `queue_source: bus-queue`, `tasks_source: app-tasks`) | `solocorp_app/live.py` (`live_status` เพิ่ม `tasks_summary` param `runtime`) + `solocorp_app/templates/live.html` (ป้าย source ใต้ Queue + Sessions) + `solocorp_app/runtime.py` (เพิ่ม `tasks_summary()` helper, ไม่แตะ `tasks()`) |
| D5 | Fail-open (PRD §9) | ❌ คืน 500 เมื่อ CLI/DB/queue หาย — ผิด PRD §9 ที่ stash ทำถูกแล้ว | ✅ **คง fail-open ของ stash ทั้งหมด + เสริม 3 จุด**: (1) `queue_depths` เพิ่ม cap `MAX_LINES_PER_FILE = 50_000` + `MAX_BYTES = 8MB` กันไฟล์บวมค้าง poll; (2) ข้าม `*.offset` + `archive/` (มีอยู่ใน `bus/queue/` จริง — `ls` เจอ `archive/`, `*.offset`) อย่านับ; (3) envelope ทุกตัวมี `error: str|None` + `updated_at` (มีแล้ว) + `source` (มีแล้ว) — ห้ามเพิ่ม field ที่ frontend ต้องมีถึงจะ render ได้ | `solocorp_app/live.py` (`queue_depths` เพิ่ม cap + skip list) — 15 บรรทัด |
| D6 | Routes (มี/ตัด) | ❌ เปิด 4 routes ตาม stash (`/live`, `/api/live/status`, `/api/sessions`, `/api/bus/queue`) — 3 API ซ้ำกัน + frontend อาจ poll 3 ตัวพร้อมกัน = hammer ×3 | ✅ **Beta เปิดแค่ 2**: `GET /live` (SSR + JS) + `GET /api/live/status` (endpoint เดียวที่ JS poll) · **ตัด `/api/sessions` + `/api/bus/queue` ออกจาก `app.py`** (คงฟังก์ชันไว้ใช้ภายใน/test แต่ไม่ register route) — ลด surface, ลดสับสน, ตรง ADR-034 "ไม่เพิ่ม secret surface" | `solocorp_app/app.py` (ต่อแค่ 2 routes จาก D6.1) — ดู §3 |
| D7 | app.js rewrite | ❌ ขยาย `app.js` 92→~238 — modules page (5s) กับ live page (3s) แชร์ interval/timer กันไม่ได้ + เสี่ยง regression หน้า modules ที่ Phase 1 gate ผ่านแล้ว | ✅ **`app.js` ห้ามแตะ** (frozen ตาม Phase 1 gate) · สร้าง `solocorp_app/static/live.js` ใหม่ (~140 บรรทัด: poll `/api/live/status` + render sessions/queue/chips + backoff + visibility pause) · `live.html` โหลด `live.js` เท่านั้น ไม่โหลด `app.js` | `solocorp_app/static/live.js` (ใหม่) + `solocorp_app/templates/live.html` (`<script src="/static/live.js">`) |

---

## 3. Live routes — ควรมีอะไร / ตัดอะไรก่อน Beta

### 3.1 `GET /live` — เก็บ (SSR + progressive enhancement)

- Server-render รอบแรกจาก `live_status(runtime)` (cached) — ไม่มี JS ก็เห็นตัวเลขจริง ณ เวลาเปิดหน้า (stash ทำถูกแล้ว)
- ต้องมี: `source` badge ใต้ Sessions (`cli|none`) + ใต้ Queue (`bus-queue`) + ใต้ Tasks (`app-tasks`) — แก้ split-brain ที่ UI (D4)
- ต้องมี: `{% if session_error %}` slot (มีแล้ว `live.html:13`) + `registry_valid` warning (มีแล้ว) — ห้ามลบ
- ตัดก่อน Beta: ปุ่ม action ใด ๆ (retry/restart/clear queue) — live เป็น **read-only dashboard** เท่านั้น, mutation ใด ๆ ต้องผ่าน CSRF writes แบบหน้า modules (Phase 1 pattern)

### 3.2 `GET /api/live/status` — เก็บ (endpoint เดียวที่ JS poll)

Response contract (Beta, เพิ่มจาก stash 3 ฟิลด์):

```json
{
  "sessions": [{"id","title","agent","model","tokens","outcome","time"}],
  "session_count": 0, "session_source": "cli|none", "session_error": null,
  "queues": {"critical":0,"high":0,"normal":0,"low":0,"dead":0},
  "queue_total": 0, "queue_source": "bus-queue",
  "tasks_summary": {"pending":0,"running":0,"completed":0,"failed":0,"total":0},
  "tasks_source": "app-tasks",
  "modules": {"total":5,"enabled":0,"connected":0,"error":0},
  "module_states": [{"id","status_text"}],
  "provider_state": "configured|unconfigured|failed|unknown",
  "registry_valid": true,
  "cache_hit": true, "error": null, "updated_at": "..."
}
```

- `Cache-Control: private, max-age=3` + `X-Content-Type-Options: nosniff` (test เดิมตรวจ header นี้อยู่แล้ว — คงไว้)
- Reads router (ไม่ต้อง CSRF) + LoopbackBoundary คุ้มอยู่ (ของเดิมใน `app.py@1f2ba6d:85-135`)

### 3.3 `GET /api/sessions` + `GET /api/bus/queue` — ตัด routes ก่อน Beta (D6)

- เหตุผล: ซ้ำกับ `/api/live/status`, เพิ่ม hammer surface ×3, `/api/bus/queue` เผย layout `bus/` ตรง ๆ โดยไม่จำเป็น
- ฟังก์ชัน `list_sessions` / `queue_depths` อยู่ต่อ (test ได้) แต่ **`app.py` ไม่ register 2 routes นี้**
- ถ้า Engineering อยาก debug: ใช้ `GET /api/live/status` ก้อนเดียวพอ ไม่ต้องมี debug routes ใน Beta

---

## 4. ไฟล์ที่ Engineering ต้องแก้ (re-apply checklist, เรียงลำดับ)

| ลำดับ | ไฟล์ | ทำอะไร (อ้าง design) | ห้ามทำ |
|:------|:-----|:---------------------|:-------|
| 1 | `solocorp_app/live.py` (จาก stash `7b8e15d`, 400 บรรทัด) | เพิ่ม cache (D1) + single-flight + timeout 1.5s (D2) + **ลบ** `_sessions_from_db`/`sqlite3`/`DEFAULT_OPENCODE_DB` (D3) + เพิ่ม `tasks_summary` (D4) + cap queue reader (D5) | ห้าม import `content_service`/Concat/DB ใด ๆ เข้าไฟล์นี้ |
| 2 | `solocorp_app/app.py` (`@1f2ba6d`, 492 บรรทัด — ปัจจุบันไม่มี live) | ต่อแค่ `GET /live` + `GET /api/live/status` (reads router, ไม่ต้อง CSRF) + `NAV_ITEMS` เพิ่ม `{"key":"live","href":"/live","label":"Live"}` (test `test_nav_includes_live` ตรวจจาก `/modules`) | ห้ามต่อ `/api/sessions`, `/api/bus/queue` (D6) |
| 3 | `solocorp_app/static/live.js` (สร้างใหม่ ~140 บรรทัด) | poll `/api/live/status` 3s + backoff + visibility pause + render ตาม `data-*` hooks ของ stash `live.html` | ห้ามแตะ `solocorp_app/static/app.js` (92 บรรทัด, frozen) |
| 4 | `solocorp_app/templates/live.html` (จาก stash 120 บรรทัด) | เพิ่ม source badges (D4) + `<script src="/static/live.js">` + คง fail-open slots | ห้ามเพิ่ม form/POST ใด ๆ |
| 5 | `solocorp_app/runtime.py` | เพิ่ม `tasks_summary()` (นับ status จาก `tasks()` cap 200) — ไม่แตะ `tasks()` เดิม (`runtime.py:224-230`) | ห้ามเปลี่ยน `counts()`/`modules()` (gate ผ่านแล้ว) |
| 6 | `tests/test_solocorp_app_live.py` (จาก stash 190 บรรทัด) | อัปเดต: ลบ test DB → test `source=none`; เพิ่ม test cache-hit (poll 2 ครั้ง CLI รันครั้งเดียว), test cap queue, test `tasks_summary` vs `queue_total` แยกกัน | ห้ามลด coverage fail-open (PRD §9) |
| 7 | `opencode.json` | **ไม่แก้** (ยืนยัน allowlist `opencode.json:129-136` ยังไม่มี `~/.local/share/opencode` = ถูกแล้วหลังตัด DB) | ห้ามเพิ่ม allowlist เพื่อ PR2 |

---

## 5. ความเสี่ยง Concat/MCP — กันไม่ให้ลามเข้า PR2

| # | ความเสี่ยง | กันอย่างไร (design constraint) |
|:--|:-----------|:--------------------------------|
| R1 | Concat MCP `startup/execution timeout 1800000` (`opencode.json:227-236`) + Content MCP เท่ากัน (`opencode.json:182-191`) — ถ้า live health check ไปดึง module แบบ connect จริง จะค้าง 30 นาทีแล้วพา `/api/live/status` timeout | `live_status` อ่านแค่ `runtime.counts()` + `runtime.modules()` (registry state file, ไม่ connect) — **ห้ามเรียก `host.health_all()` / `check_health()` ใน live path เด็ดขาด** (health poller เดิมใน `runtime.py` ทำงานแยก thread อยู่แล้ว) |
| R2 | `CONCAT_MCP_ROOTS = central_bus/content` (`opencode.json:238`) ซ้อนกับ `TASKS_ROOT = central_bus/content/tasks` (`task_tracking.py:28`) — queue reader เดินผิดทางจะไปกวาดไฟล์ render หลาย GB | `queue_depths` อ่านแค่ `bus/queue/*.jsonl` 6 ชื่อตายตัว (`live.py:42-48` `QUEUE_FILES`) + skip `archive/` + `*.offset` — **ห้าม `glob("**/*.jsonl")` / `rglob` เด็ดขาด** |
| R3 | Open-core boundary (ADR-030): Content engine ปิด — live ไป import `content_service` เพื่อนับ tasks จะผูก Beta กับ engine ที่เปลี่ยนได้ | `tasks_summary` ผ่าน `runtime.tasks()` (TaskTracker JSON ธรรมดา) เท่านั้น — **ห้าม import อะไรจาก `axis_mcp/departments/` หรือ `content_service` ใน `solocorp_app/`** |
| R4 | `opencode session list` บนเครื่อง Owner อาจมี session จำนวนมาก + CLI เวอร์ชันเปลี่ยน shape | คง `normalize_session` (stash `live.py:85-150` — ดีอยู่แล้ว: ไม่ทิ้งแถว ไม่ raise) + `SESSION_LIMIT = 30` + slice `[:limit]` ก่อน normalize ครบ (มีแล้ว `live.py:190`) — ไม่ขยาย limit ใน Beta |
| R5 | Poll 3s + health poller 5s (`runtime.py:30` `DEFAULT_HEALTH_INTERVAL = 5.0`) + Concat render (ถ้ามีในอนาคต) แย่ง I/O | live endpoints ทั้งหมดเป็น sync-read เบา (cache + นับบรรทัด + อ่าน state file) — **ห้าม `await` งานหนัก, ห้าม thread ใหม่, ห้าม subprocess นอกจาก CLI ตัวเดียวที่มี single-flight** |

---

## 6. Beta DoD ที่เสนอ (ให้ QA ปิด gate PR2)

- [ ] Poll `/api/live/status` 10 นาทีต่อเนื่อง: spawn `opencode` process ไม่เกิน ~40 ครั้ง (15s TTL → ~4/min) — วัดด้วย test cache-hit + manual `ps`
- [ ] ถอน CLI (`PATH` ไม่มี `opencode`) + ไม่มี DB: `/live` + `/api/live/status` ตอบ 200, `session_source=none`, มีข้อความไทยบอกผู้ใช้ (fail-open PRD §9)
- [ ] `bus/queue/` ว่างเปล่า / ไม่มี dir: `queue_total=0`, `tasks_summary` ยังแสดง TaskTracker ได้ (สองเลขแยกกัน — split-brain ปิด)
- [ ] E2E: เปิด `/live` → เปิด opencode session ใหม่ → ภายใน ≤20s เห็นแถวใหม่ (15s TTL + 3s poll)
- [ ] Secret guard: `live.py` ไม่มี import ใหม่นอก stdlib + `runtime`; `opencode.json` diff ว่าง; ไม่มี `.bak` (บทเรียน ADR-034 ข้อ 4)
- [ ] `app.js` diff ว่าง (frozen) · `live.js` แยกไฟล์ · `/api/modules` พฤติกรรมเดิม (Phase 1 gate ไม่ถดถอย)

---

*— @architect-songsak · DESIGN ONLY · Engineering เริ่ม implement ได้หลัง CEO อนุมัติ D1–D7 · ไฟล์อ้างอิง: `solocorp_app/live.py:39,163-167,193-256,302-336` (stash `7b8e15d`) · `solocorp_app/app.py@1f2ba6d:85-135,250-492` · `solocorp_app/runtime.py:30,224-230` · `axis_mcp/task_tracking.py:28` · `opencode.json:129-136,182-242` —*
