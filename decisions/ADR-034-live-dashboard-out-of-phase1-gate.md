# ADR-034 — /live แยกเป็น PR2 นอก Gate Phase 1 (2026-11-12)

> **Status:** Accepted (CEO Go Option A Minimal Close, 2026-11-12) · **Scope:** Phase 1 gate per PRD §11 · **Head:** @product-produck

## Decision (5 บรรทัด)

1. แยกเพราะ `/live` ไม่อยู่ใน PRD §11 Phase 1 gate (gate = config one model + enable/disable Content จาก UI เท่านั้น) รวมไว้ทำให้ gate ปิดไม่ได้
2. แยกเพราะ Architect ชี้ risk 3 ข้อ (spawn CLI ทุก 3s, อ่าน `opencode.db` นอก allowlist, split-brain TaskTracker vs `bus/queue`) ต้องแก้แบบมี design ไม่ใช่พ่วง PR1
3. Gate Phase 1 จึงนับเฉพาะ provider settings + toggle Content + `/healthz` + `/api/modules` + secret guard เท่านั้น
4. `/live` (`live.py`/`live.html`/`test_live`/`app.js` +146 + `.bak` 5.8K) ย้ายเป็น PR2 ไม่บล็อก merge PR1 และต้องลบ `.bak` ก่อน merge
5. PR2 กลับมารวมได้เมื่อผ่าน Beta criteria: poll ไม่ spawn CLI ถี่/อยู่ใน allowlist, task source of truth เดียว, มี E2E ผ่าน, ไม่เพิ่ม secret surface

## Gate Phase 1 DoD (นับแค่นี้ — /live ไม่นับ)

- [ ] Provider: ตั้งค่า one model จาก UI ได้, fail ชัดเจนไม่ fallback เงียบ, credential ไม่อยู่ใน artifact/log
- [ ] Toggle: enable/disable Content Creator จาก UI ได้, เห็นสถานะ disabled/connecting/connected/error
- [ ] `GET /healthz` ตอบ ok
- [ ] `GET /api/modules` แสดง registry + status ตรงกับ state จริง
- [ ] Secret guard: ไม่มี secret ใน git/log/artifact, เก็บแบบ `api_key_ref` เท่านั้น
