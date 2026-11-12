# PR2 Live Beta Hardening — Implementation Checklist v2.0 (D1–D7 Final)

> **Status:** DESIGN FINAL — ห้าม implement จากไฟล์อื่น · **Author:** @architect-songsak · **Date:** 2026-11-12
> **Upstream:** design v1.0 (`/tmp/opencode/pr2-untracked-backup/PR2-LIVE-BETA-HARDENING-DESIGN-v1.0.md`, read-only) + DoD v1.0 (Product) + main@c449702 (Beta v1, 445/522/291/120/300/190 บรรทัด)
> **Safety:** Engineering re-apply เองหลัง CEO approve · ไม่ commit/push · ไม่แตะ stash/branch · `opencode.json` ห้ามแก้
> **Gate อ้างอิง:** ADR-034 (แยก /live เป็น PR2) · ADR-035 (ตัด `_sessions_from_db`) · PRD §9 (fail-open ห้ามรายงานเท็จ) · PRD §11 (Phase gate)

## 0. สิ่งที่ตรวจบน main@c449702 แล้ว (หลักฐานก่อนสั่งงาน)

| ไฟล์ | ขนาด | พบจริง (file:line) |
|:-----|:-----|:--------------------|
| `solocorp_app/live.py` | 445 | `CLI_TIMEOUT_S = 4.0` (`live.py:43`) ยาวกว่า poll 3s → ซ้อนได้ · `import sqlite3` (`live.py:23`) + `DEFAULT_OPENCODE_DB` (`live.py:35-40`) นอก allowlist `opencode.json:129-136` · `_sessions_from_db` (`live.py:213-274`) เดาชื่อตาราง + `ORDER BY` · cache มีแค่ sessions 10s (`live.py:49-51`) ไม่มี queue cache / ไม่มี `_CLI_LOCK` single-flight / ไม่มี `cache_hit` / ไม่มี `tasks_summary` / ไม่มี cap |
| `solocorp_app/app.py` | 522 | มี 4 routes: `/live` (`app.py:334-345`) + `/api/sessions` (`app.py:347-350`) + `/api/bus/queue` (`app.py:352-354`) + `/api/live/status` (`app.py:356-358`) → เกิน D6 (ต้องเหลือ 2) · `NAV_ITEMS` มี live แล้ว (`app.py:46`) ไม่ต้องเพิ่ม · import `list_sessions, queue_depths` (`app.py:26`) ผูก 2 routes ที่ต้องตัด |
| `solocorp_app/static/app.js` | 291 | modules block (92 บรรทัด, 5s) + live block ต่อเติม (`app.js:94-291`, 3s) อยู่ไฟล์เดียวกัน → ผิด D7 · live poller ไม่มี `visibilitychange` / `pagehide` / `AbortController` / backoff |
| `solocorp_app/templates/live.html` | 120 | มีป้าย bus-queue แล้ว (`live.html:101`) + fail-open slots (`live.html:13-14,69-71`) + `registry_valid` (`live.html:33-37`) — ดี เก็บไว้ · **ขาด:** แถว Tasks summary + `source` badges ครบ 3 ก้อน + `<script src="/static/live.js">` |
| `solocorp_app/runtime.py` | 300 | มี `tasks()` (`runtime.py:224-231`) เท่านั้น · **ไม่มี `tasks_summary()`** · `check_all()` / `_poll_loop()` เรียก `host.health_all()` (`runtime.py:185,274`) — ห้ามลากเข้า live path |
| `tests/test_solocorp_app_live.py` | 190 | ยัง assert `source in ("cli","db","none")` + มี test DB path — ต้องลบ `db` ออก · ไม่มี test cache-hit / cap / `tasks_summary` |
| `opencode.json` | 356 | allowlist (`opencode.json:129-136`) ยังไม่มี `~/.local/share/opencode` = ถูกต้องหลังตัด DB · MCP timeout 1800000 (`opencode.json:188,233`) คงเดิม |

---

## 1. Checklist เรียงไฟล์ (Engineering ทำตามลำดับ — ห้ามสลับ)

### F1 — `solocorp_app/live.py` (งานใหญ่สุด — 6 เรื่องในไฟล์เดียว)

