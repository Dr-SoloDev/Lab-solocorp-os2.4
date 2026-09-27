# A+B v2 Execution Evidence (2026-09-27 ~22:05-22:20, Owner approved)

Forum: bus/forum/forum-20260927-004 (4/4 insights + synthesis)

## 1. Grep Bearer clients (before flip)
- `loop_runner/loops/daily_brief.py:26` — Bearer → fixed
- `loop_runner/loops/subscription_audit.py:25` — Bearer → fixed
- `pipeline_executor.py` — in-process queue, no HTTP, untouched
- `workers/agents/base_agent.py:186` — already X-API-Key, untouched
- `workers/maxplus_llm_provider.py:87` — Bearer for MaxPlus external API, NOT busd, untouched

## 2. Compat (forum: compat window, not same-day flip)
- `central_bus/main.py` api_key_auth: accepts X-API-Key primary + Authorization Bearer fallback with warning log. TODO remove 2026-10-04.
- busd restarted (PID new, uptime reset). Verified: X-API-Key → 200 path, Bearer → 200 path, no key → 401.
- **Latent bugs found during verify** (same area, fixed together):
  - loops sent POST with NO body → 400 VALIDATION_ERROR even with right header. Fixed: send `{"agent_id":..., "keys":["*"]}` + Content-Type json.
  - loops parsed old fact shape `{id, content}` but API returns `{key, value, version}` → normalized in fetch (fail-open preserved).

## 3. Manual run (first since 2026-08-26)
- `--dry-run`: 4/4 due, heartbeat fired ✅
- real run: daily_brief ✅ (cited fresh fact test.fact.hello), subscription_audit ✅, brain_auto_commit ✅ 14 files, pipeline_executor ⏭ (no task-type messages)
- state.db: all 4 loops + __scheduler__ timestamped 2026-09-27 22:18-22:20

## 4. Cron + single-flight + dry-run
- `main.py`: fcntl single-flight lock (SKIP if another run) + `--dry-run` flag
- crontab added: `*/30 * * * * cd /data/... && .venv/bin/python -m loop_runner.main >> logs/loop_runner_cron.log`
- Old `cron_central_bus.py` entry kept (same fs device 2065, path resolves)

## 5. Heartbeat 401 watch
- `daily_brief._fetch_facts` records `bus_auth_watch` to state.db on 401/UNAUTHORIZED (fail-open: report still generated offline)

## Open follow-ups (for Architect CMD-005-T2/T3 or next forum)
- queue_pending=19 but pipeline_executor sees no task-type messages → verify queue stores (jsonl vs SQLite) + drain/DLQ policy
- facts_count=1 (only test.fact.hello) → seed real facts
- routing_rules=0 in DB → import 16 JSON rules
- space-bunny returns empty/timeout on long TH prompts twice today → fallback covers; consider per-loop primary model later
- Bearer compat removal due 2026-10-04
