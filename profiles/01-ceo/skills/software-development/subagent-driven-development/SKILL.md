---
name: subagent-driven-development
description: "Execute plans via delegate_task subagents (2-stage review)."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, subagent, implementation, workflow, parallel]
    related_skills: [writing-plans, requesting-code-review, test-driven-development]
---

# Subagent-Driven Development

## Overview

Execute implementation plans by dispatching fresh subagents per task with systematic two-stage review.

Supports two modes:
- **Sequential mode** (default): One task at a time, implementer + 2 reviewers per task. Best for dependent tasks.
- **Parallel batch mode**: Group independent tasks into batches, dispatch simultaneously. Best for independent multi-file outputs.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) + integration validation + report = high quality, self-documenting delivery.

### Extended Lifecycle

The full feature lifecycle extends beyond just implementation. In practice, features pass through these phases:

1. **Phase 0: Research & Data Collection** — gather information from multiple sources (configs, repos, docs, APIs) using parallel delegate_task
2. **Phase 0.5: Blueprint / Design** — create comprehensive blueprints using parallel delegate_task (architecture, data models, flows, edge cases)
3. **Phase 1: Scope Breakdown** — review big picture, break into focused, distraction-free task scopes
4. **Phase 2: Implementation** — execute tasks per plan (the core process this skill documents)
5. **Phase 3: Review & Summary** — spec compliance + quality review of all implemented work
6. **Phase 4: Final QA** — integration check, cross-reference, functional test
7. **Phase 5: Sign-off** — human approval of complete deliverable

The full lifecycle is governed by a **development pipeline** where different roles handle different phases. See `references/dev-pipeline.md` for a concrete example.

## When to Use

Use this skill when:
- You have an implementation plan (from writing-plans skill or user requirements)
- Tasks are mostly independent
- Quality and spec compliance are important
- You want automated review between tasks

