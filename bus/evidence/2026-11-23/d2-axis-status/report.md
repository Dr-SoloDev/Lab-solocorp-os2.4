# D2 — AXIS STATUS C1 (Unified Status Layer)

> **Branch:** `feat/axis-status-c1` · **Date:** 2026-11-23 · **Maker:** CTO/`build` (subagent)
> **Contract:** [AXIS-STATUS-CONTRACT-v1.1.md](../../../docs/plans/AXIS-STATUS-CONTRACT-v1.1.md) (v1.1 amends v1.0) · **D1:** [AXIS-STATUS-C0-D1-v1.0.md](../../../docs/plans/AXIS-STATUS-C0-D1-v1.0.md)
> **Post-D2 hardening:** 2026-11-23 — contract v1.1 (Plan B) + previous M1/N1 fixes, uncommitted; see §2b.

Read-only status layer: one MCP tool `axis_status(force=False)` returning
`axis.status/1` for 7 sources, with per-source isolation, parallel fan-out,
1200 ms per-source / 2000 ms total budgets, weighted scoring and a 10 s cache.

**Timeline — read this first.** The D2 commit `fbb5dc3` passed the independent
audit with **29 tests** and contract v1.0. D3 then found two false-green paths
(M1: busd partial payload; N1: `score_sources()` partial rows); those were fixed
in the previous working-tree round. That round and its 37-case D3 evidence were
later committed by another process as `53d1f35` and `172740e`. Contract v1.1
(Owner-approved, Plan B) then closed the remaining L1/O1 gaps and tightened busd
field validation. The v1.1 changes in this report are **uncommitted on top of
`172740e`**; the current tree has **40 tests**. This report's evidence pass was
regenerated **after** the final v1.1 product-code edit. The D2 commit itself is
unchanged; the current tree needs its own re-audit.

---

## 1. Files (current working tree)

| File | Lines | Role |
|:-----|------:|:-----|
| `axis_mcp/status/__init__.py` | 29 | package exports |
| `axis_mcp/status/sources.py` | 748 | 7 read-only probes + freshness helper + v1.1 guards |
| `axis_mcp/status/aggregator.py` | 341 | fan-out, timeout, scoring, cache, redaction, missing-critical guard, `_build_payload` robustness |
| `axis_mcp/status/server.py` | 51 | FastMCP server `axis-status`, one tool, `--smoke` |
| `tests/test_axis_status.py` | 799 | 40 deterministic tests (mocked probes) |
| `scripts/d2_axis_status_check.py` | 149 | D2 harness (11 checks; writes its own log) |

The audited D2 commit `fbb5dc3` had the pre-hardening counts: `sources.py` 660,
`aggregator.py` 312, `tests/test_axis_status.py` 465 / 29 tests. The first
hardening round raised the tree to 675/339/551 / 31 tests; contract v1.1 raised
it to 748/341/799 / 40 tests. No other product files changed.

D3 uses `scripts/d3_axis_status_eval.py` (2574 lines) and
`docs/certification/D3-axis-status-2026-11-23.md`; they are separate D3
deliverables, not part of the D2 artifact.

---

## 2. Re-audit findings — what changed (original D2)

