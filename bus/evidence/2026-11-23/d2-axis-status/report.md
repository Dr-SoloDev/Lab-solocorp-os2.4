# D2 — AXIS STATUS C1 (Unified Status Layer)

> **Branch:** `feat/axis-status-c1` · **Date:** 2026-11-23 · **Maker:** CTO/`build` (subagent)
> **Contract:** [AXIS-STATUS-CONTRACT-v1.0.md](../../../docs/plans/AXIS-STATUS-CONTRACT-v1.0.md) · **D1:** [AXIS-STATUS-C0-D1-v1.0.md](../../../docs/plans/AXIS-STATUS-C0-D1-v1.0.md)
> **Post-D2 hardening:** 2026-11-23 — D3-driven M1/N1 fixes (uncommitted); see §2b.

Read-only status layer: one MCP tool `axis_status(force=False)` returning
`axis.status/1` for 7 sources, with per-source isolation, parallel fan-out,
1200 ms per-source / 2000 ms total budgets, weighted scoring and a 10 s cache.

**Timeline — read this first.** The D2 commit `fbb5dc3` passed the independent
audit with **29 tests**. D3 then found two false-green paths: M1 (a busd payload
missing required fields was reported `ok`) and N1 (`score_sources()` with rows
missing a critical source returned healthy). The fixes are in the **current
working tree, uncommitted**; the current tree has **31 tests**. This report's
evidence pass was regenerated **after** those fixes. The D2 commit itself is
unchanged, so its independent audit remains valid for that commit; the current
tree needs its own re-audit.

---

## 1. Files (current working tree)

| File | Lines | Role |
|:-----|------:|:-----|
| `axis_mcp/status/__init__.py` | 29 | package exports |
| `axis_mcp/status/sources.py` | 675 | 7 read-only probes + freshness helper + partial-payload guard |
| `axis_mcp/status/aggregator.py` | 339 | fan-out, timeout, scoring, cache, redaction + missing-critical guard |
| `axis_mcp/status/server.py` | 51 | FastMCP server `axis-status`, one tool, `--smoke` |
| `tests/test_axis_status.py` | 551 | 31 deterministic tests (mocked probes) |
| `scripts/d2_axis_status_check.py` | 149 | D2 harness (11 checks; writes its own log) |

The audited D2 commit `fbb5dc3` had the pre-hardening counts: `sources.py` 660,
`aggregator.py` 312, `tests/test_axis_status.py` 465 / 29 tests. The current
tree adds the M1/N1 guards and two tests; no other product files changed.

D3 adds `scripts/d3_axis_status_eval.py` (2282 lines) and
`docs/certification/D3-axis-status-2026-11-23.md`; they are separate D3
deliverables, not part of the D2 artifact.

---

## 2. Re-audit findings — what changed (original D2)

