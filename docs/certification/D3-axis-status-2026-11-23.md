# D3 — AXIS STATUS (`axis.status/1`) evaluation

> **Evaluated:** `fbb5dc3` (`feat/axis-status-c1`) + uncommitted M1/N1 hardening · **Date:** 2026-11-23T08:37:52.498333+00:00 · **Evaluator:** `scripts/d3_axis_status_eval.py`
>
> This D3 run evaluates the working tree on the branch: D2 commit `fbb5dc3` plus the uncommitted D3-driven M1/N1 hardening. The only product changes are the two fixes; no other product behavior was changed. FAIL rows would still be recorded with a root cause and a proposed minimal fix; SKIP rows are recorded as SKIP-NA.
>
> **Status: maker evidence, not an approval.** An independent checker must rerun `scripts/d3_axis_status_eval.py`, compare the evidence and confirm the M1/N1 PASS rows and the L1/O1 SKIP-NA decisions before D3 is considered passed.
>
> **Evidence:** `bus/evidence/2026-11-23/d3-axis-status/` (`eval.json`, `eval.log`, `env.txt`, `sha256.txt`, `table.md`).

## 1. Summary

- **Cases:** 37 · **PASS:** 35 · **FAIL:** 0 · **SKIP:** 2
- **Exit code:** `0` (0 only when every non-SKIP case passes)
- **Pytest post-check:** `31 passed in 5.82s` (exit `0`)
- **Product code changed:** **YES — M1/N1 only** (`axis_mcp/status/aggregator.py`, `axis_mcp/status/sources.py`, `tests/test_axis_status.py`)

## 2. What was evaluated

| File | SHA-256 | Size |
|:-----|:--------|-----:|
| `axis_mcp/status/__init__.py` | `43e408c4081a81cdd29cd9927d3b71d1cc3bb1140de6f746b5c89cf9b750d861` | 564 |
| `axis_mcp/status/aggregator.py` | `d8b6e3e1e0bef636e31446ea532ac619da72d07ed21fcce3cea7a7c640f977e3` | 10937 |
| `axis_mcp/status/sources.py` | `1e223b6eec809159a1e69f97b65150854d9c0734e24fcf2151c9659fad54ab3e` | 22624 |
| `axis_mcp/status/server.py` | `29a64e7da1c1ca64b76d9856e2f4f62066ee4cec3c1eff7c9c04943a7cff316b` | 1393 |
| `axis_mcp/runtime_freshness.py` | `46ef56d7d760143a31b398ad796c55782c93166aadb907626711c0a063f72dc6` | 5158 |
| `tests/test_axis_status.py` | `17a7eac0e18c0eb921d8fe061cb48776c67bf260794349fcd39f2977e5132a3a` | 17273 |
| `docs/plans/AXIS-STATUS-CONTRACT-v1.0.md` | `2eb6530b2b0129d22ca90119911a017c30b73e7fe1903fed6dd2f0967dd6514d` | 7066 |
| `scripts/d3_axis_status_eval.py` | `d21b7884dab9286490256600badc67e0865e95c314ee32e7e305b35123e43249` | 76303 |

## 3. Method

- Deterministic cases inject probes into `axis_mcp.status.aggregator.aggregate`; the aggregator cache is reset before and after every case.
- Real-probe cases patch only the probe's external boundary (`urllib.request.urlopen`, `PROJECT_ROOT`, `_mcp_processes`, and the two `runtime_freshness` time/source helpers) with `unittest.mock`; every patch is restored by its context manager. CTO/codegraph fixtures use throwaway SQLite files under a temporary directory.
- Live cases: `python -m axis_mcp.status.server --smoke` in a subprocess, and one MCP stdio client call to `axis_status(force=True)`.
- The no-write case is an AST scan of `axis_mcp/status/*.py` for file writes, non-read SQLite opens, HTTP write verbs and git write verbs.
- The eval itself did not modify product code, config or a product database; the working tree already contains the M1/N1 fixes under evaluation. No existing process was killed or restarted; all network calls are loopback.

