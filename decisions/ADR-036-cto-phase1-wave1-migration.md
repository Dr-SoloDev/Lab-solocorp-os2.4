# ADR-036: CTO Phase 1 — รวม Architect+Engineering+QA เป็น MCP เดียว (`axis_mcp/cto`)

**วันที่:** 2026-11-13
**สถานะ:** Proposed (Wave 1 ทำบน `feat/cto-phase1-wave1`, รอ CEO/Owner ตรวจก่อน merge)
**เกี่ยวกับ:** Owner อนุมัติ Phase 1 = 3 แกน (Architect+Engineering+QA), CTO=C-Level รายงาน CEO ตรง, ไม่เอา R&D/Product · Two-Tier (ADR-002) · E2E-10 (2026-11-10)

---

## บริบท

`unified-technical` รวม 3 modules ใน process เดียวอยู่แล้ว แต่ชื่อ/โครงสร้างยังผูกกับยุคก่อน CTO (key `unified-technical`, module `axis_mcp.unified_technical`, DB `central_bus/unified_technical.db`) ขณะที่ org chart มี CTO (C-Level) เป็นเจ้าของสายเทคนิค Phase 1 แล้ว ชื่อเก่าทำให้ routing สับสนว่าใคร own pipeline

## การตัดสินใจ

1. `git mv axis_mcp/unified_technical -> axis_mcp/cto` (pure rename, 16 ไฟล์, commit แยก — ห้าม copy คู่)
2. label/command เป็น `cto` (`python -m axis_mcp.cto.server`, FastMCP name `cto`, DB `central_bus/cto.db`)
3. **namespaces เครื่องมือคงเดิมทั้งก้อน**: `architect_*` / `engineering_*` / `qa_*` / `unified_*` (รวมชื่อ tool `unified_technical_health`) — ห้าม re-prefix เป็น `cto_*`
4. DB ย้ายด้วย copy + ตรวจ sha256 ตรงกัน (`881da767…`, 3 tables เท่าเดิม) แล้วเก็บไฟล์เก่าไว้ก่อน (2-step deprecation)
5. `engineering` + `qa` standalone ใน `opencode.json` คงไว้ก่อน — ลบได้ก็ต่อเมื่อ CTO เขียวเท่านั้น
6. `opencode.json` + `opencode.jsonc` + README truth table อยู่ใน commit เดียวกัน (กัน drift)

## เหตุผล

- CTO ต้อง own pipeline 3 แกนใน process เดียว (Two-Tier: Control ผ่าน Head, Data ผ่าน server นี้)
- เปลี่ยนชื่อแต่ไม่เปลี่ยน contract: client/E2E เดิม (`unified_technical_health`) เรียกได้เหมือนเดิม ไม่พัง
- แยก commit (mv → rewire → config) เพื่อให้ revert ได้ทีละชั้น และ review ได้ว่าไม่มี logic change แฝง

## สิ่งที่พบระหว่างย้าย (Wave 1)

- **latent bug (มีมาก่อน, E2E ไม่เคยเจอ):** tool `unified_pipeline_status` ใน `server.py` เรียกตัวเองซ้ำ (ชื่อชนกับ helper ที่ import มา) → `maximum recursion depth exceeded` แก้โดย alias import (`_pipeline_status_impl`) — ชื่อ tool ภายนอกไม่เปลี่ยน
- **open contention (ยังไม่ตัดสิน):** มี WIP นอก Wave 1 เพิ่ม key `cto` ชี้ `axis_mcp.departments.cto_mcp` (boundary wrapper) ใน working tree ขณะย้าย — flat MCP namespace รับ `cto` ได้ key เดียว ฝั่ง live resolve มาที่ `axis_mcp.cto.server` ของ Wave 1 แล้ว (toolset 10 ตัวครบ) เรื่อง wrapper จะอยู่ key ไหนให้ orchestrator/CEO ตัดสินก่อน merge ลง `main` (ห้าม merge ทั้งคู่ชนกัน)

## ผลกระทบ

- Client ต้อง restart MCP host จึงจะเห็น server `cto` (process เก่า `unified-technical` ค้าง = stale)
- `central_bus/unified_technical.db` ยังอยู่บน disk (ไม่ถูกลบ) จนกว่า CTO green
- E2E เดิม (`unified_technical_health` → healthy ×3 + database) ต้องเขียวก่อน merge — ตรวจแล้วทั้ง direct probe และ live MCP
- ห้ามแตะ `product_mcp` / `legal_mcp` / `content_mcp` / `bus_mcp` / `legal_vault/**` (Wave 1 ไม่แตะ — ตรวจ diff ได้)

## References

