# D4 — Final independent re-check of `docs/runbooks/AXIS-STATUS.md` (v1.1, post V1–V7)

**Verifier:** `deepseek-v4.1-flash` — independent D4 checker, no prior context
**Date (UTC):** 2026-11-23T10:12:25Z → 2026-11-23T10:14:00Z
**Repo:** `/data/projects/Lab-solocorp-os2.4`
**Branch / HEAD:** `feat/axis-status-c1` / `e5b9d74c3b7c113decee5e67950e99872c4329f0`
**Runbook:** `docs/runbooks/AXIS-STATUS.md`, **207 lines**, SHA-256
`5bf6c664356b3ee94b5d6d9d28c96e0c578e514b771a8543de19c443eee820b1` (unchanged before/after replay; not edited)
**Python:** 3.12.3 · pytest 9.1.1 · `mcp` 1.28.1

> **Supersedes:** this report supersedes (a) the round-1 report preserved at
> `round1/verifier-report.md` (runbook v1.0, SHA `aca0804…`), and (b) the loose
> `verifier-*` files in the parent directory, which §9 lines 185–186 now declare
> `superseded/ignored`. Per §9 line 186 this is the latest-UTC sign-off.

---

## Verdict

**D4 PASS.** All seven fixes V1–V7 are present in the revised text and all are
behaviorally confirmed by replay. The §4 snippet runs verbatim and prints exactly
`axis.status/1 7 False` with exit 0. The four §3 commands reproduce 40 / 11-11 /
schema+7 / 43-0-0, all exit 0. The §3 restore command returns the tree to its
pre-replay state byte-for-byte and leaves the runbook and product code untouched.

**No fix is wrong.** Seven low-severity residual wording/robustness nits remain
(A1–A7); none blocks D4.

---

## 1. Fix-by-fix verification

| Fix | Revised ref | What the runbook now says | Check performed | Status |
|:---|:--|:--|:--|:--:|
| **V1** per-source loss | §6 L145 | `busd 12.5 + content 7.5 + mcp_freshness 7.5 + browse 10 = 37.5 loss → 100−37.5=62.5→63; queue state เปลี่ยนได้` | Recomputed from live `smoke.json`: nonzero losses were exactly **busd 12.5, content 7.5, mcp_freshness 7.5, browse 10 = 37.5** → `floor(62.5+0.5)=63`; payload score 63 | **PASS** |
| **V2** smoke acceptance | §3 L49; §9 L179–180 | acceptance = `axis.status/1` + 7 sources + exit 0; `overall` environment-dependent, `down/63` labelled "snapshot นี้" | Observed schema+7+exit 0 and `down/63`; the acceptance wording no longer requires 63 | **PASS** |
| **V3** `structuredContent` | §4 L83–85 | "key `structuredContent` ไม่มีใน result; keys ที่มีคือ `content`, `isError`" | Raw result keys = `['content','isError']`; no `structuredContent` key (absent, not `null`) | **PASS** |
| **V4** runnable stdio + §9 coverage | §4 L86–105; §9 L178, L180 | verbatim bash/python snippet; §9 requires running it and expects `axis.status/1 7 False`, exit 0 | Extracted lines 89–104 with `sed` (no retyping) and ran `bash stdio-snippet.sh`: stdout exactly `axis.status/1 7 False`, exit 0, stderr empty. Raw transcript confirms real `initialize → notifications/initialized → tools/call` | **PASS** |
| **V5** sign-off location | §9 L185–186 | only `verifier-<name>-<UTC>/verifier-report.md` counts; root `verifier-*` are `superseded/ignored`; multiple rounds use latest UTC | This report lives in `verifier-deepseek-v4flash-20261123T100215Z/`; previous report moved to `round1/` and declared superseded here | **PASS** |
| **V6** evidence policy | §9 L193–195 | `bus/evidence/` is gitignored; keep local subdir; to certify `git add -f` only the sign-off files per SOP-06, or record SHA-256 in the registry; never commit secrets | Files are local-only (git-ignored, verified with `git check-ignore` in round 1); no secrets present; policy is followable. Commit path not exercised (no commits allowed in this task) | **PASS** |
| **V7** formats | §9 L187, L192 | `git-status.txt` = full `git status --porcelain` before + after; `commands=` syntax = `1:pytest:0;2:d2:0;3:smoke:0;4:d3:0;stdio:0` | `git-status.txt` now contains labelled full BEFORE and AFTER blocks; signature uses the exact `commands=` syntax | **PASS** |

---

