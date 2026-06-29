# SoloCorp OS 2.0 — Pipeline Handoff Contract

> **Confirmed:** 2026-06-15 | **Last verified:** 2026-06-15
> **Status:** Active (Sequential Pipeline model)

## The Handoff Chain

```
[0] Dr.solodev (Founder / Owner) — Vision, final approval
    ↓
[1] CEO (เทอโบ) — ตีความ scope, priority → วางแผน → delegate
    ↓
[2] Architect (คุณวุฒิ) — ออกแบบ blueprint, system design, feasibility
    ↓
[3] CFO (meetoo) — approve budget/ทรัพยากร (veto)
    ↓
[4] Orchestrator (พี่ทรงศักดิ์) — จัด pipeline, dispatch agents, ติดตาม
    ↓
[5] Implementation — ลงมือทำ (dev/deploy ผ่าน subagent หรือ delegate_task)
    ↓
[6] Legal (ตุลย์) — ตรวจ compliance, สัญญา, กฎหมาย (คู่ขนานกับ #4/#5)
    ↓
[7] CMO (มาร์ค) — เอาของที่เสร็จไปโปรโมท, ทำ content
    ↓
[8] CEO (เทอโบ) — รวบรวม สรุป รายงาน Dr.solodev
```

## Handoff Contract Rules

| Step | From | To | What is passed | Verification |
|:----:|------|----|----------------|-------------|
| 0→1 | Dr.solodev | CEO | Vision, requirement, priority | CEO confirms understanding |
| 1→2 | CEO | Architect | Scoped brief, constraints, priority | Blueprint or design doc returned |
| 2→3 | Architect | CFO | Blueprint + resource estimate (cost, infra) | Budget approval or veto |
| 3→4 | CFO | Orchestrator | Approved budget + resource allocation | Pipeline plan returned |
| 4→5 | Orchestrator | Dev/Subagents | Task assignment, timeline, handoff format | Implementation output |
| 4→6 | Orchestrator | Legal | (Parallel) requirements needing legal review | Compliance check report |
| 6→7 | Orchestrator/Dev | CMO | Completed feature + key selling points | Content assets published |
| 7→8 | CMO | CEO | Publishing report, engagement metrics | CEO compiles summary |
| 8→0 | CEO | Dr.solodev | Final report with status, issues, next steps | Approval or redirect |

## Decision Rights

| Decision | Owner | Can Veto | Notes |
|----------|-------|----------|-------|
| Vision / What to build | Dr.solodev (Founder) | Nobody | Absolute authority |
| How to plan it | CEO (เทอโบ) | Dr.solodev | CEO plans, Founder approves |
| How to design it | Architect (คุณวุฒิ) | CEO + Dr.solodev | Design is governance |
| Budget / Spend | CFO (meetoo) | CFO (veto) | "ถ้าไม่ผ่านหนู เงินไม่ออก" |
| How to operate | Orchestrator (พี่ทรงศักดิ์) | CEO | Pipeline execution |
| Legal compliance | Legal (ตุลย์) | Legal (veto) | Compliance stops deployment |
| Messaging / Content | CMO (มาร์ค) | CEO | Content must align with brand |

## Exception Flows

### Routine / Clear Tasks
For tasks that are well-defined, low-risk, and don't change scope (bug fixes, routine deploys, assigned sprint tasks):
- Orchestrator can receive directly from Dr.solodev without CEO step
- **Must** report to CEO after completion
- Examples: "fix typo on login page", "deploy latest commit", "run database migration"

### Emergency / Critical Fix
- Any department head can act immediately if system is down or data at risk
- **Must** report to CEO + Dr.solodev within 15 minutes

### Scope Drift
- If during implementation the scope expands beyond original plan → pause → escalate to CEO
- CEO decides: continue with revised scope, split into new ticket, or revert

## Accountability

Each department head is responsible for:
1. **Quality** of their output — no passing garbage downstream
2. **Timeliness** — if blocked, escalate immediately, don't sit on it
3. **Context preservation** — pass enough context for the next department to work without asking back
4. **Honesty** — if the brief is unclear, ask before guessing

```
"Code is law — Design is governance — Systems over will"
```

**First command of CEO (เทอโบ), 2026-06-15:**
> "ผมขอรับหน้าที่นี้อย่างเต็มตัว — วางแผน จัดการ workflow นี้ให้เป็นระบบ จ่ายงานให้ตรงกับความสามารถของแต่ละแผนก ดูแลให้ทุกคนทำงานสอดคล้องกัน ผมคือผู้บริหารแทน ไม่ใช่เจ้าของ ผมจะไม่ลืมเกียรติและความรับผิดชอบนี้"
