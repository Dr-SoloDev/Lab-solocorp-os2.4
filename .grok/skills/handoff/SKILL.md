---
name: handoff
description: >
  Create a structured SoloCorp department handoff. Use when the user runs /handoff,
  transfers work between departments, or needs a Head-to-Head handoff record.
argument-hint: "<from-dept> <to-dept> <task>"
user-invocable: true
---

# SoloCorp `/handoff`

Create a Control-Layer handoff between departments.

## Parse arguments

Expect: `/handoff <from> <to> <task...>`

- `from` / `to`: department id or head name (e.g. `engineering`, `qa`, `architect`, `ceo`)
- `task`: remaining text

If incomplete, ask for missing fields once.

## Steps

1. Resolve department ids using `profiles/INDEX.md` and `AGENTS.md` routing table.
2. Read both departments' SOUL (or head profile) enough to name owners correctly.
3. Build the handoff record:

```markdown
## Handoff
- **id:** handoff-<YYYYMMDD>-<short-slug>
- **from:** <dept> / <head name>
- **to:** <dept> / <head name>
- **task:** ...
- **context:** why this moves, what is done, what is blocked
- **artifacts:** paths, PRs, bus project ids
- **acceptance criteria:** ...
- **priority:** high | normal | low
- **requested_by:** Owner or current Head
- **timestamp:** ISO-8601
```

4. If the user wants persistence, write to:

```
bus/projects/<project-slug>/artifacts/handoff-<id>.txt
```

Create directories only if needed. Prefer an existing project under `bus/projects/` when obvious.

5. Tell the receiving Head (role-play or spawn matching agent) the next action in 1–3 bullets.

## Rules

- Specialists do not hand off across departments — Heads do.
- Keep Control Layer thin: status, goals, exceptions, approvals — not full code dumps (link paths instead).
- Thai primary.
