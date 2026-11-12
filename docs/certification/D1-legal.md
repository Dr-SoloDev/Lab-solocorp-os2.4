# D1 — Agent Rationale: `legal-tulya` MCP (Legal · ตุลย์)

> ตาม `sop/TEMPLATE-D1-agent-rationale.md` · `rules/06-certification.md` §2
> **ผู้ทำ (maker):** CEO เทอโบ — ออกแบบ ยังไม่ implement
> **วันที่:** 2026-11-10 · **งาน/CMD:** Legal MCP D1+D2 (Owner สั่งหลังพบว่ายังไม่มี MCP แผนก Legal)
> **สถานะ:** Draft — รอ Owner ตัดสิน (default = ยังไม่ผ่าน)

---

## 0. สถานะจริงของโค้ดวันนี้ (ต้องอ่านก่อน — กัน overclaim)

| ของ | มีจริงไหม |
|:--|:--|
| `profiles/13-legal/SOUL.md` | ✅ มี (ตุลย์ — Compliance, Contracts, Law) |
| `.opencode/agents/legal-tulya.md` | ✅ มี (สเปก AXIS, Owner-authored) |
| `axis_mcp/departments/legal_mcp.py` | ❌ ยังไม่มี (engineering/qa/content/product มีแล้ว) |
| `legal_vault/` | ❌ ยังไม่มี (gitignored — runtime-only by design) |

→ เอกสารนี้คือ **แผน (rationale)** ไม่ใช่หลักฐานว่า implement แล้ว → **implement = งาน D2** ต้องมีหลักฐาน

---

## 1. งานคืออะไร

ให้แผนก Legal มี **department MCP** ที่ expose งานกฎหมายแบบไม่ใช้ LLM และ **ไม่ให้คำแนะนำกฎหมายจริง** (hard stop):

**Input:** โจทย์จาก CEO ("ขอ review สัญญา X" / "เช็กลิสต์ compliance เรื่อง Y")
**Output:** review request record / compliance checklist (ไฟล์จริง + sha) ที่สถานะ `requires_human_review: true` เสมอ — ไม่ approve ไม่ตัดสิน

**ขอบเขตรอบนี้ = 3 อย่างเท่านั้น:** info + matters list + review-request draft + compliance-checklist draft (opinion/approval = ขยายภายหลังพร้อมทนายจริง)

## 2. ทำไมต้องใช้ agent

| เหตุผล | เงื่อนไขที่มนุษย์/script ทำแทนไม่ได้ |
|:--|:--|
| **อ่านหลายแหล่งต่อ 1 งาน** | ต้องอ่าน SOUL + ระเบียบ + ไฟล์สัญญาก่อนสกัด checklist — script ไม่รู้ว่าจะหยิบอะไร |
| **ต้อง "ลงมือ" ไม่ใช่ "ตอบ"** | ต้องเขียน record ลง `legal_vault/reviews/` + คืน sha ให้ตรวจย้อนได้ |
| **guard สำคัญกว่าฉลาด** | ต้องกันไม่ให้ approve เอง + กัน path traversal ออกจาก vault |

**script ทดแทนไม่ได้เพราะ:** การตัดสินใจว่า "อะไรต้องมีมนุษย์ตรวจ" + การผูก task record + evidence ต้องมี reasoning

## 3. agent ตัวไหน + เครื่องมือที่ต้องใช้

**ตัวแทน:** `legal-tulya` (`profiles/13-legal/SOUL.md`) → MCP หัวหน้าตาม pattern `engineering_mcp.py` (FastMCP `"legal"`)

| เครื่องมือ | ใช้ทำอะไร | มีจริงไหม |
|:--|:--|:--|
| `legal_department_info` | แจ้ง scope/head/specialists/data root | ❌ ต้องสร้าง D2 |
| `legal_list_matters` | รายการ matters ตาม status | ❌ ต้องสร้าง D2 |
| `legal_create_review` | เขียน review request (template, ไม่ approve) | ❌ ต้องสร้าง D2 |
| `legal_check_compliance` | checklist ที่ทุกข้อ = requires_human_review | ❌ ต้องสร้าง D2 |

**ไม่ใช้:** LLM (`think`), ความเห็นกฎหมาย, การ approve ใดๆ

## 4. ขอบเขตสิทธิ/เครื่องมือ

**ได้ทำ:** อ่าน `profiles/13-legal/**`, `docs/**` · เขียนไฟล์ **เฉพาะใต้ `legal_vault/reviews/`** (gitignored, runtime-only) · slug validate แบบเดียวกับ product

**ห้ามทำ (hard stop):**
- ⛔ ห้ามให้คำแนะนำ/ความเห็นทางกฎหมาย (ทุกผลลัพธ์ต้องมี `requires_human_review: true`)
- ⛔ ห้าม approve / รับรองเอกสารใดๆ (publish gate อยู่ที่มนุษย์เท่านั้น)
- ⛔ ห้ามเขียนนอก `legal_vault/reviews/`
- ⛔ ห้ามอ่าน `.env`, คีย์, ไฟล์เงิน
- ⛔ ห้าม commit/push
- ⛔ ห้าม expose specialist ภายในเป็นการเรียกตรง external client

> ⚠️ **ความจริงที่ต้องยอมรับ:** ข้อห้ามข้างบนยัง **ไม่ถูกบังคับในโค้ดวันนี้** เพราะยังไม่มีโค้ด
> → **guard = งาน D2** ต้องมีหลักฐานก่อนผ่าน → จนกว่าจะมี guard: `legal-tulya` ถือว่า **D0** (ร่างได้เท่านั้น)

## 5. เส้นชัยของงานนี้ (D1 ผ่านเมื่อครบ 5 ข้อ)

| # | เกณฑ์ | วัดด้วย |
|:-:|:--|:--|
| 1 | Legal มี MCP ตัวแยก? Decide standalone | D1 นี้: standalone ตาม pattern eng/qa/content/product (FR-07) |
| 2 | มี tools 4 ตัวขั้นต่ำ | `legal_department_info`, `legal_list_matters`, `legal_create_review`, `legal_check_compliance` |
| 3 | ไม่ approve เอง 100% | ทุก output มี `requires_human_review: true`, ไม่มีคำว่า approved |
| 4 | FR-07 standalone ผ่าน | test ได้โดยไม่ต้อง CEO/Core MCP |
| 5 | Maker ≠ Checker | Owner เป็น checker อ่าน D1 นี้ก่อนอนุมัติ D2 |

**ไม่ผ่านถ้า:** ไม่มีร่าง options · ไม่มี permission scope · ไม่มี 4 tools · ไม่มีเส้นชัย measurable · tool ใด approve เอง