| Finding | Change | Location |
|:--------|:-------|:---------|
| **FIX 1 (blocker)** CTO schema drift reported green | a missing/unreadable required table is now `down` with `missing_tables` + warning; no more `tables[table]=None` + `ok` | `sources.py:358` (`probe_cto`) |
| **FIX 2 (blocker)** false `tool-calls.jsonl` provenance | the harness now writes `harness.log` **and** `tool-calls.jsonl` from the same invocation (no shell redirection needed); docstring corrected | `scripts/d2_axis_status_check.py:27-28,120,144` |
| **FIX 3** unchecked `git branch` returncode | non-zero branch returncode → `down` ("git branch --show-current failed"), no false "detached" | `sources.py:552` |
| **FIX 4** `ok` + warning tolerated | `ok` with a non-null warning is demoted to `degraded` centrally | `aggregator.py:129-130` |
| **FIX 5** `"false"` truthy | `fresh` must be a real `bool`; anything else → `down` with "non-boolean fresh value" | `aggregator.py:121` |
| **FIX 6** critical `unknown` could stay healthy | any critical source `unknown` forces overall `down/red` + warning (score remains the contract's renormalized value) | `aggregator.py:239,290` |
| **FIX 7** `relative_to` ValueError escape | falls back to `path.name`, so a probe never raises | `sources.py:170` |

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

## 2b. Contract v1.1 hardening (post-D2, uncommitted)

| # | Contract change | Code | Tests | D3 |
|:-:|:----------------|:-----|:------|:---|
| 1 | **CTO required columns** — `tool_calls`: id/module/tool_name/status; `build_artifacts`: id/project_id/artifact_path; `qa_evidence`: id/task_id/status. Missing table stays `down` + `missing_tables`; missing columns → `down` + `missing_columns` + warning. Tables+columns complete with 0 rows → `ok`. | `CTO_REQUIRED_COLUMNS` at `sources.py:58`; `probe_cto` checks at `sources.py:351-381` | `test_cto_missing_required_column_is_down` (`tests:570`), `test_cto_full_columns_zero_rows_is_ok` (`tests:611`) | **L1 PASS**, **L2 PASS** |
| 2 | **Codegraph thresholds** — `files == 0` or `nodes == 0` → `degraded` + "index is empty"; `nodes > 0` and `edges == 0` → `degraded` + "index has no edges"; else `ok`. Unreadable/missing tables stay `down`. | `probe_codegraph` at `sources.py:726-738` | `test_codegraph_zero_files_is_degraded` (`tests:732`), `test_codegraph_zero_nodes_is_degraded` (`tests:753`), `test_codegraph_nodes_without_edges_is_degraded` (`tests:764`), `test_codegraph_positive_counts_is_ok` (`tests:775`) | **O1 PASS**, **O2 PASS**, **O3 PASS** |
| 3 | **busd required fields non-null/typed** — `status` string; `rules_in_sync` bool; `version` non-empty string; `uptime_seconds` int ≥ 0. Missing/null/wrong type → `degraded` + warning naming the bad fields. | `_is_nonneg_int` at `sources.py:195`; `probe_busd` invalid-field check at `sources.py:260-300` | `test_busd_partial_payload_is_degraded` (`tests:312`), `test_busd_null_field_is_degraded` (`tests:350`) | **M1 PASS**, **M2 PASS** |
| 4 | **busd `db` block required** — dict with `queue_pending`/`queue_failed`/`queue_dead` int ≥ 0; missing/wrong type → `degraded` + warning. Existing queue_failed/dead/rules_in_sync=false warnings stay. | `probe_busd` invalid-field check at `sources.py:260-300` | `test_busd_invalid_db_block_is_degraded` (`tests:385`) | **M3 PASS** |
| 5 | **`_build_payload` robustness** — use `row.get("warning")`; a row without the key does not raise. | `aggregator.py:271-280` (`row.get` at `:279`) | `test_build_payload_row_without_warning_key_is_safe` (`tests:195`) | **N2 PASS** |

The previous M1 fix (missing fields → degraded) is now covered by the stricter
contract v1.1 field validation: missing, null and wrong-typed fields all produce
one `invalid field(s)` warning. The previous N1 fix (`score_sources` with a
missing critical source → `down/red` + warning) remains in place
(`aggregator.py:205-254`; `test_score_sources_missing_critical_is_down` at
`tests:146`; D3 **N1 PASS**).

Post-v1.1 SHA-256 (also recorded in the D3 evidence `sha256.txt`):

| File | SHA-256 |
|:-----|:--------|
| `axis_mcp/status/sources.py` | `902b13ac8dec72421632f38a7e9d8c40d9210270a827a96fa416e335806b9c66` |
| `axis_mcp/status/aggregator.py` | `319e1f08de46be36616d1021cdcbf3f3c3b99b3d934b31f51b1a883727be5723` |
| `tests/test_axis_status.py` | `7f258a295bcae7fc96af40eacba102f7e8eb34ae1ee19531a06fa383f13723ad` |

The MCP tool path is unchanged: `aggregate()` always supplies all seven rows,
so `missing_critical` is empty there and `overall` keeps its contract shape.
The v1.1 guards only affect the partial/invalid inputs.

D3 re-ran all **43 cases** after the fixes: **43 PASS / 0 FAIL / 0 SKIP**, exit
0. L1/O1 are now PASS (no SKIP-NA remains); M1/M2/M3/N1/N2/L2/O2/O3 are PASS.
D3 evidence: `docs/certification/D3-axis-status-2026-11-23.md` and
`bus/evidence/2026-11-23/d3-axis-status/`.

No other product behavior changed. The 40-test suite passes, the D2 harness
re-ran 11/11, and the live smoke remains `down/63` for the same contract
reasons as the D2 pass (busd half, browse down, stale MCP generations).

---

## 3. Commands + exit codes + evidence provenance

All evidence was produced **after the final product-code edit**: `sources.py`
16:24:14, `aggregator.py` 16:24:19, `tests/test_axis_status.py` 16:25:52 local
time. Evidence mtimes are 16:29:51–16:30:16 local time.

| # | Command | Result | Exit | Evidence (mtime, local +07) |
|:-:|:--------|:-------|:----:|:-----------------|
| 1 | `PYTHONPATH=. .venv/bin/python3 -m pytest tests/test_axis_status.py -q` | `40 passed in 6.25s` | **0** | `run.log` 16:29:51.225 |
| 2 | `PYTHONPATH=. .venv/bin/python3 -m axis_mcp.status.server --smoke` | valid `axis.status/1`, 7 sources | **0** | `smoke.json` 16:29:56.599 |
| 3 | `PYTHONPATH=. .venv/bin/python3 scripts/d2_axis_status_check.py` | `11/11 checks passed · 171 ms` | **0** | `tool-calls.jsonl` 16:30:03.509 and `harness.log` 16:30:03.510 — **same invocation** |
| 4 | MCP stdio client → `axis_status(force=True)` | 1 tool, 7 sources, `isError=false` | **0** | `mcp-call.log` 16:30:11.900 |
| 5 | direct aggregator classification repros | see §5 | **0** | `classification-check.log` 16:30:16.899 |
| 6 | `git status --porcelain` | see §8 | — | — |

### 3.1 Evidence regeneration (this pass)

| File | mtime (local +07) | Produced by |
|:-----|:------------------|:------------|
| `run.log` | 2026-11-23 16:29:51.225 | pytest command (stdout+stderr, exit code appended) |
| `smoke.json` | 2026-11-23 16:29:56.599 | `python -m axis_mcp.status.server --smoke` |
| `tool-calls.jsonl` | 2026-11-23 16:30:03.509 | `scripts/d2_axis_status_check.py` |
| `harness.log` | 2026-11-23 16:30:03.510 | `scripts/d2_axis_status_check.py` (same invocation) |
| `mcp-call.log` | 2026-11-23 16:30:11.900 | `/tmp/opencode/d3probe/d2_mcp_call.py` (not committed) |
| `classification-check.log` | 2026-11-23 16:30:16.899 | `/tmp/opencode/d3probe/d2_classification_check.py` (not committed) |
| `report.md` | after the pass above | this update from the regenerated evidence |

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

## 4. Live smoke result (`smoke.json`, 2026-11-23T09:29:56Z, `meta.duration_ms = 166`)

| source | status | latency_ms | fresh | warning |
|:-------|:-------|-----------:|:-----:|:--------|
| busd | degraded | 61 | true | 1 failed queue item(s) awaiting retry |
| cto | ok | 116 | true | — |
| content | degraded | 163 | false | content MCP process is older than the newest axis_mcp source — restart before trusting its answers |
| mcp_freshness | degraded | 126 | false | 3 MCP process(es) older than axis_mcp/status/aggregator.py — restart before trusting results (axis_mcp.bus_mcp, axis_mcp.cto.server, axis_mcp.departments.content_mcp) |
| git | ok | 47 | true | — |
| browse | down | 19 | false | browse relay is not running at http://127.0.0.1:19988 (it starts when an agent uses browse) |
| codegraph | ok | 12 | true | — |

**overall:** `{"status": "down", "score": 63, "color": "red"}`

Arithmetic (contract §4): busd 25×0.5 = 12.5 · cto 20 · content 15×0.5 = 7.5 ·
mcp_freshness 15×0.5 = 7.5 · git 10 · browse 10×0 = 0 · codegraph 5 → **62.5 → 63**.
No critical source is `down` or `unknown`; 63 < 70 → `down`.

Loss sizes: the **largest single loss is busd (12.5 pts)**, then browse (10 pts),
then the two freshness halves (7.5 pts each, 15 pts combined). The freshness
loss exists because the contract v1.1 edits made `axis_mcp/status/aggregator.py`
the newest source at 09:24:19Z; the running generation started at 06:30:54Z.

Codegraph at the final run: **7903 nodes / 14813 edges / 388 files**, 18.5 MB,
DB mtime 09:29:00Z, daemon running. The index grows as the daemon re-indexes
edits, so these figures are a snapshot of the cited run; `smoke.json` is
authoritative for this pass.

No source is `unknown` in the live run. At this pass **3 MCP processes** were
running (pids 4352–4354, started 06:30:54Z), all older than the newest source,
so `mcp_freshness` is degraded. This evidence pass did not start or stop any of
them.

---

## 5. Direct classification proofs (verification #4)

`classification-check.log` (first four = original D2; next two = previous M1/N1
hardening; last four = contract v1.1):

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
busd partial payload (M1): probe=degraded fresh=True warning='busd health payload has invalid field(s): rules_in_sync (None), version (None), uptime_seconds (None)'
  overall={"status": "degraded", "score": 88, "color": "amber"}
  warnings=["busd: busd health payload has invalid field(s): rules_in_sync (None), version (None), uptime_seconds (None)"]
score_sources partial (git+cto) (N1): {"status": "down", "score": 100, "color": "red", "missing_critical": ["busd", "mcp_freshness"], "warning": "critical source(s) missing from the score: busd, mcp_freshness \u2014 overall forced down"}
cto missing required column (L1): probe=down fresh=False warning='CTO database is missing required column(s): tool_calls: status — measurement failed'
  overall={"status": "degraded", "score": 80, "color": "amber"}
codegraph empty (O1): probe=degraded fresh=True warning='codegraph index is empty — rebuild the index'
  overall={"status": "healthy", "score": 98, "color": "green"}
busd null field (M2): probe=degraded fresh=True warning='busd health payload has invalid field(s): version (None)'
  overall={"status": "degraded", "score": 88, "color": "amber"}
_build_payload row without warning (N2): overall={"status": "healthy", "score": 100, "color": "green"} warnings=[] warning_keys=0
```

- content weight 15 at zero → 85, amber.
- cto weight 20 at zero → 80, amber (both DB-unreadable and schema-drift;
  the new wrong-column proof also lands at 80).
- critical-unknown keeps the contract's renormalized score (100 over measured
  weights) but forces `status=down/red` because a critical source is unverified.
- M1 (missing fields) and M2 (null version): busd weight 25 at half → 87.5 → 88,
  amber; the warning names the bad fields; no values are invented.
- N1: git+cto carry 30 weight and renormalize to 100, but the absent
  `busd`/`mcp_freshness` force `down/red`; the warning names both. The payload's
  `overall` remains exactly `{status, score, color}`.
- L1: a table with the wrong columns is `down` + `missing_columns`; the score is
  80 (cto at zero), amber.
- O1: an empty index is `degraded`; codegraph's 5 weight at half → 97.5 → 98,
  healthy/green.
- N2: a row without a `warning` key does not raise; the all-ok payload is
  100/healthy/green with no warnings.

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
   measurement (its SQLite DB with all required tables and columns,
   `quick_check=ok`) succeeded; only the on-demand MCP process is idle. DB
   missing/unreadable, missing tables or missing columns → `down`.
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
10. **CTO required columns (v1.1 §1).** Validate `PRAGMA table_info` after the
    table exists; missing columns are `down` + `missing_columns`. Extra columns
    are allowed; zero rows with complete columns is `ok`.
11. **Codegraph thresholds (v1.1 §2).** Empty (`files==0` or `nodes==0`) and
    edge-less (`nodes>0`, `edges==0`) indexes are `degraded`; unreadable DB or
    missing tables remain `down`.
12. **busd required fields (v1.1 §3).** Missing, null or wrong-typed fields are
    `degraded` + one `invalid field(s)` warning; existing queue_failed/dead and
    `rules_in_sync=false` warnings stay. Unreachable/401/403/non-JSON remain
    `down`.
13. **`_build_payload` robustness (v1.1 §4).** Use `row.get("warning")`; a row
    without the key cannot raise. The payload's `overall` stays exactly
    `{status, score, color}`.

---

## 7. Known limitations

- Live `overall=down` is contract arithmetic, not a probe failure: busd 12.5 +
  browse 10 + freshness 15. Restarting the stale MCP generation (not done here)
  clears the staleness; the relay starts on demand.
- **L1/O1 are closed by contract v1.1:** wrong-column CTO is `down/80`, and an
  empty/no-edge codegraph index is `degraded/98`. D3 cases L1/L2 and O1/O2/O3
  are PASS.
- **M1/N1 are fixed in this tree:** busd missing/null/wrong-typed fields are
  `degraded` + invalid-field warning; `score_sources()` with rows missing a
  critical source is `down/red` + warning.
- **NIT-4 remains:** `codegraph.fresh` is `true` because the probe reads the
  live DB; index age is reported in `detail.db_mtime` but there is no contract
  threshold to judge an old-but-populated index.
- Cache is process-local (10 s per server instance); `force=True` bypasses it.
- The server is **not** registered in `opencode.jsonc` — contract §8 defers
  that to a separate PR after D4.
- `browse` extension-pairing semantics could not be exercised against a live
  relay (relay was down); the code degrades rather than guessing.
- `cto`/`codegraph` probes read SQLite directly; an unexpected schema now
  returns `down` + warning, and wrong columns return `missing_columns`.
- `tests/test_axis_status.py` runs with the repo's coverage plugin, which prints
  a "No data was collected" warning; the current suite is **40 passed**. The
  audited D2 commit `fbb5dc3` had 29 tests.
- The contract v1.1 fixes and the regenerated D2 evidence are **uncommitted**.
  The D2 commit `fbb5dc3` remains the audited baseline; an independent checker
  must re-audit the current tree.

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
 M bus/evidence/2026-11-23/d3-axis-status/env.txt
 M bus/evidence/2026-11-23/d3-axis-status/eval.json
 M bus/evidence/2026-11-23/d3-axis-status/eval.log
 M bus/evidence/2026-11-23/d3-axis-status/sha256.txt
 M bus/evidence/2026-11-23/d3-axis-status/table.md
 M docs/certification/D3-axis-status-2026-11-23.md
 M docs/plans/AXIS-STATUS-C0-D1-v1.0.md
 M scripts/d3_axis_status_eval.py
 M tests/test_axis_status.py
?? config/.module-registry.json.lock
?? docs/plans/AXIS-STATUS-CONTRACT-v1.1.md
```

- `axis_mcp/status/sources.py`, `axis_mcp/status/aggregator.py` and
  `tests/test_axis_status.py` carry the contract v1.1 changes; no other product
  files changed.
- The six D2 evidence files above were regenerated; `report.md` is updated by
  this write.
- The D3 docs, harness and evidence were regenerated for contract v1.1; they are
  tracked (force-added in `172740e`) and now appear as modified.
- `docs/plans/AXIS-STATUS-CONTRACT-v1.1.md` is the Owner-approved amendment; it
  is untracked and is hashed by D3 as an evaluated file.
- `docs/plans/AXIS-STATUS-C0-D1-v1.0.md` has a 1-line link update to v1.1 made
  outside this evidence pass; this pass did not edit it.
- `brain/learnt.md` was already modified before this session started; not mine.
- `config/.module-registry.json.lock` is a 0-byte runtime lock created by the
  **existing** `axis_mcp/module_registry.py` when the MCP host loaded servers;
  it is left in place.

Not done by this pass: no commit, no push, no branch change; no edits to
`opencode.jsonc`, `central_bus/`, existing `axis_mcp` servers, `brain/`, or
`bus.db`; no process killed or restarted; no DB writes (all SQLite opens are
`mode=ro`); no POST/PUT/PATCH; loopback only; no secret in any output or log.
HEAD is `172740e`; the earlier M1/N1 round and D3 docs were committed by
another process as `53d1f35`/`172740e`. This v1.1 pass remains uncommitted.

---

## 9. Verification of no unrelated behavior change

- The product diff is limited to contract v1.1: `sources.py` (127 changed
  lines: CTO columns, codegraph thresholds, busd field/db validation),
  `aggregator.py` (4 lines: `_build_payload` `row.get`), and
  `tests/test_axis_status.py` (250 changed lines: the new/updated tests). No
  other product files changed.
- D2 suite: **40 passed**, exit 0.
- D2 harness: **11/11**, exit 0.
- Live smoke: `axis.status/1`, 7 sources, exit 0; `overall=down/63` for the same
  contract reasons as the D2 pass.
- D3: **43 PASS / 0 FAIL / 0 SKIP**, exit 0; L1/O1 are PASS; M1/M2/M3/N1/N2/
  L2/O2/O3 are PASS.
- The only behavior changes are the five contract v1.1 rules (plus the prior
  N1 guard); no schema, weights, critical sources, timeout, cache, freshness,
  redaction or out-of-scope path changed.
