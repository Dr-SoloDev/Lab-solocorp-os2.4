# SoloCorp OS × Grok Build — Support Guide

**Status:** Active (v1 pack)  
**Updated:** 2026-07-18  
**Pack location:** `.grok/` + root `AGENTS.md`

---

## Goal

Let Grok CLI develop and operate SoloCorp OS without requiring OpenCode for everyday runtime/dev work, while remaining honest about gaps vs full multi-agent org UX.

---

## What works

| Capability | How |
|:-----------|:----|
| Project rules | `AGENTS.md` auto-loaded in repo |
| Pipeline commands | `/pipeline` `/handoff` `/status` `/audit` `/deploy` `/brain` `/route` |
| Department agents | `.grok/agents/*` spawnable as `subagent_type` |
| Personas | `.grok/personas/*.toml` |
| Runtime | Central Bus, govctl, loop_runner, scoped pytest |
| MCP | Stealth browser via `.grok/config.toml` |

---

## Quick test checklist

Run from repo root:

```bash
source .venv/bin/activate
export PYTHONPATH=.
grok
```

In TUI:

1. Type `/` → confirm SoloCorp skills appear (`pipeline`, `status`, …).
2. Run `/status` → health table (bus may be down; that is OK).
3. Run `/route เพิ่ม metrics endpoint บน central bus` → Engineering + Architect.
4. Run `/pipeline smoke status check` → plan without needing all services up.
5. Ask: “spawn architect-songsak ไล่ central_bus router” → subagent uses project agent.
6. `grok inspect` (shell) → shows `AGENTS.md` and project skills/agents.

Optional live runtime:

```bash
uvicorn central_bus.main:app --host 127.0.0.1 --port 8099
curl -s http://127.0.0.1:8099/v1/health
```

Then `/status` again should show bus **up**.

---

## Compatibility matrix (Grok column)

| Feature | Grok |
|:--------|:----:|
| Agent profiles on disk | Yes |
| Department agents invocable | Yes (spawn / role-play) |
| OpenCode-style `@mention` | No |
| Pipeline slash commands | Yes (skills) |
| Skills discoverable | Yes (`.grok/skills`) |
| Governance (govctl) | Yes (via shell) |
| MCP tools | Yes (project config) |
| Multi-agent delegation | Partial (depth 1) |
| Config entry | `AGENTS.md` + `.grok/` |

Full matrix: `docs/prds/PRD-Multi-Platform-Compatibility-v1.0.md`

---

## Limits

1. **Subagent depth = 1** — Orchestrator parent must fan-out; children cannot spawn.
2. **Not a drop-in OpenCode** — no native `@ceo-turbo` mention UI.
3. **55+ specialists** — only core Heads packaged as Grok agents in v1; rest via `profiles/*/SOUL.md` role-play.
4. **MCP path** — stealth browser command uses absolute paths for this machine; adjust `.grok/config.toml` if the repo moves.
5. **pytest** — always scope paths; do not collect entire monorepo.

---

## Extending the pack

| Add | Where |
|:----|:------|
| New slash workflow | `.grok/skills/<name>/SKILL.md` |
| New department agent | `.grok/agents/<name>.md` |
| Behavioral overlay | `.grok/personas/<name>.toml` |
| MCP server | `.grok/config.toml` `[mcp_servers.*]` |

Keep `skills/REGISTRY.md` and this doc in sync when adding skills.

---

## Related

- `.grok/README.md` — pack overview  
- `AGENTS.md` — session rules  
- `CLAUDE.md` — Claude/OpenCode routing (still valid)  
- `docs/operations-runbook.md` — govctl ops  