## 4. Results

| # | ID | Group | Case | Expected | Actual | Verdict | Root cause / note |
|--:|:---|:------|:-----|:---------|:-------|:--------|:------------------|
| 1 | `A1` | A. Happy path | all 7 sources ok | 100/healthy/green; warnings=[]; every row ok+fresh | 100/healthy/green; warnings=0; rows=7 | **PASS** | — |
| 2 | `B1` | B. One source down | busd down | 75/down/red (100-25; critical down) | 75/down/red; busd=down fresh=false warning='source did not respond' | **PASS** | — |
| 3 | `B2` | B. One source down | cto down | 80/degraded/amber (100-20; 80 in 70..89) | 80/degraded/amber; cto=down fresh=false warning='source did not respond' | **PASS** | — |
| 4 | `B3` | B. One source down | content down | 85/degraded/amber (100-15) | 85/degraded/amber; content=down fresh=false warning='source did not respond' | **PASS** | — |
| 5 | `B4` | B. One source down | mcp_freshness down | 85/down/red (100-15; critical down) | 85/down/red; mcp_freshness=down fresh=false warning='source did not respond' | **PASS** | — |
| 6 | `B5` | B. One source down | git down | 90/healthy/green (100-10; 90>=90) | 90/healthy/green; git=down fresh=false warning='source did not respond' | **PASS** | — |
| 7 | `B6` | B. One source down | browse down | 90/healthy/green (100-10; 90>=90) | 90/healthy/green; browse=down fresh=false warning='source did not respond' | **PASS** | — |
| 8 | `B7` | B. One source down | codegraph down | 95/healthy/green (100-5; 95>=90) | 95/healthy/green; codegraph=down fresh=false warning='source did not respond' | **PASS** | — |
| 9 | `C1` | C. busd degraded | busd queue_failed>0 | 88/degraded/amber (100-12.5=87.5 -> 88; 88 in 70..89) | 88/degraded/amber; busd=degraded fresh=true warning='1 failed queue item(s) awaiting retry' | **PASS** | — |
| 10 | `D1` | D. unknown | non-critical codegraph unknown | 100/healthy/green; codegraph excluded; measured weight 95 renormalized to 100; warning present | 100/healthy/green; codegraph=unknown fresh=false warning='source could not be measured'; warnings=1 | **PASS** | — |
| 11 | `D2` | D. unknown | critical busd unknown | 100/down/red; busd excluded (measured weight 75); critical unknown forces down | 100/down/red; busd=unknown fresh=false warning='source could not be measured'; critical_warning=True | **PASS** | — |
| 12 | `D3` | D. unknown | critical mcp_freshness unknown | 100/down/red; mcp_freshness excluded (measured weight 85); critical unknown forces down | 100/down/red; mcp_freshness=unknown fresh=false warning='source could not be measured'; critical_warning=True | **PASS** | — |
| 13 | `E1` | E. ok + warning | busd reports ok with a warning | 88/degraded/amber; busd demoted ok->degraded (loss 12.5) | 88/degraded/amber; busd=degraded fresh=true warning='odd but true' | **PASS** | — |
| 14 | `F1` | F. non-boolean fresh | fresh="false" (string) | git down + non-boolean warning; 90/healthy/green | 90/healthy/green; git=down fresh=false warning='probe returned a non-boolean fresh value — measurement failed' | **PASS** | — |
| 15 | `F2` | F. non-boolean fresh | fresh=1 (int) | git down + non-boolean warning; 90/healthy/green | 90/healthy/green; git=down fresh=false warning='probe returned a non-boolean fresh value — measurement failed' | **PASS** | — |
| 16 | `F3` | F. non-boolean fresh | fresh=None | git down + non-boolean warning; 90/healthy/green | 90/healthy/green; git=down fresh=false warning='probe returned a non-boolean fresh value — measurement failed' | **PASS** | — |
| 17 | `G1` | G. timeout | browse probe sleeps 3 s | aggregate <=2000 ms; browse down/timeout; other 6 intact; 90/healthy/green | elapsed=1202ms; browse=down fresh=false warning='timed out after 1200 ms (per-source limit 1200 ms)'; others_ok=True; overall=90/healthy/green | **PASS** | — |
| 18 | `H1` | H. freshness boundary | mtime = start + 0.5 s | fresh=true by both predicates; runtime.status=current | sources.is_fresh=True; runtime.restart_required=False; runtime.status=current; tolerance=1.0 | **PASS** | — |
| 19 | `H2` | H. freshness boundary | mtime = start + 1.5 s | fresh=false/stale by both predicates; runtime.status=stale | sources.is_fresh=False; runtime.restart_required=True; runtime.status=stale; tolerance=1.0 | **PASS** | — |
| 20 | `I1` | I. cache | TTL hit then force | 2nd call cache=cached with identical generated_at; force=True cache=fresh with new generated_at | first=fresh; second=cached; same_generated_at=True; third=fresh; new_generated_at=True; probe_calls=2 | **PASS** | — |
| 21 | `J1` | J. secret canary | canary in env + probe payload | 0 occurrences of the synthetic canary in output/warnings/JSON; [redacted] present | canary_occurrences=0; redacted=True; warnings=1 | **PASS** | — |
| 22 | `K1` | K. CTO schema drift | 0-byte cto.db + fake running process | cto=down, missing_tables=[build_artifacts,qa_evidence,tool_calls]; 80/degraded/amber | probe=down; missing=['build_artifacts', 'qa_evidence', 'tool_calls']; overall=80/degraded/amber | **PASS** | — |
| 23 | `L1` | L. CTO column drift | valid SQLite, required table names, wrong columns | SKIP-NA: contract §3 defines table names, not columns; actual must be documented | probe=ok; fresh=True; tables={'tool_calls': 0, 'build_artifacts': 0, 'qa_evidence': 0}; warning=None | **SKIP** | Contract §3 defines CTO measurement as 'health probe / DB ที่ประกาศ' and does not define table columns. The probe counts rows, so a DB with only an id column is reported ok. There is no contract threshold to call this PASS or FAIL; recorded as SKIP-NA so it is not silently green. |
| 24 | `M1` | M. busd partial payload | payload missing rules_in_sync/version/uptime_seconds | 88/degraded/amber; warning contains "partial measurement" and the missing field names | probe=degraded; warning='busd health payload is missing required field(s): rules_in_sync, version, uptime_seconds — partial measurement'; missing=['rules_in_sync', 'version', 'uptime_seconds']; overall=88/degraded/amber | **PASS** | — |
| 25 | `N1` | N. partial score_sources | public score_sources() rows missing busd+mcp_freshness | down/red + warning naming busd,mcp_freshness (renormalized score kept) | 100/down/red; missing=['busd', 'mcp_freshness']; warning='critical source(s) missing from the score: busd, mcp_freshness — overall forced down'; rows=['git', 'cto'] | **PASS** | — |
| 26 | `O1` | O. empty codegraph | valid DB, 0 nodes/edges/files | SKIP-NA: contract has no threshold; actual must be documented | probe=ok; nodes=0; edges=0; files=0; warning=None | **SKIP** | Contract §3 lists files/nodes/edges/size as codegraph data but defines no minimum. The probe reports ok for a readable but empty index; there is no contract threshold to call this PASS or FAIL. Recorded as SKIP-NA, not silently green. |
| 27 | `P1` | P. live smoke | python -m axis_mcp.status.server --smoke | axis.status/1; 7 sources; meta.duration_ms<2000; exit 0 | exit=0; wall=1157ms; schema=axis.status/1; sources=7; meta.duration_ms=157; overall={'status': 'down', 'score': 63, 'color': 'red'} | **PASS** | wall includes interpreter startup; the contract budget is the tool's meta.duration_ms |
| 28 | `Q1` | Q. repeatability | same mocked scenario twice | identical overall + per-source status/fresh/warnings (generated_at may differ) | overall=50/down/red; same_fingerprint=True; generated_at_differs=True | **PASS** | — |
| 29 | `R1` | R. MCP stdio | MCP client -> axis_status(force=True) | 1 tool named axis_status; 7 sources; isError=false; schema axis.status/1 | tools=['axis_status']; isError=False; schema=axis.status/1; sources=7 | **PASS** | — |
| 30 | `S1` | S. no-write scan | static scan of axis_mcp/status/*.py | 0 file writes, 0 POST/PUT/PATCH, 0 non-ro sqlite opens, 0 git write verbs | findings=0; files=4; calls=305 | **PASS** | AST scan; str.replace() is excluded, Path/os/shutil writes are not |
| 31 | `T1` | T. redaction | busd returns 401/403 (with key) and 401 (no key) | warnings + JSON contain no canary; warnings name the HTTP status | 401='busd rejected the API key (HTTP 401)' leaked=False; 403='busd rejected the API key (HTTP 403)' leaked=False; 401-no-key='SOLOCORP_API_KEY missing — set it to read busd health' leaked=False | **PASS** | — |
| 32 | `U1` | U. browse degraded | relay up, extension not paired | 95/healthy/green (browse 10*0.5=5 lost) | 95/healthy/green; browse=degraded fresh=true warning='browse relay is up but no browser extension is paired' | **PASS** | — |
| 33 | `V1` | V. git detached | detached HEAD | 95/healthy/green (git 10*0.5=5 lost) | 95/healthy/green; git=degraded fresh=true warning='git HEAD is detached' | **PASS** | — |
| 34 | `W1` | W. busd queue dead | real probe_busd with queue_dead>0 + rules_in_sync=false | 88/degraded/amber; warnings mention dead queue + out-of-sync rules | probe=degraded; warning='busd routing rules are out of sync with routing.json; 2 dead queue item(s) need triage'; overall=88/degraded/amber | **PASS** | — |
| 35 | `X1` | X. all unknown | all 7 probes unknown | 0/down/red + 'not healthy' warning | 0/down/red; warnings=9; not_healthy=True | **PASS** | — |
| 36 | `Y1` | Y. probe exception | cto probe raises RuntimeError | cto down (RuntimeError), no traceback; 80/degraded/amber | 80/degraded/amber; cto=down fresh=false warning='probe raised RuntimeError'; traceback=False | **PASS** | — |
| 37 | `Z1` | Z. invalid status | git probe returns status='bogus' | git down + 'no valid status' warning; 90/healthy/green | 90/healthy/green; git=down fresh=false warning='probe returned no valid status — measurement failed' | **PASS** | — |

### Contract arithmetic used by the cases

Weights: busd 25 · cto 20 · content 15 · mcp_freshness 15 · git 10 · browse 10 · codegraph 5. Values: ok=1, degraded=0.5, down=0, unknown=excluded. `score = round(Σ(weight×value) / Σ(measured weight) × 100)`; critical down/unknown → overall down; otherwise ≥90 healthy, 70–89 degraded, <70 down.

## 5. Failures and skips

### L1 — valid SQLite, required table names, wrong columns (SKIP)

- **Expected:** SKIP-NA: contract §3 defines table names, not columns; actual must be documented
- **Actual:** probe=ok; fresh=True; tables={'tool_calls': 0, 'build_artifacts': 0, 'qa_evidence': 0}; warning=None
- **Note:** Contract §3 defines CTO measurement as 'health probe / DB ที่ประกาศ' and does not define table columns. The probe counts rows, so a DB with only an id column is reported ok. There is no contract threshold to call this PASS or FAIL; recorded as SKIP-NA so it is not silently green.
- **Proposed minimal fix:** Add a contract-level required-column map per table and validate PRAGMA table_info in probe_cto (needs CTO owner + contract update). Until then, list this as a known limitation.

### O1 — valid DB, 0 nodes/edges/files (SKIP)

- **Expected:** SKIP-NA: contract has no threshold; actual must be documented
- **Actual:** probe=ok; nodes=0; edges=0; files=0; warning=None
- **Note:** Contract §3 lists files/nodes/edges/size as codegraph data but defines no minimum. The probe reports ok for a readable but empty index; there is no contract threshold to call this PASS or FAIL. Recorded as SKIP-NA, not silently green.
- **Proposed minimal fix:** Define a contract threshold (for example nodes == 0 -> degraded) or compare against a known baseline; needs a contract update and codegraph owner input.

## 6. Exact commands and exit codes

| # | Command | Observed | Exit |
|--:|:--------|:---------|:----:|
| 1 | `PYTHONPATH=. .venv/bin/python3 scripts/d3_axis_status_eval.py` | 35 PASS · 0 FAIL · 2 SKIP | `0` |
| 2 | `PYTHONPATH=. .venv/bin/python3 -m pytest tests/test_axis_status.py -q` | `31 passed in 5.82s` | `0` |
| 3 | `git status --porcelain` | 3 untracked path(s); 11 modified path(s) | — |

## 7. Environment

```text
date_utc=2026-11-23T08:37:57.217285+00:00
git_head=fbb5dc3132a6a37ae41a9eacc15a429997ff0834
git_branch=feat/axis-status-c1
python_version=3.12.3
python_executable=/data/projects/Lab-solocorp-os2.4/.venv/bin/python3
platform=Linux-7.0.0-43-generic-x86_64-with-glibc2.39
cwd=/data/projects/Lab-solocorp-os2.4
browse_cli=/home/drsolodev/.local/bin/browse
pytest_version=pytest 9.1.1
busd={"url": "http://127.0.0.1:8099/v1/health", "http_status": 200}
mcp_processes=[{"pid": 4352, "module": "axis_mcp.bus_mcp"}, {"pid": 4353, "module": "axis_mcp.cto.server"}, {"pid": 4354, "module": "axis_mcp.departments.content_mcp"}, {"pid": 83142, "module": "axis_mcp.bus_mcp"}, {"pid": 83143, "module": "axis_mcp.cto.server"}, {"pid": 83144, "module": "axis_mcp.departments.content_mcp"}]
codegraph_db={"exists": true, "size_bytes": 19423232}
```

## 8. Known limitations and proposed fixes

- **M1 (fixed in this run):** a busd payload missing `rules_in_sync`, `version` or `uptime_seconds` now returns `degraded` with a 'partial measurement' warning. Covered by D3 case M1 and D2 test `test_busd_partial_payload_is_degraded`.
- **N1 (fixed in this run):** `score_sources()` with rows missing a critical source now forces `down/red` and names the missing source(s) in a warning; the payload's `overall` keeps its fixed `{status, score, color}` shape. Covered by D3 case N1 and D2 test `test_score_sources_missing_critical_is_down`.
- **L1 (SKIP-NA):** CTO column drift is invisible; contract §3 does not define columns. Needs a contract/CTO-owner decision.
- **O1 (SKIP-NA):** an empty but valid codegraph index is reported `ok`; contract §3 has no minimum threshold.
- **P1:** wall-clock includes interpreter startup; the contract budget is the tool's `meta.duration_ms`.
- Live cases (P1/R1) depend on the local runtime; the deterministic cases do not. The secret canary is synthetic; no real secret is used.
- The M1/N1 fixes were applied before this D3 run; the eval itself did not modify product code. The changes are limited to `axis_mcp/status/sources.py`, `axis_mcp/status/aggregator.py` and the two new tests; no other product behavior changed.

## 9. Workspace state

```text
$ git status --porcelain
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

The snapshot is taken immediately before this Markdown file is rewritten, so the docs path appears once the file exists from a previous run.

New paths from this D3 work: `scripts/d3_axis_status_eval.py`, `docs/certification/D3-axis-status-2026-11-23.md` and the gitignored `bus/evidence/2026-11-23/d3-axis-status/` directory. `brain/learnt.md` and `config/.module-registry.json.lock` were already present before this run and were not touched.

> Generated by `scripts/d3_axis_status_eval.py`. Re-running the harness rewrites this file and the evidence JSON from the same data.
