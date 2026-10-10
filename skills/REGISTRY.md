# SoloCorp OS — Skills Registry

> Single source of truth for all skills. Every platform config must reference or be generated from this registry.

**Version:** 1.3 | **Updated:** 2026-08-26

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
| Grok Build | `/skill-name` (SKILL.md frontmatter) | `.grok/skills/<name>/SKILL.md` |
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
| `pipeline` | pipeline | `.grok/skills/pipeline/SKILL.md` | grok | Active |
| `handoff` | pipeline | `.grok/skills/handoff/SKILL.md` | grok | Active |
| `status` | pipeline | `.grok/skills/status/SKILL.md` | grok | Active |
| `audit` | pipeline | `.grok/skills/audit/SKILL.md` | grok | Active |
| `deploy` | pipeline | `.grok/skills/deploy/SKILL.md` | grok | Active |
| `brain` | pipeline | `.grok/skills/brain/SKILL.md` | grok | Active |
| `route` | pipeline | `.grok/skills/route/SKILL.md` | grok | Active |
| `pipeline-full-cycle` | pipeline | _(alias of grok `pipeline`)_ | grok | Active |
| **`pipeline-bridge`** 🆕 | **cross-dept** | **`@solocorp/cross-dept/pipeline-bridge/`** | **opencode + grok** | **🟢 Active** |
| **`mirror-check`** 🆕 | **cross-dept** | **`@solocorp/cross-dept/mirror-check/`** | **opencode + grok + claude** | **🟢 Active** |
| **`sprint-plan`** 🆕 | **ceo** | **`@solocorp/ceo/sprint-plan/`** | **opencode + grok + claude** | **🟢 Active** |
| **`daily-ops`** 🆕 | **coo** | **`@solocorp/coo/daily-ops/`** | **opencode + grok** | **🟢 Active** |
| **`deploy`** 🆕 | **engineering** | **`@solocorp/engineering/deploy/`** | **opencode + grok** | **🟢 Active** |
| **`budget-check`** 🆕 | **cfo** | **`@solocorp/cfo/budget-check/`** | **opencode + grok** | **🟢 Active** |
| **`smoke-test`** 🆕 | **qa** | **`@solocorp/qa/smoke-test/`** | **opencode + grok + claude** | **🟢 Active** |
| **`rfc`** 🆕 | **governance** | **`@solocorp/governance/rfc/`** | **opencode + grok** | **🟢 Active** |

---

## Hermes Skill Mapping

The `@solocorp/*` OpenCode skills are also converted to Hermes standard format
(`name` = lowercase-hyphen, no slash + one-line `description: "Use when ..."` trigger)
and installed at `~/.hermes/skills/<hermes-name>/SKILL.md`.
Body content is identical across platforms; only frontmatter differs.
Conversion script: `skills/convert_to_hermes.py`.

| OpenCode name | Category | Trigger | Hermes name | Install path |
|:--------------|:---------|:--------|:------------|:-------------|
| `@solocorp/ceo/sprint-plan` | ceo | `/sprint-plan` | `solocorp-ceo-sprint-plan` | `~/.hermes/skills/solocorp-ceo-sprint-plan/SKILL.md` |
| `@solocorp/cfo/budget-check` | cfo | `/budget-check` | `solocorp-cfo-budget-check` | `~/.hermes/skills/solocorp-cfo-budget-check/SKILL.md` |
| `@solocorp/coo/daily-ops` | coo | `/daily-ops` | `solocorp-coo-daily-ops` | `~/.hermes/skills/solocorp-coo-daily-ops/SKILL.md` |
| `@solocorp/cross-dept/mirror-check` | cross-dept | `/mirror-check` | `solocorp-cross-dept-mirror-check` | `~/.hermes/skills/solocorp-cross-dept-mirror-check/SKILL.md` |
| `@solocorp/cross-dept/pipeline-bridge` | cross-dept | `/pipeline-bridge` | `solocorp-cross-dept-pipeline-bridge` | `~/.hermes/skills/solocorp-cross-dept-pipeline-bridge/SKILL.md` |
| `@solocorp/engineering/deploy` | engineering | `/deploy` | `solocorp-engineering-deploy` | `~/.hermes/skills/solocorp-engineering-deploy/SKILL.md` |
| `@solocorp/governance/rfc` | governance | `/rfc-new` | `solocorp-governance-rfc` | `~/.hermes/skills/solocorp-governance-rfc/SKILL.md` |
| `@solocorp/qa/smoke-test` | qa | `/smoke-test` | `solocorp-qa-smoke-test` | `~/.hermes/skills/solocorp-qa-smoke-test/SKILL.md` |

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
