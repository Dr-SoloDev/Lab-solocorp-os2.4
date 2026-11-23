# D2 — AXIS STATUS C1 (Unified Status Layer)

> **Branch:** `feat/axis-status-c1` · **Date:** 2026-11-23 · **Maker:** CTO/`build` (subagent)
> **Contract:** [AXIS-STATUS-CONTRACT-v1.0.md](../../../docs/plans/AXIS-STATUS-CONTRACT-v1.0.md) · **D1:** [AXIS-STATUS-C0-D1-v1.0.md](../../../docs/plans/AXIS-STATUS-C0-D1-v1.0.md)

Read-only status layer: one MCP tool `axis_status(force=False)` returning
`axis.status/1` for 7 sources, with per-source isolation, parallel fan-out,
1200 ms per-source / 2000 ms total budgets, weighted scoring and a 10 s cache.

---

## 1. Files added (final)

| File | Lines | Role |
|:-----|------:|:-----|
| `axis_mcp/status/__init__.py` | 29 | package exports |
| `axis_mcp/status/sources.py` | 660 | 7 read-only probes + freshness helper |
| `axis_mcp/status/aggregator.py` | 312 | fan-out, timeout, scoring, cache, redaction |
| `axis_mcp/status/server.py` | 51 | FastMCP server `axis-status`, one tool, `--smoke` |
| `tests/test_axis_status.py` | 465 | 29 deterministic tests (mocked probes) |
| `scripts/d2_axis_status_check.py` | 149 | D2 harness (11 checks; writes its own log) |

---

## 2. Re-audit findings — what changed

