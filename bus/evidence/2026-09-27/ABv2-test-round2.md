# Test Round 2 (2026-09-27 ~22:41, post A+B v2)

## PASS ✅
1. main re-run: heartbeat fired, all loops correctly SKIPPED (intervals not due)
2. Single-flight: lock held externally → `SKIP: another run in progress (locked)` ✅
3. busd log: compat Bearer warning logged once (probe), X-API-Key → 200 ×3, no-key → 401 ✅ no errors
4. daily_brief direct: PASS with fresh fact, no `bus_auth_watch` in state.db = zero 401s since fix ✅

## PROBLEMS for further analysis 🔬
1. **space-bunny empty on long TH prompt — 3/3 today** (manual run + test round 1 + now). Pattern confirmed: primary fails on this workload class, fallback (muse-spark) delivers every time. → Consider per-loop primary model (TH-heavy loops → muse-spark first, space-bunny for multimodal). Needs Owner decision (changes Owner-ordered order).
2. **queue_pending=19 stagnant** — pipeline_executor finds no task-type messages across 2 runs. Hypotheses: (a) items are non-task types skipped by design, (b) jsonl vs SQLite dual stores. → Architect T2: inspect 19 items, define drain/DLQ policy.
3. **facts_count=1 / routing_rules=0** — unchanged, pending T2 seeding + JSON→DB import.
