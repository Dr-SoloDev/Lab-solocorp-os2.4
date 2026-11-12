<!--
  AXIS — README (Powered by SoloCorp OS Architecture)
  Funnel: Hook → Prerequisite → Try → Evidence
  Counts below are from the git tree (config-file rows) plus one runtime row
  verified 2026-11-08 with `opencode mcp list`. No number without a verify command.
  v2.4.0 is the product-pack line, not "the OS is finished".
-->

<details>
<summary><strong>AXIS</strong> — ASCII banner (click to expand)</summary>

```text
================================================================================
  ███████  ██████  ██       ██████   ██████  ██████  ██████  ██████
  ██      ██    ██ ██      ██    ██ ██      ██    ██ ██   ██ ██   ██
  ███████ ██    ██ ██      ██    ██ ██      ██    ██ ██████  ██████
       ██ ██    ██ ██      ██    ██ ██      ██    ██ ██   ██ ██
  ███████  ██████  ███████  ██████   ██████  ██████  ██   ██ ██


   ██████  ███████  ███████   ██   ██
  ██    ██ ██            ██   ██   ██
  ██    ██ ███████  ███████ █ ███████
  ██    ██      ██  ██      █      ██
   ██████  ███████  ███████        ██
================================================================================
              PACK LINE v2.4  ·  SYSTEM STILL PRE-RELEASE
================================================================================
```

</details>

# ⚡ AXIS — OpenCode-Native Multi-Agent Framework

> **One Axis, Multiple Identities.**
> *The premier multi-agent department architecture framework built 100% for OpenCode (Desktop, CLI, Web, and Mobile). Powered by SoloCorp OS Architecture.*

**An organizational OS for AI agents.** Turn a single AI into a workforce where every unit of work has a named owner, a specialist executor, and an explicit handoff — coordinated through a central bus, not a single overloaded prompt.

> **Brand mapping (display → repo ID, runtime unchanged):** `axis-ceo` → `ceo-turbo` · `skills/@axis/` → `skills/@axis/` · `AXIS Central Bus` → `central_bus/` + `axis_mcp.bus_mcp`. Agent IDs and paths stay as-is until a rename runbook lands; display names above are brand-only.

This repository is a **pre-release**. **v2.4.0 is the product-pack line** (CFO, Legal, Content Creator). It is not a claim that the operating system is finished.