| Finding | Change | Location |
|:--------|:-------|:---------|
| **FIX 1 (blocker)** CTO schema drift reported green | a missing/unreadable required table is now `down` with `missing_tables` + warning; no more `tables[table]=None` + `ok` | `sources.py:323` (`probe_cto`) |
| **FIX 2 (blocker)** false `tool-calls.jsonl` provenance | the harness now writes `harness.log` **and** `tool-calls.jsonl` from the same invocation (no shell redirection needed); docstring corrected | `scripts/d2_axis_status_check.py:27-28,120,144` |
| **FIX 3** unchecked `git branch` returncode | non-zero branch returncode → `down` ("git branch --show-current failed"), no false "detached" | `sources.py:493` |
| **FIX 4** `ok` + warning tolerated | `ok` with a non-null warning is demoted to `degraded` centrally | `aggregator.py:129-130` |
| **FIX 5** `"false"` truthy | `fresh` must be a real `bool`; anything else → `down` with "non-boolean fresh value" | `aggregator.py:121` |
| **FIX 6** critical `unknown` could stay healthy | any critical source `unknown` forces overall `down/red` + warning (score remains the contract's renormalized value) | `aggregator.py:239,288` |
| **FIX 7** `relative_to` ValueError escape | falls back to `path.name`, so a probe never raises | `sources.py:163` |

Original D2 tests (all in `tests/test_axis_status.py`):

- `test_cto_schema_drift_is_down` — 0-byte DB + fake running process → `cto=down`, overall `80/degraded`
- `test_critical_unknown_forces_overall_down` — partial probes map, `busd=unknown` → overall `down/red`
- `test_git_branch_failure_is_down`
- `test_ok_with_warning_is_demoted`
- `test_non_boolean_fresh_is_down`
- `test_newest_source_survives_relative_to_failure`

No `return _result("unknown"` remains in `sources.py`; `unknown` is only the
unregistered-probe branch, and a critical one now forces `down`.

---

## 2b. D3-driven hardening (post-D2, uncommitted)

| Finding | Change | Location | Test |
|:--------|:-------|:---------|:-----|
| **M1** busd partial payload was `ok` | absent `rules_in_sync`/`version`/`uptime_seconds` → `degraded` + "partial measurement" warning. Present-but-bad values keep their existing warnings; fields that were present stay in `detail`. | `sources.py:245-258` (`probe_busd`) | `test_busd_partial_payload_is_degraded` (`tests/test_axis_status.py:271`) |
| **N1** `score_sources()` partial rows were healthy | `present = {row["id"]}`; absent critical → force `down/red`, keep the renormalized score, add `missing_critical` + warning. `_build_payload` moves the warning to the top level and keeps `overall` exactly `{status, score, color}`. | `aggregator.py:205-254`, `aggregator.py:274-279` | `test_score_sources_missing_critical_is_down` (`tests/test_axis_status.py:146`) |

Post-hardening SHA-256 (also recorded in the D3 evidence `sha256.txt`):

| File | SHA-256 |
|:-----|:--------|
| `axis_mcp/status/sources.py` | `1e223b6eec809159a1e69f97b65150854d9c0734e24fcf2151c9659fad54ab3e` |
| `axis_mcp/status/aggregator.py` | `d8b6e3e1e0bef636e31446ea532ac619da72d07ed21fcce3cea7a7c640f977e3` |
| `tests/test_axis_status.py` | `17a7eac0e18c0eb921d8fe061cb48776c67bf260794349fcd39f2977e5132a3a` |

The MCP tool path is unchanged: `aggregate()` always supplies all seven rows,
so `missing_critical` is empty there and `overall` keeps its contract shape.
The fixes only affect the two false-green inputs.

D3 re-ran all 37 cases after the fixes: **35 PASS / 0 FAIL / 2 SKIP**, exit 0.
M1 and N1 are now PASS; L1 (CTO column drift) and O1 (empty codegraph) remain
SKIP-NA because the contract defines no threshold. D3 evidence:
`docs/certification/D3-axis-status-2026-11-23.md` and
`bus/evidence/2026-11-23/d3-axis-status/`.

No other product behavior changed. The 31-test suite passes, the D2 harness
re-ran 11/11, and the live smoke remains `down/63` for the same contract
reasons as the D2 pass (busd half, browse down, stale MCP generations).

---

## 3. Commands + exit codes + evidence provenance

All evidence was produced **after the final product-code edit**: `sources.py`
15:29:51, `aggregator.py` 15:30:09, `tests/test_axis_status.py` 15:30:36 local
time. Evidence mtimes are 15:34:11–15:34:51 local time.

| # | Command | Result | Exit | Evidence (mtime, local +07) |
|:-:|:--------|:-------|:----:|:-----------------|
| 1 | `PYTHONPATH=. .venv/bin/python3 -m pytest tests/test_axis_status.py -q` | `31 passed in 5.99s` | **0** | `run.log` 15:34:11.321 |
| 2 | `PYTHONPATH=. .venv/bin/python3 -m axis_mcp.status.server --smoke` | valid `axis.status/1`, 7 sources | **0** | `smoke.json` 15:34:17.895 |
| 3 | `PYTHONPATH=. .venv/bin/python3 scripts/d2_axis_status_check.py` | `11/11 checks passed · 157 ms` | **0** | `tool-calls.jsonl` 15:34:42.891 and `harness.log` 15:34:42.892 — **same invocation** |
| 4 | MCP stdio client → `axis_status(force=True)` | 1 tool, 7 sources, `isError=false` | **0** | `mcp-call.log` 15:34:51.429 |
| 5 | direct aggregator classification repros | see §5 | **0** | `classification-check.log` 15:34:49.560 |
| 6 | `git status --porcelain` | see §8 | — | — |

### 3.1 Evidence regeneration (this pass)

| File | mtime (local +07) | Produced by |
|:-----|:------------------|:------------|
| `run.log` | 2026-11-23 15:34:11.321 | pytest command (stdout+stderr, exit code appended) |
| `smoke.json` | 2026-11-23 15:34:17.895 | `python -m axis_mcp.status.server --smoke` |
| `tool-calls.jsonl` | 2026-11-23 15:34:42.891 | `scripts/d2_axis_status_check.py` |
| `harness.log` | 2026-11-23 15:34:42.892 | `scripts/d2_axis_status_check.py` (same invocation) |
| `classification-check.log` | 2026-11-23 15:34:49.560 | `/tmp/opencode/d3probe/d2_classification_check.py` (not committed) |
| `mcp-call.log` | 2026-11-23 15:34:51.429 | `/tmp/opencode/d3probe/d2_mcp_call.py` (not committed) |
| `report.md` | after the pass above | manual update from the regenerated evidence |

The harness opens no shell redirection for its own log: `check()` accumulates
lines in `LINES`, and one `LOG_PATH.write_text(...)` at the end writes the log
for the same run that wrote `tool-calls.jsonl` (both mtimes are 1 ms apart).
Running the harness again rewrites both together, so a later audit run cannot
desynchronise them; those two mtimes then advance to that run.
`tool-calls.jsonl` is the harness's own probe pass (real probes,
aggregator-enforced 1200 ms per-source timeout), not the tool's internal calls
and not "every call ever made".

