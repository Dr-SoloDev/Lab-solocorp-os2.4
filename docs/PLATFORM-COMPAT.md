# 📱 Platform Compatibility

> SoloCorp OS รองรับ AI Client ไหนบ้าง? — 2026-07-27

## Overview

| Platform | Config Path | Skills | Agents | Status |
|:---------|:------------|:------:|:------:|:------:|
| **OpenCode** | `opencode.json` | ✅ 18 commands | ✅ 4 agents | 🟢 Active |
| **Claude Code** | `.claude/settings.json` | ✅ 6 commands | ❌ (via MCP) | 🟡 Partial |
| **Grok Build** | `.grok/agents/` + `.grok/skills/` | ✅ 7 pipeline | ❌ | 🟡 Partial |
| **Codex CLI** | `.codex/config.toml` + `.codex/agents/` | ❌ | ✅ 86 agents | 🟡 Partial |
| **Hermes** | `dist/hermes/` profiles | ❌ | ✅ 81 profiles | 🟡 Partial |
| **Cursor** | `.cursor/mcp.json` | ❌ | ❌ (via MCP) | 🟢 MCP only |

---

## OpenCode (Primary)

**Config**: `opencode.json`

| Feature | Status | Notes |
|:--------|:------:|:------|
| CEO default agent | ✅ | `default_agent: ceo-turbo` |
| 18 slash commands | ✅ | pipeline, handoff, status, audit, deploy, brain, pipeline-bridge, mirror-check, bootstrap, triage, mirror, orchestrate, summary, sprint-plan, daily-ops, eng-deploy, budget-check, smoke-test, rfc-new |
| Skills paths | ✅ | 7 paths in `skills.paths` incl. `@solocorp/` |
| MCP servers | ✅ | solocorp, github, stealth-browser |
| Profile references | ✅ | 9 reference paths (profiles, docs, decisions, etc.) |
| Auto-bootstrap | ✅ | `/bootstrap` on session start |

## Claude Code

**Config**: `.claude/settings.json`

| Feature | Status | Notes |
|:--------|:------:|:------|
| MCP servers | ✅ | solocorp + stealth-browser |
| Slash commands | ✅ | 6 commands registered |
| `.claude/commands/` | ✅ | 6 `.md` files (sprint-plan, daily-ops, eng-deploy, budget-check, smoke-test, rfc-new) |
| Agent model | ❌ | No native agent system — uses MCP for SoloCorp |
| Claude Code quick start | ❌ | No CLAUDE.md or QUICKSTART.md for Claude Code |

## Grok Build

**Config**: `.grok/skills/` + `AGENTS.md`

| Feature | Status | Notes |
|:--------|:------:|:------|
| Pipeline skills | ✅ | 7 skills (pipeline, handoff, status, audit, deploy, brain, route) |
| Department skills | ❌ | Not yet ported from `@solocorp/*` format |
| Agent profiles | ❌ | `AGENTS.md` defines hierarchy but no per-agent configs |
| MCP | ❌ | No MCP config found for Grok |

## Codex CLI

**Config**: `.codex/config.toml` + `.codex/agents/`

| Feature | Status | Notes |
|:--------|:------:|:------|
| Agent configs | ✅ | 86 agent TOML files |
| Export pipeline | ✅ | `scripts/export-codex-agents.py` — build + validate |
| Slash commands | ❌ | No commands section in `.codex/config.toml` |
| MCP | ❌ | Not yet configured |

## Hermes

**Config**: `dist/hermes/` (81 profiles)

| Feature | Status | Notes |
|:--------|:------:|:------|
| Profiles built | ✅ | `scripts/build-profiles.py` → 3 formats (droid/codex/hermes) |
| Hermes deploy | ❌ | Profiles built but not deployed to Hermes runtime |
| Agent commands | ❌ | No command system in Hermes |

## Cursor

**Config**: `.cursor/mcp.json`

| Feature | Status | Notes |
|:--------|:------:|:------|
| MCP servers | ✅ | solocorp + github |
| Slash commands | ❌ | Cursor uses OpenCode format via `opencode.json` |
| Agent integration | ❌ | Via MCP only |

---

## SkillHub Coverage by Platform

| Skill | OpenCode | Claude Code | Grok | Bus API |
|:-----|:--------:|:-----------:|:----:|:-------:|
| `/pipeline` | ✅ | ❌ | ✅ | ❌ |
| `/handoff` | ✅ | ❌ | ✅ | ❌ |
| `/status` | ✅ | ❌ | ✅ | ❌ |
| `/deploy` | ✅ (profile) | ❌ | ✅ | ❌ |
| `/brain` | ✅ | ❌ | ✅ | ❌ |
| `/pipeline-bridge` | ✅ | ❌ | ❌ | ✅ |
| `/mirror-check` | ✅ | ❌ | ❌ | ✅ |
| `/sprint-plan` | ✅ | ✅ | ❌ | ✅ |
| `/daily-ops` | ✅ | ✅ | ❌ | ✅ |
| `/eng-deploy` | ✅ | ✅ | ❌ | ✅ |
| `/budget-check` | ✅ | ✅ | ❌ | ✅ |
| `/smoke-test` | ✅ | ✅ | ❌ | ✅ |
| `/rfc-new` | ✅ | ✅ | ❌ | ✅ |

**Legend**: ✅ available | ❌ not yet ported | 🟡 partial

---

## Gaps & Next

| Gap | Priority | Resolution |
|:----|:--------:|:-----------|
| Claude Code agent model | P3 | Create `.claude/CLAUDERC.md` for auto-agent |
| Grok dept skills | P2 | Port 6 `@solocorp/*` skills → `.grok/skills/` |
| Codex CLI commands | P3 | Add commands to `.codex/config.toml` |
| Hermes deployment | P3 | Add Hermes deploy step to `/deploy` pipeline |
| Cross-platform test suite | P2 | Create smoke test for each platform |
| All platform docs | P3 | Quickstart per platform |

---

*SoloCorp OS — System First, Everything Follows*
