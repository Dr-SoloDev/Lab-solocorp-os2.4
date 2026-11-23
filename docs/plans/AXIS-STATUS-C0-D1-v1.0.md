# AXIS STATUS — C0 / D1 · 1-Page Note

> **สถานะ:** ✅ อนุมัติแล้ว (2026-11-23) · **เจ้าของ:** AXIS CEO (เทอโบ)
> **ด่าน:** D1 ตาม `rules/06-certification.md` — เอกสารนี้ **ห้ามมีการเขียนโค้ด**
> **ภาพประกอบ:** [axis-status-option-c.html](../explainers/axis-status-option-c.html) · **Contract เต็ม:** [AXIS-STATUS-CONTRACT-v1.0.md](AXIS-STATUS-CONTRACT-v1.0.md)

---

## 1. งานคืออะไร

สร้าง **Unified Status Layer** — MCP server ใหม่ `axis-status` เปิด tool เดียว `axis_status` รวมสถานะ 7 แหล่ง (busd, CTO, Content, MCP freshness, git, browse, codegraph) เป็น JSON schema เดียว (`axis.status/1`) ภายใน 1 call

**ปัญหา:** สถานะกระจายอยู่ 6–7 ที่ ไม่มีจุดเดียวตอบว่า “ทั้งองค์กรเป็นยังไง” · ไม่มีกลไกกัน process เก่ากว่าซอร์ส · relay ขึ้นแต่ extension offline ก็ยังรายงานว่าเขียว

**ผลลัพธ์:** Owner ถามครั้งเดียวได้ภาพรวม + warning · App/CLI/CI ใช้ schema เดียวกัน

---

## 2. ทำไมต้องเป็น agent/tool (ไม่ใช่มนุษย์สรุป)

| เหตุผล | คำอธิบาย |
|:---|:---|
| วัดซ้ำได้ | สถานะเปลี่ยนทุกนาที — ต้องวัดสด ไม่ใช่ความจำ |
| กัน false green | freshness/degraded คำนวณจาก process + mtime จริง |
| มีหลักฐาน | ทุกผลมี timestamp, latency, source id |
| ใช้ซ้ำ | CEO session, App, CLI, CI พูดภาษาเดียวกัน |
| ขยายได้ | เพิ่มแผนก = เพิ่ม adapter 1 ตัว |

---

## 3. ใช้ใคร + เครื่องมืออะไร

| บทบาท | คน/ตัว |
|:---|:---|
| Maker | CTO (เวคเตอร์) → `build` agent |
| Checker | QA / `reality-checker` (คนละตัวกับ Maker) |
| Approver | Owner / CEO |

**แหล่งวัด (read-only):** busd `/v1/health` · CTO modules · Content runtime/registry · MCP process+mtime · `git rev-parse/status` · `browse status` · `codegraph_status`

**ข้อจำกัด:** MCP stdio ไม่มี server-to-server call → วัดจากภายนอก (HTTP/FS/process) เท่านั้น

---

## 4. ขอบเขตสิทธิ

**ทำได้:** อ่าน repo (`axis_mcp/`, `central_bus/`, `bus/`, `brain/`, `opencode.jsonc`) · GET `127.0.0.1:8099` · `ps`/`/proc`/`stat`/`git` แบบ read-only · `browse status`

**ห้าม:** เขียน/ลบ/แก้ไฟล์หรือ DB ใดๆ · POST/PUT/PATCH · approve/publish/retry · log/ส่ง secret · แตะ `.env`, `legal_vault/`, นอก repo · เรียก MCP อื่นแบบ server-to-server

**Redaction:** API key อยู่ใน header เท่านั้น — ห้ามปรากฏใน output/log/error

---

## 5. เส้นชัย

| ด่าน | หลักฐาน | ผ่านเมื่อ |
|:---:|:---|:---|
| **D1** | เอกสารนี้ + contract | Owner/CEO อนุมัติ |
| **D2** | server 50–150 บรรทัด + run output + exit code | 1 call คืน schema ครบ 7 sources |
| **D3** | ตาราง ≥20 งาน (คาด/ได้จริง/root cause) | ครอบ source ล่ม, timeout, process เก่า, relay offline, queue failed, git dirty — **ไม่มี false green** |
| **D4** | runbook + ผลรันคนอื่น | คนละคนกับ Maker รันซ้ำได้ผลเดิม |

**Acceptance C1:** ครบ 7 sources ≤2s · มี status/latency/fresh ครบ · `unknown ≠ ok` · fresh=false ตรวจเจอเมื่อแตะไฟล์ · ไม่มี secret ใน output · partial result เมื่อ timeout

---

## 6. อนุมัติ

| บทบาท | ชื่อ | ผล | วันที่ |
|:---|:---|:---:|:---|
| Owner | Dr.solodev | ☑ อนุมัติ | 2026-11-23 |
| CEO | เทอโบ | ☑ อนุมัติ | 2026-11-23 |

> อนุมัติแล้ว → เริ่ม C1 (D2) ที่ CTO/`build` · Checker = QA/reality-checker