- [ ] **F1.1 ลบ DB path ทั้งหมด (ADR-035):** ลบ `import sqlite3` (`live.py:23`) · ลบ `DEFAULT_OPENCODE_DB` (`live.py:35-40`) · **ลบฟังก์ชัน `_sessions_from_db` ทั้งก้อน (`live.py:213-274`)** ห้ามเหลือ helper / comment / env `OPENCODE_DB` fallback
- [ ] **F1.2 timeout:** `CLI_TIMEOUT_S 4.0 → 1.5` (`live.py:43`) — สั้นกว่า poll 3s เสมอ กัน poll N+1 ซ้อน CLI ของ poll N
- [ ] **F1.3 cache 2 ชั้น + lock คู่ (แทนของเดิม `SESSION_CACHE_TTL_S = 10.0` + `_SESSIONS_CACHE` + `_SESSIONS_CACHE_LOCK` ที่ `live.py:49-51`):**
  ```python
  TTL_SESSIONS_S = 15.0   # sessions เปลี่ยนช้า (คนเปิด session ใหม่)
  TTL_QUEUE_S = 5.0       # queue เปลี่ยนเร็ว แต่ยังกัน hammer 3s → ยิงไฟล์จริง ~1/2 poll
  _CACHE: dict[str, tuple[float, dict]] = {}   # keys: "sessions:<limit>", "queue:<dir>"
  _CACHE_LOCK = threading.Lock()
  _CLI_LOCK = threading.Lock()                 # single-flight: non-blocking acquire
  ```
  helpers ใหม่: `_get_cached(key, ttl) -> (value, hit, ttl_remaining)` / `_set_cached(key, value)` · `list_sessions_cached()` + `queue_depths_cached()` เป็นทางผ่านเดียวที่ `live_status` เรียก · `live_status` ห้าม `subprocess.run` ตรง
- [ ] **F1.4 single-flight (กัน spawn ซ้อน):** ใน `list_sessions` path CLI — `if not _CLI_LOCK.acquire(blocking=False): return stale-or-empty envelope ทันที` (พร้อม `cache_hit: True` ถ้ามี cache, ไม่งั้น `source=none` + `error="cli busy, serving stale"`) · `finally: _CLI_LOCK.release()` เฉพาะเมื่อ acquire สำเร็จ
- [ ] **F1.5 `list_sessions` เหลือ CLI-only:** signature ตัด `db_path` ทิ้ง (`list_sessions(limit, *, queue_cli=None)` สำหรับ test inject เท่านั้น) · flow: cache-hit → CLI → fail-open `{"sessions": [], "count": 0, "source": "none", "error": <cli_error>, "updated_at"}` · **ห้าม cache path ที่ล้ม** (ของเดิม `live.py:334-336` ทำถูกแล้ว — คงไว้) · `source` เหลือแค่ `cli|none`
- [ ] **F1.6 `queue_depths` ใส่ cap + skip (ของเดิม `live.py:347-375` ไม่มี):** เพิ่ม `MAX_LINES_PER_FILE = 50_000` + `MAX_BYTES = 8_000_000` ต่อไฟล์ (เกินแล้วหยุดนับ + ใส่ `truncated: True` ใน envelope) · ข้าม `archive/` + `*.offset` เสมอ · อ่านแค่ 6 ชื่อใน `QUEUE_FILES` (`live.py:63-69`) ห้าม `glob`/`rglob` (R2) · envelope เพิ่ม `"source": "bus-queue"`
- [ ] **F1.7 `live_status` รวม 3 ก้อน + 3 ฟิลด์ใหม่ (ของเดิม `live.py:378-445` มี 2 ก้อน):** signature `live_status(runtime, *, session_limit=SESSION_LIMIT, queue_dir=None)` (ลบ `db_path`) · เรียก `list_sessions_cached` + `queue_depths_cached` + `runtime.tasks_summary()` (F4) · response เพิ่ม: `tasks_summary {pending,running,completed,failed,total}` + `tasks_source: "app-tasks"` + `queue_source: "bus-queue"` + `cache_hit: bool` · ห้ามเพิ่ม field ที่ frontend **ต้องมี** ถึงจะ render ได้ (fail-open contract)
- [ ] **F1.8 ห้ามในไฟล์นี้:** ห้าม `import` ใหม่นอก stdlib + `runtime` (ห้าม `content_service`, `axis_mcp/departments/*`, `Concat`, DB driver ใด ๆ) · ห้ามเรียก `runtime.host.health_all()` / `check_health()` / `check_all()` · ห้าม thread ใหม่ / `await` งานหนัก / subprocess ตัวที่สอง

