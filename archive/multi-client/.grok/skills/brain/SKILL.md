---
name: brain
description: >
  Save SoloCorp session context to durable notes. Use when the user runs /brain,
  asks to remember session context, or wants to persist decisions for later sessions.
argument-hint: "<context to remember>"
user-invocable: true
---

# SoloCorp `/brain`

Persist session context for continuity across Grok sessions.

## Input

- `$ARGUMENTS` = free-form context (required). If empty, summarize the current conversation’s key decisions and ask confirmation before writing.

## Steps

1. Choose project slug:

- Prefer active project under `bus/projects/` if the conversation already targets one.
- Else use `Lab-solocorp-os2.4` or create `bus/projects/grok-brain/artifacts/`.

2. Write a note file:

```
bus/projects/<slug>/artifacts/brain-<YYYYMMDD-HHMMSS>.txt
```

Content template:

```text
# Brain note
timestamp: <ISO-8601>
source: grok-cli
session: <short summary of topic>

## Context
<user-provided context>

## Decisions
- ...

## Open threads
- ...

## Pointers
- files: ...
- commands: ...
```

3. Confirm path written and give a one-line recall summary.

## Rules

- Do not store secrets, API keys, or credentials.
- Keep notes concise; link paths instead of pasting large code.
- Thai primary OK in note body.
