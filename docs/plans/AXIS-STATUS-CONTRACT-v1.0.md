# AXIS STATUS — Contract v1.0 (`axis.status/1`)

> **สถานะ:** รอยืนยันคู่กับ D1 · **วันที่:** 2026-11-23
> **D1 note:** [AXIS-STATUS-C0-D1-v1.0.md](AXIS-STATUS-C0-D1-v1.0.md)
> เอกสารนี้เป็นรายละเอียดเชิงสัญญา — ยังไม่ใช่โค้ด

---

## 1. Schema

```json
{
  "schema": "axis.status/1",
  "generated_at": "<ISO-8601 UTC>",
  "overall": { "status": "healthy|degraded|down", "score": 0, "color": "green|amber|red" },
  "sources": [
    {
      "id": "busd",
      "status": "ok|degraded|down|unknown",
      "latency_ms": 0,
      "fresh": true,
      "detail": {},
      "warning": null
    }
  ],
  "warnings": ["<human-readable>"],
  "meta": { "duration_ms": 0, "cache": "fresh|cached", "tool_version": "1.0.0" }
}
```

**หลัก:** field ชื่อคงที่ · เพิ่ม source ใหม่ได้โดยไม่เปลี่ยน schema · ห้ามลบ field ในเวอร์ชัน 1.x

---

## 2. Status vocabulary

| ค่า | ความหมาย | ตัวอย่าง |
|:---|:---|:---|
| `ok` | วัดได้ + ตรง contract | busd 200, queue dead=0 |
| `degraded` | ทำงานบางส่วน/มี warning | relay up แต่ extension offline |
| `down` | ติดต่อไม่ได้/error | HTTP timeout, process ไม่มี |
| `unknown` | ยังวัดไม่ได้/ข้อมูลไม่พอ | source ใหม่ที่ยังไม่ implement |

**กฎเหล็ก:**
- `unknown` ห้ามนับเป็น `ok` — ต้องมี warning และถูกตัดออกจาก weighted score (renormalize)
- `degraded` ต้องมี `warning` ที่มนุษย์อ่านรู้เรื่อง (บอกผลกระทบ ไม่ใช่รหัส)

---

## 3. Sources + weights

| source id | น้ำหนัก | critical | วิธีวัด | ข้อมูลหลัก |
|:---|---:|:---:|:---|:---|
| `busd` | 25 | ✅ | `GET http://127.0.0.1:8099/v1/health` + `X-API-Key` | status, queue pending/failed/dead, rules_in_sync, uptime, version |
| `cto` | 20 | — | health probe / DB ที่ประกาศ | architect/engineering/qa, db, cache |
| `content` | 15 | — | artifact/registry + runtime metadata | specialists, `restart_required`, module registry |
| `mcp_freshness` | 15 | ✅ | `stat /proc/<pid>` + mtime ใต้ `axis_mcp/` | generations, fresh, `process_started_at` |
| `git` | 10 | — | `git rev-parse`, `git status --porcelain` | HEAD, branch, dirty count |
| `browse` | 10 | — | `browse status --json` / relay endpoint | relay up, extension paired |
| `codegraph` | 5 | — | `codegraph_status` / CLI | files, nodes, edges, size |

---

## 4. Scoring

- ค่าเดี่ยว: `ok=1`, `degraded=0.5`, `down=0`, `unknown=ตัดออก`
- `score = Σ(weight × value) / Σ(weight ที่ไม่ unknown) × 100` (ปัดเป็นจำนวนเต็ม)
- **Overall:**
  - ถ้า critical (`busd` หรือ `mcp_freshness`) เป็น `down` → `down` ทันที
  - ไม่เช่นนั้น `score ≥ 90` → healthy · `70–89` → degraded · `< 70` → down
- `color`: healthy=green · degraded=amber · down=red

---

## 5. Timeouts + cache

| ค่า | ค่าเริ่มต้น | หมายเหตุ |
|:---|:---|:---|
| Budget รวม | 2000 ms | ตัดจบแล้วคืน partial |
| Per-source | 1200 ms | source ใด timeout → `down` + warning |
| Cache TTL | 10 s | ต้องรายงาน `meta.cache`; force flag ข้าม cache |

**Partial > Fail:** source หนึ่งล่ม ต้องยังคืนผลที่เหลือ ไม่ throw ทั้งก้อน

---

## 6. Freshness rule

- MCP fresh = `process_started_at > newest_source_mtime + 1s`
  (tolerance เดียวกับ `axis_mcp/runtime_freshness.py`)
- Content fresh = `runtime.restart_required == false`
- `fresh=false` → warning: “process เก่ากว่าซอร์ส → restart ก่อนเชื่อผล”
- ต้องทดสอบด้วยการแตะไฟล์ระหว่าง process รัน (D3)

---

## 7. Redaction rule

- API key อ่านจาก env ใส่ header เท่านั้น
- ห้ามมี key/token/cookie ใน output, log, error message
- error ต้องไม่ echo request headers
- D2 ต้องมี test ที่ค้นหา secret pattern ใน output

---

## 8. Out of scope (ห้ามขยายใน C)

- ไม่ใช่ที่แทน CTO/Content tool — ไม่มี write/approve/publish
- ไม่มี UI/dashboard ใน C (เฉพาะ schema + tool)
- ไม่มี cross-MCP call / external network
- ไม่แตะ queue DB เพื่อ retry/ลบ — รายงานเท่านั้น
- ไม่แก้ `opencode.jsonc` จนกว่า D4 ผ่าน (แยก PR)

---

## 9. ความเสี่ยง / จุดตัดสินตอน D2

| ความเสี่ยง | แนวทาง |
|:---|:---|
| busd ต้องมี API key | อ่านจาก env; ไม่มี → `busd=down` + warning (ไม่ crash) |
| repo path เป็น symlink (`/home/...` → `/data/...`) | resolve path ก่อนเทียบ mtime |
| process start กับ mtime ใกล้กัน | tolerance 1s ตามโค้ดเดิม |
| browse ไม่มีใน headless | `paired-offline` = degraded (งานหลักไม่พัง) |
| CTO/content ไม่มี HTTP endpoint | D2 เลือก probe DB/artifact หรือเพิ่ม health endpoint (แยก PR) |
| aggregator เองช้า | รายงาน `meta.duration_ms` + เฝ้าใน CI |

---

## 10. D3 test matrix (ขั้นต่ำ 20 งาน)

| กลุ่ม | ตัวอย่างเคส |
|:---|:---|
| Happy path | ทุก source ok · cache fresh |
| Source ล่ม | ปิด busd · kill MCP · relay ไม่มี |
| Timeout | หน่วง source เกิน 1200 ms |
| Freshness | แตะไฟล์หลัง process start · restart แล้ว fresh |
| Queue | failed>0 · dead>0 · oldest routed ค้าง |
| Git | dirty หลายไฟล์ · detached HEAD |
| Secrets | env มี key → output ต้องไม่มี |
| Degraded | browse offline · CTO module degraded |
| Unknown | source ที่ยังไม่ implement |
| Repeat | เรียกซ้ำใน TTL ได้ cached · force ได้ fresh |

> ทุกแถวต้องมี: คาดว่าได้อะไร / ได้จริง / ผ่าน-ไม่ผ่าน / root cause (ถ้าพัง) — ห้าม cherry-pick
