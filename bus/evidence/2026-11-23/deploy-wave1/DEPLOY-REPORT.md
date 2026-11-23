# Deploy Wave-1 — COMPLETED (option B: lossless checkout)

- **Date:** 2026-11-23 09:2x–09:2x +07
- **Verdict:** ✅ **PASS — all verification criteria met**
- **Mode:** CEO-authorized option B (checkout preserving working tree)
- **Rollback used:** ❌ none needed

---

## 1. Canonical repo update (lossless)

| Item | Before | After |
|:-----|:-------|:------|
| HEAD | `83d5f93` (detached) | **`32fba06`** ✅ |
| Branch | *(detached)* | `main` (tracks `origin/main`) |
| `brain/learnt.md` sha256 | `aca83fa4bbeafa69334e9bb4c12fd14e7ebe8403b3beaad316e5e6ba16d4df30` | **identical** ✅ |
| `git status --porcelain` | ` M brain/learnt.md` | ` M brain/learnt.md` ✅ |
| Tracked changes added | — | **none** ✅ |

Command: `git checkout -B main origin/main` → exit `0`. No `stash`, no `clean`, no `--force`.
Git carried the local `+23` lines across without conflict (file is byte-identical in
both commits — predicted by the empty `git diff HEAD origin/main -- brain/learnt.md`).

`brain/learnt.md` remains **uncommitted** as instructed — left to `brain_auto_commit`.
Line count 450, `+23` insertions in `git diff --stat` (unchanged delta).

⚠️ Git note (informational, not a problem): the checkout printed *"leaving 1 commit behind
… 83d5f93 chore(brain): auto-commit 1 brain files"*. That commit is a brain auto-commit
whose content is fully preserved in the working tree (sha256 identical). The object still
exists in the repo — nothing was lost. No extra branch was created (not authorized).

## 2. busd restart (scoped)

| Item | Before | After |
|:-----|:-------|:------|
| MainPID | `1252` | **`84796`** ✅ (≠ 1252) |
| ActiveState | `active` / `running` | `active` / `running` ✅ |
| Started | 07:18:22 (2h 6min up) | 09:25:23 |
| NRestarts | — | `0` |
| Health ready | — | **2 s** after restart (poll ≤30 s, not exhausted) |

Only `solocorp-bus.service` was restarted. No MCP, no crontab, no other process.

## 3. Health verification

`GET http://127.0.0.1:8099/v1/health`

```json
{
  "status": "ok",
  "db": { "queue_pending": 0, "queue_failed": 1, "queue_dead": 0 },
  "facts_count": 167,
  "routing_rules": 22,
  "routing_rules_cached": 22,
  "rules_in_sync": true,
  "routing_json_rules": 22,
  "oldest_routed_age_seconds": null,
  "loops_active": 0,
  "uptime_seconds": 88,
  "version": "0.6.2"
}
```

| Criterion | Required | Actual | Result |
|:----------|:---------|:-------|:------:|
| `status` | `ok` | `ok` | ✅ |
| `routing_rules` | `22` | `22` | ✅ |
| `version` | `"0.6.2"` | `"0.6.2"` | ✅ |
| `rules_in_sync` | `true` | `true` | ✅ |
| `oldest_routed_age_seconds` | present (null/0 ok) | `null` | ✅ |
| `queue_pending` | `0` | `0` | ✅ |

Before (pid 1252, old code): `version "0.6.0"`, **no** `rules_in_sync`, **no**
`oldest_routed_age_seconds`. The deploy is confirmed to have actually shipped code —
not a green-looking no-op. `oldest_routed_age_seconds: null` is correct with
`queue_pending: 0` (no routed-but-unprocessed rows).

## 4. Engine-level routing matrix — **11/11 PASS**

> ⚠️ **LABEL: engine-level, NOT HTTP.** `central_bus` exposes no read-only routing
> endpoint (every routing-adjacent route is a `POST` that writes). The canonical
> `RoutingEngine` was driven directly, per the pre-agreed fallback.

**Zero-write proof:** live DB opened as `file:...?mode=ro`, snapshotted with
`sqlite3.backup()` (consistent, includes WAL), engine run against the **snapshot**.
No test messages injected into the live queue.

| Live DB fingerprint | Before matrix | After matrix |
|:--------------------|:--------------|:-------------|
| `queue` rows | 3223 | **3223** |
| `queue_pending` | 0 | **0** |
| `routing_rules` | 22 | **22** |

Snapshot meta: live DB `/data/projects/Lab-solocorp-os2.4/central_bus/bus.db`
(11,182,080 bytes) → snapshot 12,201,984 bytes; `count_rules() = 22`;
SSoT parity `True` (json 22 = db 22, no missing/extra).

| # | Payload | Expected | Actual | Result |
|:-:|:--------|:---------|:-------|:------:|
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
| 11 | hello there, nice weather *(no match → `r_fallback`)* | coo | coo | ✅ |

**11/11 passed**, script exit code `0`. Case 11 confirms the SSoT fallback routes to
`coo`, **not** hardcoded `ceo` — the core Wave-1 regression.

Reproduce: `PYTHONPATH=. .venv/bin/python bus/evidence/2026-11-23/deploy-wave1/matrix_engine_level.py`
(run from canonical repo, project venv).

## 5. Final state

| Item | Value |
|:-----|:------|
| Canonical HEAD | `32fba06` on `main` ✅ |
| Canonical working tree | ` M brain/learnt.md` only ✅ |
| busd | pid `84796`, active/running, `version 0.6.2` ✅ |
| Health | `ok`, `rules_in_sync: true` ✅ |
| Matrix | 11/11 (engine-level) ✅ |

## 6. Files in this evidence pack

| File | Contents |
|:-----|:---------|
| `STOPPED-report.md` | First attempt — gate hit at step 1, blocked with evidence |
| `health-before.json` | Health on old code (pid 1252, v0.6.0) |
| `health-before-restart.json` | Health immediately pre-restart (v0.6.0) |
| `health-after.json` | Health post-restart (v0.6.2) |
| `health-after-final.json` | Health after 88 s uptime (stability re-check) |
| `matrix_engine_level.py` | Reproducible matrix runner (read-only snapshot design) |
| `matrix-result.json` | Matrix machine-readable result + snapshot meta |

## 7. Confirmation of scope compliance

- ✅ Only `solocorp-bus.service` restarted
- ✅ No MCP touched, no `restart-mcp.sh`
- ✅ No crontab changes, no other process killed
- ✅ No campaigns / frozen artifacts touched
- ✅ `brain/learnt.md` **not committed** (left to `brain_auto_commit`)
- ✅ No `stash` / `clean` / `checkout --force`
- ✅ No source or tracked file edited by me
- ✅ Nothing committed, no PR (per instruction — CEO will order separately)

## 8. Rollback (not used, kept on record)

```bash
cd /data/projects/Lab-solocorp-os2.4
git checkout 87ed75d   # or 83d5f93 to restore the exact pre-wave line
systemctl --user restart solocorp-bus.service
```
`brain/learnt.md` (sha256 `aca83fa4…`) survives either rollback — it is uncommitted
working-tree state, untouched by branch switches.
