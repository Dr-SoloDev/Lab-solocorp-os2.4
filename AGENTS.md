# SoloCorp OS 2.4 — Grok Project Rules

> Organizational operating system for AI agents. Grok is a **first-class platform**
> for developing and operating SoloCorp runtime + department workflows.
> Full platform notes: `.grok/README.md` · Profiles: `profiles/INDEX.md`

## Environment

Always work from the repo root. Prefer the project venv:

```bash
source .venv/bin/activate
export PYTHONPATH=.
```

| Service | Command | Port / Path |
|:--------|:--------|:------------|
| Central Bus (busd) | `uvicorn central_bus.main:app --host 127.0.0.1 --port 8099` | `8099` · `/v1/health` |
| govctl API / Dashboard | `python -m govctl_cli api start` (or see runbook) | `8765` |
| govctl CLI | `python -m govctl_cli <cmd>` or `./govctl <cmd>` with `PYTHONPATH=.` | `gov/` artifacts |
| Loop Runner | `python -m loop_runner.main` | cron every 30m |
| Tests (scoped) | `pytest tests/ central_bus/tests/ -q` | do **not** collect whole tree |

Do not run bare `pytest` from repo root without path filters — profile-embedded tests can abort collection.

## Three Pillars (non-negotiable)

1. **Heads lead, do not implement** — Department Heads set direction, decide, escalate, hand off. Specialists execute.
2. **Leadership & ownership** — every work item has a named owner at every stage.
3. **Two-tier architecture** — Control Layer (Head-to-Head status/approvals) vs Data Layer (Central Bus artifacts).

## Chain of command

```
Human (Owner) → CEO เทอโบ → C-Level (CFO/CMO/Orchestrator)
  → Department Heads → Specialist sub-agents
```

- Human speaks primarily to **CEO**.
- Cross-department work goes **Head-to-Head** (or via Orchestrator for multi-dept pipelines).
- Specialists never talk across departments directly.

## Department routing (when acting as SoloCorp)

| Topic keywords | Department | Profile / agent |
|:---------------|:-----------|:----------------|
| vision, strategy, final decision | CEO | `profiles/01-ceo/SOUL.md` · agent `ceo-turbo` |
| pipeline, orchestration, handoff | Orchestrator | `profiles/04-orchestrator/SOUL.md` · `orchestrator-wut` |
| finance, budget, cost | CFO | `profiles/02-cfo/SOUL.md` |
| marketing, brand, campaign | CMO | `profiles/03-cmo/SOUL.md` |
| architecture, bus, routing | Architect | `profiles/05-architect/` · `architect-songsak` |
| product, PRD, roadmap | Product | `profiles/06-product/SOUL.md` · `product-produck` |
| code, backend, frontend, implement | Engineering | `profiles/07-engineering/SOUL.md` · `engineering-changful` |
| UX, design system | Design | `profiles/08-design/SOUL.md` |
| UI components, interface | UI Designer | `profiles/09-ui-designer/SOUL.md` |
| test, QA, bug, quality | QA | `profiles/10-qa/SOUL.md` · `qa` |
| sales, deal | Sales | `profiles/11-sales/SOUL.md` |
| support, customer | Support | `profiles/12-support/SOUL.md` |
| legal, compliance, contract | Legal | `profiles/13-legal/SOUL.md` |
| solana, DeFi, smart contract | Web3 | `profiles/14-web3/SOUL.md` |
| content, caption, video | Content | `profiles/15-content-creator/SOUL.md` |
| network, CDN, VPN, DNS | NetEng | `profiles/16-neteng/SOUL.md` |
| security, threat, IR | CyberSec | `profiles/17-cybersec/SOUL.md` |
| psychology, behavior, bias | Psychology | `profiles/18-psychology/SOUL.md` |

When a request maps to a department: **role-play that Head** (or spawn the matching `.grok/agents/*` subagent). Read the department `SOUL.md` before deciding.

## Grok SoloCorp slash skills

| Command | Skill | Purpose |
|:--------|:------|:--------|
| `/pipeline <feature>` | `pipeline` | Full-cycle SoloCorp pipeline simulation |
| `/handoff <from> <to> <task>` | `handoff` | Structured department handoff |
| `/status` | `status` | Pipeline / bus / governance health |
| `/audit [scope]` | `audit` | Audit trail inspection |
| `/deploy` | `deploy` | Deploy/export profiles + validate config |
| `/brain <context>` | `brain` | Save session context notes |
| `/route <request>` | `route` | Classify request → department + agent |

## How to use Grok subagents for SoloCorp

- Spawn project agents from `.grok/agents/` as `subagent_type` (e.g. `engineering-changful`, `architect-songsak`).
- Use `explore` for read-only research; `plan` for implementation plans; department agents for owned decisions.
- Prefer **parallel independent research** (e.g. auth + billing) over one giant context.
- Max subagent depth is **1** (child cannot spawn children). Parent orchestrates.
- For file-mutating experiments use `isolation: worktree`.

## Language & style

- **Thai primary**, technical terms in English.
- Prefer concrete file paths and commands.
- Do not invent platform features that only exist on OpenCode unless implementing them.

## Key paths

| Path | What |
|:-----|:-----|
| `central_bus/` | FastAPI busd v0.6 |
| `govctl_cli/` | Governance CLI + API |
| `gov/` | ADR / RFC / Guard TOML |
| `bus/` | Queue, project state, governance events |
| `loop_runner/` | Scheduled loops |
| `profiles/` | 18 department SOUL + teams |
| `.grok/` | Grok pack (agents, skills, MCP) |
| `CLAUDE.md` | Claude/OpenCode routing (compat) |
| `docs/operations-runbook.md` | Ops commands |
| `docs/MASTER-FLOW.md` | Constitutional operating flow |

## Safety

- Confirm before destructive git/db operations.
- Do not commit secrets. Bus DBs and logs may be local-only.
- Prefer scoped tests and targeted edits over repo-wide refactors unless asked.
