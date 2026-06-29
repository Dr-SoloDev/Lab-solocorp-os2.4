# SoloCorp OS 2.0 — Development Pipeline Reference

> **Version:** 2.0.0
> **Type:** Reference (concrete pipeline for subagent-driven-development)
> **適用プロファイル:** SoloCorp OS 2.0

---

## Overview

The SoloCorp OS 2.0 development pipeline defines **who does what** in each phase of feature development. It is a concrete instance of the subagent-driven-development full lifecycle, with named roles and formal handoffs.

### The 3 Roles

| Role | Name | Alias | Responsibility | Phase |
|:---|:---|:---|:---|:---|
| 🏗️ **Architect** | คุณวุฒิ | Design Lead | Research, design blueprints, review implementation | Phase 0, 0.5, 3 |
| 👑 **CEO** | เทอโบ | Executive | Big-picture oversight, scope breakdown, final QA | Phase 1, 4 |
| 🛠️ **Ops** | พี่ทรงศักดิ์ | Implementer | Build according to blueprint | Phase 2 |
| 👤 **User** | Dr.solodev | Decision-maker | Final sign-off | Phase 5 |

### Pipeline Flow

```
┌──────────────────────────────────────────────────────────────┐
│                SoloCorp OS 2.0 — Development Pipeline        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│    │ คุณวุฒิ  │    │  เทอโบ  │    │พี่ทรงศักดิ์│              │
│    │ (Arch)   │───▶│ (CEO)   │───▶│ (Ops)    │              │
│    │ Phase 0  │    │ Phase 1 │    │ Phase 2  │              │
│    │ +0.5     │    │         │    │          │              │
│    └──────────┘    └──────────┘    └──────────┘              │
│         │                                  │                 │
│         │                                  ▼                 │
│         │                          ┌──────────┐              │
│         │◀─────────────────────────│ คุณวุฒิ  │              │
│         │     Phase 3: Review      │ (Arch)   │              │
│         │                          └──────────┘              │
│         │                                  │                 │
│         │                                  ▼                 │
│         │                          ┌──────────┐              │
│         │◀─────────────────────────│  เทอโบ  │              │
│         │     Phase 4: Final QA    │ (CEO)    │              │
│         │                          └──────────┘              │
│         │                                  │                 │
│         │                                  ▼                 │
│         │                          ┌──────────┐              │
│         │◀─────────────────────────│ Dr.solo  │              │
│         │     Phase 5: Sign-off    │  (user)   │              │
│         │                          └──────────┘              │
│                                                              │
│    Rework loop: Phase 3 or 4 failure → back to Phase 2       │
│    Critical rework: Phase 4 failure → back to Phase 0.5      │
└──────────────────────────────────────────────────────────────┘
```

---

## Phase-by-Phase Specification

### Phase 0: Research & Data Collection (คุณวุฒิ)

**Input:** User request / feature idea
**Output:** Research report with findings, gaps, and data matrix

**Steps:**
1. Identify information sources (configs, repos, docs, APIs)
2. Spawn parallel research subagents (max 3 for this user)
3. Synthesize findings into structured report
4. Save report in project docs (e.g. `docs/research-round2.md`)
5. Proceed to Phase 0.5 if research is sufficient

**Quality Gate A:** Report must answer: What did we assume vs what is actually true? What did we miss?

### Phase 0.5: Blueprint / Design (คุณวุฒิ)

**Input:** Research report
**Output:** Formal blueprints per feature (`lab/experiments/<feature>/blueprint.md`)

**Steps:**
1. Identify features that need design (based on research gaps)
2. Spawn parallel design subagents (one per feature)
3. Each blueprint MUST include: executive summary, architecture, data model, flows, edge cases, effort estimate, roadmap
4. Verify consistency across blueprints (no conflicts, detect dependencies)
5. Hand off to เทอโบ for Phase 1

**Quality Gate B:** Each blueprint must have effort estimate (person-days) and explicit constraints section.

### Phase 1: Scope Breakdown (เทอโบ — CEO)

**Input:** Blueprint documents
**Output:** Scoped task list with priorities, ordered by dependency

**Steps:**
1. Review all blueprints — understand the big picture
2. Identify dependencies between features (which blocks which)
3. Break each feature into **bite-sized tasks** (2-5 min each)
4. Set priority: P0 (immediate), P1 (this week), P2 (next week)
5. Ensure scope doesn't lose focus — reject scope creep
6. Hand off scoped task list to พี่ทรงศักดิ์ for Phase 2

**Key principle:** Break down without losing the architectural vision. Don't let พี่ทรงศักดิ์ have to rediscover the design.

**Quality Gate C:** Each task must have: exact file paths, expected output, verification step. No task should leave the implementer guessing.

### Phase 2: Implementation (พี่ทรงศักดิ์ — Ops)

**Input:** Scoped task list
**Output:** Working implementation with tests

**Steps:**
1. Follow subagent-driven-development core process (implementer + 2-stage review per task)
2. Use TDD: failing test → minimal code → passing test → commit
3. Run integration validation after all tasks complete (5-check pattern: files, syntax, cross-refs, functional, consistency)
4. Generate implementation report
5. Hand off to คุณวุฒิ for Phase 3

**Quality Gate D:** All tests pass. Integration validation passes (5/5 checks). Report documents what was built.

### Phase 3: Review & Summary (คุณวุฒิ — Architect)

**Input:** Implementation + report
**Output:** Review verdict + summary

**Steps:**
1. Verify implementation matches blueprint (spec compliance)
2. Check code quality (security, error handling, naming, test coverage)
3. Identify any deviations from blueprint — document rationale
4. If issues found → send back to พี่ทรงศักดิ์ (Phase 2 rework loop)
5. If approved → write review summary and hand off to เทอโบ for Phase 4