### F2 — `solocorp_app/app.py` (เหลือ 2 routes)

- [ ] **F2.1 ตัด 2 routes:** ลบ `api_sessions` (`app.py:347-350`) + ลบ `api_bus_queue` (`app.py:352-354`) ทั้งก้อน — ฟังก์ชัน `list_sessions` / `queue_depths` ยังอยู่ใน `live.py` ให้ test เรียกตรงได้ แต่ `app.py` ต้องไม่ register path 2 สายนี้
- [ ] **F2.2 เก็บ 2 routes:** `GET /live` (`app.py:334-345`, SSR จาก `live_status`) + `GET /api/live/status` (`app.py:356-358`, endpoint เดียวที่ JS poll) — ทั้งคู่ reads router (ไม่ต้อง CSRF) อยู่ใต้ `LoopbackBoundary` เดิม (`app.py:106-153`)
- [ ] **F2.3 import:** แก้ `from .live import ...` (`app.py:26`) เหลือ `SESSION_LIMIT, live_status` (ถ้าไม่ใช้ `list_sessions`/`queue_depths` ในไฟล์แล้ว) — ห้ามเหลือ import ที่ไม่มีคนใช้
- [ ] **F2.4 NAV + headers:** `NAV_ITEMS` (`app.py:44-50`) มี live แล้ว — ยืนยัน `test_nav_includes_live` ยังเขียว ไม่ต้องเพิ่ม · `Cache-Control: private, max-age=3` + `X-Content-Type-Options: nosniff` บน `/api/live/status` (test เดิมตรวจ header อยู่แล้ว — คงไว้)
- [ ] **F2.5 ห้าม:** ห้าม action/mutation ใด ๆ บน live routes (read-only, POST ไม่มี) — mutation ยังเป็น CSRF writes แบบหน้า modules เท่านั้น

### F3 — `solocorp_app/static/live.js` (สร้างใหม่) + `app.js` (frozen)

- [ ] **F3.1 สร้าง `solocorp_app/static/live.js` ใหม่ ~140 บรรทัด** (ห้ามรวมใน `app.js`): ค่าคงที่เดียว `LIVE_POLL_MS = 3000` · early-return ถ้าไม่มี `[data-live]` (หน้าอื่นไม่ poll) · guard `if (window.__solocorpLiveStarted) return` + `setInterval` ตัวเดียว
- [ ] **F3.2 3 กลไกกัน hammer ฝั่ง client (ของเดิม `app.js:270-290` ไม่มี):** (1) `AbortController` — fetch ค้าง >2.5s ตัดทิ้ง + ขึ้น `data-live-dot` เป็น stale ห้ามล้างตาราง; (2) `document.visibilitychange` — tab ซ่อนหยุด poll กลับมาเห็นค่อยต่อ; (3) `pagehide → clearInterval` — กัน back-forward สะสม interval
- [ ] **F3.3 backoff + jitter:** error ติดกัน → 3s → 6s → 12s (max 30s) + jitter ±500ms · สำเร็จ reset กลับ 3s · render ผ่าน `textContent` + `createElement` เท่านั้น ห้าม `innerHTML` (XSS) · hooks ตรงกับ `live.html`: `data-live-updated`, `data-session-source`, `data-q-*`, `data-session-count` + ใหม่ `data-t-*` (tasks_summary)
- [ ] **F3.4 `app.js` frozen:** ลบ live block (`app.js:94-291`) กลับเป็น 92 บรรทัด modules-only (5s) ตาม Phase 1 gate · `git diff -- solocorp_app/static/app.js` ต้องว่างหลังจบ (ยกเว้น revert commit) · `live.html` โหลด `live.js` เท่านั้น ไม่โหลด `app.js`
- [ ] **F3.5 ห้าม:** ห้าม POST/PUT/mutation · ห้ามส่ง secret/token/brief · ห้าม spawn/read CLI หรือ DB จาก JS · ห้าม poll เร็วกว่า 3s / หลาย poller ต่อหน้า

### F4 — `solocorp_app/templates/live.html` (ป้ายกัน split-brain)

