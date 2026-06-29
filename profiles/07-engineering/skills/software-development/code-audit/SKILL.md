---
name: code-audit
description: Comprehensive code audit methodology encompassing security, architecture, database, infrastructure, frontend, business logic, and compliance — with structured finding format, severity levels, Quick Wins, and Priority Fix Order. Use when the user requests a code audit, security review, vulnerability assessment, or "audit this codebase". Pairs with delegate_task for deep audit via subagents.
version: 1.0
---

# Code Audit Methodology

## Overview

A structured, multi-dimensional approach to auditing a codebase. Unlike code review (which focuses on PR-level changes), a code audit is a **holistic deep dive** into the entire system — uncovering auth bypasses, architectural debt, data integrity issues, and configuration gaps.

**Core principle:** Systematic coverage across 7 independent dimensions, with every finding classified by severity and packaged with a clear fix recommendation.

---

## When to Use

- User says "audit this codebase", "security audit", "code audit", "review security"
- User asks for "vulnerability assessment" or "penetration test"
- Before a production deployment to catch latent issues
- After major refactoring to verify nothing regressed
- User delegates by asking "who should do this" in an org chart context

---

## 7 Audit Dimensions

Work through each dimension separately. Do not scan randomly.

| # | Dimension | Focus Areas |
|---|-----------|-------------|
1. **Security** | Auth bypass, SQLi, XSS, CSRF, file upload safety, secrets management, rate limiting, CORS, HTTP headers
   - **Function Verification** — For every XSS/sanitization function, don't just check it EXISTS — verify it WORKS. Call it with a test payload and inspect the output. A function can be present but completely broken (e.g. template render bug corrupts replacement strings).
   - **Caller Tracing** — After finding a broken utility, trace ALL callers across the entire codebase. Some files may have their OWN working implementation (bypassing the broken global), while others silently depend on the broken version. Map real impact, not assumed impact.
| 2️⃣ | **Architecture** | Coupling, separation of concern, routing logic, error handling, code duplication, dependency direction |
| 3️⃣ | **Database & Migrations** | Migration ordering/idempotency, indexing, foreign keys, data integrity, duplicate migrations |
| 4️⃣ | **Infrastructure** | Dockerfile safety, Apache/Nginx config, network exposure, health checks, restart policies, secrets in compose |
| 5️⃣ | **Frontend** | DOM-based XSS, token storage (localStorage vs HttpOnly), client-side validation bypass, CSRF |
| 6️⃣ | **Business Logic** | State transition correctness, edge cases, race conditions (TOCTOU), financial calculations (FIFO), audit trail |
| 7️⃣ | **Compliance** | Data privacy (PII storage), identity protocols, logging of critical actions, regulatory requirements (PDPA, GDPR, PCI-DSS) |

---

## Finding Template

Every finding MUST use this template:

| Field | Description |
|-------|-------------|
| **ID** | Area-SXX (e.g. S-01, A-02, DB-03) |
| **Title** | One-line description |
| **Severity** | 🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low |
| **Location** | `file:line` |
| **Description** | What is wrong, why it exists |
| **Impact** | What an attacker or failure can achieve |
| **Recommendation** | Concrete fix with code snippet when possible |

### Severity Definitions

| Severity | Label | Blocks Deploy? | Meaning |
|----------|-------|----------------|---------|
| 🔴 Critical | `[CRITICAL]` | Yes | Auth bypass, data leak, RCE, arbitrary SQL execution |
| 🟠 High | `[HIGH]` | Strongly advised | Missing role checks, XSS vector, brute-force exposure, weak crypto |
| 🟡 Medium | `[MEDIUM]` | No | Race conditions, info disclosure, missing validation |
| 🔵 Low | `[LOW]` | No | Logging gaps, missing headers, cosmetic issues, best-practice deviations |

---

## Subagent Delegation Pattern

For a deep audit, delegate as a structured subagent task:

