# AXIS STATUS — Contract v1.1 (`axis.status/1`)

> **สถานะ:** อนุมัติโดย Owner (Dr.solodev) 2026-11-23 — **แก้ไขเพิ่มเติมจาก v1.0** ตามแผน B (timebox 1 รอบ)
> **แทนที่:** [`AXIS-STATUS-CONTRACT-v1.0.md`](AXIS-STATUS-CONTRACT-v1.0.md) สำหรับงานใหม่ทั้งหมด · v1.0 เก็บเป็นประวัติ
> **D1:** [`AXIS-STATUS-C0-D1-v1.0.md`](AXIS-STATUS-C0-D1-v1.0.md) (ขอบเขตเดิมไม่เปลี่ยน)

---

## 0. Changelog v1.0 → v1.1

| # | เปลี่ยน | เหตุผล | D3 ที่เกี่ยวข้อง |
|:-:|:---|:---|:---|
| 1 | **CTO required columns** — กำหนดคอลัมน์บังคับต่อ table + ตรวจ `PRAGMA table_info` | v1.0 กำหนดแค่ชื่อ table → wrong-column DB ยัง `ok/green` | L1 |
| 2 | **Codegraph ขั้นต่ำ** — `files == 0` หรือ `nodes == 0` → `degraded`; `edges == 0` ขณะ `nodes > 0` → `degraded` | v1.0 ไม่มี threshold → index ว่างยัง `ok/green` | O1 |
| 3 | **busd required fields ต้องไม่เป็น null** — ไม่ใช่แค่ "มี key" | v1.0 ตรวจแค่ key หาย → `null` ยัง `ok/green` | NIT-1 |
| 4 | **busd `db` block บังคับ** — ต้องเป็น dict และมี `queue_pending/queue_failed/queue_dead` เป็น int | ป้องกัน partial payload ที่ดูเหมือนสุขภาพดี | NIT-1 |
| 5 | **`_build_payload` robustness** — ใช้ `row.get("warning")` | private helper ไม่ควร `KeyError` | NIT-2 |

> ไม่เปลี่ยน: schema, 7 source ids, weights, critical sources, thresholds, timeout, cache, freshness, redaction, out-of-scope (§1–§10 ของ v1.0 ยังใช้)

---

## 1. CTO required columns (v1.1)

ตรวจด้วย `PRAGMA table_info(<table>)` แบบ read-only · ถ้า table หาย **หรือ** คอลัมน์บังคับหาย → `cto = down` + `missing_tables` / `missing_columns` + warning

| Table | Required columns |
|:---|:---|
| `tool_calls` | `id`, `module`, `tool_name`, `status` |
| `build_artifacts` | `id`, `project_id`, `artifact_path` |
| `qa_evidence` | `id`, `task_id`, `status` |

**หมายเหตุ:** คอลัมน์อื่นนอกเหนือจากนี้ไม่บังคับ (รองรับ schema evolution) · ถ้า DB อ่านได้แต่ table ว่าง ยัง `ok` (ไม่มีข้อมูล ≠ พัง)

---

## 2. Codegraph thresholds (v1.1)

| เงื่อนไข | ผล |
|:---|:---|
| DB อ่านไม่ได้ / table หาย | `down` |
| `files == 0` หรือ `nodes == 0` | `degraded` + warning "index is empty" |
| `nodes > 0` แต่ `edges == 0` | `degraded` + warning "index has no edges" |
| อื่นๆ | `ok` (รายงาน counts + size ตามปกติ) |

---

## 3. busd required fields (v1.1)

ต้องมีและไม่เป็น `null`/ค่าว่าง:

| Field | ชนิด/เงื่อนไข |
|:---|:---|
| `status` | string, ต้องเป็น `"ok"` จึงจะเป็น `ok` |
| `db` | dict ที่มี `queue_pending`, `queue_failed`, `queue_dead` เป็น int ≥ 0 |
| `rules_in_sync` | bool |
| `version` | string ไม่ว่าง |
| `uptime_seconds` | int ≥ 0 |

- ขาด/`null`/ชนิดผิด → `degraded` + warning ระบุ field ที่ผิด (ค่า `queue_failed > 0`, `queue_dead > 0`, `rules_in_sync == false` ยังใช้ warning เดิม)
- ติดต่อไม่ได้ / 401 / 403 / non-JSON → `down` (ตาม v1.0)

---

## 4. การทดสอบที่ต้องมี (D2/D3)

| เคส | คาด |
|:---|:---|
| CTO table ครบ แต่ column หาย | `down` + `missing_columns` (เช่น `tool_calls` ไม่มี `status`) |
| CTO table + column ครบ (แม้ 0 rows) | `ok` |
| codegraph 0 files | `degraded` |
| codegraph 0 nodes | `degraded` |
| codegraph nodes>0, edges=0 | `degraded` |
| busd field เป็น `null` | `degraded` + warning |
| busd `db` block หาย/ชนิดผิด | `degraded` + warning |
| `_build_payload` row ไม่มี key `warning` | ไม่ raise · warning = `None` |

---

## 5. Acceptance / Timebox

- Timebox: **1 รอบ audit เท่านั้น** สำหรับ v1.1
- ผ่านเมื่อ: D2 tests + D2 harness ผ่าน · D3 ≥39 cases, **0 FAIL, 0 SKIP** · checker อิสระ PASS
- ถ้ารอบแรกยังมี FAIL/SKIP ใหม่ → **หยุด** รับ SKIP ที่เหลือ + Owner sign-off แล้วไป D4 (fallback แผน C)

---

## 6. อนุมัติ

| บทบาท | ชื่อ | ผล | วันที่ |
|:---|:---|:---:|:---|
| Owner | Dr.solodev | ☑ อนุมัติแผน B + contract v1.1 | 2026-11-23 |
| CEO | เทอโบ | ☑ อนุมัติ | 2026-11-23 |
