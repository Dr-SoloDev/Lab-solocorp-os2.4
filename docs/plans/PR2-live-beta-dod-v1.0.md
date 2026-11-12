# PR2 — /live Beta Spec (แยกจาก Phase 1 Gate) v1.0

> **Owner:** @product-produck (Head of Product) · **Date:** 2026-11-12
> **Upstream:** main@1f2ba6d (Gate CLOSED, live ถอดออกแล้ว) · ADR-034 · Stash `stash@{0}` 2ca3557
> **Status:** SPEC ONLY — ห้ามเขียนโค้ดในไฟล์นี้ · Engineering เขียนใหม่จาก spec นี้ (ห้าม apply stash ตรง ๆ)
> **Scope:** Beta = รวม `/live` กลับเข้า app ได้โดยไม่เปิด Gate Phase 1 ใหม่

## 0. Input ที่ CEO ให้มา (ล็อกไว้ กันเถียงทีหลัง)

- Stash PR2 = 3 ไฟล์ untracked: `solocorp_app/live.py` (400 บรรทัด) + `solocorp_app/templates/live.html` (120) + `tests/test_solocorp_app_live.py` (190) รวม ~710 บรรทัด + `app.js` +146 บรรทัดที่**ไม่อยู่ใน stash** (ปัจจุบัน `app.js` 92 บรรทัด มีแค่ modules poll 5s — ต้องเขียน live polling ใหม่)
- ADR-034 Beta criteria (4 ข้อกว้าง): poll ไม่ spawn ถี่/อยู่ใน allowlist · source of truth เดียว · E2E ผ่าน · ไม่เพิ่ม secret surface
- Architect risks (3 ข้อที่ต้องปิด): (1) spawn `opencode session list` CLI ทุก 3s ต่อ client (2) อ่าน `opencode.db` (~/.local/share/…) นอก allowlist (3) split-brain TaskTracker (`central_bus/content/tasks/`, โชว์ที่ `/tasks`) vs `bus/queue/*.jsonl` (transport counts)

---

## 1. PR2 Beta DoD — 6 ข้อ ตรวจได้จริงทุกข้อ