`report.md` was written after the evidence pass above; it is not itself part of
the measured snapshot.

---

## 4. Live smoke result (`smoke.json`, 2026-11-23T08:34:17Z, `meta.duration_ms = 159`)

| source | status | latency_ms | fresh | warning |
|:-------|:-------|-----------:|:-----:|:--------|
| busd | degraded | 65 | true | 1 failed queue item(s) awaiting retry |
| cto | ok | 108 | true | — |
| content | degraded | 157 | false | content MCP process is older than the newest axis_mcp source — restart before trusting its answers |
| mcp_freshness | degraded | 122 | false | 6 MCP process(es) older than axis_mcp/status/aggregator.py — restart before trusting results (axis_mcp.bus_mcp, axis_mcp.cto.server, axis_mcp.departments.content_mcp) |
| git | ok | 31 | true | — |
| browse | down | 15 | false | browse relay is not running at http://127.0.0.1:19988 (it starts when an agent uses browse) |
| codegraph | ok | 14 | true | — |

**overall:** `{"status": "down", "score": 63, "color": "red"}`

Arithmetic (contract §4): busd 25×0.5 = 12.5 · cto 20 · content 15×0.5 = 7.5 ·
mcp_freshness 15×0.5 = 7.5 · git 10 · browse 10×0 = 0 · codegraph 5 → **62.5 → 63**.
No critical source is `down` or `unknown`; 63 < 70 → `down`.

Loss sizes: the **largest single loss is busd (12.5 pts)**, then browse (10 pts),
then the two freshness halves (7.5 pts each, 15 pts combined). The freshness
loss exists because the M1/N1 edits made `axis_mcp/status/aggregator.py` the
newest source at 08:30:09Z; the running generations started at 06:30:54Z and
08:28:02Z, both older.

Codegraph at the final run: **7882 nodes / 14729 edges / 388 files**, 18.5 MB,
DB mtime 08:32:56Z, daemon running. The index grows as the daemon re-indexes
edits, so these figures are a snapshot of the cited run; `smoke.json` is
authoritative for this pass.

No source is `unknown` in the live run. At this pass **6 MCP processes across
two generations** were running (pids 4352–4354, started 06:30:54Z; pids
83142–83144, started 08:28:02Z). All six are older than the newest source, so
`mcp_freshness` is degraded. This evidence pass did not start or stop any of
them.

---

## 5. Direct classification proofs (verification #4)

`classification-check.log` (the first four are the original D2 proofs; the last
two are the D3-driven M1/N1 proofs):

