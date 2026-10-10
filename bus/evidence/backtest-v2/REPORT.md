# Backtest v2 — Report (read-only replay)

> **SCOPE BANNER (n=1 sanity check):** กฎชุดนี้ออกแบบหลังเห็นเคส media_daily การจับมันได้ยืนยันทิศเท่านั้น
> ห้ามใช้ "12 วัน → ≤4 วัน" เป็นตัวเลขขายหรืออ้างอิงข้างนอก — n=1 และเป็นเคสที่กฎจูนมาจากมันเอง

generated: 2026-10-10 19:14 +07:00 | criteria: c03fdc7 (locked before run)
inputs: /tmp/bt copies (inbox 221 msgs, state.db copy — state.db has NO history, latest-run only)

## 1. Baseline (no ceilings — what actually happened)
- inbox __human__: 221 msgs, of which media_daily SKIP = 216 (~17/day), all byte-identical except timestamps
- span: 2026-09-28 06:00 → 2026-10-10 18:30 (12.5 days); system TTD = never (∞); human TTD = 12 days (bootstrap Oct 10)

## 2. Fingerprint ablation (raw vs normalized)
- distinct reasons raw = 1, fingerprinted(v1) = 1
- conclusion: dataset has zero variance → fingerprint value NOT demonstrable here; reason-change rule fired 0 times in 12 days (needs canary pairs, per CRITERIA §4)

## 3. Reason-change rule → incidents on: 2026-09-28
- no-Ack branch: first SKIP Sep 28 = new reason → incident day 0 ✅ (criterion: incident day 1)

## 4. Silence rule → no-verdict days: 2026-09-29
- ✅ VERIFIED (2 independent sources, 2026-10-10): `logs/loop_runner_cron.log` มี Sep 27/28/30 แต่ 0 บรรทัด Sep 29;
  `/var/log/syslog.1` มี 11,276 บรรทัด Sep 27 + 5,490 Sep 28 + 3,854 Sep 30 แต่ 0 บรรทัด Sep 29 —
  เครื่องดับทั้งวัน ไม่ใช่แค่วันที่ไม่มีงาน → silence rule จะดังวันที่ 1 (ยกระดับจาก "สัญญาณที่น่าสนใจ" เป็นหลักฐาน)

## 5. Repeat rule → digest
- strict-evidence reading (streak resets Sep 29): digest ['2026-10-02'] — criterion ≤Sep 30 MISSED by 2 days
- continuous-operation reading (verdict assumed daily): digest 2026-09-30 ✅ (criterion met)
- note: under BOTH readings some rule fires by day ≤2 (incident d0 / silence d1 / digest d2–d4) vs 12-day actual

## 6. Healthy periods (bug removed from stream)
- Period Q (Sep 29–30): real events = 0, simulated incidents = 0, digest lines = 0 → ✅ (criteria ≤2/wk, ≤5/day)
- Period B (Oct 8–9): real events = 0, simulated incidents = 0, digest lines = 0 → ✅
- Sep 29 silence + Sep 30 digest counted as DETECTION (real failure), not noise — per counting rule

## 7. Miss side — real events preserved
- forum synthesis arrivals in __human__: 5/5 preserved (replay does not touch non-SKIP paths) ✅
  - 2026-09-26 [Forum forum-20260926-001] synthesis พร้อม
  - 2026-09-26 [Forum forum-20260926-002] synthesis พร้อม
  - 2026-09-26 [Forum forum-20260926-003] synthesis พร้อม
  - 2026-09-27 [Forum forum-20260927-004] synthesis พร้อม
  - 2026-09-28 [Forum forum-20260928-005] synthesis พร้อม

## 8. Verdict vs locked criteria
- [⚠️ PARTIAL] detection ≤3 days: incident d0 (no-Ack) / silence d1 / digest d2 (continuous reading) — แต่ **digest rule เดี่ยวๆ เกิน 3 วันใน strict reading (digest Oct 2 = วันที่ 4)** ผ่านได้เพราะ silence rule คลุม ไม่ใช่เพราะ repeat rule เอง — เขียนไว้ตรงๆ กันตีความเข้าข้างตัวเอง
- [✅] healthy: 0 incidents, 0 digest lines (both periods)
- [✅] miss side: 5/5 preserved; [✅] reason-change stability: 0 false incidents
- overall: sanity check PASSES on direction (12d/∞ → ≤4d worst reading); numbers are NOT proven — per CRITERIA §2

## 9. Limitations (stated upfront, per approval condition 1)
- catch rate NOT measurable historically (no canary existed); TTD only for real events
- state.db keeps latest run only → no verdict-history replay possible
- daily_brief Aug-26 / zombie era / bus.db loss → labeled replay-impossible, not simulated
- watcher-independence → design review only, not replayable from logs
- inbox logging starts Sep 26 → no mid-Sep healthy week measurable on alert streams (used in-window days instead)