## 2. §4 stdio — snippet verbatim

Extracted from the runbook with `sed -n '89,104p'` into `stdio-snippet.sh` (no manual edits),
run from the repo root as `bash stdio-snippet.sh`:

```
$ bash stdio-snippet.sh
axis.status/1 7 False
exit=0  wall=1330 ms  stderr=0 bytes  exact_match=yes
```

Handshake proof (raw JSON-RPC, from `stdio_probe.py`, same sequence):

```
>> {"jsonrpc":"2.0","id":1,"method":"initialize", …}
<< {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05", … "serverInfo":{"name":"axis-status","version":"1.28.1"}}}
>> {"jsonrpc":"2.0","method":"notifications/initialized"}
>> {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"axis_status","arguments":{"force":true}}}
<< {"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"{…}"}],"isError":false}}
```

Negative control (still documented at §4 L74): bare `tools/call` without handshake →
`{"code":-32602,"message":"Invalid request parameters"}`.
Parsed payload: `schema=axis.status/1`, 7 sources
`[busd,cto,content,mcp_freshness,git,browse,codegraph]`, `isError=False`,
`meta.duration_ms=165`.

---

## 3. §3 commands — output, exit code, wall time

| # | Command (verbatim §3) | Exit | Wall | Observed |
|:-:|:--|:--:|--:|:--|
| 1 | `PYTHONPATH=. .venv/bin/python3 -m pytest tests/test_axis_status.py -q` | 0 | 7.16 s | `40 passed in 6.24s` |
| 2 | `PYTHONPATH=. .venv/bin/python3 scripts/d2_axis_status_check.py` | 0 | 1.59 s | `11/11 checks passed · 169 ms` |
| 3 | `PYTHONPATH=. .venv/bin/python3 -m axis_mcp.status.server --smoke` | 0 | 1.19 s | `schema=axis.status/1`, 7 sources, `down/63/red`, `duration_ms=159` |
| 4 | `PYTHONPATH=. .venv/bin/python3 scripts/d3_axis_status_eval.py` | 0 | 13.00 s | `CASES: 43 · PASS 43 · FAIL 0 · SKIP 0`; `PYTEST: 40 passed in 6.45s (exit 0)`; `EXIT: 0` |
| 5 | stdio snippet (§4) | 0 | 1.33 s | `axis.status/1 7 False` |

Full logs: `pytest.log`, `d2-harness.log`, `smoke.json`, `d3-eval.log`,
`stdio-snippet.log`, `stdio.log`, plus `*.exit.txt`.

---

## 4. Tree integrity / restore

- BEFORE (full porcelain): ` M brain/learnt.md`, `?? config/.module-registry.json.lock`,
  `?? docs/runbooks/AXIS-STATUS.md` — exactly the pre-existing set §9 L176–177 allows.
- After the four commands: only the seven documented tracked evidence files changed
  (`d2-axis-status/{harness.log,tool-calls.jsonl}`, `d3-axis-status/{env.txt,eval.json,eval.log,table.md}`,
  `docs/certification/D3-axis-status-2026-11-23.md`).
- Restore command (§3 L56) rc 0 → AFTER identical to BEFORE; all **7/7** tracked evidence
  files match their `HEAD` blob SHA-256 (`restore-hash-proof.txt`).
- `git diff --name-only -- axis_mcp tests` empty before and after restore.
- Runbook SHA-256 unchanged: `5bf6c664…e820b1`.

---

## 5. Residual ambiguity (none blocking)

- **A1 — §1 L3 pre-declares certification (low).** The header already says
  `D4 PASSED (2026-11-23, verifier deepseek-v4.1-flash)` and `v1.1` before this final
  signature. It is accurate only because this re-check passes; a maker-authored PASS line
  is fragile if a future revision fails. Also L60 still says the MCP entry waits for
  "D4 ผ่าน", which now contradicts L3. Suggest the verifier owns the status line, or the
  header reads "PASSED — pending final signature" until signed.
- **A2 — §4 L97/L100 snippet robustness (low).** `p.stdout.readline()` has no timeout (the
  snippet can hang if the server fails to start), and `p.wait()`'s return code is ignored,
  so the command's exit 0 proves the client ran, not that the server exited 0. Suggest
  `raise SystemExit(p.wait())` and/or a read timeout.
- **A3 — §4 L92 vs §9 L178 (low).** The snippet hard-codes `stderr=subprocess.DEVNULL`, but
  §9 L178 asks the verifier to record the stdio client's stderr. There is none to record;
  reconcile the wording or drop stderr from the stdio item.