| # | DoD | เกณฑ์ผ่าน (ตัวเลข) | วิธีตรวจ (คำสั่ง/ไฟล์) |
|:--|:----|:-------------------|:------------------------|
| 1 | **Poll interval ล็อก 3s ฝั่ง client** | `app.js` มีค่าคงที่เดียว `LIVE_POLL_MS = 3000`, ไม่มี magic number อื่น, เปลี่ยน interval ต้องแก้ที่เดียว | `grep -n POLL_MS solocorp_app/static/app.js` → เจอ 1 จุด; เปิด `/live` + DevTools Network → `/api/live/status` ห่างกัน 3.0s ±0.5s |
| 2 | **Server cache TTL + single-flight (กัน spawn CLI ถี่)** | `GET /api/live/status` ตอบจาก cache เมื่อห่างกัน < `LIVE_CACHE_TTL_S = 10s`; spawn `opencode` CLI **≤1 ครั้ง / 10s / host** ไม่ว่าจะมีกี่ tab เปิดอยู่; concurrent request ซ้อนกันต้องรอผลก้อนเดียวกัน (single-flight) ไม่ spawn เพิ่ม | Code review: `live_status()` อ่านผ่าน cache layer เท่านั้น ห้าม `subprocess.run` ใน request path ตรง ๆ; test: เรียก `/api/live/status` 5 ครั้งใน 3s แล้ว assert ว่า CLI ถูก spawn ≤1 ครั้ง (mock counter); soak: เปิด 3 tab 30s → spawn count ≤3 |
| 3 | **Read allowlist (ปิด risk opencode.db)** | Default อ่านได้แค่: `bus/queue/*.jsonl` + registry/state ที่ runtime ถืออยู่เท่านั้น; `opencode.db` **ห้ามเป็น default source** — ใช้ได้เฉพาะเมื่อตั้ง env `SOLOCORP_LIVE_DB=1` ชัดเจน + เปิด `mode=ro` + path ต้องอยู่ใน allowlist dir ที่ config ระบุ; CLI (`opencode session list`) เป็น source หลักแทน DB; ไม่มี absolute path `~/.local/share/opencode/opencode.db` hardcode ใน default path | `grep -rn "opencode.db\|\.local/share" solocorp_app/` → ต้องไม่เจอใน default path (เจอได้แค่ใน opt-in branch + test); test `test_list_sessions_fail_open_when_nothing_exists` ต้องผ่านโดยไม่มี DB จริง; E2E บนเครื่องที่ไม่มี opencode CLI/DB → `/live` + 3 API ตอบ 200 พร้อม `source: none` ห้าม 500 |
| 4 | **Label bus-queue vs app-tasks (กัน split-brain)** | `/live` section queue แปะป้ายถาวรว่าเป็น **bus transport depth** (`bus/queue/*.jsonl`) และมีลิงก์/ข้อความว่า **"ไม่ใช่ Task History"**; `/tasks` ยังเป็นหน้าเดียวที่อ่าน TaskTracker (`central_bus/content/tasks/`) พร้อม brief-hidden; API field แยกชื่อ: `queues.*`/`queue_total` (bus) vs `tasks` (tracker) ห้ามใช้ชื่อ `tasks` ใน `/api/live/status` | ดู §2; ตรวจ: `curl /api/live/status` → ต้องมี `queues` + `queue_total` และ**ไม่มี** key `tasks`; เปิด `/live` อ่านเจอคำว่า "ไม่ใช่ Task History" ด้วยตา; `grep -n "tasks" solocorp_app/live.py` → ต้องว่าง (live.py ห้าม import TaskTracker) |
| 5 | **E2E proof (รันได้ซ้ำ)** | `pytest tests/test_solocorp_app_live.py` ผ่าน 10/10 + `pytest tests/ central_bus/tests/` ไม่พังเพิ่ม (pre-existing live-network fail ยกเว้นได้ตาม CI note); manual proof 3 คำสั่งผ่าน: `GET /live` 200 + `GET /api/live/status` 200 (มี key ครบ §2) + เปิด 2 tab 30s ไม่ 500 / ไม่ spawn เกิน TTL | แนบใน PR: pytest output + `curl -s -o /dev/null -w "%{http_code}"` ของ 2 endpoint + Network timing screenshot หรือ `watch -n3 curl` log 10 รอบ |
| 6 | **Secret guard (ไม่เพิ่ม surface)** | `/live` + 3 API ไม่ส่ง `api_key`/`api_key_ref`/`brief`/credential เด็ดขาด; session envelope มีแค่ `id,title,agent,model,tokens,outcome,time` 7 ฟิลด์; TaskTracker `brief` ไม่รั่วผ่าน live (live ไม่แตะ tracker อยู่แล้ว); `git grep -i "api_key\|secret\|token\|brief" solocorp_app/live.py solocorp_app/templates/live.html` → ว่าง (ยกเว้น `csrf_token` ใน base) | Automated: เพิ่ม 1 test assert ว่า `live_status` payload ไม่มี key ใน deny-list `{"api_key","api_key_ref","brief","credential","secret"}`; manual: `curl /api/live/status \| python3 -c "assert 'api_key' not in open(0).read()"` |

> หมายเหตุ DoD-2: ตัวเลข 3s (client) / 10s (server TTL) คือสัญญา Beta — cache เก่าสุดที่ user เห็นได้ = 10s + รอบ poll 3s ≈ 13s ถือว่ารับได้สำหรับ dashboard สถานะ (ไม่ใช่ realtime control)

---

## 2. /live อ่านอะไรเป็นหลัก + แปะป้ายกัน split-brain อย่างไร

### 2.1 Source map (ตารางเดียวจบ)

| Section ใน `/live` | อ่านจาก (primary) | ห้ามอ่านจาก | แสดงเป็น |
|:-------------------|:------------------|:-------------|:----------|
| Sessions | `opencode session list --format json` (CLI, timeout 4s) → opt-in DB fallback (§1-DoD3) → fail-open `[]` | TaskTracker / `central_bus/content/tasks/` | envelope 7 ฟิลด์ (§1-DoD6) + `session_source: cli\|db\|none` + `session_error` (ถ้ามี) |
| Queue depth | `bus/queue/{critical,high,normal,low,dead_letter}.jsonl` นับบรรทัด non-empty, ไฟล์หาย = 0 | TaskTracker (เด็ดขาด — คนละมิติกัน) | `queues.*` + `queue_total` + `updated_at` |
| Modules/Provider/Registry | `AppRuntime` ที่มีอยู่ (`counts()`, `provider.status()`, `registry_health()`) — ไม่เพิ่ม source ใหม่ | — | เหมือน `/modules` (read-only ซ้ำ ไม่ mutate) |

