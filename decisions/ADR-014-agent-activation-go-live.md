# ADR-014: Agent Activation System — Go-Live

**Date:** 2026-07-09
**Decision by:** เทอโบ (CEO)
**Mode:** Command
**Owner Approval:** ✅ Dr.solodev — ไฟเขียว

---

## Decision

เริ่มต้น **Agent Activation System** แบบ Hybrid (A + C) ตาม blueprint ที่มีอยู่ โดยมี Pre-Activation Phase ใน July 2026 และ Go-Live Phase 1 ใน August 2026

---

## Context

Owner (Dr.solodev) อนุมัติให้เริ่ม Agent Activation System ตาม blueprint ใน `decisions/agent-activation-blueprint.md` โดยมีเป้าหมายให้ 55+ Specialist Agents มีตัวตนจริง — CEO สั่งงานแล้วมีคนรับ ทำ และส่งผลกลับ

---

## Timeline

| Phase | ระยะเวลา | Scope |
|:------|:---------|:------|
| Pre-Activation | July 2026 (W1-W4) | Spec → Build → Test → Dry Run |
| **Phase 1** 🔴 | **August 2026** | **5 กรมหลัก: CFO, Architect, Engineering, Product, Orchestrator** |
| Phase 2 🟠 | TBD | CMO, Design, QA, Sales, Support |
| Phase 3 🟡 | TBD | Legal, Web3, Content, NetEng, CyberSec |
| Phase 4 🟢 | TBD | Psychology, UI, R&D, Specialists (~40) |

---

## Method

Hybrid Approach:
- **Method A (OpenCode Agents):** 5 กรมหลัก — CEO @mention → agent รับงาน → แก้ไขไฟล์ → ส่งกลับ
- **Method C (Python Worker):** Agent Worker Service — Poll Central Bus queue → execute → report

---

## Delegation

| Department Head | งาน | Deadline |
|:----------------|:----|:---------|
| @architect-songsak | Design Agent Worker Service spec | July W2 |
| @product-produck | PRD + Sprint Plan Phase 1 | July W2 |
| @changful | OpenCode agent configs + effort assessment | July W2 |
| @orchestrator-wut | Pipeline timeline + checkpoint gates | July W2 |
| @cfo-meetoo | Resource assessment (API keys, compute, storage) | July W2 |

---

## Risks

1. Dependency บน Central Bus queue — ถ้า bus ล่ม งานหยุดทั้งระบบ
2. 55+ specialists ไม่พร้อมเปิดพร้อมกัน — ต้อง incremental
3. Agent Worker Service ต้องไม่ overload Central Bus
4. Cross-platform sync (OpenCode ↔ Codex ↔ Claude) อาจช้า

---

## Mitigation

1. Incremental activation — เริ่ม 5 กรมหลักก่อน
2. Rate limiting + circuit breaker บน Agent Worker Service
3. Checkpoint ทุกสิ้นสัปดาห์ — ถ้าตกรีบปรับ plan
4. Dry run W4 ก่อน Phase 1 จริง

---

## Impact

- ทั้ง 19 departments จะได้รับผลกระทบเมื่อระบบสมบูรณ์
- CEO workflow เปลี่ยนจากสั่งลอย → สั่งผ่านระบบที่มี feedback
- ต้องมี department-level API keys (P1)

---

## Review Date

2026-07-16 (W1 Checkpoint)
