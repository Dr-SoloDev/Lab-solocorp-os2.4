# ADR-040: Single Source of Truth + Drift Gates (routing · version · config · runtime)

**วันที่:** 2026-11-23
**สถานะ:** Accepted (Owner อนุมัติ Option B, 2026-11-23) — Wave 1 implemented on `feat/wave1-routing-ssot`, awaiting `@pipeline-auditor` (maker ≠ checker)
**เกี่ยวกับ:** ADR-002 (Two-Tier) · ADR-016 (Behavior routing) · ADR-017 (route_v2 signal gate) · ADR-021 (model health) · Incident pattern: "connected ≠ current", "migration never ran"

> **เลข ADR:** ใบงานขอ `ADR-033` แต่ `ADR-033-axis-concerns-acceptance.md` ถูกใช้แล้ว (และลำดับปัจจุบันถึง ADR-039) — จึงออกเลขถัดไป **ADR-040** และไม่แตะ ADR เดิม

---

## บริบท — ปัญหาที่เจอ (ตรวจซ้ำ 2026-11-23)

Routing มี "สองที่ที่อ้างว่าเป็นความจริง" แต่ไม่มีใครตรงกัน:

| ชั้น | สถานะจริงเมื่อตรวจ | ผล |
|:-----|:--------------------|:---|
| `bus/system/routing_rules.json` (SSoT ที่คนแก้) | 22 rules ครบ | เป็นเอกสาร ไม่ได้ถูกใช้โดย busd |
| SQLite `routing_rules` (ที่ engine อ่าน) | **0 แถว** (live + backup pre-governance) | engine ไม่มี rule |
| `central_bus/migrate.py` transform | มีโค้ด แต่ CLI เรียก `db.initialize()` ซึ่งไม่มีอยู่ใน `DbManager` (`init()` เท่านั้น) | migration ไม่เคยรันสำเร็จ |
| `_evaluate_condition` | รองรับ `field/equals/contains/exists/and/or` | `trigger = {"keywords": [...]}` ประเมินเป็น `False` ทุก rule |
| `main.py:248` | `engine.match(..., fallback_department="ceo")` | ทุก request ตกลง `ceo` เงียบ ๆ |
| `BehaviorRouter` | มีโค้ด + ADR-016/017 แต่ **ไม่ถูก wire** ใน `main.py` | ไม่ใช่ทางออกของปัญหา |

สรุป: ระบบไม่ได้ "route ผิด" — มัน **ไม่เคย route เลย** และ health บอกแค่ `routing_rules: 0` โดยไม่มีสัญญาณว่า
"SSoT กับ runtime ไม่ตรงกัน" (`connected ≠ current`)

## การตัดสินใจ — Option B

**SSoT หนึ่งเดียว + derived copy ที่พิสูจน์ความตรงกันได้ + drift gate ที่มองเห็นจาก health**

- `bus/system/routing_rules.json` = **ความจริงเดียว** ของ routing (มนุษย์แก้ที่นี่เท่านั้น)
- SQLite `routing_rules` = **derived index/cache** ไม่มีสิทธิ์เป็นความจริงที่สอง
- ทุกชั้นที่ derive ต้องมี (ก) กลไก sync ที่ idempotent (ข) หลักฐาน checksum (ค) health flag ที่ฟ้องเมื่อเพี้ยน

### 4 เสาหลัก (drift gates)

| # | เสา | กติกา | สถานะ |
|:-:|:----|:------|:------|
| 1 | **Routing SSoT** | JSON → SQLite ทางเดียว, stable key = `rule_id`, upsert idempotent, ห้ามลบแถว, `schema_migrations` ผูก checksum, health มี `rules_in_sync` | ✅ Wave 1 (นี้) |
| 2 | **Version SSoT** | version ต้องมาจากที่เดียว (package metadata) — ห้าม hardcode ซ้ำใน health/README/agent files; health ต้องรายงาน version ที่ derive แล้ว | ⏭ Wave 2 |
| 3 | **Config validator** | `opencode.jsonc` + MCP config ต้องผ่าน schema/reference validation ใน CI (fail) และตอน boot (warn); path ที่อ้างต้องมีจริง, key ที่ชนกันต้องฟ้อง | ⏭ Wave 3 |
| 4 | **Runtime visibility** | สิ่งที่ระบบ "อ้างว่าเปิด/มี" ต้องอ่านได้จาก health โดยไม่ต้องเปิดโค้ด: routing parity, version parity, config validity, queue backlog age (`oldest_routed_age_seconds`) | ✅ เริ่ม Wave 1 (routing + backlog age) / ต่อ Wave 4 |

### กติกากลางที่ผูกทุกเสา

