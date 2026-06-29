# Workflow Registry + Sequential Agent Pipeline Pattern

> For constrained-hardware agent armies — one agent at a time, no resource contention.

## Concept: Assembly Line, Not Swarm

Instead of running agents in parallel (Swarm), route work sequentially through specialist agents via profiles:

```
CEO (เทอโบ)  ──แตกงาน──→  Specialist A  ──→  Specialist B  ──→  Orchestrator  ──→  CEO รีวิว
```

Each step uses `hermes --profile <name> -z "..."` with the previous step's output as context. Only one profile runs at a time. RAM stays at ~200-400 MB — no multiplication.

## The Workflow Registry Pattern

Dr.solodev's POS project uses a REGISTRY.md + per-workflow spec pattern. Each workflow document has:

### Workflow Spec Structure (template)

```markdown
# WORKFLOW: [Name] (WF-[ID])
**Version**: 0.1
**Date**: YYYY-MM-DD
**Author**: Workflow Architect
**Status**: Draft
**Priority**: 🚨 CRITICAL / 🔴 High / 🟡 Medium / 🟢 Low

---

## Overview
เหตุผลของ workflow นี้ connected to project reality

## Verified Findings
| # | Finding | Severity | Evidence |
|---|---------|----------|----------|

## Actors
| Actor | บทบาทใน workflow นี้ |
|-------|---------------------|
| [Role Name] | [responsibility] |

แต่ละ Actor แทน agent profile หรือ human role

## Target End-State (Definition of Done)
1. ข้อที่ต้องสำเร็จ (เรียงลำดับ)
2. มี verification ที่ measurable

## Workflow Tree (Steps)
### STEP N: [Step Name]
**Actor**: [responsible agent/role]
**Action**: [what to do]
**Output SUCCESS**: observable → GO STEP N+1
**Output FAILURE**: [failure mode] → [action]
**Handoff**: สิ่งที่ส่งต่อให้ step ถัดไป

## Handoff Contracts
### [Sender] → [Receiver]
**ส่งมอบ**: [เอกสาร/ข้อมูล]
**คาดหวังกลับ**: [expected output]

## Verification / Test Cases
| Test | Trigger | Expected |
|------|---------|----------|

## Cleanup Inventory
| สิ่งที่สร้าง/แก้ | สร้างที่ step | rollback |

## Open Questions
- [คำถามที่ยังไม่มีคำตอบ]
```

### Registry Structure (REGISTRY.md)

```markdown
# 🗺️ Workflow Registry — [Project Name]

## View 1 — By Workflow
| ID | Workflow | Spec file | Status | Trigger | Actor หลัก | Goal |

## View 2 — By Component (โค้ด → workflows)
| Component | ไฟล์ | เกี่ยวกับ workflow ไหน |

## View 3 — By User Journey
| สิ่งที่ทำ | workflow เบื้องหลัง | จุดเข้า |

## View 4 — By State
| State | เข้าโดย | ออกโดย | workflow ที่เกี่ยวข้อง |

## ลำดับการเดินงาน (Execution Order)
WF-00 → WF-01 → WF-02 → ...
```

## How to Run a Sequential Pipeline (Hermes implementation)

```bash
# Step 1: CEO breaks down the task
ceo -q "แตกงาน ${TASK}"

# Step 2: Architect designs solution
hermes --profile architect -z "Context from CEO: ${CEO_OUTPUT}"

# Step 3: CFO evaluates cost
hermes --profile cfo -z "Context from Architect: ${ARCHITECT_OUTPUT}"

# Step 4: Orchestrator synthesizes
hermes --profile orchestrator -z "Context from CFO: ${CFO_OUTPUT}"

# Step 5: CEO reviews + presents
ceo -q "Review outputs: ${ORCHESTRATOR_OUTPUT}"
```

Or use `delegate_task` for programmatic chaining when all agents use the same profile/session.

## Key Principles

1. **Single-threaded execution** — one agent runs, others are dormant profiles
2. **Context carry-forward** — each step gets the previous step's output as input
3. **Clear handoff format** — output must be parseable as next step's input
4. **Fail-stop** — if a step fails, pipeline halts; no cascading errors
5. **No shared mutable state** — agents communicate via passed context, not side effects
