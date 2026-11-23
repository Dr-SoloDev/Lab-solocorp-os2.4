# Wave 2 — Version SSoT + Config SSoT / Drift Gate

**Date:** 2026-11-23
**Branch:** `feat/wave2-ssot-config` (based on `origin/main` @ `b6e509f`)
**Scope:** version single-source-of-truth, `opencode.jsonc` drift repair, a config validator with a warn-only CI gate.
**Not merged by the author** — PR open for review.

---

## 1. Drift inventory — before → after

| # | Drift | Before (origin/main) | After | Enforced by |
|:-:|:------|:---------------------|:------|:------------|
| 1 | Version has two literals | `health.VERSION="0.6.0"` (since 2026-07-06) vs `main.py version="0.6.2"` + log `v0.6.2` | `central_bus.__version__` only; health + FastAPI + log derive from it | `tests/test_version_single_source.py` |
| 2 | Version drift baked into a test | `test_integration.py` asserted `== "0.6.0"` | asserts `== central_bus.__version__` | same file |
| 3 | Dead `skills.paths` | `skills/@axis/design`, `skills/@axis/marketing` (no such dirs) | removed | `config-lint` → `skills-paths` |
| 4 | Real skills not loaded | `skills/@axis/cto` (deploy, smoke-test) + `skills/@axis/handoff-protocol` not in paths | `cto` added; `skills/@axis` added as a source root (covers `handoff-protocol`, whose `SKILL.md` sits at its own folder root) | `config-lint` → `skills-paths` |
| 5 | `skill.toml` 14 vs 16 `SKILL.md` | missing `cross-dept/dept-workspace`, `handoff-protocol` | both added (schema of existing manifests) | `config-lint` → `skill-manifest` |
| 6 | Heads not wired | 19 `agents{}` entries vs 87 agent files — missing `product-produck`, `neteng-neet`, `cybersec-sai`, `psych-jit`, `rd-lab` | 24 entries; all five mirror peer-head shape | `config-lint` → `agents-coverage` |
| 7 | L1 had no permission block | `build` / `plan` / `explore` had none → inherited the global model unchanged (`explore` could edit files, contradicting ADR-017) | `explore` + `plan` read-only (deny edit/bash/subagent); `build` narrowed (protected paths + destructive git/shell denied) | `config-lint` → `permission-lint` + tests |
| 8 | Skill ID shadowing (**found while building the gate**) | adding `skills/@axis/cto` at the end of the array makes `cto/deploy` + `cto/smoke-test` override the canonical `engineering/deploy` + `qa/smoke-test` (OpenCode picks by ID, last source wins) | `skills/@axis/cto` ordered **before** engineering/qa → canonical skills win; override is declared and pinned | `config-lint` → `skill-id-collisions` |

Validator output, before and after: `config-lint-before.txt` / `config-lint-after.txt` (12 findings → `result: OK`, strict exit 0).

---

## 2. Decisions and why

1. **Single source = `central_bus/__init__.py`.** It is the only place a version literal may exist. `health.py` and `main.py` import `__version__`; `tests/test_version_single_source.py` also fails if a local literal reappears (`VERSION = "…"` in health, `version="…"` in the FastAPI factory). The FastAPI `title` is derived too — it carried its own `v0.6` claim.
   - `__version__` is assigned **before** the submodule imports in `__init__.py`, so `import central_bus.health` first (partial package init) still resolves. All three import orders verified (`version-ssot-after.txt`).
2. **`skills/@axis` added, granular paths kept.** OpenCode's documented rule: a directory containing `SKILL.md` is one skill, grouping dirs nest up to six levels below a source root. `handoff-protocol/SKILL.md` sits at that folder's own root, so a source pointing at `skills/@axis/handoff-protocol` would not load it — `skills/@axis` does. The granular paths stay because the loader generation on this host is unverified; keeping both cannot lose a skill.
3. **`skills/@axis/cto` is ordered before the canonical roots.** Its `deploy`/`smoke-test` are *shadow shims* that forward to the canonical skills, and skill IDs collide. Array order decides the winner, so the canonical `engineering/deploy` and `qa/smoke-test` must come later. The validator now pins this (`SKILL_ID_OVERRIDE_ALLOWLIST` names the expected winner; a reorder fails the gate). Loading the shims requires renaming their directories — Wave 4 / CTO.
4. **`skill.toml` for the two skills declares `[bus] registered = false` + `reason`.** Neither has a route in `bus/system/skill_routes_config.json`; inventing an endpoint/queue topic would be fabricated provenance.
5. **The five heads get scoped blocks, never `read *`.** Each mirrors a peer head: scoped read/edit of its own domain plus `deny legal_vault/**` + `deny finance/**`.
6. **Only narrowing, under either precedence rule.** New L1 rules are denies only (no added allows), so they stay correct whether the agent block is merged after the global model or replaces it.
7. **`cto` profile is exempt, not added.** Its runtime identity is declared in `.opencode/agents/cto.md` frontmatter (Wave 1 dual-run); a jsonc block narrower than its own frontmatter could silently cut its declared scope. Agent-vs-global precedence is Wave 4's to prove.
8. **`qa-team` / `sales-team` / `support-team` id ≠ runtime file stem (`qa.md`, `sales.md`, `support.md`) is a note, not a failure.** Renaming either side changes agent identity/permission scope — out of scope here.