### 2.2 ป้ายกัน split-brain (บังคับมี 3 จุด)

1. **บนหน้า `/live` (HTML static text — ไม่ใช่ JS render):** ใต้หัวข้อ Queue depth ต้องมีบรรทัดถาวร (ตัวอย่างคำ):
   > ` bus transport depth จาก bus/queue/*.jsonl — ไม่ใช่ Task History (ดูงานที่ถูก track ที่ /tasks)`
2. **Sessions header:** `sessions บนเครื่องนี้ (opencode) — ไม่ใช่ app tasks` + โชว์ `source` อยู่แล้ว (`data-session-source`)
3. **API contract:** `/api/live/status` ห้ามมี key `tasks`/`task_count`/`brief` (assert ใน test — ดู DoD-4/6); ใครอยากได้ tasks ให้เรียกหน้า `/tasks` (TaskTracker) เท่านั้น

### 2.3 ทำไมต้องแยก (เหตุผลให้ Eng/QA อ้างได้)

- `bus/queue/*.jsonl` = **transport มิติ** (งานค้างท่อเท่าไร, รวม dead-letter) — ตัวเลขดิบ ไม่รู้ dept/status lifecycle
- TaskTracker `central_bus/content/tasks/*.json` = **lifecycle มิติ** (task_id, dept, module, status, artifact_refs, brief-hidden) — งานที่ถูก track แล้ว
- เอาเลข transport ไปเรียก "tasks" บน dashboard = user นับงานซ้ำ/หายแล้วโทษระบบ — split-brain ที่ Architect เตือนคือข้อนี้

---

## 3. `app.js` +146 live polling — ต้องมีอะไร / ห้ามมีอะไร

> ปัจจุบัน `app.js` (92 บรรทัด) ทำแค่ modules poll 5s + early-return ถ้าไม่มี `[data-module]` — live polling ต้องเป็น block ใหม่ที่อยู่ร่วมกันได้ ไม่แก้ behavior เดิม

### 3.1 MUST (ไม่มี = ไม่ผ่าน DoD-1/6)

- [ ] `LIVE_POLL_MS = 3000` ค่าคงที่เดียว + early-return ถ้าไม่มี `[data-live]` (หน้าอื่นต้องไม่ poll — ประหยัด + กัน spawn เปล่า)
- [ ] Poll `GET /api/live/status` ด้วย `fetch` + `Accept: application/json`, render ครั้งแรกมาจาก server (HTML) JS เติมรอบถัดไปเท่านั้น
- [ ] **Fail-open:** fetch ล้ม/timeout/non-JSON → เก็บจอเดิมไว้ + ขึ้น `data-live-dot` เป็น stale (เช่น "● stale") ห้ามล้างตาราง ห้าม throw หลุด console เป็น error loop
- [ ] **CSP no-inline:** logic อยู่ใน `/static/app.js` เท่านั้น ห้าม `<script>` inline ใน `live.html` (CSP ปัจจุบัน `script-src 'self'` อยู่แล้ว — คงไว้ ห้ามเติม `'unsafe-inline'`)
- [ ] **Single-instance:** guard `if (window.__solocorpLiveStarted) return; window.__solocorpLiveStarted = true;` + `setInterval` ตัวเดียว + `document.addEventListener('visibilitychange')` หยุด poll ตอน tab hidden (กัน spawn สะสม) + `pagehide` → `clearInterval`
- [ ] อัปเดตผ่าน `textContent` เท่านั้น (กัน XSS จาก title/session id) + `data-*` hooks ตรงกับ `live.html` (`data-live-updated`, `data-session-source`, `data-q-*`, `data-session-count`)

### 3.2 MUST NOT (มี = ตกทันที ไม่ต้องเถียง)