1. **Derived ≠ authority** — copy ทุกตัวต้อง regenerate ได้จาก SSoT; ถ้า regenerate ไม่ได้ ถือว่าเป็น authority ที่ผิดกฎ
2. **Idempotent by stable key** — sync รันซ้ำต้องได้ผลเท่าเดิม (ไม่ใช่ "ครั้งแรกเท่านั้น")
3. **Never delete silently** — แถวที่ DB มีแต่ SSoT ไม่มี → รายงาน `db_only` ไม่ลบ
4. **Checksum เป็นหลักฐาน** — ทุก migration record ต้องมี hash ของ input
5. **Health เป็นสัญญา** — drift ที่ตรวจไม่เห็น = drift ที่ไม่มีอยู่จริงในทางปฏิบัติ
6. **แก้ SSoT ก่อน แล้วค่อย sync** — ห้ามแก้ DB แล้วหวังว่า JSON จะตาม (จะกลับไปเป็นสองความจริง)

## Wave 1 — สิ่งที่ทำจริง (branch `feat/wave1-routing-ssot`)

1. **`central_bus/routing_sync.py`** (ใหม่)
   - `python -m central_bus.routing_sync` = **dry-run โดย default**, `--apply` จึงเขียน
   - `--db <path>` ระบุ DB ตรง ๆ (worktree กับ canonical คนละไฟล์), path ต้องมีอยู่จริง — ไม่งั้น exit 2 (กันสร้าง DB เปล่าโดยอุบัติเหตุ)
   - stable id = `rule_id`; `INSERT … ON CONFLICT(id) DO UPDATE`; ไม่มี `new_id()` ใน routing path
   - `schema_migrations` record `002-routing-rules` + sha256[:16] ของ SSoT
   - รองรับ `schema_migrations` **สองหน้าตา**: repo ใหม่ `(id,name,…)` และ live เก่า `(version,…)`
   - output มี `rollback_sql` ที่ลบ **เฉพาะ id ที่ run นี้ insert**
2. **`central_bus/router.py` — keyword adapter**
   - `trigger.keywords` เป็น shape เดียวของ SSoT และ `_evaluate_condition` เดิมอ่านไม่ได้ → เพิ่มเส้นทาง keyword ใน `RoutingEngine.match`
   - "most hits wins" (ตรงกับ `route()` เดิม: rule เฉพาะเจาะจงชนะ rule กว้าง), tie → priority DESC → `_seq` (ลำดับในไฟล์) → rowid
   - `keywords: []` + `is_fallback: true` → ใช้เมื่อไม่มี keyword ไหน match; fallback มาจาก **SSoT (coo)** ไม่ใช่ hardcode `ceo`
   - Thai keyword ใช้ substring (เพราะ `\b` ไม่มีความหมายกับอักษรไทย) — ไม่งั้น keyword ไทยใน SSoT ตายทั้งหมด
   - legacy field-condition rules ยังทำงานเหมือนเดิม (first match, priority order)
3. **Health (`central_bus/health.py`)**
   - `rules_in_sync` (JSON count == DB enabled count, นับจาก DB ตรง ๆ ไม่ผ่าน 60s cache)
   - `routing_json_rules`, `routing_rules` (ค่าจริงจาก DB), `routing_rules_cached` (ค่าที่ engine เห็น)
   - `oldest_routed_age_seconds` — อายุของข้อความเก่าสุดที่ยัง `status='routed'` ( backlog-age signal) จาก `SQLiteQueueManager.oldest_routed_age_seconds()`
4. **`central_bus/migrate.py`** — ปิด footgun
   - `db.initialize()` → `db.init()` (CLI เดิมพังทันทีที่เรียก)
   - routing migration delegate ไป `routing_sync.sync_rules` — รันซ้ำไม่สร้าง 22 แถวใหม่ด้วย random id (เดิมจะ duplicate ทุกครั้ง)
5. **`central_bus/db.py`** — `init(init_schema=False)` สำหรับ tooling ที่ต้องแตะ DB ที่มีอยู่โดยไม่รัน `SCHEMA_SQL` (seed live ต้องไม่สร้าง/แก้ schema เกินจำเป็น)
6. **Tests** `central_bus/tests/test_routing_ssot.py` — 29 tests: transform 22, dry-run ไม่เขียน, apply 2 ครั้ง = 22 แถวเดิม, update in-place, ไม่ลบ db-only, legacy migration schema, semantic matrix 10 payloads + fallback, health parity, backlog age

### ผลลัพธ์ที่วัดได้

- semantic matrix 10/10 routed ถูกแผนก (ไม่ตก `ceo`), fallback ไม่ match → `coo` ตาม SSoT
- sync dry-run → apply → re-apply: `0 → 22`, แล้ว `22 → 22`, `insert 0 / update 0 / unchanged 22`
- live DB seed: health `routing_rules 0 → 22` และ `rules_in_sync false → true` **โดยไม่ restart busd** (อ่าน DB ตรง)
  - หมายเหตุความจริง: busd ที่รันอยู่โหลด **โค้ดเดิม** จาก canonical repo → การ seed ทำให้ "ข้อมูล" ตรง แต่ semantic ของ keyword routing จะมีผลกับ live process หลัง deploy โค้ด + restart (ดู Consequences)