---

## 3. Verification (reproduce)

```bash
# from the branch worktree, Python 3.12
python3 scripts/validate-opencode-config.py             # strict → exit 0
python3 scripts/validate-opencode-config.py --warn-only  # CI phase 1 → exit 0
python3 scripts/validate-opencode-config.py --json       # machine-readable

source .venv/bin/activate && export PYTHONPATH=.
python -m pytest tests/test_version_single_source.py tests/test_validate_opencode_config.py \
                 central_bus/tests/test_integration.py -q     # 85 passed
python -m pytest tests/ central_bus/tests/ --tb=short --cov-report=json:.coverage.json --no-header -q
```

Artifacts in this folder:

| File | What it is |
|:-----|:-----------|
| `version-drift-before.txt` | the two literals on `origin/main` (source-level proof, not a stale process) |
| `version-ssot-after.txt` | live import assertion: `health.VERSION == app.version == __version__`; all import orders |
| `config-lint-before.txt` / `.json` | 12 findings on the pre-fix tree |
| `config-lint-after.txt` / `.json` | all five checks PASS, strict exit 0 |
| `config-lint-warn-only.txt` | the exact CI command, exit 0 |
| `skill-inventory.txt` | configured paths → loadable skill dirs, with collision sources shown |
| `targeted-tests.txt` | 85 passed |
| `full-suite.txt` | full CI suite: 1444 passed, 1 pre-existing failure (below) |
| `pre-existing-live-test-failure.txt` | same failure reproduced on the main worktree, different branch |
| `ci-lint-dryrun.txt` | warn-only today vs strict after the flip date |

### Full-suite result — read this before calling it green

`full-suite.txt` ends with:

```
FAILED tests/test_solocorp_app_live.py::test_live_payload_has_no_secrets - as...
1 failed, 1444 passed, 1 skipped, 3 deselected
```

That test asserts the string `brief` never appears in `/api/live/status`, which serialises **live local session data**. It fails on an environment whose session titles contain "brief" and passes on a fresh CI checkout. Reproduced unchanged on the main session worktree (`pre-existing-live-test-failure.txt`) → **pre-existing / environmental, not caused by this branch.** No change was made to it.

---

## 4. CI gate

New job `config-lint` in `.github/workflows/ci.yml`:

```yaml
      - name: Validate opencode config (warn-only until 2026-11-30)
        continue-on-error: true
        run: python3 scripts/validate-opencode-config.py --warn-only
```

- **Phase 1 (now):** warn-only — findings visible in the job log, never blocking.
- **FLIP DATE 2026-11-30:** remove `--warn-only` **and** `continue-on-error: true` to make it blocking. The validator already exits `1` on findings and `2` on an unreadable config in strict mode.
- Stdlib only (no `pip install` in the job), so the gate cannot be broken by dependency drift.

---

## 5. Explicitly NOT done

| Item | Why |
|:-----|:----|
| Narrowing `architect-songsak` / `ceo-turbo` / `coo-kit` / `axis-ceo` / `cfo-meetoo` / `content-creator-sek` / `legal-tulya` / `orchestrator-wut` broad reads | `LEADERSHIP_ALLOWLIST` declares them with reasons; agent-vs-global precedence is unproven → Wave 4 |
| `cto` in `agents{}` | Wave 4 (decision 7) |
| Renaming `qa-team`/`sales-team`/`support-team` to match runtime files | identity/permission change → Wave 4 |
| Renaming the `cto/deploy` + `cto/smoke-test` shadow shim dirs so they can load | CTO-owned skill identity → Wave 4 / CTO |
| Touching `oldest_routed_age_seconds` / `rules_in_sync` / routing / seed / health queue metrics | Wave 1 (Architect) owns them |
| Campaigns / frozen evidence / running processes | out of scope, forbidden |
| Merging | reviewer's call |

---

## 6. Rebase note

Branch was cut from `origin/main` @ `b6e509f` and has **not** needed a rebase (`origin/main` unchanged at push time). Overlap with Wave 1 is limited to three lines in `central_bus/health.py` (one import line, `VERSION`) and three in `central_bus/main.py` (import, lifespan log, FastAPI factory); if Wave 1 lands first, re-run §3 after rebasing — those lines are the only conflict surface.

---

*Wave 2 — Version SSoT + Config SSoT/Drift Gate. Evidence, not assertion.*
