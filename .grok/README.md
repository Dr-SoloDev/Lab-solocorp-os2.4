# SoloCorp OS — Grok Platform Pack

Makes **Grok Build CLI** a first-class host for SoloCorp OS 2.4 (alongside OpenCode, Hermes, Codex).

## What's included

| Path | Purpose |
|:-----|:--------|
| `../AGENTS.md` | Project rules injected every Grok session in this repo |
| `agents/` | Department Head agent definitions (spawnable subagent types) |
| `skills/` | Pipeline slash commands: `/pipeline`, `/handoff`, `/status`, … |
| `personas/` | Optional behavioral overlays for subagents |
| `config.toml` | Project-scoped MCP (stealth browser) |

## Quick start

```bash
cd /path/to/Lab-solocorp-os2.4
source .venv/bin/activate
export PYTHONPATH=.
grok
```

Then try:

```
/status
/route อยากเพิ่ม endpoint health metrics บน central bus
/pipeline central-bus metrics endpoint
```

Or natural language:

- “ทำตัวเป็น CEO แล้วแตกงานไป Engineering + QA”
- “spawn architect-songsak ไป review central_bus routing”
- “รัน bus แล้วเช็ค /v1/health”

## Agent types (spawnable)

| `subagent_type` | Role |
|:----------------|:-----|
| `ceo-turbo` | CEO — strategy, prioritization, final call |
| `orchestrator-wut` | Multi-dept pipeline coordination |
| `architect-songsak` | Central Bus, routing, monitoring |
| `product-produck` | PRD / roadmap / acceptance |
| `engineering-changful` | Implementation (code) |
| `qa` | Tests, quality evidence |

Parent may also use built-in `explore` / `plan` / `general-purpose`.

## Skills (slash commands)

| Command | What it does |
|:--------|:-------------|
| `/pipeline <feature>` | Full cycle: route → plan → implement → QA → status |
| `/handoff <from> <to> <task>` | Structured handoff record |
| `/status` | Bus + gov + queue health snapshot |
| `/audit [scope]` | Audit trail / governance check |
| `/deploy` | Export profiles / validate packaging |
| `/brain <context>` | Persist session notes under `bus/projects/` |
| `/route <request>` | Map request → department + recommended agent |

## Runtime services

| Service | Start | Check |
|:--------|:------|:------|
| Central Bus | `uvicorn central_bus.main:app --host 127.0.0.1 --port 8099` | `curl -s localhost:8099/v1/health` |
| govctl API | `python -m govctl_cli api start` | `curl -s localhost:8765/api/v1/health` |

Always set `PYTHONPATH=.` from repo root (or use activated `.venv` with editable install).

## MCP

Project config wires **stealth-browser** MCP when the local venv exists:

`tools/stealth-browser-mcp/venv/bin/python` + `src/server.py`

Disable in `.grok/config.toml` (`enabled = false`) if unused.

## Compatibility limits (honest)

| Works well | Partial / not native |
|:-----------|:---------------------|
| Dev runtime (bus, govctl, tests) | OpenCode-only `@mention` UI |
| Department agents via spawn | 55+ specialist auto-registry |
| Pipeline skills as workflows | Hermes profile deploy |
| CLAUDE.md + AGENTS.md routing | Infinite multi-agent depth (Grok max depth 1) |

See `docs/GROK-SUPPORT.md` and the multi-platform PRD matrix.

## Verify pack is loaded

```bash
cd /path/to/Lab-solocorp-os2.4
grok inspect
```

Confirm `AGENTS.md`, project skills, and agents appear. In TUI: type `/` and look for `/pipeline`, `/status`, etc. Open `/config-agents` to see project agents.