- [ ] **F4.1 เพิ่ม Tasks card ใหม่** (ใต้ Queue card `live.html:91-102`): แสดง `status.tasks_summary.{pending,running,completed,failed,total}` + ป้าย `app-tasks อ่านจาก TaskTracker (งานที่สร้างแล้ว ถาวร) — คนละตัวกับ queue ด้านบน`
- [ ] **F4.2 ป้าย source ครบ 3 ก้อน:** Sessions ใต้หัวข้อ (`live.html:40`) เติม `sessions บนเครื่องนี้ (opencode) — ไม่ใช่ app tasks` + `data-session-source` มีแล้ว (`live.html:13`) · Queue ป้ายเดิมดีแล้ว (`live.html:101`) เก็บไว้ · Modules ไม่ต้องเพิ่ม
- [ ] **F4.3 script tag:** `<script src="/static/live.js" defer></script>` (CSP `script-src 'self'` เดิม ห้าม `unsafe-inline`) · คง fail-open slots (`live.html:13-14,69-71`) + `registry_valid` warning (`live.html:33-37`) — ห้ามลบ
- [ ] **F4.4 ห้าม:** ห้าม `<form>` / POST / ปุ่ม action ใด ๆ (retry/restart/clear) — live เป็น read-only dashboard

### F5 — `solocorp_app/runtime.py` (เพิ่ม helper เดียว)

- [ ] **F5.1 เพิ่ม `tasks_summary()` ใต้ `tasks()` (`runtime.py:224-231`):**
  ```python
  def tasks_summary(self, *, cap: int = 200) -> dict[str, int]:
      """นับ status จาก tasks() แบบ cap กันช้า — fail-open คืน 0 ทั้งก้อน."""
      # pending/running/completed/failed/total — key ที่ไม่รู้จักนับเป็น pending
  ```
  อ่านผ่าน `self.tasks()` (TaskTracker JSON) เท่านั้น · `cap` slice ก่อนนับ · `except OSError/Exception → zeros` ห้าม raise
- [ ] **F5.2 ห้ามแตะ:** `tasks()` (`runtime.py:224-231`), `counts()` (`runtime.py:98-108`), `modules()` (`runtime.py:61-96`) คงเดิม (gate ผ่านแล้ว) · ห้าม import ใหม่ใด ๆ ในไฟล์นี้

### F6 — `tests/test_solocorp_app_live.py` (ลบ DB → เติม 4 test ใหม่)

- [ ] **F6.1 ลบ DB ออก:** ลบ `db` จาก `assert payload["source"] in ("cli","db","none")` (`test_live.py:83`) → เหลือ `("cli","none")` · แก้ `test_list_sessions_fail_open_when_nothing_exists` (`test_live.py:176-184`) ตัด `db_path=` ทิ้ง · grep `opencode.db|\.local/share|_sessions_from_db|DEFAULT_OPENCODE_DB` ใน `solocorp_app/` + `tests/` ต้องว่าง (ยกเว้น ADR/checklist)
- [ ] **F6.2 test `source=none`:** CLI หาย + ไม่มี DB → `/live` + `/api/live/status` ตอบ 200, `session_source == "none"`, มีข้อความไทย (fail-open PRD §9)
- [ ] **F6.3 test cache-hit:** เรียก `/api/live/status` 2 ครั้งห่าง <15s แล้ว assert CLI ถูก spawn ≤1 ครั้ง (mock counter) + `cache_hit == True` ครั้งที่สอง
- [ ] **F6.4 test cap + skip:** queue file เกิน `MAX_LINES` / มี `archive/` + `*.offset` → นับ capped + `total` ไม่รวม archive
- [ ] **F6.5 test แยกเลข:** `tasks_summary` (จาก TaskTracker) vs `queue_total` (จาก bus) อยู่คนละ key กัน — เปลี่ยนข้างหนึ่ง อีกข้างไม่ขยับ · คง test fail-open + security headers เดิม (`test_live.py:133-137`) ห้ามลด coverage

### F7 — `opencode.json` (ห้ามแก้)

- [ ] **F7.1 ยืนยันไม่แก้:** `git diff -- opencode.json` ต้องว่าง · allowlist (`opencode.json:129-136`) ต้องยังไม่มี `~/.local/share/opencode` (ถูกแล้วหลังตัด DB) · MCP timeout 1800000 (`opencode.json:188,233`) คงเดิม — Beta ไม่แตะ Content/Concat config

