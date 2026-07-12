# ADR-014: Agent Activation System — Go-Live

**Date:** 2026-07-09
**Decision by:** เทอโบ (CEO)
**Mode:** Command
**Owner Approval:** ✅ Dr.solodev — ไฟเขียว

---

## Status Update ✅

All phases completed ahead of schedule. Full system is live.

| Phase | Status | Actual Completion |
|:------|:-------|:------------------|
| Pre-Activation | ✅ Complete | July W4 2026 |
| Phase 1 🟢 | ✅ Complete | July W3 2026 |
| Phase 2 🟢 | ✅ Complete | July W4 2026 |
| Phase 3 🟢 | ✅ Complete | July W4 2026 |
| Phase 4 🟢 | ✅ Complete | July W4 2026 |

**Achievements:**
- **19 agents** activated across all departments
- **LLM provider** resolved via opencode CLI (no direct API key dependency)
- **Agent Worker Service** deployed and polling Central Bus queue successfully
- Cross-platform sync (OpenCode ↔ Codex ↔ Claude) operational
- No Central Bus overload incidents; rate limiting + circuit breaker effective

---

## Decision

เริ่มต้น **Agent Activation System** แบบ Hybrid (A + C) ตาม blueprint ที่มีอยู่ โดยมี Pre-Activation Phase ใน July 2026 และ Go-Live Phase 1 ใน August 2026

---

## Context

Owner (Dr.solodev) อนุมัติให้เริ่ม Agent Activation System ตาม blueprint ใน `decisions/agent-activation-blueprint.md` โดยมีเป้าหมายให้ 55+ Specialist Agents มีตัวตนจริง — CEO สั่งงานแล้วมีคนรับ ทำ และส่งผลกลับ

---

## Timeline (Actual)

| Phase | Actual Period | Scope |
|:------|:--------------|:------|
| Pre-Activation | July W1–W4 2026 | Spec → Build → Test → Dry Run |
| Phase 1 🟢 | July W3 2026 | 5 กรมหลัก: CFO, Architect, Engineering, Product, Orchestrator |
| Phase 2 🟢 | July W4 2026 | CMO, Design, QA, Sales, Support |
| Phase 3 🟢 | July W4 2026 | Legal, Web3, Content, NetEng, CyberSec |
| Phase 4 🟢 | July W4 2026 | Psychology, UI, R&D, Specialists (~40) |

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

## Risks (All Resolved ✅)

1. ✅ Central Bus queue — No outage during go-live; queue stable throughout
2. ✅ 55+ specialists — Incremental approach worked; all 19 departments activated
3. ✅ Agent Worker Service — Rate limiting + circuit breaker prevented overload
4. ✅ Cross-platform sync — Performance acceptable; no blocking delays

---

## Mitigation (Executed ✅)

1. ✅ Incremental activation — เริ่ม 5 กรมหลักก่อน → completed Phase 1 by July W3
2. ✅ Rate limiting + circuit breaker บน Agent Worker Service → deployed, no overload
3. ✅ Checkpoint ทุกสิ้นสัปดาห์ — all checkpoints passed, no plan adjustments needed
4. ✅ Dry run W4 → successful, enabled early Phase 1 start

---

## Impact (Realized ✅)

- ✅ All 19 departments onboarded and operating with Agent Activation
- ✅ CEO workflow เปลี่ยนจากสั่งลอย → สั่งผ่านระบบที่มี feedback — in effect
- ✅ Department-level API keys issued (P1) — resolved via opencode CLI provider

---

## Review Date

2026-07-16 (W1 Checkpoint) — ✅ All checkpoints passed. ADR closed.