- [ ] ห้าม spawn/read CLI หรือ DB จาก JS (browser ทำไม่ได้อยู่แล้ว — ข้อนี้กันคนแอบใส่ Electron/native bridge ทีหลัง)
- [ ] ห้ามส่ง/เก็บ secret, `api_key`, token, brief ใน JS (poll เป็น GET ไม่มี body ไม่มี credential)
- [ ] ห้าม POST/PUT/mutation ใด ๆ จาก live poller (read-only; toggle/health-check ยังเป็น form POST + CSRF เหมือนเดิม)
- [ ] ห้าม `setInterval` ซ้ำซ้อน / หลาย poller ต่อหน้า / poll เร็วกว่า 3s / เอา `setInterval(refresh, 5000)` ของ modules มาใช้ร่วม (แยก timer คนละตัว)
- [ ] ห้าม `innerHTML` กับข้อมูลจาก API (XSS) — สร้าง row ด้วย `createElement` + `textContent` หรือ escape ก่อน

---

## 4. Handoff กลับ CEO (Go / No-Go + ขอบเขต)

### 4.1 Beta DoD (ย่อจาก §1 — เอาไปติ๊กใน PR)

1. Client poll 3s จุดเดียว · 2. Server cache 10s + single-flight (CLI ≤1/10s/host) · 3. Allowlist (DB เป็น opt-in เท่านั้น) · 4. ป้าย bus-queue ≠ app-tasks + API ไม่มี key `tasks` · 5. E2E 10/10 + manual proof 3 คำสั่ง · 6. Secret guard (deny-list assert)

### 4.2 Acceptance (CEO/Checker ตรวจก่อน merge PR2)

- [ ] 6 ข้อ §1 ผ่านครบ มีหลักฐานใน PR (pytest log + curl + grep ผลว่าง)
- [ ] `live.py` ไม่มี `TaskTracker` import; `app.py` มี route `/live` + 3 API + nav link (ของที่ `1f2ba6d` ถอดออกไป) กลับครบโดยไม่แตะ Phase 1 behavior
- [ ] `.bak` 5.8K (ADR-034 ข้อ 4) ถูกลบก่อน merge — `git status --short` ต้องไม่เห็น `*.bak`
- [ ] Checker ≠ maker (Product เขียน spec นี้แล้ว → checker เป็น QA/Architect ตามบันได 06-certification)

### 4.3 Out-of-scope (ห้ามลากเข้า PR2 — เจอให้ตัดออกทันที)

| ห้ามเอาเข้า | ไปอยู่ที่ไหนแทน |
|:-----------|:----------------|
| Phase 2 CEO loop (brief → task create → invoke Content MCP → terminal status) | PRD §6.2 / Phase 2 task path — PR2 อ่านอย่างเดียว ห้ามสร้าง task |
| Standalone MCP acceptance (ต่อ Content MCP ตรงจาก external client) | PRD §6.1 standalone path — คนละ acceptance กับ dashboard |
| Concat render / local-media render / publish gate | Content Creator pipeline — ไม่เกี่ยวดับ dashboard สถานะ |
| Multi-user/hosted/auth | Post-MVP (PRD Phase 5) |
| Auto-resolve/retry/cancel งานจาก `/live` | Should-have หลัง MVP (PRD §6.2) — PR2 ไม่มีปุ่ม mutation |

### 4.4 Next step สั่ง Eng/QA (CEO ส่งต่อได้เลย)

1. **Eng:** เขียนใหม่จาก spec นี้ (reference stash อ่านได้อย่างเดียว) — ประมาณ `live.py` (cache+allowlist ตาม DoD-2/3) + `live.html` (ป้าย §2.2) + `app.js` block ใหม่ (§3.1) + test 10 เคสเดิม + 1 deny-list test ใหม่ (DoD-6)
2. **QA:** รัน DoD-5 suite + soak 3 tab 30s + ตรวจ grep ว่าง 2 จุด (DoD-3/6) แล้ว sign Beta
3. **Product (ผม):** ตรวจ acceptance §4.2 แล้วปิด PR2 → `/live` กลับเข้า tree โดย Gate Phase 1 ไม่เปิดใหม่