**Choose sequential mode when:**
- Tasks share files (writing to the same file from different tasks = conflict)
- Tasks have ordering dependencies (B needs A's output)
- You want the tightest per-task quality control (implementer + 2 reviewers per task)

**Choose parallel batch mode when:**
- Tasks touch different files entirely (independent outputs)
- Tasks create new files (don't modify shared files)
- Tasks are in different directories / modules
- You want faster time-to-completion (batches complete concurrently)
- You can do integration validation after all batches (covers cross-task consistency)

**vs. manual execution:**
- Fresh context per task (no confusion from accumulated state)
- Automated review process catches issues early
- Consistent quality checks across all tasks
- Subagents can ask questions before starting work

---

## Phase 0: Research & Data Collection (Pre-Plan)

Use this phase when you need to **gather information** before you can write a plan. Common scenarios:
- Understanding the current state of a system you haven't inspected
- Evaluating an external tool, library, or API
- Comparing multiple approaches before choosing one
- Collecting configs, logs, or metrics from a running system

### Technique: Parallel Data Gathering

Spawn 3-4 subagents simultaneously, each collecting a different data stream:

```python
results = delegate_task(tasks=[
    {
        "goal": "Collect [dataset A]",
        "context": "What to look for, where to find it, specific commands",
        "toolsets": ["terminal", "file"]
    },
    {
        "goal": "Collect [dataset B]",
        "context": "URL, what to extract, specific queries",
        "toolsets": ["web", "browser"]
    },
    {
        "goal": "Collect [dataset C]",
        "context": "File paths, what to read, sections needed",
        "toolsets": ["file"]
    }
])
```

**Research subagent context MUST include:**
- **Exact commands** to run (file paths, search patterns, URLs)
- **Output format** expectation (structured report preferred)
- **Deadline awareness** (set reasonable timeout — research can be slow via web/browser)
- **Question to answer** (not just "collect data" but "what does this data tell us?")

### When to Use Parallel vs Sequential Research

| Scenario | Parallel | Sequential |
|:---------|:--------:|:----------:|
| Independent data sources (configs, repos, docs) | ✅ | ❌ |
| One source depends on another (need A before B) | ❌ | ✅ |
| Need to compare/contrast across sources | ✅ (then synthesize) | ⚠️ |
| Time-sensitive (user waiting) | ✅ | ❌ |
| Deep analysis of a single source | ❌ | ✅ |

### After Data Collection: Synthesis

Always synthesize parallel research results into a **single structured report**:

1. **Read all subagent summaries** carefully
2. **Cross-reference** — does dataset A contradict dataset B?
3. **Identify gaps** — what's still unknown?
4. **Document Key Findings** with before/after or assumption/reality table
5. **Save** the synthesis as a project document (e.g. `docs/research-round2.md`)
6. **Update todo** — mark research tasks complete

**⚠️ Warning:** Subagent self-reports may be inaccurate or incomplete. Always verify critical findings yourself (read the config file, check the URL, run the command) before building conclusions on them.

---

## Phase 0.5: Design / Blueprint Creation

Use this phase when research is complete and you need to **translate findings into actionable designs**. One research round may produce requirements for multiple features — design each one in parallel.

### Technique: Parallel Blueprint Authoring

Spawn one subagent per feature, each producing a self-contained blueprint:

```python
results = delegate_task(tasks=[
    {
        "goal": "Design Feature X — complete blueprint with architecture, data models, flows",
        "context": """
        RESEARCH FINDINGS: [key context this feature needs]
        CONSTRAINTS: [technical limits, no-fork policy, stack]
        LOCATION: Create blueprint at experiments/feature-x/blueprint.md
        FORMAT: Executive summary, layer architecture, flows, edge cases, effort
        """,
        "toolsets": ["file", "terminal"]
    },
    {
        "goal": "Design Feature Y — complete blueprint",
        "context": "...similar structure..."
    }
])
```

**Each blueprint MUST include:**
1. **Executive Summary** — problem, goal, success criteria, constraints
2. **Architecture / Design** — layers, components, data flow (text diagram)
3. **Data Model** — schema, structure, file format
4. **Flows** — key workflows step by step
5. **Edge Cases & Mitigations** — what can go wrong, how to handle it
6. **Effort Estimate** — person-days per phase
7. **Implementation Roadmap** — ordered milestones

**After all blueprints are complete:**
1. **Collect summaries** from each blueprint subagent
2. **Verify consistency** — do blueprints conflict? Any dependency chain?
3. **Present overview** to the user (or next role in pipeline) with file locations
4. **Proceed to Phase 1: Scope Breakdown** — the pipeline owner reviews and decomposes

### Pipeline: Full-Lifecycle Role Handoff

For projects with defined roles, the full handoff after Phase 0.5 looks like:

```
[คุณวุฒิ — Architect]
  Phase 0: Research & Data ✅
  Phase 0.5: Blueprints Created ✅
     ↓ handoff blueprints
[เทอโบ — CEO]
  Phase 1: Big Picture Review + Scope Breakdown
     ↓ handoff scoped tasks
[พี่ทรงศักดิ์ — Ops]
  Phase 2: Implementation
     ↓ handoff completed work
[คุณวุฒิ — Architect]
  Phase 3: Review & Summary
     ↓ handoff review results
[เทอโบ — CEO]
  Phase 4: Final QA
     ↓ handoff verified work
[Dr.solodev]
  Phase 5: Sign-off
```

See `references/dev-pipeline.md` for the formal pipeline definition with RACI matrix, handoff card format, and quality gates.

---

## The Process

### 1. Read and Parse Plan

Read the plan file. Extract ALL tasks with their full text and context upfront. Create a todo list:

```python
# Read the plan
read_file("docs/plans/feature-plan.md")

# Create todo list with all tasks
todo([
    {"id": "task-1", "content": "Create User model with email field", "status": "pending"},
    {"id": "task-2", "content": "Add password hashing utility", "status": "pending"},
    {"id": "task-3", "content": "Create login endpoint", "status": "pending"},
])
```

**Key:** Read the plan ONCE. Extract everything. Don't make subagents read the plan file — provide the full task text directly in context.

### 2. Per-Task Workflow

For EACH task in the plan:

#### Step 1: Dispatch Implementer Subagent

Use `delegate_task` with complete context:

```python
delegate_task(
    goal="Implement Task 1: Create User model with email and password_hash fields",
    context="""
    TASK FROM PLAN:
    - Create: src/models/user.py
    - Add User class with email (str) and password_hash (str) fields
    - Use bcrypt for password hashing
    - Include __repr__ for debugging

    FOLLOW TDD:
    1. Write failing test in tests/models/test_user.py
    2. Run: pytest tests/models/test_user.py -v (verify FAIL)
    3. Write minimal implementation
    4. Run: pytest tests/models/test_user.py -v (verify PASS)
    5. Run: pytest tests/ -q (verify no regressions)
    6. Commit: git add -A && git commit -m "feat: add User model with password hashing"

    PROJECT CONTEXT:
    - Python 3.11, Flask app in src/app.py
    - Existing models in src/models/
    - Tests use pytest, run from project root
    - bcrypt already in requirements.txt
    """,
    toolsets=['terminal', 'file']
)
```

#### Step 2: Dispatch Spec Compliance Reviewer

After the implementer completes, verify against the original spec:

```python
delegate_task(
    goal="Review if implementation matches the spec from the plan",
    context="""
    ORIGINAL TASK SPEC:
    - Create src/models/user.py with User class
    - Fields: email (str), password_hash (str)
    - Use bcrypt for password hashing
    - Include __repr__

    CHECK:
    - [ ] All requirements from spec implemented?
    - [ ] File paths match spec?
    - [ ] Function signatures match spec?
    - [ ] Behavior matches expected?
    - [ ] Nothing extra added (no scope creep)?

    OUTPUT: PASS or list of specific spec gaps to fix.
    """,
    toolsets=['file']
)
```

**If spec issues found:** Fix gaps, then re-run spec review. Continue only when spec-compliant.

#### Step 3: Dispatch Code Quality Reviewer

After spec compliance passes:

```python
delegate_task(
    goal="Review code quality for Task 1 implementation",
    context="""
    FILES TO REVIEW:
    - src/models/user.py
    - tests/models/test_user.py

    CHECK:
    - [ ] Follows project conventions and style?
    - [ ] Proper error handling?
    - [ ] Clear variable/function names?
    - [ ] Adequate test coverage?
    - [ ] No obvious bugs or missed edge cases?
    - [ ] No security issues?

    OUTPUT FORMAT:
    - Critical Issues: [must fix before proceeding]
    - Important Issues: [should fix]
    - Minor Issues: [optional]
    - Verdict: APPROVED or REQUEST_CHANGES
    """,
    toolsets=['file']
)
```

**If quality issues found:** Fix issues, re-review. Continue only when approved.

#### Step 4: Mark Complete

```python
todo([{"id": "task-1", "content": "Create User model with email field", "status": "completed"}], merge=True)
```

### 3. Parallel Batch Execution (alternative mode)

For plans with independent tasks, batch them into parallel `delegate_task` calls:

```python
# Batch 1: All independent file-creation tasks (run simultaneously)
results = delegate_task(tasks=[
    {
        "goal": "Create User model with email field",
        "context": "TASK: Create src/models/user.py ...",
        "toolsets": ["terminal", "file"]
    },
    {
        "goal": "Create password hashing utility",
        "context": "TASK: Create src/utils/hash.py ...",
        "toolsets": ["terminal", "file"]
    },
    {
        "goal": "Add JWT helpers",
        "context": "TASK: Create src/utils/jwt.py ...",
        "toolsets": ["terminal", "file"]
    }
])
```

**Parallel batch rules:**
- Max 3 concurrent subagents per user (configurable via delegation.max_concurrent_children)
- Each subagent gets **its own context** — provide full task text, constraints, file paths
- Subagents **cannot** see each other's output — design tasks to be standalone
- If tasks touch the same file → use sequential mode (conflict prevention)
- After all batches complete → run Post-Execution Validation

**3-batch pattern** (from Sprint 1 SoloCorp OS 2.0):

```
Batch 1 (3 parallel): routing.yaml + AAR Protocol + AgentCard schema
  ↓ wait all complete
Batch 2 (1 task): Pipeline Trace script + docs
  ↓ wait all complete  
Post-Execution Validation: cross-reference check, YAML lint, functional test
Report: comprehensive summary with architecture diagram
```

**Multi-Track Parallel Execution (Large Tasks):**

For building complete feature modules in parallel (entire pages, full API layers, PWA shell). Each track = one domain, 1-5 files, 400-1,400+ lines. See `references/multi-track-execution.md` for:
- Track decomposition template
- Context building checklist
- Cross-track integration validation (essential after multi-track runs)
- Checkpoint / commit pattern

**When to batch vs sequential:**
| Factor | Sequential | Parallel Batch |
|--------|:----------:|:--------------:|
| Task count | Any | 2-3+ independent |
| Shared files | ✅ Safe | ❌ Conflicts |
| Quality per task | ✅ 2 reviews each | ⚠️ Self-report only |
| Total time | Sum of tasks | ~Longest task |
| Integration risk | Low | Higher (validate after) |

**You MUST run Post-Execution Validation after parallel batches — the subagents self-report and may miss cross-task inconsistencies.**

### 4. Post-Execution Validation

After ALL tasks complete (sequential or parallel), do NOT declare done yet. Run integration validation:

```python
# Multi-check validation script
# Check 1: All files exist
for f in expected_files:
    assert os.path.exists(f), f"MISSING: {f}"

# Check 2: All generated YAML/JSON valid
# (run tool-specific lint)

# Check 3: Cross-references between files
# Do references in file A point to real paths in file B?

# Check 4: Functional test (if applicable)
# Run the script/app and verify it produces correct output

# Check 5: Count routes, entities, match plan spec
```

**Validation checklist template:**
- [ ] All target files from plan actually created?
- [ ] All generated files parse/lint correctly?
- [ ] Cross-references between files resolve (A refers to B, B exists)?
- [ ] Functional test passes (if applicable)?
- [ ] Count/length matches plan spec (e.g. "22 routes" = 22)?
- [ ] No orphan/incomplete artifacts?

**When validation fails:** Fix the failing items by dispatching a fix subagent, then re-validate. Do not proceed to reporting until validation passes.

### 5. Report Generation

After validation passes, generate a comprehensive report:

```python
# Report structure
report = f"""
# 🏁 [Project/Sprint] — Complete

**Time:** ~{estimated_hours}h
**Status:** ✅ ALL TASKS DONE

## Summary

| Task | Files | Status |
|:-----|:------|:------:|
| Task 1 | file1, file2 | ✅ |
| Task 2 | file3 | ✅ |

## Architecture (After)

[ASCII/schematic diagram showing how new files connect]

## Validation Results

| Check | Result |
|:------|:------:|
| All {N} files exist | ✅ |
| Lint/parse | ✅ |
| Cross-references | N/N ✅ |

## Next Steps

[Concrete suggestions for what comes next]
"""
```

**Save the report** as a markdown file in the project (e.g. `docs/sprint-complete-report.md`) and present key results to the user.

**Report always includes:**
1. ✅ Summary table (task → files → status)
2. 🏗️ Architecture diagram or file structure
3. ✅ Validation results
4. 🔮 Recommended next steps

### 6. Sequential Final Review & Verify

After ALL tasks are complete, dispatch a final integration reviewer:

```python
delegate_task(
    goal="Review the entire implementation for consistency and integration issues",
    context="""...""",
    toolsets=['terminal', 'file']
)
```
**Alternative (parallel batch mode):** Run **Post-Execution Validation** (section 4) instead of a single review subagent. Validation checks are automated and cover all tasks simultaneously — more thorough than a single subagent can manage for multi-file, multi-module output.

### 7. Verify and Commit

```bash
# Run full test suite
pytest tests/ -q

# Review all changes
git diff --stat

# Final commit if needed
git add -A && git commit -m "feat: complete [feature name] implementation"
```

## Task Granularity

**Each task = 2-5 minutes of focused work.**

**Too big:**
- "Implement user authentication system"

**Right size:**
- "Create User model with email and password fields"
- "Add password hashing function"
- "Create login endpoint"
- "Add JWT token generation"
- "Create registration endpoint"

## Red Flags — Never Do These

- Start implementation without a plan
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed critical/important issues
- Dispatch multiple implementation subagents for tasks that touch the same files
- Make subagent read the plan file (provide full text in context instead)
- Skip scene-setting context (subagent needs to understand where the task fits)
- Ignore subagent questions (answer before letting them proceed)
- Accept "close enough" on spec compliance
- Skip review loops (reviewer found issues → implementer fixes → review again)
- Let implementer self-review replace actual review (both are needed)
- **Start code quality review before spec compliance is PASS** (wrong order)
- Move to next task while either review has open issues
- **Skip Post-Execution Validation after parallel batches** (subagents self-report, may miss cross-task inconsistencies)
- **Skip report generation** (report is the record — without it, work is invisible to future sessions)
- **Declare done before integration validation passes** (all checks must pass, not just "seems ok")

## Handling Issues

### If Subagent Asks Questions

- Answer clearly and completely
- Provide additional context if needed
- Don't rush them into implementation

### If Reviewer Finds Issues

- Implementer subagent (or a new one) fixes them
- Reviewer reviews again
- Repeat until approved
- Don't skip the re-review

### If Subagent Fails a Task

- Dispatch a new fix subagent with specific instructions about what went wrong
- Don't try to fix manually in the controller session (context pollution)

## Efficiency Notes

**Why fresh subagent per task:**
- Prevents context pollution from accumulated state
- Each subagent gets clean, focused context
- No confusion from prior tasks' code or reasoning

**Why two-stage review:**
- Spec review catches under/over-building early
- Quality review ensures the implementation is well-built
- Catches issues before they compound across tasks

**Cost trade-off:**
- More subagent invocations (implementer + 2 reviewers per task)
- But catches issues early (cheaper than debugging compounded problems later)

**Parallel batch vs sequential:**
- Sequential = higher per-task quality (each gets 2 reviews) but slower total time
- Parallel = faster (tasks run concurrently) but self-reported quality (no per-task reviewer)
- Use parallel for file-creation tasks (new files only, no shared edits)
- Always run Post-Execution Validation after parallel batches
- The "no 2-stage review per task" in parallel mode is offset by thorough integration validation across all outputs

## Integration with Other Skills

### With writing-plans

This skill EXECUTES plans created by the writing-plans skill:
1. User requirements → writing-plans → implementation plan
2. Implementation plan → subagent-driven-development → working code

### With test-driven-development

Implementer subagents should follow TDD:
1. Write failing test first
2. Implement minimal code
3. Verify test passes
4. Commit

Include TDD instructions in every implementer context.

### With requesting-code-review

The two-stage review process IS the code review. For final integration review, use the requesting-code-review skill's review dimensions.

### With systematic-debugging

If a subagent encounters bugs during implementation:
1. Follow systematic-debugging process
2. Find root cause before fixing
3. Write regression test
4. Resume implementation

## Example Workflow

```
[Read plan: docs/plans/auth-feature.md]
[Create todo list with 5 tasks]

--- Task 1: Create User model ---
[Dispatch implementer subagent]
  Implementer: "Should email be unique?"
  You: "Yes, email must be unique"
  Implementer: Implemented, 3/3 tests passing, committed.

[Dispatch spec reviewer]
  Spec reviewer: ✅ PASS — all requirements met

[Dispatch quality reviewer]
  Quality reviewer: ✅ APPROVED — clean code, good tests

[Mark Task 1 complete]

--- Task 2: Password hashing ---
[Dispatch implementer subagent]
  Implementer: No questions, implemented, 5/5 tests passing.

[Dispatch spec reviewer]
  Spec reviewer: ❌ Missing: password strength validation (spec says "min 8 chars")

[Implementer fixes]
  Implementer: Added validation, 7/7 tests passing.

[Dispatch spec reviewer again]
  Spec reviewer: ✅ PASS

[Dispatch quality reviewer]
  Quality reviewer: Important: Magic number 8, extract to constant
  Implementer: Extracted MIN_PASSWORD_LENGTH constant
  Quality reviewer: ✅ APPROVED

[Mark Task 2 complete]

... (continue for all tasks)

[After all tasks: dispatch final integration reviewer]
[Run full test suite: all passing]

--- Post-Execution Validation ---
[Check all files exist: ✅]
[Cross-reference check: AUTHORS.md → /docs/users.md exists ✅]
[Lint all new files: ✅]
[Functional test: login flow works ✅]

[Done! Generate report]

--- Alternative: Parallel Batch ---
[Plan has 6 independent tasks across 3 modules]
[Batch 1: Task 1 (User model) + Task 2 (JWT) + Task 3 (Email service)]
  → dispatch 3 delegate_task calls simultaneously
  → wait all complete
[Batch 2: Task 4 (Tests) + Task 5 (Docs) + Task 6 (Config)]
  → dispatch 3 more delegate_task calls
  → wait all complete
[Post-Execution Validation: cross-reference all 6 outputs]
[Report: sprint1-complete-report.md]
```

## Remember

```
Plan first
Fresh subagent per task (sequential) OR batch independent tasks (parallel)
Two-stage review every time (sequential) OR Post-Execution Validation (parallel)
Spec compliance FIRST
Code quality SECOND
INTEGRATION validation AFTER all done
REPORT always
Never skip reviews or validation
Catch issues early
```

**Quality is not an accident. It's the result of systematic process.**

## Further reading (load when relevant)

When the orchestration involves significant context usage, long review loops, or complex validation checkpoints, load these references for the specific discipline:

- **`references/context-budget-discipline.md`** — Four-tier context degradation model (PEAK / GOOD / DEGRADING / POOR), read-depth rules that scale with context window size, and early warning signs of silent degradation. Load when a run will clearly consume significant context (multi-phase plans, many subagents, large artifacts).
- **`references/gates-taxonomy.md`** — The four canonical gate types (Pre-flight, Revision, Escalation, Abort) with behavior, recovery, and examples. Load when designing or reviewing any workflow that has validation checkpoints — use the vocabulary explicitly so each gate has defined entry, failure behavior, and resumption rules.
- **`references/integration-validation.md`** — The 5-check integration validation pattern (file existence, syntax lint, cross-reference, functional test, content consistency). Load after any batch-parallel or multi-task execution to catch cross-task gaps that subagent self-reports miss.

- **`references/multi-track-execution.md`** — Multi-Track Parallel Execution pattern for building complete feature modules (400-1,400+ lines per track). Covers track decomposition, context template, cross-track integration validation, and checkpoint pattern. Use when a phase decomposes into independent domains (auth/infra + business logic + pages) and each subagent needs full project context.

- **`references/qa-t3-stack.md`** — Stack-specific QA checklist for Next.js/T3 projects after Phase 1 delivery. Covers TypeScript compile gotchas (React Query version compat, barrel export completeness, type narrowing), auth flow verification, pages structure, env vars, and seed data. Use after any parallel or sequential implementation to catch framework-level issues before CEO demo.

Both references adapted from gsd-build/get-shit-done (MIT © 2025 Lex Christopherson).

**Note:** `integration-validation.md` was derived from Sprint 1 SoloCorp OS 2.0 (18 Jun 2026) and is original to this skill (not from gsd-build).