**Rework rules:**
- **Minor issues** (typos, style, missing comments) → send back with specific fix instructions
- **Major issues** (missing feature, wrong architecture) → send back with scope change notice
- **Critical issues** (security, data loss, broke existing system) → STOP. Notify Dr.solodev immediately

**Quality Gate E:** Summary must explicitly state: "Blueprint matched" or list specific deviations with acceptance rationale.

### Phase 4: Final QA (เทอโบ — CEO)

**Input:** Implementation + Review summary
**Output:** QA verdict + handoff report

**Steps:**
1. Run final integration test (E2E flow)
2. Check that the feature works in the actual runtime environment
3. Verify no regression in existing functionality
4. If QA fails → send back with clear failure report:
   - **Minor failure** → back to พี่ทรงศักดิ์ (Phase 2)
   - **Major failure** → back to คุณวุฒิ for redesign (Phase 0.5)
5. If QA passes → write handoff report and send to Dr.solodev

**Quality Gate F:** Report must contain: ✅/❌ for each success criterion, screenshot/log evidence where possible, "Ready for sign-off" verdict.

### Phase 5: Sign-off (Dr.solodev)

**Input:** QA verdict + full report chain
**Output:** Final decision

**Expected behavior:**
- Dr.solodev reviews the final report
- If approved → work is complete
- If changes requested → send back to appropriate phase

---

## Handoff Card Format

Every handoff between phases MUST use this format:

```yaml
---
handoff:
  from_role: "🏗️ คุณวุฒิ (Architect)"
  to_role: "👑 เทอโบ (CEO)"
  phase: "Phase 0.5 → Phase 1"
  timestamp: "2026-06-18T14:30:00+07:00"
  summary: "F3 Context Grid, F1+F2 Inbox, and F4 Goal blueprints complete"
  deliverables:
    - "lab/experiments/f3-context-grid/blueprint.md"
    - "lab/experiments/f1-f2-agent-inbox/blueprint.md"
    - "workflows/F4-GOAL-MANAGEMENT.md"
  quality_gates:
    gate_b: "✅ Pass — each blueprint has effort estimate and constraints"
    consistency: "✅ Pass — no conflicts between features"
  open_questions:
    - "F2 approval timeout value (60 vs 1800) needs verification"
  next_action: "Review big picture, break into scoped tasks for Ops"
---
```

**In chat, use the compact format:**

```
🏗️→👑 [Phase 0.5→1] Handoff
==============================
Summary: [one-line]
Deps: [N] blueprints ready
Gates: Gate B ✅, Consistency ✅
Action: [what the receiver should do]
```

---

## Naming Convention

| Artifact | Pattern | Example |
|:---------|:--------|:--------|
| Research report | `docs/research-round<N>-<date>.md` | `docs/research-round2-20260618.md` |
| Blueprint | `lab/experiments/<feature>/blueprint.md` | `lab/experiments/f3-context-grid/blueprint.md` |
| Scoped task list | `workflows/tasks/<feature>-tasks.md` | `workflows/tasks/f3-context-grid-tasks.md` |
| Implementation report | `docs/reports/<feature>-impl-<date>.md` | `docs/reports/f3-impl-20260618.md` |
| Review summary | `docs/reviews/<feature>-review-<date>.md` | `docs/reviews/f3-review-20260618.md` |
| QA report | `docs/qa/<feature>-qa-<date>.md` | `docs/qa/f3-qa-20260618.md` |
| Final handoff | `docs/handoffs/<feature>-complete-<date>.md` | `docs/handoffs/f3-complete-20260618.md` |

---

## Rework Loop Rules

| Failure location | Severity | Action |
|:-----------------|:---------|:-------|
| Phase 3 (Arch Review) | Minor | Back to Phase 2 (Ops) — specific fix instructions |
| Phase 3 (Arch Review) | Major | Back to Phase 2 (Ops) — scope change notice |
| Phase 3 (Arch Review) | Critical | STOP. Escalate to Dr.solodev |
| Phase 4 (CEO QA) | Minor | Back to Phase 2 (Ops) |
| Phase 4 (CEO QA) | Major | Back to Phase 0.5 (Arch) for redesign |
| Phase 5 (Dr.solodev) | Any | Back to phase designated by Dr.solodev |

---

## Hotfix Path (Urgent Fixes)

For production-critical fixes only:

1. **Skip Phase 0 + 0.5** — no research or blueprint needed
2. **เทอโบ (CEO)** writes minimal scope directly
3. **พี่ทรงศักดิ์ (Ops)** implements with extra caution
4. **เทอโบ (CEO)** does QA directly (skip Architect review to save time)
5. **Dr.solodev** emergency sign-off

Hotfix expires after 24 hours — must go through full pipeline for permanent inclusion.

---

## Escalation Path

```
พี่ทรงศักดิ์ (Ops) — finds blocker
  ↓ can't resolve
คุณวุฒิ (Architect) — design guidance
  ↓ can't resolve
เทอโบ (CEO) — strategic decision
  ↓ can't resolve
Dr.solodev — final authority
```

---

## Origin

This pipeline was defined by Dr.solodev on 18 June 2026 for SoloCorp OS 2.0 Co., Ltd. development. It was refined from the earlier wipse pipeline that had the same role chain (Wutti→Therbo→Pee Thangsak→Wutti→Therbo→Dr.solodev) and was first applied during the Research Round 2 → Blueprint Creation cycle.

Key lesson from first application: Parallel delegation works well for research and design phases. The bottleneck is always **human review** (Phase 3-5) — optimize for clear handoff cards, not faster subagents.
