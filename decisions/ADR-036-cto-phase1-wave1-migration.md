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
