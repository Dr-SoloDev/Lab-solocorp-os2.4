# SoloCorp OS 2.4 — Agent Quickstart

This is an **organizational OS for AI agents**, not a normal codebase.
Every unit of work has an owner, a specialist executor, and a defined handoff path.

## First thing — read this 30-second behavior map

```
@rules/INDEX.md
```

This single file tells you how to receive requests, route them, work with teams, manage sessions, stay safe, and run commands. All 5 rule files are behavior-centric: 1 behavior = 1 file.

## Hierarchy (who decides what)

```
Owner (Dr.solodev) — L5: Vision, org, core product ONLY
  └── CEO (เทอโบ) — L4: Strategy, direction, final call
        └── COO (กิจ/Kit) — L3: Daily ops, team, front-line (L1-L3 gatekeeper)
              └── 19 Department Heads + Specialist Teams
```

**Escalation rule:** L5→Owner, L4→CEO, L3→COO decides, L2→Dept Heads, L1→auto.
If Owner sees L1-L3 work, COO failed.

## Essential commands (16 total — see `rules/INDEX.md` or `opencode.json`)

| Start / End session | Pipeline | System |
|---------------------|----------|--------|
| `/bootstrap` — auto-inject context | `/pipeline <feature>` — full cycle | `/status` — health |
| `/summary` — save brain | `/handoff <from> <to> <task>` | `/audit` — compliance |
| `/brain` — save context | `/pipeline-bridge` — cross-dept | `/deploy` — profiles+config |
| | `/mirror-check` — decision check | |

**COO:** `/coo-dispatch` — triage L1-L3, assign, report
**Proposals:** `/propose` — Dept Heads suggest ideas; `/proposals` — dashboard

## Architecture

| Layer | What | Who |
|-------|------|-----|
| **Control** | Status, goals, approvals, handoffs | Heads talk Head-to-Head |
| **Data** | Code, designs, reports, artifacts | Central Bus (async queue) |

Specialists never talk cross-department directly — always through the Bus.
Heads never implement — they delegate to specialists.

## 🔒 Security — API Key Protection

**Before you start:** SoloCorp OS uses API keys for LLM providers. **Never commit `.env` files!**

- 📖 **Full guide:** `docs/API-KEY-PROTECTION.md`
- 🚨 **Quick ref:** `docs/API-KEY-SAFETY.md`
- ✅ **Protection active:** Pre-commit hook scans for secrets automatically

```bash
# ✅ Safe: API keys in .env
echo "MAXPLUS_API_KEY=your-key" > .env

# ❌ Dangerous: Hardcoded keys
API_KEY = "ccsk-xxx"  # Will be blocked by pre-commit hook!
```

---

## How to test

```bash
pytest tests/ central_bus/tests/ -q          # main test suite
python3 workers/auto_qa_gate.py --threshold=9 # coverage gate (CI-ready)
```

⚠️ Never run bare `pytest` from root — profile-embedded tests abort collection.
Coverage baseline: 9% (gate at `workers/auto_qa_gate.py`).

## Key paths

| Path | What |
|------|------|
| `rules/` | **READ FIRST** — 5 behavior files + INDEX |
| `profiles/20*SOUL.md` | 20 departments with identity + team |
| `sop/` | 5 Standard Operating Procedures (SOP-01–05) |
| `central_bus/` | FastAPI daemon (30+ modules), queue, routing, mirror |
| `workers/agents/` | 22 agent workers with `self.think()` |
| `workers/auto_qa_gate.py` | Coverage gate (CI integration) |
| `brain/` | CEO memory, session log, learnt lessons |
| `bus/` | Queue, dispatch records, evidence, proposals |
| `decisions/` | ADRs (Architecture Decision Records) |
| `.github/workflows/ci.yml` | CI pipeline (tests + coverage gate per PR) |

## Communication

- `@ceo-turbo` — default agent, routes everything
- `@coo-kit` — COO, handles L1-L3 directly
- `@<department>` — any of 19 Dept Heads (e.g. `@changful`)
- Route via MCP: `solocorp_route_request`, `solocorp_get_department`

## Culture (non-negotiable)

- **SOP > Memory** — don't remember, read the SOP
- **Proactive > Reactive** — see problem → fix it, see opportunity → propose it
- **Trust > Permission** — decide L1-L4 without asking Owner
- **Repeatable > Hero** — process that anyone can run
- **Dashboard > Report** — Owner glances, doesn't read
- **Good enough + deployed > Perfect + not born**

## Brain memory

Session log is at `brain/session-log.md` (append-only).
Save context on close: `/summary` or manually append with format:
`วัน/time + summary + key decisions + open items + commit hash`.