## Consequences

**บวก**
- routing กลับมามีความหมาย: SSoT → DB → engine ตรงกัน และพิสูจน์ได้ด้วยตัวเลข
- sync ปลอดภัย: dry-run default, stable id, ไม่ลบ, rollback SQL ต่อ run
- health ฟ้อง drift ได้ก่อนที่คนจะเจอ symptom (`rules_in_sync`, `oldest_routed_age_seconds`)

**ลบ / ต้นทุน**
- มีโค้ด sync เพิ่มอีกชั้น → ต้องมีวินัย: แก้ routing ต้องรัน sync (และ CI ควรบังคับใน Wave 4)
- keyword adapter เป็น semantics ที่ "ตีความ" SSoT (most hits + word boundary + Thai substring) → ต้อง freeze ด้วย semantic matrix ไม่ใช่ปล่อยให้ drift
- `schema_migrations` มีสองหน้าตาบนเครื่องนี้ (live เก่า vs repo ใหม่) → tooling ต้องรองรับทั้งคู่จนกว่าจะมี migration รวมศูนย์ (Wave 2/3)

**ความเสี่ยงที่บันทึกไว้ (ยังไม่แก้)**
- **Live process ใช้โค้ดเก่า**: seed แล้ว health เห็น 22 แต่ keyword routing ใน busd ยังเป็นพฤติกรรมเดิมจนกว่าจะ deploy + restart — ห้ามรายงานว่า "live routing ใช้งานได้แล้ว" ก่อนมีหลักฐานหลัง restart
- **SSoT keyword บางตัวตายตั้งแต่ต้น**: เช่น `"orchestrat"` (prefix) ไม่ match `"orchestrate"` ภายใต้ word boundary, `"pipeline deal"` เป็น phrase ที่ไม่เกิดจริง → ต้องมี Wave 1.1 keyword hygiene (แก้ที่ SSoT + semantic matrix)
- **`mirror` rules ถูก rule กว้างกว่าชนะ** (เช่น "mirror budget" → cfo 2 hits ชนะ mirror_cfo 1 hit) — เป็นพฤติกรรมเดียวกับ `route()` เดิม; ถ้าต้องการ mirror precedence ต้องตัดสินเป็น ADR แยก
- **`schema_migrations` legacy**: `behavior_migration` query `WHERE name = ?` จะพังบน live DB เก่า (`no such column: name`) — latent, ยังไม่แตะใน Wave 1; ต้องรวมใน Wave 2

## Rollout

| Wave | ขอบเขต | Gate |
|:----:|:-------|:-----|
| **1 (นี้)** | routing SSoT + keyword adapter + health parity + backlog age | tests เขียว, semantic matrix, live seed + health before/after, PR review by `@pipeline-auditor` (ยังไม่ merge) |
| 2 | version SSoT (`VERSION` เดียว, health/agent/docs derive) + รวม `schema_migrations` shape | version parity test (health vs package) |
| 3 | config validator (`opencode.jsonc` schema + path/reference checks) ใน CI | validator fail บน fixture ที่พัง, pass บนของจริง |
| 4 | runtime visibility ครบ (config validity + routing parity + version parity ใน health), CI บังคับ sync | health dashboard เห็น drift ทุกเสา |

**Rebase note (Wave 2):** Wave 2 จะแตะ `central_bus/health.py` บรรทัดบน (imports/`VERSION`) — Wave 1 เพิ่ม import `routing_sync` และคีย์ใน dict ท้ายฟังก์ชันเท่านั้น; conflict ให้คงทั้งสองฝั่ง (version logic ของ Wave 2 + routing keys ของ Wave 1) แล้วรัน `test_routing_ssot.py` + version parity test ซ้ำ

## Non-goals (Wave 1)

- ไม่แตะ `opencode.jsonc`, campaigns, frozen v5, ไม่ kill process ใด ๆ
- ไม่ลบ rule/แถวใด ๆ (seed เท่านั้น) — rollback ระบุเป็น id list
- ไม่ wire `BehaviorRouter` (แยกการตัดสิน; ADR-017 ยัง governs signal gate)
- ไม่แก้ keyword ของ SSoT (Wave 1.1)
- ไม่ merge เอง — maker ≠ checker

## References

- `central_bus/routing_sync.py`, `central_bus/router.py`, `central_bus/health.py`, `central_bus/queue.py`, `central_bus/migrate.py`
- `central_bus/tests/test_routing_ssot.py`
- `bus/evidence/2026-11-23/wave1-routing-ssot/` (dry-run/apply output, health before/after, matrix, rollback ids)
- `bus/system/routing_rules.json` (SSoT, checksum ใน evidence)
- ADR-016 / ADR-017 (behavior routing history), ADR-021 (health check pattern)
