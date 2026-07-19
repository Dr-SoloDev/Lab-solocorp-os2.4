---
name: pipeline
description: >
  Run SoloCorp full-cycle pipeline for a feature. Use when the user runs /pipeline,
  asks for a full department cycle, or wants orchestrated multi-dept delivery
  (route → plan → implement → QA → status).
argument-hint: "<feature-name-or-description>"
user-invocable: true
---

# SoloCorp `/pipeline` — Full Cycle

Simulate the SoloCorp organization pipeline for the given feature/request.

## Inputs

- `$ARGUMENTS` or the rest of the user message = feature name / description
- If empty, ask once for the feature description

## Preconditions

1. Confirm cwd is the SoloCorp repo root (has `central_bus/`, `profiles/`, `AGENTS.md`).
2. Prefer `source .venv/bin/activate` and `export PYTHONPATH=.` for any Python commands.

## Steps

### 1. Classify & plan (Orchestrator)

- Map the feature to departments using the routing table in `AGENTS.md`.
- Produce a short plan:

```markdown
## Pipeline Plan: <feature>
- Owner (Head): ...
- Departments: ...
- Critical files: ...
- Risks: ...
```

- Read `profiles/04-orchestrator/SOUL.md` if multi-dept.

### 2. Product / Architect gate (as needed)

- If new API/surface area: read relevant `docs/prds/` or spawn `product-produck` / `architect-songsak`.
- If Central Bus involved: inspect `central_bus/` and `bus/system/routing_rules.json`.

### 3. Engineering implementation

- Spawn or act as `engineering-changful` for code changes.
- Prefer smallest viable change; follow existing patterns.
- Run scoped tests: `pytest tests/ central_bus/tests/ -q` (or more specific paths).

### 4. QA evidence

- Spawn or act as `qa`.
- Record: commands run, pass/fail, residual risks.

### 5. Status snapshot

- Follow the `/status` skill checklist (bus health if up, gov counts, queue offsets).
- Optionally write a handoff note under `bus/projects/<slug>/` if the user wants persistence.

## Output format

```markdown
# Pipeline Result: <feature>

## Routing
- Departments: ...
- Primary owner: ...

## Work done
- ...

## Tests / evidence
- ...

## Handoffs
| From | To | Task | Status |
|------|----|------|--------|

## Open blockers
- ...

## Next actions for Owner
- ...
```

## Rules

- Heads lead; do not skip Engineering → QA for code changes.
- Do not claim bus is healthy without a real health check if you started it.
- Language: Thai primary, technical terms English.
