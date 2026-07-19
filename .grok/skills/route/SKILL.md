---
name: route
description: >
  Classify a user request into SoloCorp departments and recommend Grok agents.
  Use when the user runs /route, asks which department owns work, or needs
  routing before pipeline execution.
argument-hint: "<request text>"
user-invocable: true
---

# SoloCorp `/route`

Map a request to departments, Heads, and Grok agent types.

## Input

`$ARGUMENTS` = request text. If empty, use the latest user goal from the conversation.

## Steps

1. Read routing table from `AGENTS.md` (and `CLAUDE.md` if needed).
2. Identify primary department and any secondary departments.
3. Recommend:

- Parent role (usually Orchestrator or CEO for multi-dept)
- `subagent_type` values from `.grok/agents/`
- Profile paths to read (`profiles/.../SOUL.md`)

4. If the request is pure coding inside this repo with no org ceremony, say so and recommend Engineering-only path (skip full `/pipeline`).

## Output format

```markdown
# Route

| Field | Value |
|-------|-------|
| Primary dept | ... |
| Head | ... |
| Grok agent | ... |
| Secondary | ... |
| Suggested skill | /pipeline or /handoff or direct implement |

## Why
- ...

## Next command
- Suggested: ...
```

## Rules

- Prefer one primary owner; list secondaries only if real cross-deps.
- Thai primary.
