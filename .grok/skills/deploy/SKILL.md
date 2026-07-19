---
name: deploy
description: >
  Deploy or export SoloCorp profiles and validate packaging for agent platforms.
  Use when the user runs /deploy, wants Codex export, profile packaging, or
  platform sync checks.
argument-hint: "[target]"
user-invocable: true
---

# SoloCorp `/deploy`

Package/export SoloCorp profiles and validate platform packs.

## Targets

`$ARGUMENTS` may be:

- empty or `all` — validate + export common targets
- `codex` — run Codex export script
- `profiles` — rebuild/check profiles only
- `grok` — verify Grok pack (`.grok/`, `AGENTS.md`)
- `check` — dry validation only

## Steps

1. Confirm repo root and venv/`PYTHONPATH=.`.

2. **Grok pack check**

- Ensure `AGENTS.md`, `.grok/skills/*/SKILL.md`, `.grok/agents/*.md` exist.
- List skills and agents found.

3. **Codex export** (if target is `all` or `codex`)

```bash
python3 scripts/export-codex-agents.py
```

Report output path under `dist/codex/` if successful.

4. **Profile index**

- Skim `profiles/INDEX.md` for Active departments.
- Note any missing SOUL.md for Active rows if discovered.

5. **Optional profile build**

```bash
python3 scripts/build-profiles.py
```

Only if script exists and target needs it.

## Output format

```markdown
# Deploy Report

| Target | Result | Notes |
|--------|--------|-------|
| grok pack | ok/fail | ... |
| codex export | ok/skip/fail | ... |
| profiles | ok | count |

## Next steps
- ...
```

## Rules

- Do not push remote or publish packages unless the user explicitly asks.
- Prefer reporting drift over silently overwriting user edits.