```
content process absent: probe=down fresh=False warning='content MCP process is not running — restart_required cannot be read; start it from the client to verify'
  overall={"status": "degraded", "score": 85, "color": "amber"}
cto db unreadable: probe=down fresh=False warning='CTO database could not be read read-only — measurement failed'
  overall={"status": "degraded", "score": 80, "color": "amber"}
cto schema drift + process running: probe=down fresh=False warning='CTO database is missing required table(s): build_artifacts, qa_evidence, tool_calls — measurement failed'
  overall={"status": "degraded", "score": 80, "color": "amber"}
critical unknown (busd missing probe): probe=unknown fresh=False warning='no probe registered for this source'
  overall={"status": "down", "score": 100, "color": "red"}
  warnings=["busd: no probe registered for this source", "critical source(s) busd could not be measured \u2014 overall forced down"]
busd partial payload (M1): probe=degraded fresh=True warning='busd health payload is missing required field(s): rules_in_sync, version, uptime_seconds — partial measurement'
  overall={"status": "degraded", "score": 88, "color": "amber"}
  warnings=["busd: busd health payload is missing required field(s): rules_in_sync, version, uptime_seconds \u2014 partial measurement"]
score_sources partial (git+cto) (N1): {"status": "down", "score": 100, "color": "red", "missing_critical": ["busd", "mcp_freshness"], "warning": "critical source(s) missing from the score: busd, mcp_freshness \u2014 overall forced down"}
```

- content weight 15 at zero → 85, amber.
- cto weight 20 at zero → 80, amber (both DB-unreadable and schema-drift).
- critical-unknown keeps the contract's renormalized score (100 over measured
  weights) but forces `status=down/red` because a critical source is unverified.
- M1: busd weight 25 at half → 87.5 → 88, amber. The payload keeps the fields
  it did get and names the missing ones; no values are invented.
- N1: git+cto carry 30 weight and renormalize to 100, but the absent
  `busd`/`mcp_freshness` force `down/red`; the warning names both. The payload's
  `overall` remains exactly `{status, score, color}`.

---

## 6. Decisions / deviations (explicit)

1. **busd without `SOLOCORP_API_KEY`.** `central_bus/main.py:104` allowlists
   `/v1/health`; a keyless GET returns 200 here. The probe sends the key only
   when set and reports `down` + `"SOLOCORP_API_KEY missing"` only on 401/403.
2. **Content `restart_required`.** Server-to-server MCP calls are prohibited,
   so the probe reconstructs the same fact from `/proc` + source mtimes using
   the same predicate as `runtime_freshness.py`, labelled in
   `detail.freshness_method`. Process absent → `down`.
3. **CTO process absent but DB readable → `degraded`.** The declared CTO
   measurement (its SQLite DB with all required tables, `quick_check=ok`)
   succeeded; only the on-demand MCP process is idle. DB missing/unreadable or
   missing tables → `down`.
4. **Process start time.** `/proc/<pid>/stat` field 22 (the `/proc/<pid>`
   directory mtime drifts when fds are added — observed +20 s here).
5. **browse pairing.** Relay up but pairing unreadable → `degraded`; CLI
   failure falls through to the TCP probe and ends `down` if no listener.
6. **All-unknown snapshot.** `down/0/red` plus a warning, never `healthy`.
7. **Freshness invariant.** `ok` must be `fresh`; `ok` with `fresh=false` is
   demoted to `degraded`. `ok` with any warning is demoted centrally.
8. **Freshness inequality.** Stale **iff** `newest_mtime > process_started +
   1.0` (matches `runtime_freshness.py`). Contract §6 writes the tolerance with
   the inequality reversed; the contract text was **not** edited.
9. **Critical unknown.** Contract does not specify it; overall is forced
   `down/red` (score stays the renormalized value) so a partial probe map cannot
   produce a green critical.
10. **D3-driven hardening (M1/N1).** `probe_busd` treats absent
    `rules_in_sync`/`version`/`uptime_seconds` as a partial measurement
    (`degraded` + warning). `score_sources` treats an absent critical source as
    unmeasured (`down/red` + warning + `missing_critical`); `_build_payload`
    moves that warning to the top level and keeps `overall` exactly
    `{status, score, color}`. The MCP path is unchanged because `aggregate`
    always supplies all seven rows.

---

## 7. Known limitations

- Live `overall=down` is contract arithmetic, not a probe failure: busd 12.5 +
  browse 10 + freshness 15. Restarting the stale MCP generations (not done here)
  clears the staleness; the relay starts on demand.
- **M1 (fixed in this tree):** a busd payload missing
  `rules_in_sync`/`version`/`uptime_seconds` used to return `ok`; it now returns
  `degraded` + a partial-measurement warning. Covered by
  `test_busd_partial_payload_is_degraded` and D3 M1.