| Finding | Change | Location |
|:--------|:-------|:---------|
| **FIX 1 (blocker)** CTO schema drift reported green | a missing/unreadable required table is now `down` with `missing_tables` + warning; no more `tables[table]=None` + `ok` | `sources.py:302` (`probe_cto`) |
| **FIX 2 (blocker)** false `tool-calls.jsonl` provenance | the harness now writes `harness.log` **and** `tool-calls.jsonl` from the same invocation (no shell redirection needed); docstring corrected | `scripts/d2_axis_status_check.py:28,118,144` |
| **FIX 3** unchecked `git branch` returncode | non-zero branch returncode → `down` ("git branch --show-current failed"), no false "detached" | `sources.py:473` |
| **FIX 4** `ok` + warning tolerated | `ok` with a non-null warning is demoted to `degraded` centrally | `aggregator.py:129` |
| **FIX 5** `"false"` truthy | `fresh` must be a real `bool`; anything else → `down` with "non-boolean fresh value" | `aggregator.py:112` |
| **FIX 6** critical `unknown` could stay healthy | any critical source `unknown` forces overall `down/red` + warning (score remains the contract's renormalized value) | `aggregator.py:223,261` |
| **FIX 7** `relative_to` ValueError escape | falls back to `path.name`, so a probe never raises | `sources.py:162` |

New tests (all in `tests/test_axis_status.py`):

- `test_cto_schema_drift_is_down` (line 344) — 0-byte DB + fake running process → `cto=down`, overall `80/degraded`
- `test_critical_unknown_forces_overall_down` (line 383) — partial probes map, `busd=unknown` → overall `down/red`
- `test_git_branch_failure_is_down` (line 409)
- `test_ok_with_warning_is_demoted` (line 272)
- `test_non_boolean_fresh_is_down` (line 210)
- `test_newest_source_survives_relative_to_failure` (line 304)

No `return _result("unknown"` remains in `sources.py`; `unknown` is only the
unregistered-probe branch, and a critical one now forces `down`.

---

## 3. Commands + exit codes + evidence provenance

All evidence was produced **after the last code edit** (`sources.py` 14:36:34,
`aggregator.py` 14:37:04, tests 14:39:22, harness 14:40:23 local time).

| # | Command | Result | Exit | Evidence (mtime) |
|:-:|:--------|:-------|:----:|:-----------------|
| 1 | `PYTHONPATH=. .venv/bin/python3 -m pytest tests/test_axis_status.py -q` | `29 passed in 5.95s` | **0** | `run.log` 14:42:49.485 |
| 2 | `PYTHONPATH=. .venv/bin/python3 -m axis_mcp.status.server --smoke` | valid `axis.status/1`, 7 sources | **0** | `smoke.json` 14:42:50.447 |
| 3 | `PYTHONPATH=. .venv/bin/python3 scripts/d2_axis_status_check.py` | `11/11 checks passed · 143 ms` | **0** | `tool-calls.jsonl` 14:42:51.833 and `harness.log` 14:42:51.833 — **same invocation** |
| 4 | MCP stdio client → `axis_status(force=True)` | 1 tool, 7 sources, `isError=false` | **0** | `mcp-call.log` 14:42:53.899 |
| 5 | direct aggregator classification repros | see §5 | **0** | `classification-check.log` 14:42:54.232 |
| 6 | `git status --porcelain` | see §8 | — | — |

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

## 4. Live smoke result (final `smoke.json`, 2026-11-23T07:42:50Z, `meta.duration_ms = 141`)

| source | status | latency_ms | fresh | warning |
|:-------|:-------|-----------:|:-----:|:--------|
| busd | degraded | 52 | true | 1 failed queue item(s) awaiting retry |
| cto | ok | 96 | true | — |
| content | degraded | 139 | false | content MCP process is older than the newest axis_mcp source — restart before trusting its answers |
| mcp_freshness | degraded | 103 | false | 3 MCP process(es) older than axis_mcp/status/aggregator.py — restart before trusting results |
| git | ok | 27 | true | — |
| browse | down | 12 | false | browse relay is not running at http://127.0.0.1:19988 (it starts when an agent uses browse) |
| codegraph | ok | 10 | true | — |

**overall:** `{"status": "down", "score": 63, "color": "red"}`

Arithmetic (contract §4): busd 25×0.5 = 12.5 · cto 20 · content 15×0.5 = 7.5 ·
mcp_freshness 15×0.5 = 7.5 · git 10 · browse 10×0 = 0 · codegraph 5 → **62.5 → 63**.
No critical source is `down` or `unknown`; 63 < 70 → `down`.

Loss sizes: the **largest single loss is busd (12.5 pts)**, then browse (10 pts),
then the two freshness halves (7.5 pts each, 15 pts combined). The freshness
loss exists because this C1 work added `axis_mcp/status/*.py` after the running
MCP processes started (06:30:54Z); the newest source is
`axis_mcp/status/aggregator.py` at 07:37:04Z.

Codegraph at the final run: **7760 nodes / 14357 edges / 387 files**, 18.5 MB,
DB mtime 07:40:25Z, daemon running. The index grows as the daemon re-indexes
edits, so these figures are a snapshot of the cited run; `smoke.json` is
authoritative for this pass.

No source is `unknown` in the live run. At this final pass only 3 MCP processes
(one generation, pids 4352–4354) were running — the earlier duplicate
generation was gone. I did not stop or restart any process.

---

## 5. Direct classification proofs (verification #4)

`classification-check.log`:

```
content process absent: probe=down fresh=False
  overall={"status": "degraded", "score": 85, "color": "amber"}
cto db unreadable: probe=down fresh=False
  overall={"status": "degraded", "score": 80, "color": "amber"}
cto schema drift + process running: probe=down fresh=False
  warning='CTO database is missing required table(s): build_artifacts, qa_evidence, tool_calls — measurement failed'
  overall={"status": "degraded", "score": 80, "color": "amber"}
critical unknown (busd missing probe): probe=unknown fresh=False
  overall={"status": "down", "score": 100, "color": "red"}
  warnings=["busd: no probe registered for this source",
            "critical source(s) busd could not be measured — overall forced down"]
```

- content weight 15 at zero → 85, amber.
- cto weight 20 at zero → 80, amber (both DB-unreadable and schema-drift).
- critical-unknown keeps the contract's renormalized score (100 over measured
  weights) but forces `status=down/red` because a critical source is unverified.

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

---

## 7. Known limitations

- Live `overall=down` is contract arithmetic, not a probe failure: busd 12.5 +
  browse 10 + freshness 15. Restarting the 3 MCP processes (not done here)
  clears the staleness; the relay starts on demand.
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
  a "No data was collected" warning; the suite itself is 29 passed.

---

## 8. Workspace state / not done

`git status --porcelain` after the final pass:

```
 M brain/learnt.md
?? axis_mcp/status/
?? config/.module-registry.json.lock
?? scripts/d2_axis_status_check.py
?? tests/test_axis_status.py
```

- `brain/learnt.md` was already modified before this session started; not mine.
- `config/.module-registry.json.lock` is a 0-byte runtime lock created at
  14:04 by the **existing** `axis_mcp/module_registry.py` (line 322) when the
  MCP host loaded servers. The new `axis_mcp/status/` code contains no write
  calls (verified by grep); the file is left in place.

Not done: no commit, no push, no branch change; no edits to `opencode.jsonc`,
`central_bus/`, existing `axis_mcp` servers, `brain/`, or `bus.db`; no process
killed or restarted; no DB writes (all SQLite opens are `mode=ro`); no
POST/PUT/PATCH; loopback only; no secret in any output or log.