**Status:**
[![version](https://img.shields.io/badge/packs-v2.4.0--pre--release-%23FF6B35?style=flat-square)](https://github.com/Dr-SoloDev/Lab-solocorp-os2.4/releases/tag/v2.4.0-pre)
[![status](https://img.shields.io/badge/system-pre--release-%23FF6B35?style=flat-square)](https://github.com/Dr-SoloDev/Lab-solocorp-os2.4/releases)
[![license](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

> **License:** [MIT](LICENSE) — use, modify, and sell copies freely. Keep the copyright notice.
> ⭐ If this helped you, **star the repo** and share your team in [Discussions](https://github.com/Dr-SoloDev/Lab-solocorp-os2.4/discussions).

> **Current product direction (2026-11-01):** build a local-first SoloCorp App with one CEO experience, optional department MCPs, a module registry, and a task queue. Department MCPs remain independently usable from external MCP clients (PRD FR-07). The app is a **planned MVP, not a delivered feature** — the first-party app shell, registry UI, and provider flow are **not implemented** (PRD Phase 1 gate open). Source of truth: [`docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md`](docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md).

---

## Prerequisite

- **OpenCode CLI on `PATH`** — the bundled client adapters are OpenCode-only (Owner direction, L5, 2026-11-08). Confirm with:
  ```bash
  opencode --version
  python3 --version   # 3.12 in CI
  ```
- **Python 3.12** with the project virtualenv (repo Python prep):
  ```bash
  source .venv/bin/activate && export PYTHONPATH=.
  ```
- **Git** for cloning. The generic MCP servers themselves speak standard stdio MCP and can be attached to any compatible client (see `axis_mcp/server.py` + `axis_mcp/MCP_CLIENT_CONFIGS.md` for the generic contract) — but the bundled skills, agents, and commands in this repo are wired for OpenCode.

> **Multi-client archives (2026-11-08):** bundles for Hermes, Codex, Grok, Claude Code, and Copilot were retired from the active path by the L5 Owner direction. They are preserved in tag `archive/multi-client-2026-11-08` — do not treat any `.grok/`, `dist/codex/`, or Copilot path in the working tree as an active target; check that tag if you need the old multi-client material. Legacy helpers `scripts/build-profiles.py` and `scripts/export-codex-agents.py` remain in the tree and are slated for archiving at Phase 3.

## Try it

```bash
git clone https://github.com/Dr-SoloDev/Lab-solocorp-os2.4.git
cd Lab-solocorp-os2.4
source .venv/bin/activate && export PYTHONPATH=.

# Start the CEO session (default agent: ceo-turbo)
opencode "@ceo-turbo Start my day — show me the queue, then brief me on what needs L2/L3 decisions."
```

From there:

- `@mention` a department head directly (e.g. `@product-produck`, `@engineering-changful`, `@qa`).
- Run a cross-department cycle with `/pipeline <feature>` (Spec → Plan → Build → QA → Deliver).
- Use `/workspace <dept> <task>` for cross-department work that needs a separate agent room (manual OpenCode workflow for work spanning departments — specialists never talk cross-department directly, only through the Central Bus).

### Pipeline commands

Defined in `opencode.json` (`command` block, 20 commands):

| Command | Purpose |
|:--------|:--------|
| `/pipeline` | Full cycle: spec → plan → build → qa → deliver |
| `/handoff` | Structured handoff between departments with a context pack |
| `/pipeline-bridge` | Cross-department bridge with audit trail |
| `/mirror-check`, `/mirror` | Mirror Check protocol (L3+ decisions) |
| `/bootstrap`, `/summary` | Session start / end context |
| `/triage`, `/orchestrate` | Queue classification and dispatch decomposition |
| `/status`, `/audit`, `/brain` | System status, pipeline audit, brain memory |
| `/sprint-plan`, `/daily-ops`, `/budget-check`, `/smoke-test`, `/rfc-new`, `/eng-deploy` | Department skill shortcuts |
| `/workspace` | Open a separate department workroom for a task (no direct `@mention` across departments) |

---

## What is SoloCorp OS?

SoloCorp OS is an organizational system for AI agents: a named Head for each department, specialist sub-agents that execute, and a strict rule that ownership never disappears. A Head leads and decides; specialists do the work; every handoff is structured and logged.

**Why departments instead of one agent?** One prompt cannot own finance, architecture, QA, and content at the same time without losing accountability. Departments separate *deciding* from *doing* — so every result has an owner who can be asked a question and measured on the answer.

## The Problem We Solve

- A single AI has no roster, no owner, and no handoff — work disappears between turns.
- External MCP clients force per-client setup with no shared registry or queue.
- "It runs" is not an architecture: durable execution needs a bus, a loop runner, and an audit trail.

SoloCorp answers with named ownership, a Two-Tier control/data split, and tools that every department can call without talking sideways.

---

## What is actually in the tree

Counts verified 2026-11-08 (`feat/registry-c2`, commit `267241c`):

| Item | Count | Source of truth | Verify |
|:-----|:-----:|:----------------|:-------|
| Profile directories | **20** | `profiles/` (`01-ceo` … `19-rd-lab`, incl. `02-coo`) | `ls -d profiles/*/ \| wc -l` → 20 |
| Canonical skills | **12** | `skills/@axis/` (`SKILL.md` files) | `find skills/@axis -name 'SKILL.md' \| wc -l` → 12 |
| OpenCode agent files | **21** | `.opencode/agents/*.md` | `ls .opencode/agents/*.md \| wc -l` → 21 |
| Primary agents | **4** | `opencode.json` → `agent` (`ceo-turbo`, `build`, `plan`, `explore`) | `python3 -c "import json; print(list(json.load(open('opencode.json'))['agent']))"` |
| MCP servers — runtime (primary truth) | **10 total: 9 connected + 1 disabled** (`stealth-browser` disabled) | OpenCode runtime: 9 connected — `central-bus`, `codegraph`, `concat`, `content-creator`, `engineering`, `github`, `qa`, `solocorp`, `unified-technical`; 1 disabled — `stealth-browser` | `opencode mcp list` → 9 `✓ connected` + 1 `○ disabled` (verified 2026-11-08, exit 0) |
| MCP servers — config files | **`opencode.json` = 8 · `opencode.jsonc` = 4** | `opencode.json`: `stealth-browser` (disabled), `solocorp`, `central-bus`, `content-creator`, `engineering`, `qa`, `concat`, `github`. `opencode.jsonc`: `stealth-browser` (disabled), `central-bus`, `unified-technical`, `content-creator`. Global `~/.config/opencode/opencode.json` binds `codegraph` (V1 shape, bounded inside `mcp.codegraph`) — tree counts never double-count it against the runtime row | `python3 -c "import json; s=json.load(open('opencode.json'))['mcp']['servers']; print(len(s), [(k,v.get('disabled')) for k,v in s.items()])"` → `8 [...]` |
| Pipeline commands | **20** | `opencode.json` → `command` | `python3 -c "import json; print(len(json.load(open('opencode.json'))['command']))"` |

> **Resolved (2026-11-08):** the earlier MCP discrepancy is closed — runtime and file truths now match one picture: `opencode mcp list` shows **10 servers (9 connected + 1 disabled)**. The file truth splits across two tracked configs: `opencode.json` carries 8 (`stealth-browser` disabled + `solocorp`, `central-bus`, `content-creator`, `engineering`, `qa`, `concat`, `github`), and `opencode.jsonc` carries 4 (`stealth-browser` disabled + `central-bus`, `unified-technical`, `content-creator`); `codegraph` is bound in global `~/.config/opencode/opencode.json` (V1 shape, bounded inside `mcp.codegraph`). `codegraph` and `unified-technical` never appear in `opencode.json` itself — they reach the runtime through `opencode.jsonc` and the global config, so the table above counts them once in the runtime row. See [Remaining unverified facts](#remaining-unverified-facts) for the one config item still pending a commit.

> **Stale claims removed:** "9 canonical skills" → corrected to **12**; "4 primary agents" confirmed (**4**); the Copilot badge was dropped (no Copilot workflow in the active path); the Hermes/OpenCode/Codex/Grok platform matrix and the Codex-export / `.grok/skills` active paths were removed and folded into the `archive/multi-client-2026-11-08` note above.

---

## Key Features

- **Named ownership** — every work item has a Head who owns the outcome, not just the task.
- **Two-Tier architecture** — control (status, goals, approvals) flows Head-to-Head; data (code, designs, reports) flows through the Central Bus. Heads never pass files directly.
- **Central Bus (busd)** — FastAPI daemon with SQLite + JSONL compatibility on port 8099, `X-API-Key` auth (legacy `Authorization: Bearer` compat until 2026-10-04).
- **Loop Runner** — cron-based auto-pilot (`loop_runner/`) that executes due loops without human intervention; single-flight lock + `--dry-run`.
- **Unified Technical** — Architect + Engineering + QA combined in one MCP process (`axis_mcp/unified_technical/`), with graceful lifespan shutdown (cache cleanup task stopped, SQLite connection closed on exit — `axis_mcp/unified_technical/server.py`).
- **Content Creator Pack** — local video pipeline (BYOM + local-first MCP + publish gate) with frozen Phase 1–3 evidence (see below).
- **Behavior rules** — one file per behavior (`rules/INDEX.md`): receive (01), work (02), session (03), safety (04), env (05), certification (06).
- **MCP-standalone depth** — generic stdio servers work from any compatible client without the CEO/App (PRD FR-07).

---

## Architecture

### Two-Tier diagram (text)

Control and data are separate layers by design (ADR-002). Heads work in the Control Layer; specialists work in the Data Layer through the Central Bus.

```text
CONTROL LAYER (Head-to-Head — status, goals, exceptions, approvals)
  Head A ──handoff──→ Head B ──handoff──→ Head C
  80% direct · 15% via Orchestrator · 5% escalate to CEO
        │                                    │
        ▼ below: Heads see only "Work Item X completed ✓"
DATA LAYER (autonomous via Central Bus — code, designs, reports)
  Specialist A ──→ CENTRAL BUS (queue + audit) ──→ Specialist B
  Specialist C ──→ CENTRAL BUS (queue + audit) ──→ Specialist D
```

### Hierarchy

```text
Dr.solodev (Owner, L5 — vision / org / core product ONLY)
  └── CEO (เทอโบ, L4 — strategy, cross-dept, roadmap)
        └── COO (กิจ, L3 — daily ops, L1–L3 gatekeeper)
              └── Department Heads (L2)
                    └── Specialists (L1, via Central Bus)
```

Full design: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Behavior map: [`rules/INDEX.md`](rules/INDEX.md). Quickstart: [`AGENTS.md`](AGENTS.md).

### Central Bus (busd)

- **Command:** `uvicorn central_bus.main:app --host 127.0.0.1 --port 8099`
- **Auth:** `X-API-Key` header; legacy `Authorization: Bearer` compat until 2026-10-04.
- **Code:** `central_bus/` (30+ modules). MCP adapter: `axis_mcp/bus_mcp.py` (module `axis_mcp.bus_mcp`).

### Loop Runner (cron auto-pilot)

```bash
*/30 * * * * cd /data/projects/Lab-solocorp-os2.4 && .venv/bin/python -m loop_runner.main >> logs/loop_runner_cron.log 2>&1
```

| Loop | Level | Interval | Action |
|:-----|:-----:|:---------|:-------|
| daily_brief | L1 | 20h | Finance + brain → stdout report |
| subscription_audit | L4 | 30d | Scan recurring charges and subscriptions |
| brain_auto_commit | L4 | 1h | Git commit brain files when changes detected |
| pipeline_executor | L4 | 30m | Pull queue → LLM execute → update status |

Source: `loop_runner/` (`runner.py`, `main.py`, `loops/`).

### Unified Technical (one process)

`axis_mcp/unified_technical/server.py` — Architect, Engineering, and QA modules in one process, sharing a SQLite store and cache. Run with `python3 -m axis_mcp.unified_technical.server`. Lifespan fix (commit `267241c`): graceful shutdown stops the cache cleanup task and closes the SQLite connection; the `LockManager` is stateless (locks only) with no close hook.

> Registration note: `unified-technical` **is registered in `opencode.jsonc`** (tracked config) and shows **connected** in `opencode mcp list` (verified 2026-11-08); `opencode.json` itself still does not carry the entry (see resolved note above). Any future registration change must update the table in [What is actually in the tree](#what-is-actually-in-the-tree) in the same commit.

### Content Creator Pack — Phase 1–3 evidence (2026-11-07)

The Content Creator Pack (BYOM + Local-First MCP + Publish Gate) has three frozen, locally rendered MP4s verified by independent ffprobe/SHA + ebur128 re-measure. **Pre-release only — not a production release, not a published campaign, not a claim that Concat rendering works on this host.** Approval status (2026-11-07): **phase 1 v5 has a recorded human approval** — [`central_bus/content/campaign-campaign_synth_phase1_20261107-approval-v5_20261107T031906146707Z.json`](central_bus/content/campaign-campaign_synth_phase1_20261107-approval-v5_20261107T031906146707Z.json), recorded 2026-11-07T03:19:06Z, for that exact v5 SHA only — with `gate_passed: false` and 7 explicit overrides (visual prompt, audio cue sheet, source verification, media rights, R1, R3, R5). That approval **does not publish**: `published` remains false and the campaign has not passed the normal publish gate. **Phase 2 and phase 3 have no approval** (`approved_version: null`, `review_required`). Nothing in any phase is published; publishing stays blocked. Piper voice (`th_TH-tsync2-medium`, CC BY-NC-SA 3.0) is internal/non-commercial only.

| Phase | Campaign | Video SHA-256 | Completion record |
|:------|:---------|:--------------|:------------------|
| 1 | `campaign_synth_phase1_20261107` v5 | `ef3b282fc3ed69a58064c336e780a75f79094c0d54c36ffdbe406c23837c28bb` | [`central_bus/content/ceo-phase1-completed-20261107_20261107T031659522762Z.md`](central_bus/content/ceo-phase1-completed-20261107_20261107T031659522762Z.md) |
| 2 | `campaign_synth_phase2_20261107` v7 | `60d855b1203c5a86593c451236f03fd70bd79afa3193eb54f458f702cd0aca9b` | [`central_bus/content/ceo-phase2-completed-20261107.md`](central_bus/content/ceo-phase2-completed-20261107.md) |
| 3 | `campaign_synth_phase3_20261107` v7 | `192ba6c5e0b0c74dcd02f262df5f8771e399a8573b220e75e267531f48a7cc32` | [`central_bus/content/ceo-phase3-completed-20261107_20261107T051235733316Z.md`](central_bus/content/ceo-phase3-completed-20261107_20261107T051235733316Z.md) |

Local-only renderer: Piper + FFmpeg CLI (6×15s/10×10s, per-step/fallback/lock). Concat status (2026-11-07): **not suspended** — ADR-032 was amended the same day: the `--appimage-extract` path succeeded (`squashfs-root` 362M at `/home/drsolodev/.opencode/concat/`, `AppRun` = concat 0.2.8), `concat` MCP is `enabled` in `opencode.json`, and the MCP handshake was verified on 2026-11-07 (tools answer; `project_list()` → `[]`). **Still NOT proven: `render_campaign_with_concat` has never been run on this host** — no render proof exists; if the handshake later fails, the fallback is Option 1 disable per [`decisions/ADR-032-concat-host-2026-11-07.md`](decisions/ADR-032-concat-host-2026-11-07.md) (amended). Do not claim Concat rendering works here. Runbook: [`docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md`](docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md). **Image generation (commit `001b59e`):** `generate_image(prompt, provider="nvidia")` (default) calls NVIDIA NIM FLUX.3 Klein and stores the image under `central_bus/content/` with `gate_passed: false` / `published: false` — the tool never publishes outside the human publish gate. NIM output is always JPEG: a requested `.png` is saved as `.jpg` and noted as `requested_format`/`actual_format` in the provenance manifest. License: FLUX.3 Klein defaults to **FLUX Kommunity v1.0 non-commercial** terms, recorded in the provenance `license_note`. The legacy `provider="openrouter"` path (FLUX.3 Klein chat-completions) remains unchanged. Live smoke evidence: 1 image, 197,974 bytes, JPEG, SHA-256 `ec73af27aeb2e89f21c76f8aa6d2004853d02048f21b4a0cf4e15a04fbe1fdb4`, exit 0. Tests: 65 passed (targeted `tests/test_content_mcp.py` + `tests/test_mcp_stdio.py`, re-verified 2026-11-07).

---

## The Team

**On this chart: 18 named Heads.** Profile directories in the tree: 20 (includes `02-coo` and `19-rd-lab`). Specialist headcount is not printed here until a manifest exists.

| # | Department | Head | Scope |
|:--:|:-----------|:-----|:------|
| 01 | CEO | เทอโบ (Turbo Chaisriram) | Vision, Strategy, Final Decision |
| 02 | COO | กิจ (Kit) | Daily Operations, L1–L3 gatekeeper |
| 03 | CFO | meetoo | Finance, Budget, Investment |
| 04 | CMO | มาร์ค (Mark) | Marketing, Content, Brand |
| 05 | Orchestrator | พี่วุฒิ (Wut) | System Pipeline Coordination |
| 06 | Architect | พี่ทรงศักดิ์ (Songsak) | Central Bus, Routing, Monitoring |
| 07 | Product | โปรดัค (Produck) | Feature Roadmap, PRD, Delivery |
| 08 | Engineering | ช่างฟูล (Changful) | Backend, Frontend, Architecture |
| 09 | Design | ครีเอท (Kreet) | UX Research, Brand Visual |
| 10 | UI Designer | UI Designer | Interface, Component Library |
| 11 | QA | QA-ทีม (QA Team) | Testing, Quality, Evidence |
| 12 | Sales | เซลส์ (Sales) | B2B Deal Strategy, Pipeline |
| 13 | Support | ซัพพอร์ต (Support) | Customer Success, Analytics |
| 14 | Legal | ตุลย์ (Tulya) | Compliance, Contracts, Law |
| 15 | Web3 | อัยวา (Aywa) | Blockchain, DeFi, Solana |
| 16 | Content Creator | เสก (Sek) | Content, Creative, Media |
| 17 | Network Engineer | นีต (Neet) | Network Design, Infrastructure, CDN, VPN |
| 18 | Cyber Security | ซาย (Sai) | Threat Detection, Vulnerability, Incident Response |
| 19 | Psychology | จิต (Jit) | User Behavior, Behavioral Economics, Org Psychology |
| 20 (lab) | R&D Lab | Lead Researcher | Curiosity-driven research, prototypes |

Thai names are kept as proper names; the explanation is in English. Full roster: [`profiles/INDEX.md`](profiles/INDEX.md).

---

## Development Status

No percent bars. A row marked **In tree** means the files exist. It does not mean done. The system line is still **pre-release**. v0.x is that system line. **v2.4.0 is only the pack line.**

| Phase | Content | Version | Status |
|:------|:--------|:-------:|:-------|
| Foundation | ADRs + CEO profile + architecture docs | v0.1–v0.2 | In tree |
| Pipeline agents | Architect-side pipeline agent files | v0.3 | In tree |
| Department profiles | 20 directories, 18 charted above | v0.5 | In tree |
| Sub-agent teams | `team/*.SOUL.md` under most profiles | v0.6.1 | Partial — Content Creator has none |
| Central Bus | `central_bus/` FastAPI daemon, SQLite + JSONL compat (`use_sqlite` switch) | v0.6 | In tree, pre-release |
| Dashboard + compliance | Pipeline dashboard + audit UI | v0.7 | Planned |
| Product packs | CFO · Legal · Content Creator profiles | v2.4.0 | Pre-release |
| Public launch | GTM · content · skill docs | v0.7 | Partial — this README is part of that work |
| Loop runner | `loop_runner/` cron auto-pilot | v0.5+ | In tree |
| OpenCode-only cutover (L5 2026-11-08) | `.claude/` deleted; multi-client bundles archived at tag `archive/multi-client-2026-11-08` | v2.4.0+ | In tree — `.grok/` remains as archive material, not an active target |

> **`opencode.jsonc` provider note (committed 2026-11-08):** tracked `opencode.jsonc` carries a `providers.openrouter` custom entry — model `flux-3-klein` (`black-forest-labs/flux-3-image-klein`) — alongside its MCP entries used by the runtime row above. Image generation defaults to NVIDIA NIM via the Content Creator `generate_image` tool (commit `001b59e`); the OpenRouter provider entry is kept as legacy fallback. Count it as in-tree from that commit on.

`PROJECT.md` still says in one FAQ that the Central Bus is "in design" and that the system is production-ready (its own status table also marks the bus "Production Ready" in places). Those answers are stale. Believe this table, then the code.

---

## NOT done (explicit)

Do not upgrade these to "done":

- **Stealth browser MCP:** `disabled: true` in `opencode.json` (Owner). Its venv exists on disk (`tools/stealth-browser-mcp/venv/`) but the server is not started.
- **Concat render proof:** handshake verified 2026-11-07 but `render_campaign_with_concat` has never been run on this host — no render proof. Local-media renders do not need Concat.
- **Degraded publication:** **NO-GO** pending architect D1 waiver + a real degraded render on a throwaway campaign.
- **Certification:** D3 not passed (operational E2E runs, not independent D3/D4).
- **SoloCorp App shell:** first-party app shell / registry UI / provider flow **not implemented** (PRD Phase 1 gate open). The Content Creator pilot and Central Bus are evidence, not proof the app is complete.

---

## Remaining unverified facts

Two items that used to live here as unverified claims are resolved as of 2026-11-08 and now appear with their verify commands in [What is actually in the tree](#what-is-actually-in-the-tree):

- **Test suite (verified 2026-11-08):** `python -m pytest tests/ central_bus/tests/ --tb=short --no-header -q` → **1182 passed, 1 skipped, exit 0** (~96s). The live-network test was narrowed at this commit; live-gated cases skip unless `OPENROUTER_LIVE_TEST=1`. The combined suite includes runtime-touching tests — conditions follow the tools state per D3 (content-creator), so this is run evidence, not a production-readiness claim.
- **`opencode.jsonc` provider customization (committed 2026-11-08):** `providers.openrouter` with model `flux-3-klein` (`black-forest-labs/flux-3-image-klein`) — in-tree and counted as of the commit described above (see the provider note under Development Status). Primary image generation path is NVIDIA NIM via `generate_image` (commit `001b59e`).

Still unverified — do not quote until someone verifies it in a commit:

- **`.grok/` retention:** `.grok/` files remain in the git tree (`git ls-files | grep '^\.grok'`) as archive material. Whether they should be deleted or tagged requires an Owner/CEO decision; this README does not claim they are gone.

---

## Get Started

1. Install OpenCode and ensure `opencode` is on `PATH`.
2. Clone this repo, activate the venv, and run `opencode "@ceo-turbo Start my day — show me the queue."`
3. Use `@mention` to reach a Head directly.
4. Run `/pipeline <feature>` for a cross-department cycle.
5. Start Central Bus only when bus-dependent work needs it:
   ```bash
   uvicorn central_bus.main:app --host 127.0.0.1 --port 8099
   ```

**Reference docs:**

- `profiles/INDEX.md` — profile index (reconcile it with the count table above before quoting it)
- `docs/ARCHITECTURE.md` — system design, principles, and flow
- `AGENTS.md` — agent quickstart (hierarchy, session protocol)
- `rules/INDEX.md` — 30-second behavior map (one file per behavior)
- `docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md` — current product direction (source of truth)
- `PROJECT.md` — longer tour; its status FAQ is stale where it disagrees with this page
- `CHANGELOG.md` — version history and release notes
- `decisions/` — Architecture Decision Records (ADRs)
- `sop/` — Standard Operating Procedures (SOP-01 through SOP-07)
- `docs/FAMILY.md` + SOP-07 — cross-instance dispatch for family instances

> **Codex export note (archived):** `scripts/build-profiles.py` and `scripts/export-codex-agents.py --validate-only` remain in the tree for audit but are **not** part of the active OpenCode path. The multi-client export they produced lives at tag `archive/multi-client-2026-11-08`.

> **Grok note (archived):** `.grok/` remains in the tree as archive material only. There is no `.grok/skills` active path.

---

## Contributing

SoloCorp OS is a small team with a high bar for honesty: **evidence beats reports**. If you change a number, change the line that generates it in the same commit.

- **Report "blocked" with evidence** — that is valid work. Report "done" without evidence — that is the worst failure (see `rules/06-certification.md`).
- **Maker ≠ checker.** Every gate needs a different checker than the maker; default status is NOT PASSED until evidence is attached.
- **Verify before you claim.** Run the commands in [What is actually in the tree](#what-is-actually-in-the-tree) and paste the output in your PR.
- **Docs-only changes still need `git diff --check`** and a scope note (which counts did you verify, which did you not).

---

<div align="center">

**SoloCorp OS — System First, Everything Follows**
[MIT License](LICENSE) · Copyright (c) 2026 SoloCorp Organization (Dr-SoloDev)
Use, modify, and sell copies. Keep this copyright notice.
Built by Dr.SoloDev &amp; เทอโบ ไชยศรีรัมย์

</div>
