# SoloCorp OS 2.4 — Agent Working Instructions

**Organizational OS for AI agents** — 18 departments, 55+ specialists, Central Bus, Governance.

ภาษาไทยเป็นหลัก, English for technical terms only.

---

## Core Paradigm

**You are a Department Head — you lead, you do not execute.** If you are writing code/designing UIs/producing content yourself, something is broken. Delegate via `@mention`.

| Mode | When | Action |
|------|------|--------|
| **Command** | Clear, urgent | Order directly → delegate immediately |
| **Strategic** | Complex, cross-dept | Analyse → consult Architect/CFO → decide |
| **Review** | Work submitted | Inspect results → feedback → approve/revise |

---

## Session Start: Files to Read

Read `CLAUDE.md` first (primary instruction, loaded via `opencode.json`). Then:

| File | Why |
|------|-----|
| `brain/ceo-memory.json` | Org memory + latest context |
| `brain/session-log.md` | Previous session history |
| `brain/learnt.md` | Lessons learned |
| `profiles/INDEX.md` | All 18 departments + R&D Lab |

---

## Exact Commands

```bash
# Tests (no external services — tmp_path + monkeypatch only)
python3 -m pytest tests/                          # Phase suites
python3 -m pytest tests/test_phase1.py -v         # Single phase test
python3 -m pytest central_bus/tests/              # Bus unit tests

# Build/export (edit SOUL.md only, never edit generated files directly)
python3 scripts/build-profiles.py                 # SOUL.md → dist/{droid,codex,hermes}
python3 scripts/export-codex-agents.py            # Generate .codex/agents/*.toml
python3 scripts/export-codex-agents.py --validate-only

# Services
bash scripts/start-services.sh                    # Central Bus + Agent Worker
uvicorn central_bus.main:app --host 127.0.0.1 --port 8099   # Manual bus start
python3 -m workers.agent_worker_service                      # Poll bus queue
python3 -m loop_runner.main                                 # Cron every 30min
python3 -m solocorp_mcp.server                              # MCP for external agents

# Bootstrap (fresh clone)
cp .env.example .env && bash scripts/bootstrap-ceo.sh

# Dependencies
pip install -r central_bus/requirements.txt
```

---

## Non-Obvious Constraints

- **No formatter / no LSP** — `formatter: false, lsp: false` in `opencode.json`. Do NOT call black/prettier/eslint.
- **Codex agents are generated** — edit `profiles/*/SOUL.md` only, then run `scripts/export-codex-agents.py`. Never edit `.codex/agents/*.toml` directly.
- **`.opencode/` is gitignored** — except `.opencode/agents/` and `.opencode/skills/` (tracked).
- **`.env` is committed** (private repo). API key: `sk-solocorp-admin-local-dev-001`. Bus URL: `http://127.0.0.1:8099`.
- **Central Bus** — 127.0.0.1:8099. 5 endpoints: `POST /v1/{observe,context,update}`, `GET /v1/{health,aar/{trace_id}}`. Auth via `X-API-Key` header (except `/v1/health`).
- **LLM provider** — uses `opencode run --pure --model` CLI subprocess (no HTTP API). Semaphore max 3 concurrent, timeout 60s, retry 3x. See `workers/llm_provider.py`.
- **govctl** — governance CLI at `govctl_cli/` (RFC → ADR → Guard Gates), not standalone.
- **R&D Lab (#19)** — owner-direct, bypasses normal pipeline. No deadlines, no pipeline process.
- **Zombie processes** — `[opencode] <defunct>` with parent PID 1 cannot be reaped.
- **LICENSE** — Proprietary, free for personal/educational use only.

---

## Architecture (Key Facts)

- **Two-Tier**: Control Layer (Head-to-Head: status, approvals, handoffs) vs Data Layer (Autonomous: code, designs, reports via Central Bus).
- **Chain**: Human → CEO → C-Level (CFO, CMO, Orchestrator) → Department Heads (05-18) → Specialists.
- **Pipeline commands**: `/pipeline`, `/handoff`, `/status`, `/audit`, `/deploy`, `/brain`, `/skillhub`, `/synthesize`.
- **Loop Runner**: cron every 30min — daily_brief, subscription_audit, brain_auto_commit.
- **MCP servers**: `solocorp` (enabled), `stealth-browser` (enabled), `github` (disabled).
- **Agent Worker** polls Central Bus queue, routes to 19 agent implementations, uses LLM provider.

---

## Project Structure (Key Paths)

| Path | What |
|------|------|
| `profiles/NN-name/SOUL.md` | Department Head profile (source of truth) |
| `profiles/NN-name/name/team/NN-name.SOUL.md` | Specialist agent profiles |
| `profiles/INDEX.md` | Master index of all departments |
| `brain/` | CEO memory, identity, session log, lessons |
| `central_bus/` | FastAPI daemon — queue, routing, facts, AAR, audit |
| `workers/` | Agent Worker service + 19 agent implementations |
| `workers/llm_provider.py` | LLM provider via `opencode run` CLI |
| `loop_runner/` | Cron every 30min (4 loops) |
| `.opencode/skills/` | OpenCode skill prompts (tracked) |
| `solocorp_mcp/` | MCP server (7 tools, 5 resources, 3-tier auth) |
| `govctl_cli/` | Governance CLI (RFC → ADR → Guard Gates) |
| `scripts/` | Build, export, bootstrap, verification |
| `tests/` | Phase test suites (no external services) |
| `dist/` | Generated profiles for {droid, codex, hermes} |

---

## Agent Routing (Quick)

Don't know where to send? → `@ceo-turbo`. Full routing table in `CLAUDE.md` or `profiles/INDEX.md`.

21 OpenCode agents in `.opencode/agents/*.md` with YAML frontmatter: `name`, `model`, `description`, `mode`, `color`.

---

## Bootstrap (cross-platform)

```bash
git clone <repo> && cd Lab-solocorp-os2.4
cp .env.example .env && bash scripts/bootstrap-ceo.sh
```

All MCP configs use relative paths and ship with the repo:
- OpenCode: `opencode.json`
- Claude Code: `.claude/settings.json`
- Codex CLI: `.codex/config.toml`
- Cursor: `.cursor/mcp.json`
