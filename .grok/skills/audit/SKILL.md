---
name: audit
description: >
  Inspect SoloCorp audit trails and governance compliance. Use when the user runs
  /audit, asks for audit trail, guard events, compliance, or pipeline evidence.
argument-hint: "[scope]"
user-invocable: true
---

# SoloCorp `/audit`

Inspect audit / governance evidence for a scope.

## Scope

`$ARGUMENTS` may be:

- empty → repo-wide light audit
- project id / name under `bus/projects/`
- `gov` → ADR/RFC/Guard validation
- `bus` → queue + governance events
- path glob

## Steps

1. **Governance validation**

```bash
export PYTHONPATH=.
python -m govctl_cli validate adr 2>/dev/null || true
python -m govctl_cli status 2>/dev/null || true
```

2. **Guard / bus events**

- Scan `bus/governance/*/guard_events.jsonl` (tail recent lines for scope).
- Scan `bus/projects/<scope>/` for audit JSONL / artifacts.

3. **Code / test evidence** (if scope is a code area)

- Prefer `pytest <paths> -q` with narrow paths.
- Summarize pass/fail.

4. **Architect lens**

- If deep pipeline audit, read `skills/team-architect/01-pipeline-auditor.md` or spawn `architect-songsak`.

## Output format

```markdown
# Audit Report — <scope>

## Summary
- Verdict: pass | warn | fail
- Findings: N

## Findings
| Severity | Area | Evidence | Recommendation |
|----------|------|----------|----------------|

## Evidence paths
- ...
```

## Rules

- Cite concrete paths and line/event samples.
- Do not invent audit entries.
- Thai primary.
