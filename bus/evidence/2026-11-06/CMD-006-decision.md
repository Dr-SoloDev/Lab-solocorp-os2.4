# CMD-006 — C2 Registry schema: decision note (T1 + T2 + T3)

**Ticket:** CMD-006 (`bus/dispatch/2026-11-06/CMD-006-c2-registry-schema-permissions.json`)
**Date decided:** 2026-11-06 · **Written up:** 2026-11-22 (P1 T2 — ใบปิดงาน)
**Status:** DECIDED + IMPLEMENTED · **Scope:** C2 schema v2 (config only, no transport change)
**Implements:** `d41b711` (code+config+tests+runbook, paired commit) ·
PRD wording fix `a866fd6` ·
Release note `docs/releases/C2-REGISTRY-SCHEMA-V2.md` ·
Rollback runbook `docs/runbooks/registry-schema-rollback.md`

> ไฟล์นี้คือ `bus/evidence/2026-11-06/CMD-006-decision.md` ที่ release note อ้างถึง
> (`C2-REGISTRY-SCHEMA-V2.md:6`) แต่ไม่เคยถูกเขียน — T2 เขียนย้อนหลังโดยยึด
> implementation ที่ merge แล้วเป็นหลักฐาน (code = decision record)

ทุกข้อสรุปข้างล่างอ้างไฟล์+บรรทัดบน `main @ 357720b` (branch นี้ fork ตรงจาก tip)

---

## T1 — รูปแบบของ `permissions` (P0, ตัวบล็อก C2)

**ตัดสินใจ: ทางเลือก (a) — list ของ SCOPE_LEVELS ที่ validate เป็น enum + provider-side metadata**