- `axis_mcp/cto/server.py` · `axis_mcp/cto/shared/db.py` · `opencode.json` / `opencode.jsonc` (key `cto`)
- E2E: `docs/certification/E2E-10-MCP-2026-11-10.md` (probe #9)
- Evidence: `bus/evidence/cto-migration/20261113/w1-*`

---

## Wave 2 — stabilize + support (Architect, 2026-11-13, `feat/cto-phase1-wave1`)

**บทบาท:** Architect (พี่ทรงศักดิ์) — ตรวจ CTO ตัวเดียว, ประสาน orchestrator ตอน flip, คง eng/qa standalone, เตรียม shim Wave 3 เท่านั้น
**ข้อห้าม Wave 2:** ไม่แตะ `product_mcp` / `legal_mcp` / `content_mcp` / `bus_mcp` / `legal_vault/**` (ตรวจ diff แล้ว — สะอาด), ไม่ `rm -rf` / `sudo`

### 1. Health (fresh process probe, `w2-architect-health.json`)

- `unified_technical_health` → `healthy` ×3 (`architect` / `engineering` / `qa` healthy), `database: connected`, `cache: active`
- `freshness` → `current`, `restart_required=false` (no source newer than process)
- `unified_pipeline_status('w2-probe')` → `ok` (`architect -> engineering -> qa`) — ยืนยัน recursion fix Wave 1 ทำงานใน fresh process
- Tools: `@mcp.tool()` ×10 (`unified_technical_health`, `architect_route`, `architect_pipeline_define`, `engineering_build_backend`, `engineering_build_frontend`, `engineering_code_review`, `qa_run_test`, `qa_record_evidence`, `unified_pipeline_status`, `unified_list_tools_tool`) — namespaces `architect_*` / `engineering_*` / `qa_*` / `unified_*` ครบ, ไม่ re-prefix `cto_*` (ชื่อ `unified_list_tools_tool` เป็นของเดิมตั้งแต่ `main` ไม่ใช่ regression)
- DB: `central_bus/cto.db` — 3 tables (`tool_calls`, `build_artifacts`, `qa_evidence`), sha256 `881da767…` ตรงกับ `unified_technical.db` (source เก็บไว้, 2-step deprecation)

### 2. Live resolve + flip support

- `opencode mcp list` (2026-11-13 05:44 BKK): **9 connected + 1 disabled** — `cto`, `engineering`, `qa` ล้วน `connected`
- Config: `opencode.json` (9 servers) `cto -> axis_mcp.cto.server`; `opencode.jsonc` (4 servers) `cto -> axis_mcp.cto.server`, ไม่มี key `unified-technical` แล้ว; README truth table (9/4 + `cto -> axis_mcp.cto.server`) ตรงกันทั้งสามไฟล์ — **ไม่มี tool miss / health แดงตอน flip จึงไม่ต้องซ่อม wiring**
- Host generations: `axis_mcp.cto.server` มี 2 generations (PID 24305 @05:23 BKK = stale, เริ่มก่อน `server.py` mtime 05:24:48; PID 29123 @05:35 BKK = current) — live `connected` มาจาก generation ปัจจุบัน
- Wrapper contention ยังเปิดอยู่: `axis_mcp/departments/cto_mcp.py` อยู่บน disk แต่ NOT host-wired; single live `cto` key = `axis_mcp.cto.server` — ให้ orchestrator/CEO adjudicate ก่อน merge `main` (ห้าม merge ชนกัน)

### 3. Standalone + shim (Wave 3 เท่านั้น)

- `engineering` (`axis_mcp.departments.engineering_mcp`) + `qa` (`axis_mcp.departments.qa_mcp`) คงอยู่ใน `opencode.json` — **ไม่ลบใน Wave 2**
- Shim เป็นแค่แผน (`bus/evidence/cto-migration/20261113/w2-architect-deprecation-shim-plan.md`): thin forward + `deprecated` warning 1 release (Option A) หรือถอด key (Option B) — เริ่มได้ก็ต่อเมื่อครบเงื่อนไข Wave 3
- หมายเหตุประสาน orchestrator (concurrent Wave 2 flip-default บน branch เดียวกัน): ฝั่ง orchestrator เติม `deprecated/read-only redirect` metadata ใน `engineering_mcp.py` + เปลี่ยน command templates เป็น `@cto` primary (alias 1 release) — Architect ไม่ขวางเพราะ keys ยังอยู่ครบ (ไม่ลบ) และ `mcp.servers.ctо` target ไม่เปลี่ยน; ถือว่า compatible กับแผน Wave 3 Option A (shim metadata มาก่อน, ถอด key ทีหลังเมื่อครบเงื่อนไข)

### 4. Next — Wave 3 cleanup (เข้าได้เมื่อครบทั้ง 4 ข้อ)

1. CTO นิ่ง **48 ชม.** (healthy ×3 + DB + cache ทุก probe, `restart_required=false`, ไม่มี tool miss/health แดง)
2. ไม่มี caller เก่า **7 วัน** (standalone `engineering` / `qa` ไม่มี call 7 วันติด — มี caller = รีเซ็ตนาฬิกา)
3. CEO/Owner sign-off (L4/L5 บันทึกชัด, ไม่ถอดเงียบ)
4. Rollback พร้อม (`rollback-cto-wave1.md`, config `.bak` + `restart-mcp.sh --yes`, ≤15 นาที)

### 5. Evidence (Wave 2, Architect)

- `bus/evidence/cto-migration/20261113/w2-architect-health.json` (fresh probe + tools + DB)
- `bus/evidence/cto-migration/20261113/w2-architect-wiring.json` (json+jsonc+README triple)
- `bus/evidence/cto-migration/20261113/w2-architect-deprecation-shim-plan.md` (Wave 3 only)
- หมายเหตุ: `w2-health.json` ในโฟลเดอร์เดียวกันถูก Architect เขียนทับโดยไม่ตั้งใจขณะ orchestrator ทำ W2 flip คู่ขนาน (โฟลเดอร์ `bus/evidence/` เป็น gitignored local audit) — เนื้อหาเดียวกัน (healthy ×3) จึงเก็บสำเนา namespaced เป็น `w2-architect-health.json` แทน; ให้ orchestrator regenerate `w2-health.json` ฝั่ง flip ถ้าต้องการแยกไฟล์
