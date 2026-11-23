# Wave 1 — Routing SSoT (ADR-040) · Evidence — 2026-11-23

> **Branch:** `feat/wave1-routing-ssot` (from `origin/main` @ `b6e509f`)
> **Scope:** routing SSoT sync + keyword adapter + drift health + live seed
> **Status:** implemented + tested + seeded; **PR open, not merged**; maker ≠ checker (`@pipeline-auditor`)

---

## 1. What the problem was (measured, not assumed)

| Check | Before |
|:------|:-------|
| `bus/system/routing_rules.json` | 22 rules |
| SQLite `routing_rules` (live) | **0 rows** |
| `schema_migrations` (live) | only `001-behavior-taxonomy` |
| Live `GET /v1/health` | `"routing_rules": 0` |
| `_evaluate_condition` on `{"keywords": […]}` | always `False` → every request fell to `fallback_department="ceo"` |
| `central_bus/migrate.py` CLI | called `db.initialize()` (does not exist) → migration never ran |

Root cause is a **drift chain**, not a single bug: SSoT file != DB rows != engine-understood schema != migrate CLI.

## 2. Live seed — before / after (no restart)

| Snapshot | health `routing_rules` | PID | uptime_s | file |
|:---------|:----------------------:|:---:|---------:|:-----|
| before | 0 | 1252 | 2695 | `health-before.json` |
| after (immediate) | **22** | 1252 | 2716 | `health-after.json` |
| after (+65s, > 60s engine cache) | **22** | 1252 | 2793 | `health-after-65s.json` |

Same PID throughout (`busd-process-before.txt` / `busd-process-after.txt` / `busd-ps-after.txt`): process started `Mon Nov 23 07:18:22 2026`, elapsed 2726s at capture. **No restart, no kill.**

DB after (`db-after.json`): 22 rows, 22 enabled, ids are the stable SSoT `rule_id`s, `schema_migrations` = `001-behavior-taxonomy` + **`002-routing-rules`** (checksum `03a7e8d44bd6948e`).

## 3. Sync runs

| Run | Inputs | Result | File |
|:----|:-------|:-------|:-----|
| dry-run | live DB, 22 rules | `0 → 0`, insert 22, `projected_enabled 22`, DB unchanged | `dry-run.json` |
| apply (first) | live DB | `0 → 22`, insert 22, `rules_in_sync true`, migration `version` shape | `apply.json` |
| apply (re-run) | live DB | `22 → 22`, insert 0 / update 0 / **unchanged 22** | `apply-rerun.json` |

Checksum of SSoT: `03a7e8d44bd6948e` (sha256[:16], same style as `001`).

## 4. Semantic matrix (real SSoT, new engine, live DB, read-only)

11/11 passed (`matrix-live.json`). Engine sees 22 rules. No case falls to `ceo`.

| # | Payload | Expected | Actual | Pass |
|:-:|:--------|:---------|:-------|:----:|
| 1 | review the quarterly budget and cost report | cfo | cfo | ✅ |
| 2 | deploy the backend api hotfix | engineering | engineering | ✅ |
| 3 | run regression test suite for quality | qa | qa | ✅ |
| 4 | our solana smart contract needs an audit | web3 | web3 | ✅ |
| 5 | customer support ticket escalation | support | support | ✅ |
| 6 | GDPR compliance review for the contract | legal | legal | ✅ |
| 7 | marketing content plan for the brand | cmo | cmo | ✅ |
| 8 | fix a bug in the server | engineering | engineering | ✅ |
| 9 | daily ops routine admin | coo | coo | ✅ |
| 10 | ช่วยดูเรื่องการเงินกับงบประมาณให้หน่อย | cfo | cfo | ✅ |
| 11 | hello there, nice weather today (no match) | coo (SSoT fallback) | coo | ✅ |

## 5. Rollback (seed only — nothing else deleted)

**22 inserted ids** (full list in `rollback-ids.json`):

```
r_to_cfo, r_to_cmo, r_to_architect, r_to_product, r_to_engineering,
r_to_design, r_to_ui, r_to_qa, r_to_sales, r_to_support, r_to_web3,
r_to_legal, r_to_coo, r_to_orch, r_to_governance, r_to_guard, r_fallback,
r_mirror_coo, r_mirror_ceo, r_mirror_architect, r_mirror_cfo, r_mirror_eng
```

Run `rollback.sql` against the live DB to return to `routing_rules = 0` and remove the `002-routing-rules` record. No other rows are touched. (`schema_migrations` on the live DB uses the legacy `version` column — the rollback file targets that shape.)

## 6. Tests

| Suite | Result | File |
|:------|:-------|:-----|
| `central_bus/tests/` | **186 passed** (157 pre-existing + 29 new) | `pytest-central-bus.txt` |
| `tests/ + central_bus/tests/` (CI invocation) | **1409 passed, 1 failed, 1 skipped, 3 deselected** | `pytest-full.txt` |
| coverage | **76%** (CI threshold 9%) | `qa-gate-becdcdc6.json` |

The single failure — `tests/test_solocorp_app_live.py::test_live_payload_has_no_secrets` — is **pre-existing and environmental**: a live OpenCode session title contains the word "brief", which is in that test's deny-key list. Reproduced identically on the unrelated session worktree/branch (same failure), not caused by this change.

New tests (`central_bus/tests/test_routing_ssot.py`): transform 22, dry-run no-write, apply 22 + migration record, double-apply idempotency, changed-rule in-place update, DB-only rows preserved, legacy `schema_migrations(version)` support, 10-case semantic matrix + fallback, health parity, backlog-age.

## 7. Honest limitations (do not upgrade these)

1. **The running busd still executes old code from `/data/projects/Lab-solocorp-os2.4`.** The seed made the *data* true (`routing_rules: 0 → 22`, no restart). Keyword *routing semantics* become live only after the branch is deployed to that checkout and the daemon is restarted — not done here (no process was killed).
2. `rules_in_sync` / `oldest_routed_age_seconds` are proven by tests on the new code; they are not yet present on the live endpoint because (1) applies.
3. `schema_migrations` has two shapes on this host (`name` in repo schema, `version` in live DB). The sync supports both; `behavior_migration` still queries `name` and would fail on the legacy DB — recorded in ADR-040 as Wave 2 work.
4. SSoT keyword hygiene gaps found but intentionally not changed: `"orchestrat"` cannot match `"orchestrate"` under word-boundary matching; `"pipeline deal"` is an unlikely phrase. Requires a Wave 1.1 SSoT edit + matrix update.
5. Mirror-rule precedence: broad rules can outscore `r_mirror_*` (same as legacy `route()`). Changing that needs its own ADR.

## 8. Files

- Implementation: `central_bus/routing_sync.py` (new), `central_bus/router.py`, `central_bus/health.py`, `central_bus/queue.py`, `central_bus/migrate.py`, `central_bus/db.py`
- Tests: `central_bus/tests/test_routing_ssot.py` (new, 29)
- ADR: `decisions/ADR-040-single-source-of-truth-drift-gates.md` (requested as ADR-033; 033–039 already assigned)
- Evidence: this directory