```python
delegate_task(
    goal="Audit the [project-name] codebase across all 7 dimensions",
    context=f"""
    PROJECT CONTEXT:
    - Stack: [language, framework, database]
    - Repo: [path]
    - Branch: [current branch]
    - Latest commit: [sha]

    FILES OF INTEREST:
    - Config: [paths to key config files]
    - Controllers: [controller directories]
    - Models: [model directories]
    - Frontend JS: [JS directories]
    - Infra: [Dockerfile, compose, nginx/apache conf]

    AUDIT METHODOLOGY (7 DIMENSIONS):
    1. Security  — auth, SQLi, XSS, secrets, file upload
    2. Architecture — coupling, routing, error handling
    3. Database/Migrations — ordering, indexing, integrity
    4. Infrastructure — Docker safety, network exposure
    5. Frontend  — DOM XSS, token storage
    6. Business Logic — state transitions, edge cases
    7. Compliance — PII, logging, identity

    OUTPUT REQUIREMENTS:
    1. Executive Summary (count by severity, risk score)
    2. Findings — each with: ID, Title, Severity, Location, Description, Impact, Recommendation
    3. Quick Wins — 3-5 fixes under 1 hour
    4. Priority Fix Order — ordered list
    5. Files to modify — full list
    6. Compliance Checklist — what's missing
    """,
    toolsets=['terminal', 'file', 'web']
)
```

### Key Tips for Delegation

- **Provide full project context** — stack, directory structure, current commit
- **Point to key files** — don't make the subagent discover the codebase from scratch
- **Specify the exact output format** — template-driven output is easier to report
- **Set toolsets appropriately** — 'terminal' + 'file' for reading code, 'web' only if researching CVEs
- **Use `exit_reason: max_iterations` guard** — audits are open-ended; set a reasonable budget
- **Require verbatim file paths** in findings so fixes can be applied without re-discovery

---

## Report Format

The final audit report should have these sections in order:

### 1. Executive Summary
```md
## Executive Summary

| Severity | Count | Key Impact |
|----------|-------|------------|
| 🔴 Critical | N | Short summary of worst issues |
| 🟠 High | N | ... |
| 🟡 Medium | N | ... |
| 🔵 Low | N | ... |

**Risk Score: XX/100 (High/Medium/Low)**
```

### 2. Findings (grouped by severity)

Each finding follows the template above. Critical findings first, then High, Medium, Low.

### 3. Quick Wins
```md
| # | Issue | Fix | Time |
|---|-------|-----|------|
| 1 | ... | ... | 2 min |
```

### 4. Priority Fix Order
Numbered list ordered by risk reduction per unit of effort.

### 5. Files That Need Modification
| File | Changes Required |
|------|------------------|

### 6. Compliance Checklist
| Requirement | Status | Issue Reference |
|-------------|--------|-----------------|
| ✅ / ❌ / ⚠️ Partial | ... | S-XX |

---

## Integration with Other Skills

### With `code-review`
- `code-review` covers **PR-level change review** (per-diff, per-commit)
- `code-audit` covers **holistic system-level analysis** (entire codebase, all dimensions)
- Run `code-audit` before major deployments; use `code-review` during normal development

### With `subagent-driven-development`
- `subagent-driven-development` focuses on implementing plans via subagents with 2-stage review
- `code-audit` focuses on **analyzing existing code** for issues
- After an audit, use `subagent-driven-development` to dispatch fix subagents

### With `systematic-debugging`
- Use `systematic-debugging` for **root cause analysis** of specific bugs
- Use `code-audit` for **proactive discovery** of latent issues before they become bugs

---

## Pitfalls

1. **Don't scan surface-only** — follow data flow: Input → Controller → Service → Model → DB → Response. A vulnerability at any layer matters.
2. **Don't skip infrastructure** — Dockerfiles, compose files, and Apache/Nginx configs are as critical as application code.
3. **Don't accept "it works" as proof of security** — many issues (missing auth, weak secrets, no rate limiting) don't manifest until exploited.
4. **Don't audit everything equally** — spend most time on the **critical path** (user input → money → data).
5. **Don't let the subagent self-verify** — always review the audit output yourself; subagents have been known to miss issues in their own reports.
6. **Don't trust that a security function works just because it exists** — `escapeHtml()` may be defined but completely broken (template render bug, wrong replacement). Always verify with a test payload. Then trace all callers to map real impact — some files may have their own working implementation, making the broken global function a silent risk only to files that lack their own.

## Reference Files

Two reference files ship with this skill. Load them with `skill_view(name='code-audit', file_path='references/<file>.md')`.

- **`references/audit-example-pos.md`** — Full audit report example from a real PHP+MySQL POS system. Pattern-match findings, severity assignments, and priority ordering for real-world output.
- **`references/audit-reassessment-methodology.md`** — How to verify findings against real code, trace callers for real impact, reassess severity, and build dependency chains between fixes. Essential reading when you inherit an audit report from another agent and need to validate before acting.

## Verification

After applying audit fixes:
1. Run the application and verify each fixed endpoint still works
2. Re-scan the fixed areas with the same methodology
3. Check that no new issues were introduced during fixes