- **A4 — §9 L183–184 evidence list (low).** The list omits a stdio log even though L180
  requires the stdio check. Suggest adding `stdio.log`.
- **A5 — §9 L186 "latest UTC" vs the subdirectory name (low).** My directory carries the
  round-1 UTC (`…T100215Z`) because this task required updating the prior subdirectory,
  while this report's `date_utc` is the latest round. The rule does not say whether "latest
  UTC" binds the directory name or the report. Suggest: "the report's `date_utc` is
  authoritative; the directory name may keep the first replay timestamp."
- **A6 — §9 L196 registry sign-off (info).** Updating `profiles/CERTIFICATION-REGISTRY.md`
  is outside verifier scope and was not done. L4 correctly says the official registry
  signing happens after this revision, but the runbook does not name the owner.
- **A7 — §9 L193–195 commit path (info).** The `git add -f` policy is documented but not
  exercised here (no commits allowed). The earlier root-level `verifier-report.md` remains
  on disk; per L185–186 it is ignored/superseded, which this report states explicitly.

---

## 6. What I did NOT verify

- Fresh-machine provisioning (§2 L25): `.venv` already existed; no new venv or `pip install`.
- Absent busd / `central_bus/cto.db` / `.codegraph/` paths (§2 L30–32): all present; stopping
  services or moving DBs is a repair action and was out of scope. Only `browse` was absent.
- 401/403 redaction branch (§2 L28–29, §6 L144): `/v1/health` is allowlisted here, so a wrong
  key is not rejected; only D3 case T1 covers that branch.
- §6 troubleshooting actions (`restart-mcp.sh`, `codegraph index`, DB/queue repair): not run.
- D2/D3 internal mock cases: counted and spot-checked (arithmetic, cache, canary), not re-implemented.
- Real MCP client registration (§4): `axis-status` is intentionally absent from `opencode.jsonc`;
  the snippet was exercised directly, not through a client config.
- §10 rollback/uninstall: nothing installed or registered.
- V6 commit path and registry entry (A6/A7): no commits made.
- Packet-level network isolation: static inspection only; no capture.
- 10 s TTL under load / concurrency: sequential only.

---

## 7. Evidence index — `bus/evidence/2026-11-23/d4-axis-status/verifier-deepseek-v4flash-20261123T100215Z/`

| File | Contents |
|:--|:--|
| `verifier-report.md` | This final report (supersedes round 1) |
| `env.txt` | UTC start, branch, HEAD, runbook SHA/lines, Python/pytest/mcp |
| `commands.txt` | §3 + §4 commands, exit codes, wall times, restore |
| `pytest.log`, `pytest.exit.txt` | Command 1 |
| `d2-harness.log`, `d2-harness.exit.txt` | Command 2 |
| `smoke.json`, `smoke.stderr.txt`, `smoke.exit.txt` | Command 3 |
| `d3-eval.log`, `d3-eval.exit.txt` | Command 4 |
| `stdio-snippet.sh`, `stdio-snippet.log`, `stdio-snippet.stderr.txt`, `stdio-snippet.exit.txt` | §4 snippet verbatim + result |
| `stdio.log`, `stdio-transcript.json`, `stdio.exit.txt`, `stdio_probe.py` | Raw handshake + bare-call negative control |
| `git-status-before.txt`, `git-status-after.txt`, `git-status-after-runs.txt`, `git-status.txt` | Full porcelain BEFORE/AFTER + intermediates |
| `git-diff-product-*.txt` | Empty product diffs |
| `restore-hash-proof.txt` | 7/7 tracked evidence files == `HEAD` blobs |
| `runbook-sha-after.txt` | Runbook SHA after replay |
| `static-checks.txt`, `independent_checks.py`, `independent-checks.log` | Round-1 independent checks (still valid: weights/TTL/canary/loopback) |
| `round1/` | Preserved round-1 evidence and report (superseded) |

---

```
name=deepseek-v4.1-flash | date_utc=2026-11-23T10:14:00Z | head=e5b9d74c3b7c113decee5e67950e99872c4329f0 | commands=1:pytest:0;2:d2:0;3:smoke:0;4:d3:0;stdio:0 | verdict=PASS | runbook_sha256=5bf6c664356b3ee94b5d6d9d28c96e0c578e514b771a8543de19c443eee820b1 | signature=D4-final-recheck-deepseek-v4.1-flash-20261123T101400Z
```

*No product code, tests, or runbook changes; no commits. This sign-off binds to the
runbook SHA-256 quoted above.*
