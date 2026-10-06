# SoloCorp OS 2.4 — Agent Quickstart

An **organizational OS for AI agents**, not a normal codebase. The "product" is docs-as-code (`profiles/*/SOUL.md`, `rules/`, `sop/`); `central_bus/` is the only real service. Authoritative roster: `profiles/INDEX.md`. Auto-loaded context: `opencode.json` → `instructions` (`CLAUDE.md` + `rules/INDEX.md`).

## Start here

```
@rules/INDEX.md   ← 30-sec behavior map (6 files: receive, work, session, safety, env, certification)
```

Default agent is `ceo-turbo` (strategy + routing + final call). Owner (Dr.solodev) decides L5 only.

## Hierarchy + escalation (do-not-break)

```
Owner — L5: vision / org / core product ONLY
└── CEO (เทอโบ) — L4: strategy, cross-dept, roadmap
    └── COO (กิจ) — L3 gatekeeper: daily ops, L1–L3
        └── Department Heads — L2 · Loop Runner — L1 (auto)
```

- **Heads never implement** — they delegate to specialists.
- **Specialists never talk cross-department directly** — via Central Bus only (Control = Head-to-Head status/goals/handoffs; Data = code/designs/reports through the Bus).
- If Owner sees L1–L3 work, COO failed.

## Session protocol

- Start: `/bootstrap` (or `python scripts/session-bootstrap.py`) — injects health, brain, queue, git state.
- End: `/summary` (or `python scripts/session-summary.py --save`) — appends to `brain/session-log.md` (append-only; never rewrite history).
- Memory files are git-tracked: `brain/ceo-identity.md` (who), `brain/ceo-memory.json` (what), `brain/session-log.md` (history), `brain/learnt.md` (lessons).

## Multi-chat workspaces (1 dept = 1 chat)

- `/workspace [dept] [task]` (skill: `skills/@solocorp/cross-dept/dept-workspace/`) — open a NEW session, title tab `[dept]+task`, paste the context bundle, work there, bring the return-report back to CEO chat.
- Human + visiting-agent manual: `docs/OPENCODE-GUIDE.md` (one file, both audiences).

## Python prep (required before any python work)

```bash
source .venv/bin/activate && export PYTHONPATH=.
```

CI uses **Python 3.12**. MCP server must run via `.venv/bin/python3` (`python -m solocorp_mcp.server`) with `SOLOCORP_API_KEY` set.

## Services (only when bus-dependent work needs them)

| Service | Command | Port |
|:--------|:--------|:----:|
| Central Bus (busd) | `uvicorn central_bus.main:app --host 127.0.0.1 --port 8099` | 8099 |
| govctl API | `python -m govctl_cli api start` | 8765 |
| Loop Runner | `python -m loop_runner.main` | cron 30m |

## Test (CI's exact invocation — copy verbatim)

```bash
python -m pytest tests/ central_bus/tests/ --tb=short --cov-report=json:.coverage.json --no-header -q
python workers/auto_qa_gate.py --threshold=9 --project-id=auto-qa-pipeline --test-path="tests central_bus/tests"
```

- ⚠️ **Never run bare `pytest`** from root — profile-embedded tests abort collection and it misses `central_bus/tests/`. (`pytest.ini` defaults to `tests/` only; CI overrides with both paths.)
- Coverage baseline is **9** (intentionally low, CI-ready) — do not "fix" by raising it without an ADR.
- Evidence artifacts go to `bus/evidence/` (see SOP-06).

## Deploy / codegen

```bash
python3 scripts/build-profiles.py                    # build profiles (step 1 of /deploy)
python3 scripts/export-codex-agents.py               # export agents
python3 scripts/export-codex-agents.py --validate-only  # verify before commit
python3 scripts/validate-soul-profiles.py            # validate SOUL.md edits
```

Full flow lives in the `/deploy` command template in `opencode.json`.

## Safety (hard stops)

- **Never commit `.env`** (gitignored; seeded from `.env.example`). Mirror checks need a real `MAXPLUS_API_KEY`, not a placeholder.
- Bus runtime files are local-only — never commit `*.db-shm`, `*.db-wal`, logs, or `bus.db` state.
- `rm -rf`, `sudo`, `chown` are denied; `docker`, `rm`, `chmod` ask first. Outside-repo writes allowed only under `~/.hermes/**`, `~/.claude/**`, `~/.opencode/**`, `~/.config/opencode/**`, `/tmp/**` — anything else asks.
- **Inspect `git status` + `git diff` before every commit.** No destructive git/db ops without explicit confirmation.
- Prefer scoped tests and targeted edits over repo-wide refactors.

## Certification ladder (why "done" needs a checker)

From `rules/06-certification.md` (incident: work reported complete with zero code changed — checkers now mandatory):

- Order: **D1** (1-page why/which-agent/scope) → **D2** (50–150-line agent that really calls tools, with run output + exit code) → **D3** (≥20-task eval table: expected vs actual + root cause, no cherry-picking) → **D4** (someone else reproduces via runbook). Never skip.
- **Maker ≠ checker** every gate; default status is **NOT PASSED** until evidence is attached. Reporting "done" without evidence is the worst failure; reporting "blocked" with evidence is valid work.
- Registry: `profiles/CERTIFICATION-REGISTRY.md` (CEO/checker updates only). Before dispatching execution work, verify the agent is D2+.

## Key paths

| Path | What |
|:-----|:-----|
| `rules/` | Behavior rules — read before acting |
| `sop/` | Standard Operating Procedures (SOP-01–06) |
| `profiles/` | Department identities (`SOUL.md`); roster in `profiles/INDEX.md` |
| `central_bus/` | FastAPI daemon (30+ modules): queue, routing, mirror |
| `workers/agents/` | Agent workers (`BaseAgent.think()` in `base_agent.py`) |
| `decisions/` | ADRs — check before changing architecture |
| `bus/` | Queue, dispatch records, evidence, proposals |
| `docs/API-KEY-PROTECTION.md` | Secret-handling full guide |

## Culture (operational, not slogans)

- **SOP > Memory** — read the SOP instead of recalling.
- **Trust > Permission** — decide L1–L4 and report; escalate L5 only.
- **Dashboard > Report** — 3–5 lines + status color beats a long report.
- Good enough + deployed beats perfect + unborn.
