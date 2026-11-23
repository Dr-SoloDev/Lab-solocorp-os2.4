# Deploy Wave-1 — STOPPED at Step 1 (gate hit)

- **Date:** 2026-11-23 ~09:2x +07
- **Verdict:** 🛑 **BLOCKED — no changes made to canonical repo, no service restart performed**
- **Reason:** Step-1 hard gate — canonical repo has a tracked modification.
- **Rollback needed:** ❌ none (nothing was mutated)

---

## Gate condition (explicit in brief)

> `git status --porcelain` → ถ้ามี tracked changes (M/A/D) **หยุด รายงาน** (ห้าม stash/clean/overwrite)

Observed in `/data/projects/Lab-solocorp-os2.4`:

```
 M brain/learnt.md        # +23 lines, tracked (M)
```

Untracked: `0`.

### What the dirty change is

`brain/learnt.md` — appended section "Session 2026-11-14 — คืนขนาน 6 คลิป + บทเรียน Ego (Owner สอน CEO)".
Content = Owner lessons (parallel-video recipe, Muse-Spark ego principle, card-image safety rule) + pending items.
**Non-regenerable** (hand/agent-authored org memory) → must not be discarded, stashed, or overwritten.

---

## State captured (read-only, no mutation)

| Item | Value |
|:-----|:------|
| HEAD before | `83d5f93` (detached) — `chore(brain): auto-commit 1 brain files` |
| HEAD expected by brief | `87ed75d` — **mismatch** (see note) |
| `origin/main` (local ref, **not fetched**) | `32fba06` ✅ matches expected main tip |
| Working tree | 1 tracked M (`brain/learnt.md`), 0 untracked |
| busd MainPID before | `1252` (active running, since 07:18:22, uptime ~2h) |
| Service unit | `solocorp-bus.service` — `WorkingDirectory=/home/drsolodev/projects/Lab-solocorp-os2.4` |

### Note on the HEAD mismatch (`83d5f93` ≠ `87ed75d`)

`83d5f93` = `87ed75d` + one further `chore(brain): auto-commit`. The `brain_auto_commit`
loop ran again after the brief was written. Both commits sit on a line **diverged**
from `origin/main` (neither is an ancestor of `32fba06`). Harmless for the deploy
target, but it confirms the loop is actively moving HEAD — a checkout to `32fba06`
would need re-pinning, not a moving ref.

---

## Two pre-checks that would have blocked anyway (resolved — good news)

**1. Service directory is NOT a mismatch.** Unit references `/home/drsolodev/projects/...`,
but `readlink -f` resolves it to `/data/projects/Lab-solocorp-os2.4`, and
`/proc/1252/cwd -> /data/projects/Lab-solocorp-os2.4`. Restarting would indeed pick up
the canonical repo. ✅

**2. The deploy is meaningful (old code is live).** Running busd is on pre-Wave-1 code:

| Field | Live now (pid 1252) | Expected after 32fba06 |
|:------|:--------------------|:-----------------------|
| `version` | `0.6.0` | `0.6.2` (`central_bus/__init__.py`) |
| `routing_rules` | `22` | `22` |
| `rules_in_sync` | **absent** | present (`routing_sync.py`) |
| `oldest_routed_age_seconds` | **absent** | present (`queue.py:321`) |
| `queue_pending` | `0` | `0` |

So a restart *without* the canonical update would have produced a green-looking
but unchanged service — exactly the false-"done" failure mode. Update + restart
are both required.

`HEAD..origin/main`: **388 files, +15,492 / −815** (includes version SSoT,
routing_sync, health parity, `test_routing_ssot.py` 29 tests).

---

## Step-3 matrix: pre-researched (ready to run once unblocked)

- **No read-only HTTP routing endpoint exists.** Every routing-adjacent route is a
  `POST` that writes (`/v1/observe`, `/v1/context`, `/v1/facts`, `/v1/update`).
  Only `GET` routes: `/v1/health`, `/v1/ceo-alerts`, `/v1/facts`, `/v1/aar/{id}`,
  `/v1/ab-test/report`, `/v1/dashboard`.
- → The brief's fallback applies: **engine-level** matrix, canonical code + live DB
  via **read-only URI**, explicitly labelled "engine-level, not HTTP".
- Matrix source: `central_bus/tests/test_routing_ssot.py::SEMANTIC_MATRIX` — **11 cases**
  (10 department expectations + `test_no_match_uses_ssot_fallback_not_hardcoded_ceo` → `coo`):

| # | Payload | Expected |
|:-:|:--------|:---------|
| 1 | review the quarterly budget and cost report | cfo |
| 2 | deploy the backend api hotfix | engineering |
| 3 | run regression test suite for quality | qa |
| 4 | our solana smart contract needs an audit | web3 |
| 5 | customer support ticket escalation | support |
| 6 | GDPR compliance review for the contract | legal |
| 7 | marketing content plan for the brand | cmo |
| 8 | fix a bug in the server | engineering |
| 9 | daily ops routine admin | coo |
| 10 | ช่วยดูเรื่องการเงินกับงบประมาณให้หน่อย | cfo |
| 11 | (no match) hello there, nice weather | coo (SSoT fallback) |

Note: `test_count_rules_matches_ssot` asserts `count_rules() == 22` — consistent with
the 22 already visible live.

---

## Safe-path analysis for CEO (unblock options)

`git diff HEAD origin/main -- brain/learnt.md` → **empty**. The file is byte-identical
between `83d5f93` and `32fba06`, so `git checkout -B main origin/main` would carry the
local +23 lines across **without conflict or loss**. I did **not** run it — the brief's
gate is unconditional, and overriding an explicit stop on non-regenerable org memory is
not mine to decide.

| # | Option | Effect on `brain/learnt.md` | Who decides |
|:-:|:-------|:----------------------------|:------------|
| A | Let `brain_auto_commit` (hourly) commit it, then re-issue wave-1 | preserved, committed | CEO — zero risk, may wait ≤1h |
| B | CEO authorises `git checkout -B main origin/main` despite dirt | preserved in working tree (proven identical), stays uncommitted | CEO |
| C | CEO authorises committing `brain/learnt.md` first, then checkout | preserved as a commit | CEO |
| D | Abort wave-1 | untouched | CEO / Owner |

**My recommendation: A or B.** A costs nothing but time; B is proven lossless by the
empty diff and gets the deploy done now. Both keep the Owner's lessons intact.

---

## Confirmation of non-actions (per "ห้าม")

- ❌ No `git fetch`, no `checkout`, no `stash`, no `clean`, no commit
- ❌ No `systemctl restart` — busd still pid `1252`, untouched
- ❌ No `restart-mcp.sh`, no process kills, no crontab edits
- ❌ No campaigns / frozen artifacts touched
- ❌ No source or tracked file edited
- ✅ Only reads + 2 files written under this evidence dir

## Rollback

Not required — nothing changed. Standing command if a later wave fails verification:
`cd /data/projects/Lab-solocorp-os2.4 && git checkout 87ed75d && systemctl --user restart solocorp-bus.service`
(adjust to `83d5f93` if the brain-commit line is to be restored exactly as found).