---

## 2. DoD (QA ปิด gate PR2 — วัดได้ทุกข้อ)

- [ ] Poll `/api/live/status` 10 นาทีต่อเนื่อง: spawn `opencode` process ≤ ~40 ครั้ง (TTL 15s → ~4/min) — วัดด้วย test cache-hit + `ps`
- [ ] ถอน CLI (`PATH` ไม่มี `opencode`): `/live` + `/api/live/status` ตอบ 200, `session_source=none`, มีข้อความไทย (fail-open PRD §9)
- [ ] `bus/queue/` ว่าง / ไม่มี dir: `queue_total=0` แต่ `tasks_summary` ยังแสดง TaskTracker ได้ (สองเลขแยกกัน — split-brain ปิด)
- [ ] E2E: เปิด `/live` → เปิด opencode session ใหม่ → ภายใน ≤20s เห็นแถวใหม่ (TTL 15s + poll 3s)
- [ ] Secret guard: `live.py` ไม่มี import ใหม่นอก stdlib + `runtime`; `opencode.json` diff ว่าง; ไม่มี `*.bak`
- [ ] `app.js` diff ว่าง (frozen) · `live.js` แยกไฟล์ · `/api/modules` พฤติกรรมเดิม (Phase 1 gate ไม่ถดถอย)

---

## 3. ความเสี่ยง Concat/MCP (constraints — เจอให้ตัดออกทันที)

| # | ความเสี่ยง | กันอย่างไร |
|:-:|:-----------|:------------|
| R1 | Concat/Content MCP `timeout 1800000` (`opencode.json:188,233` = 30 นาที) — ถ้า live health check ไป connect จริง จะพา `/api/live/status` ค้าง | `live_status` อ่านแค่ `runtime.counts()` + `runtime.modules()` (registry state file) — **ห้ามเรียก `host.health_all()` / `check_health()` / `check_all()` ใน live path เด็ดขาด** (health poller `runtime.py:271-276` ทำงานแยก thread อยู่แล้ว) |
| R2 | `CONCAT_MCP_ROOTS = central_bus/content` (`opencode.json:194,238`) ซ้อนกับ `TASKS_ROOT = central_bus/content/tasks` — reader เดินผิดจะกวาดไฟล์ render หลาย GB | `queue_depths` อ่านแค่ 6 ชื่อใน `QUEUE_FILES` + skip `archive/` + `*.offset` — **ห้าม `glob("**/*.jsonl")` / `rglob` เด็ดขาด** |
| R3 | Open-core boundary (ADR-030): Content engine ปิด — live ไป import `content_service` จะผูก Beta กับ engine ที่เปลี่ยนได้ | `tasks_summary` ผ่าน `runtime.tasks()` เท่านั้น — **ห้าม import อะไรจาก `axis_mcp/departments/` หรือ `content_service` ใน `solocorp_app/`** |
| R4 | `opencode session list` shape เปลี่ยน / session เยอะ | คง `normalize_session` (`live.py:105-169` — ไม่ทิ้งแถว ไม่ raise) + `SESSION_LIMIT = 30` (`live.py:42`) ไม่ขยายใน Beta |
| R5 | Poll 3s + health poller 5s (`runtime.py:28`) แย่ง I/O | live endpoints เป็น sync-read เบาเท่านั้น (cache + นับบรรทัด + อ่าน state file) — **ห้าม `await` งานหนัก, ห้าม thread ใหม่, ห้าม subprocess ตัวที่สอง** |

---

*— @architect-songsak · DESIGN FINAL · Engineering เริ่มได้หลัง CEO approve D1–D7 · ไฟล์อ้างอิง: `solocorp_app/live.py:23,35-43,49-51,105-169,213-274,277-445` · `solocorp_app/app.py:26,44-50,334-358` · `solocorp_app/static/app.js:94-291` · `solocorp_app/templates/live.html:13-14,33-37,69-71,91-102` · `solocorp_app/runtime.py:28,185,224-231,271-276` · `tests/test_solocorp_app_live.py:83,133-137,176-184` · `opencode.json:129-136,182-242` —*
