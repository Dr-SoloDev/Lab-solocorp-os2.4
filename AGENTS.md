# SoloCorp OS 2.4 — Agent Quickstart

An **organizational OS for AI agents**, not a normal codebase. Every unit of work has an owner, a specialist executor, and a defined handoff path. The "product" is mostly docs-as-code — `profiles/*/SOUL.md` (department identities), `rules/` (behavior), `sop/` (procedures); `central_bus/` is the only real service.

## First thing — read the behavior map

```
@rules/INDEX.md
```

30-sec map, auto-loaded via `opencode.json` `instructions` (with `CLAUDE.md`). All **6 rule files** are behavior-centric: 1 behavior = 1 file (receive, work, session, safety, env, certification).

## Hierarchy (who decides what)

```
Owner (Dr.solodev) — L5: Vision, org, core product ONLY
  └── CEO (เทอโบ / ceo-turbo) — L4: Strategy, direction, final call  ← default agent
        └── COO (กิจ / coo-kit) — L3: Daily ops, L1-L3 gatekeeper
              └── 19 Department Heads + Specialist Teams  (master list: profiles/INDEX.md)
```

**Escalation:** L5→Owner, L4→CEO, L3→COO decides, L2→Dept Heads, L1→auto. If Owner sees L1-L3 work, COO failed.

**Do-not-break rules:** Heads never implement — they delegate to specialists. Specialists never talk cross-department directly — always through the Bus.

## Commands (19 slash-commands in `opencode.json`; most mirrored in `.claude/commands/`)

| Session | Pipeline / autopilot | System |
|---------|----------------------|--------|
| `/bootstrap` — inject context | `/pipeline <feature>` — full cycle | `/status` — health |
| `/brain` — save context | `/handoff <from> <to> <task>` | `/audit` — compliance |
| `/summary` — save brain | `/pipeline-bridge` — cross-dept | `/deploy` — profiles+config |
| | `/mirror-check` — decision check | |
| | `/triage` `/mirror` `/orchestrate` — autopilot | |

Skill commands: `/sprint-plan` `/daily-ops` `/eng-deploy` `/budget-check` `/smoke-test` `/rfc-new` (POST to `solocorp_skills` / central_bus `/v1/skills/*`).

## Architecture

| Layer | What | Who |
|-------|------|-----|
| **Control** | Status, goals, approvals, handoffs | Heads talk Head-to-Head |
| **Data** | Code, designs, reports, artifacts | Central Bus (async queue) |

## Services (must be running for bus-dependent work)

```bash
source .venv/bin/activate && export PYTHONPATH=.   # required prep for any python work
```

| Service | Command | Port |
|---------|---------|------|
| Central Bus (busd) | `uvicorn central_bus.main:app --host 127.0.0.1 --port 8099` | 8099 |
| govctl API | `python -m govctl_cli api start` | 8765 |
| Loop Runner | `python -m loop_runner.main` | cron 30m |
| MCP Server | `python -m solocorp_mcp.server` | — |

## 🔒 Security — API Key Protection

**Never commit `.env`** (gitignored; pre-commit hook scans for secrets). Local `.env` from `.env.example`:

- `SOLOCORP_API_KEY` — needed for `solocorp` MCP server (runs via `.venv/bin/python3`)
- `MAXPLUS_API_KEY` — LLM provider for mirror check (must be real, not the `ccsk-xxx` placeholder)

Full guide: `docs/API-KEY-PROTECTION.md` · quick ref: `docs/API-KEY-SAFETY.md`

## How to test

```bash
pytest tests/ central_bus/tests/ -q            # CI's exact invocation
python3 workers/auto_qa_gate.py --threshold=9  # coverage gate (CI-ready)
```

⚠️ Never run bare `pytest` from root — repo rule: profile-embedded tests abort collection, and it would also miss `central_bus/tests/`. Coverage baseline: 9%. CI runs this same gate on every PR/push to main (`.github/workflows/ci.yml`, Python 3.12).

## Key paths

| Path | What |
|------|------|
| `rules/` | **READ FIRST** — 6 behavior files + INDEX |
| `profiles/` | 19 departments — start at `profiles/INDEX.md`, then `*SOUL.md` |
| `sop/` | 6 Standard Operating Procedures (SOP-01–06) |
| `central_bus/` | FastAPI daemon (30+ modules), queue, routing, mirror — the only real service |
| `workers/agents/` | 21 agent workers extending `BaseAgent` (`self.think()` in `base_agent.py`) |
| `workers/auto_qa_gate.py` | Coverage gate (CI integration) |
| `brain/` | CEO memory, `brain/session-log.md` (append-only) |
| `bus/` | Queue, dispatch records, evidence, proposals |
| `decisions/` | ADRs (Architecture Decision Records) |
| `scripts/` | `build-profiles.py` + `export-codex-agents.py` — profile/agent generation (via `/deploy`) |

## Agent wiring (Claude Code / OpenCode)

- `.claude/agents/` — 20 agent personas matching the department roster (e.g. `ceo-turbo`, `coo-kit`, `engineer-full`); `@`-mention any dept head
- `.claude/skills/solocorp/` — 9 skills (sprint-plan, budget-check, daily-ops, deploy, rfc, smoke-test, mirror-check, pipeline-bridge, ui-animation-review)
- `solocorp_skills/` Python module + `solocorp` MCP server expose the same org API: `route_request()`, `get_department()`, `check_status()`, `create_dispatch()`, `push_queue()`, `mirror_check()`, `announce()`
- `opencode.json` — default agent `ceo-turbo`; permissions allow python/git/npm, ask for rm/docker, deny sudo/rm -rf

## Communication

- `@ceo-turbo` — default agent, routes everything
- `@coo-kit` — COO, handles L1-L3 directly
- `@<department>` — any dept head (e.g. `@changful`)
- Route programmatically via MCP: `solocorp_route_request`, `solocorp_get_department`

## Culture (non-negotiable)

- **SOP > Memory** — don't remember, read the SOP
- **Proactive > Reactive** — see problem → fix it, see opportunity → propose it
- **Trust > Permission** — decide L1-L4 without asking Owner
- **Repeatable > Hero** — process that anyone can run
- **Dashboard > Report** — Owner glances, doesn't read
- **Good enough + deployed > Perfect + not born**

## Brain memory

Session log is at `brain/session-log.md` (append-only). Save context on close: `/summary` or manually append with format: `วัน/time + summary + key decisions + open items + commit hash`.
