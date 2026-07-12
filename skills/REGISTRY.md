# SoloCorp OS — Skills Registry

> Single source of truth for all skills. Every platform config must reference or be generated from this registry.

**Version:** 1.1 | **Updated:** 2026-07-12

---

## What Is a Skill?

A **skill** is a named, reusable prompt template that triggers a structured workflow.
Skills are not agents — they are instructions an agent executes.
Think of them as "slash commands with memory."

---

## Invocation by Platform

| Platform | Syntax | Resolution Path |
|:---------|:-------|:----------------|
| OpenCode | `/skill-name` or agent system prompt ref | `.opencode/skills/` |
| Claude Code | `/skill-name` (if registered) or prompt ref | `.claude/commands/` or `skills/` |
| Codex CLI | `!skill skill-name` or inline prompt | `.codex/skills/` (proposed) |
| Hermes | Embedded in profile system prompt at deploy | `~/.hermes/profiles/` |
| "r" | TBD | TBD |

---

## Skill Registry

| ID | Category | File | Platforms | Status |
|:---|:---------|:-----|:----------|:------:|
| `pipeline-auditor` | architect | `team-architect/01-pipeline-auditor.md` | opencode | Active |
| `routing-config` | architect | `team-architect/02-routing-config-agent.md` | opencode | Active |
| `monitor-watchdog` | architect | `team-architect/03-monitor-watchdog.md` | opencode | Active |
| `exception-triage` | architect | `team-architect/04-exception-triage-agent.md` | opencode | Active |
| `cron-pipeline` | architect | `team-architect/05-cron-pipeline-agent.md` | opencode | Active |
| `dispatching-parallel-agents` | superpowers | `superpowers/dispatching-parallel-agents.md` | all | Active |
| `ui-animation-review` | ui-designer | `.opencode/skills/ui-animation-review/SKILL.md` | opencode | Active |
| `eng-deploy` | engineering | _(proposed)_ | all | Planned |
| `cfo-budget-check` | cfo | _(proposed)_ | all | Planned |
| `qa-smoke-test` | qa | _(proposed)_ | all | Planned |
| `gov-adr-new` | governance | _(proposed)_ | all | Planned |
| `gov-rfc-new` | governance | _(proposed)_ | all | Planned |
| `pipeline-full-cycle` | pipeline | _(proposed)_ | all | Planned |

---

> **Note:** This registry is actively growing as new skills are authored and refined. The "93 skills" figure referenced in the project README is an aspirational target — not a count of currently registered skills. New skills are added as workflows are formalized and tested.

---

## Skill File Format

```markdown
---
id: <skill-id>
version: 1.0
category: <architect|engineering|cfo|qa|governance|pipeline>
platforms: [opencode, claude-code, codex, hermes]
trigger: "<keyword that auto-activates>"
agent: <preferred-agent-name>
---

# Skill: <Name>

## Purpose
One sentence: what this skill does.

## Inputs
| Field | Required | Description |
|:------|:--------:|:------------|
| scope | Yes | ... |

## Steps
1. ...

## Output Format
What the user gets back.
```

---

## Adding a New Skill — Checklist

```
[ ] Create skill file in skills/<category>/<nn>-<id>.md
[ ] Add required frontmatter (id, version, category, platforms)
[ ] Add entry to this REGISTRY.md
[ ] Register in opencode.json commands (OpenCode)
[ ] Create .claude/commands/<id>.md (Claude Code)
[ ] Re-run export-codex-agents.py (Codex CLI)
[ ] Embed in relevant Hermes profile during next /deploy
[ ] Update docs/PLATFORM-COMPAT.md
```

---

*SoloCorp OS — System First, Everything Follows*