- **N1 (fixed in this tree):** `score_sources()` with rows missing a critical
  source used to return healthy; it now forces `down/red` + a warning naming
  the missing source(s), while `_build_payload` keeps `overall` exactly
  `{status, score, color}`. Covered by
  `test_score_sources_missing_critical_is_down` and D3 N1.
- **L1/O1 (D3 SKIP-NA):** CTO column drift and an empty codegraph index have no
  contract threshold; recorded as SKIP-NA in D3, not silently green.
- **NIT-4 disclosure:** `codegraph.fresh` is `true` because the probe reads the
  live DB; index age is reported in `detail.db_mtime` but there is no contract
  threshold to judge it. Left as-is rather than inventing one.
- Cache is process-local (10 s per server instance); `force=True` bypasses it.
- The server is **not** registered in `opencode.jsonc` — contract §8 defers
  that to a separate PR after D4.
- `browse` extension-pairing semantics could not be exercised against a live
  relay (relay was down); the code degrades rather than guessing.
- `cto`/`codegraph` probes read SQLite directly; an unexpected schema now
  returns `down` + warning.
- `tests/test_axis_status.py` runs with the repo's coverage plugin, which prints
  a "No data was collected" warning; the current suite is **31 passed**. The
  audited D2 commit `fbb5dc3` had 29 tests.
- The M1/N1 fixes and the regenerated D2 evidence are **uncommitted**. The D2
  commit `fbb5dc3` remains the audited baseline; an independent checker must
  re-audit the current tree.

---

## 8. Workspace state / not done

`git status --porcelain` after the evidence pass and this report update:

```
 M axis_mcp/status/aggregator.py
 M axis_mcp/status/sources.py
 M brain/learnt.md
 M bus/evidence/2026-11-23/d2-axis-status/classification-check.log
 M bus/evidence/2026-11-23/d2-axis-status/harness.log
 M bus/evidence/2026-11-23/d2-axis-status/mcp-call.log
 M bus/evidence/2026-11-23/d2-axis-status/report.md
 M bus/evidence/2026-11-23/d2-axis-status/run.log
 M bus/evidence/2026-11-23/d2-axis-status/smoke.json
 M bus/evidence/2026-11-23/d2-axis-status/tool-calls.jsonl
 M tests/test_axis_status.py
?? config/.module-registry.json.lock
?? docs/certification/D3-axis-status-2026-11-23.md
?? scripts/d3_axis_status_eval.py
```

- `axis_mcp/status/sources.py`, `axis_mcp/status/aggregator.py` and
  `tests/test_axis_status.py` carry the M1/N1 fixes; no other product files
  changed.
- The six tracked D2 evidence files above were regenerated; `report.md` is
  updated by this write.
- `brain/learnt.md` was already modified before this session started; not mine.
- `config/.module-registry.json.lock` is a 0-byte runtime lock created by the
  **existing** `axis_mcp/module_registry.py` when the MCP host loaded servers;
  it is left in place.
- `docs/certification/D3-axis-status-2026-11-23.md` and
  `scripts/d3_axis_status_eval.py` are the D3 deliverables; `bus/evidence/` is
  gitignored, so the D3 evidence directory does not appear in `git status`.

Not done: no commit, no push, no branch change; no edits to `opencode.jsonc`,
`central_bus/`, existing `axis_mcp` servers, `brain/`, or `bus.db`; no process
killed or restarted; no DB writes (all SQLite opens are `mode=ro`); no
POST/PUT/PATCH; loopback only; no secret in any output or log.

---

## 9. Verification of no unrelated behavior change

- The product diff is limited to `sources.py` (+15 lines: M1 guard and comment),
  `aggregator.py` (+33 lines: N1 guard, `missing_critical` annotation,
  `_build_payload` pop and comments) and `tests/test_axis_status.py` (+86 lines:
  two tests and one fake-response helper).
- D2 suite: **31 passed**, exit 0.
- D2 harness: **11/11**, exit 0.
- Live smoke: `axis.status/1`, 7 sources, exit 0; `overall=down/63` for the same
  contract reasons as the D2 pass.
- D3: **35 PASS / 0 FAIL / 2 SKIP**, exit 0; M1/N1 PASS; L1/O1 remain SKIP-NA.
- The only behavior changes are the two false-green guards; no other probe,
  score, cache, timeout or redaction path changed.