`permissions` ของ module คือ **"scope ที่ tool ของ module ตัวเองประกาศว่าใช้"**
(provider-side: what this module's own tools expose) — **ไม่ใช่** "scope ที่ caller
ต้องมีเพื่อเรียก module นี้" (consumer-side gate) เหตุผล: ความหมายแบบ consumer-side
ขัดกับ DESIGN D3:113 ("scope ที่ module ขอ") และทำให้ department MCP แบบ standalone
ดูเหมือนต้องมี Core credential — ซึ่งผิด FR-07 (PRD Must Have #5)

หลักฐานการผูกความหมายไว้ในเอกสารแล้ว:

- `docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md:100` (Must Have #3,
  แก้ wording โดย `a866fd6`): *"declared permissions (the scopes the module's
  own tools expose — metadata, not a caller gate)"*
- `axis_mcp/module_registry_schema.py:1-11` (module docstring): *"`permissions`
  names the scopes a module's own tools use, and nothing here gates a
  connect/call on it (FR-07)"*

กฎ validator (ตอบ acceptance criteria T1 ทั้ง 5 ข้อ):

1. **Enum จาก vocabulary เดียว:** `VALID_PERMISSION_LEVELS = frozenset(SCOPE_LEVELS)`
   (`module_registry_schema.py:54`) — import จาก `axis_mcp/auth.py:16`
   (`SCOPE_LEVELS = {"public": 1, "team": 2, "admin": 3}`) ไม่มี word list ที่สอง
   (`module_registry_schema.py:51-53` comment อ้าง DESIGN §5.3)
2. **Provider-side, never a gate:** ไม่มี code path ใดใน registry/auth ที่เอา
   `permissions` มาตัดสิน connect/call — เป็น declarative metadata อย่างเดียว
3. **FR-07 ไม่เสีย:** department MCP ไม่สร้าง registry ตอน import อีก;
   สร้างแบบ lazy และ seed เฉพาะ module ของตัวเอง (`module_registry.py:246-256`
   `seed_module_ids`; docstring `module_registry.py:17-35`)
4. **ไม่ต้องแก้ `auth.py`:** ไม่เพิ่ม scope ใหม่ — ถ้าวันหนึ่งเพิ่ม (เช่น scope ใหม่)
   ต้องแก้ `SCOPE_LEVELS` + `KEY_PATTERN` (`auth.py:19`) + tests พร้อมกัน
   (vocabulary เดียว บังคับโดย construction)
5. **Scope ที่ยังไม่มีในระบบ = error (ไม่ใช่ warning, ไม่เก็บเฉยๆ):**
   `_validate_permissions` (`module_registry_schema.py:216-231`) —
   unknown → `"permissions must be a subset of [...]"`, duplicate → error,
   non-list/non-string → error; ลำดับไม่มีความหมาย ฝั่งเขียน normalize ด้วย
   `canonical_permissions` (`module_registry_schema.py:249-261`,
   เขียนตาม `SCOPE_LEVELS` order; ฝั่งอ่านไม่ reorder ไม่ write)
   ครอบคลุมด้วย test `test_permissions_*` (`tests/test_module_registry_c2.py:351-399`,
   รวม `test_permission_levels_are_the_auth_vocabulary`)

ตัวอย่างจริง 3 module (`config/module-registry.json` บน main):

| module | permissions | อ่านว่า |
|:--|:--|:--|
| `solocorp` (Core) | `["public", "team", "admin"]` | tool ของ Core ใช้ครบ 3 scope |
| `content-creator` | `["public"]` | tool ของ Content ใช้แค่ public |
| `qa` | `["public"]` | tool ของ QA ใช้แค่ public |

---

## T2 — นโยบาย schema migration + rollback (P1)

**ตัดสินใจ: version gate แบบ fail-closed + paired-commit + ซ่อมด้วย procedure (ไม่ใช่ UI)**

กฎ `_meta.schema_version` (`module_registry_schema.py:95` `SCHEMA_VERSION = 2`,
`:98` `LEGACY_SCHEMA_VERSION = 1`):

| config ที่เจอ | code v2 ทำอะไร | หลักฐาน |
|:--|:--|:--|
| ไม่มี `_meta.schema_version` (legacy) | = v1, **accepted** | `_declared_schema_version` (`:571-587`): absent/unusable → legacy |
| `< SCHEMA_VERSION` (เช่น 1) | **accepted** — upgrade ไม่ทำลาย install เก่า | comment `:301`; test `test_v1_config_*` (`test_module_registry_c2.py:113-141`) |
| `> SCHEMA_VERSION` (เช่น 3) | **`RegistryDowngradeError` ก่อน field validation** — 1 ข้อความ actionable เดียว ไม่ใช่ "unknown field" noise | `load_and_validate_config` (`:589-616`, raise ที่ `:607-614`); test `test_newer_schema_raises_downgrade_error` (`:175`) + `test_downgrade_is_detected_before_field_validation` (`:195`) |

- `status()` / `validate()` ติดป้าย `error_kind ∈ {corrupt, downgrade, invalid, None}`
  (`module_registry.py:608-618`, `:695-702`) — C1 keys/shapes ไม่เปลี่ยน
- **เมื่อไร bump version:** เมื่อไฟล์ที่ code ใหม่เขียนจะถูก code เก่า reject
  (เพิ่ม optional field ก็นับ เพราะ reader เก่า reject unknown field —
  `module_registry_schema.py:88-93` comment)
- **Paired-commit rule:** code + `config/module-registry.json` ต้องไป commit เดียวกัน
  (`d41b711` ทำแบบนี้โดยเจตนา — `git revert <sha>` เอาทั้งสองฝั่งกลับ);
  code-only deploy = v1 reader เจอ v2 config = registry ตายทั้งก้อน (กับดักที่ QA เจอ)
- **Recovery (ตามลำดับ):** restart MCP ทุกตัวก่อน/หลัง (`scripts/restart-mcp.sh --yes`
  — MCP load code ครั้งเดียวตอน startup) → `git revert` commit คู่ →
  ถ้า revert ไม่ได้ (มี module ลงทะเบียนหลัง upgrade) ใช้
  `python scripts/registry-repair.py --to-schema 1 --keep-modules --yes`
  (dry-run เป็น default) → ทำตาม `docs/runbooks/registry-schema-rollback.md`
- **ข้อจำกัดที่ยอมรับ:** v1→v2 rollback ซ่อมด้วย procedure ไม่ใช่ UI
  (v1 ไม่มี `RegistryDowngradeError`) — ห้าม describe ว่าเป็น zero-pain
  (release note `:80-81`)

หลักฐานว่า procedure ใช้ได้จริง (รัน 2026-11-22, output ใน
`bus/evidence/2026-11-22/CMD-006-T2/`):

- v1 code (`a866fd6:solocorp_mcp/module_registry_schema.py`) อ่าน v2 config ปัจจุบัน
  → **31 errors** (`unknown field` × 30 + `schema_version must be 1, got 2`) —
  คือ dead-end ที่ version gate ถูกสร้างมาแก้
- `registry-repair.py --to-schema 1 --keep-modules` (dry-run, exit 0) → strip 30 fields
- รันจริงบนสำเนา (`--yes`) → v1 `validate_config` ผ่าน **CLEAN 0 errors**,
  5 modules อยู่ครบ, `_meta = {schema_version: 1, total_modules: 5}`
- live gate: config `schema_version: 99` เจอ code ปัจจุบัน →
  `RegistryDowngradeError` ก่อน field validation ทันที; config จริง
  `validate()/status()` → `error_kind: None`
- `tests/test_module_registry_c2.py` เต็มไฟล์: **81 passed**

---

## T3 — ชนิดข้อมูล field ที่เหลือ (P2, implement ครั้งเดียวจบ)

| field | type | validation (code ref) | ตัวอย่างจริง (5 modules) | หมายเหตุ decision |
|:--|:--|:--|:--|:--|
| `version` | string `MAJOR.MINOR.PATCH` (+ `-`/`+` suffix ≤32 chars) | `VERSION_PATTERN` (`:101-104`); `≤48` chars (`:171-184`) | ทุก module `"0.1.0"` | **module ประกาศเอง** (declared) ไม่ใช่ runtime observe; ไม่ใช่ free string |
| `capabilities` | list ⊂ `{"tools","resources","prompts"}` | allow-list (`:57`); unknown/duplicate → error (`:186-201`) | Core `["tools","resources"]`; ที่เหลือ `["tools"]` ยกเว้น content `["tools","resources"]` | มีไว้ให้ **UI แสดง + CEO เลือก route** (D3:111) |
| `dependencies` | list of string: module id ใน config เดียวกัน หรือ `"busd"` | shape-only ตอนตรวจ entry (`:203-213`); cross-entry check ตอนรวม (`:498-502`); `INFRA_DEPENDENCIES = {"busd"}` (`:60`) | ทุก module `[]` | ว่างได้; เอาไว้ตอบ FR-04 (D3:112); `"busd"` คือ infra ไม่ใช่ module |
| `permissions` | list ⊂ `{"public","team","admin"}` | ดู T1 (`:216-231`) | ดูตาราง T1 | scope ที่ module ขอ สอดคล้อง `SOLOCORP_API_KEY` scope (D3:113) |
| `entry_repo` | string: `"internal"` \| path \| url | 1–512 chars, ห้าม whitespace หัวท้าย/newline (`:234-246`); **ไม่ stat filesystem** (`:234` docstring — config แชร์ข้ามเครื่อง) | ทุก module `"internal"` | เปลี่ยนแค่ field นี้ตอน ADR-030 split → app ไม่แก้โค้ด (D3:114, D3:139) |
| `transport` | enum (ตอนนี้ `{"stdio"}`) | `VALID_TRANSPORTS` (`:48`); transport ไม่รู้จัก → error (`:342-350`) | ทุก module `"stdio"` | ขยายเป็น `http` = เพิ่ม enum + entry field ใน `TRANSPORT_ENTRY_FIELDS` (`:66`) ไม่ใช่ breaking change (CMD-006 §3.2); `command` จำเป็น **ต่อ stdio** ไม่ใช่ทุก transport |

ทั้งหมด optional (`CONFIG_MANIFEST_FIELDS`, `:74-75`) — config ยุค v1 ไม่มี field
พวกนี้ก็ load ได้ ไม่ต้อง migrate (`:450` `validate_config`, `:74-78`)

---

## Owner sign-off

- [ ] **Owner (Dr.solodev)** — รับทราบ T1 (enum + provider-side), T2 (version/rollback
      rules + rollback ไม่ใช่ zero-pain), T3 (ตาราง field) — หลักฐานอ้างไฟล์+บรรทัดจริง
      และมี test output รองรับ (ดู Evidence index ข้างล่าง)
- [ ] ถ้าไม่เห็นด้วยกับข้อใด — comment ใต้บรรทัดนี้ แล้วตีกลับเป็น CMD-006-Tx ใหม่
      (ห้ามแก้ implementation ย้อนหลังโดยไม่มี ticket)

```
Signed-off-by: ________________________   Date: __________
```

## Evidence index

- `bus/evidence/2026-11-22/CMD-006-T2/dry-run.txt` — repair dry-run (exit 0, strip 30 fields)
- `bus/evidence/2026-11-22/CMD-006-T2/repair-write.txt` — repair `--yes` บนสำเนา
- `bus/evidence/2026-11-22/CMD-006-T2/v1-reads-v2-errors.txt` — v1 reader เจอ v2 config (31 errors)
- `bus/evidence/2026-11-22/CMD-006-T2/downgrade-test.txt` — v1 อ่านไฟล์หลัง repair (CLEAN) + live gate schema 99 + live validate
- `bus/evidence/2026-11-22/CMD-006-T2/pytest-c2.txt` — `tests/test_module_registry_c2.py` 81 passed
- Dispatch ต้นฉบับ (ปิดแล้ว): `bus/dispatch/2026-11-06/CMD-006-c2-registry-schema-permissions.json`
  (T1/T2/T3 → `completed`, หลักฐานชี้มาไฟล์นี้)
