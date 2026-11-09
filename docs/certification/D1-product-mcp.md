# D1 — Agent Rationale: `product-produck` MCP (Product · โปรดัค)

> ตาม `sop/TEMPLATE-D1-agent-rationale.md` · `rules/06-certification.md` §2  
> **ผู้ทำ (maker):** CEO เทอโบ — ออกแบบแทน Product / Architect ยังไม่ implement  
> **วันที่:** 2026-11-09 · **งาน/CMD:** T3 — Product MCP D1 (draft for Owner decision 18:00)  
> **สถานะ:** Draft — รอ Owner ตัดสิน (default = ยังไม่ผ่าน)

---

## 0. สถานะจริงของโค้ดวันนี้ (ต้องอ่านก่อน — กัน overclaim)

เทียบกับ `docs/certification/D1-content-creator.md` (ผ่านแล้ว) สถานะจริงของ Product วันนี้คือ:

| ของ | มีจริงไหม | หลักฐาน |
|:--|:--|:--|
| `profiles/06-product/SOUL.md` | ✅ มี | โปรดัค (Product Manager) — 9 ปีประสบการณ์, PRD/roadmap/user research |
| `solocorp_mcp/departments/product_mcp.py` | ❌ ยังไม่มี | `ls solocorp_mcp/departments/` = content / engineering / qa เท่านั้น |
| `opencode.json` → `mcp.servers` | ❌ ไม่มี product | 8 ตัว: stealth, solocorp, central-bus, content-creator, engineering, qa, concat, github |
| `opencode.jsonc` → `mcp.servers` | ❌ ไม่มี product | 4 ตัว: stealth, central-bus, unified-technical, content-creator |
| Core MCP (solocorp_mcp/server.py) | ⚠️ มี routing/org data | ไม่ใช่ product spec tool — เป็น org/routing ให้ CEO |
| **Product MCP วันนี้** | **ยังไม่ implement** — D1 นี้เป็นร่างแผนเท่านั้น |

**ตอนนี้ใช้ `solocorp_get_commands` / `solocorp_get_department` ผ่าน Core MCP ได้** (org data + routing) — แต่ไม่มี spec/PRD/roadmap tool เป็นของแผนกตัวเอง

→ เอกสารนี้คือ **แผน (rationale)** ไม่ใช่หลักฐานว่า implement แล้ว → **implement = งาน D2** ต้องทำแยก

**ความจริงที่ต้องยอมรับ:** PRD MVP ต้องมี 1 CEO experience + department MCPs standalone (PRD §4 #2 FR-07) — Product เป็นหนึ่งใน department ที่ควร standalone ได้ แต่ยังไม่มี MCP → เป็นช่องโหว่

---

## 1. งานคืออะไร

ให้แผนก Product มี **department MCP** ที่ expose product capability ให้ external client / CEO เรียกได้แบบเดียวกับ Content/Engineering/QA:

**Input:** โจทย์จาก CEO หรือ Owner ("ขอ PRD สำหรับ X" / "จัด priority roadmap Q1" / "วิเคราะห์ feedback")  
**Output:** PRD draft / roadmap doc / priority list + evidence (ไฟล์ + task record) — ไม่ใช่ตอบแค่ประโยคในแชท

**ขอบเขตรอบนี้ = 1 ประเภทเท่านั้น:** **PRD + Roadmap draft** (user research / stakeholder alignment / delivery tracking = ขยายภายหลังพร้อมเกณฑ์ของตัวเอง)

ตัวอย่าง MCP tools ที่จะเสนอ (ยังไม่ทำ):
- `product_department_info()` — head, specialists, scope, data root (pattern เดียว engineering/qa)
- `product_list_features(limit)` — รายการ feature ตาม roadmap/status
- `product_create_prd(title, brief)` — สร้าง PRD draft (ลงไฟล์ `bus/product/` หรือ `docs/prds/drafts/`)
- `product_prioritize(items)` — จัด RICE/MoSCoW/Kano

---

## 2. ทำไมต้องใช้ agent

| เหตุผล | เงื่อนไขที่มนุษย์/script ทำแทนไม่ได้ |
|:--|:--|
| **อ่านหลายแหล่งต่อ 1 งาน** | ต้องอ่าน PRD เก่า + roadmap + feedback + business goal ก่อนสกัด PRD — script ไม่รู้ว่าจะเลือกอะไร |
| **ตัดสินใจ trade-off** | PRD เป็นเรื่อง trade-off (impact vs effort) ที่เปลี่ยนทุก sprint — template ตายตัวไม่ได้ |
| **ปรับตามบริบทองค์กร** | SoloCorp มี hierarchy + rule ข้ามแผนก — agent ต้องรู้ว่า feature กระทบแผนกไหน |
| **ต้อง "ลงมือ" ไม่ใช่ "ตอบ"** | ต้องเขียนไฟล์จริง + task record ใน Central Bus + report ค่าความแม่น spec (>90% dev ไม่ต้องถาม) |

**script ทดแทนไม่ได้เพราะ:** template PRD เป็นแค่แบบฟอร์มกลาง — การตัดสิน priority + เก็บ evidence + หา trade-off ต้องมี reasoning

---

## 3. agent ตัวไหน + เครื่องมือที่ต้องใช้

**ตัวแทน:** `product-produck` (`profiles/06-product/SOUL.md`) → MCP หัวหน้าตาม pattern `engineering_mcp.py` / `qa_mcp.py` (FastMCP `"product"`)

| เครื่องมือ | ใช้ทำอะไร | มีจริงไหม |
|:--|:--|:--|
| `product_department_info` | แจ้ง scope/head/specialists/data root | ❌ ยังไม่มี — ต้องสร้าง D2 |
| `product_list_features` | กฎ roadmap/status จาก config หรือ file | ❌ ยังไม่มี |
| `product_create_prd` | เขียน PRD draft (ไฟล์จริง) | ❌ ยังไม่มี |
| `product_prioritize` | จัดอันดับ RICE/MoSCoW | ❌ ยังไม่มี |
| `team`/specialists ภายใน | Alex PM / Product Feedback Synthesizer / Sprint Prioritizer (อ้าง LICENSE) | ⚠️ profiles มี แต่ยังไม่ expose ผ่าน MCP |

**ไม่ใช้ใน D1 รอบนี้:** `central_bus` เขียนโดยตรง (ต้องผ่าน tool), external LLM provider (Go จะมา 13:00 สำหรับ quota)

**บทบาท specialists (internal) ตาม ARCHITECTURE.md §06:** Alex PM, Product Feedback Synthesizer, Sprint Prioritizer — เป็นทีมของโปรดัค ไม่ใช่ cross-department

---

## 4. ขอบเขตสิทธิ/เครื่องมือ

**ได้ทำ:** อ่าน `profiles/06-product/**`, `docs/prds/**`, `bus/product/**` · เขียนไฟล์ **เฉพาะใต้ `docs/prds/drafts/` หรือ `bus/product/drafts/`** · เรียก Central Bus task API นาทีละไม่เกินตาม pattern content/engineering

**ห้ามทำ (hard stop):**
- ⛔ ห้ามแก้ `profiles/**`, `rules/**`, `sop/**`, `decisions/**` — ground truth องค์กร
- ⛔ ห้ามเขียนนอก `docs/prds/drafts/` หรือ `bus/product/drafts/`
- ⛔ ห้าม publish / เปิดเผยข้อมูล user โดยไม่ขออนุมัติ (PRD §10 Beta data policy: opt-in เท่านั้น)
- ⛔ ห้ามตัดสินใจทางธุรกิจแทน CEO/Owner (spec เป็น draft — ต้องรอ md — ยังไม่ implement)
- ⛔ ห้าม commit/push · ห้ามแตะ `.env`, API key, ค่าใช้จ่าย LLM
- ⛔ ห้าม expose specialist ภายในเป็นการเรียกตรง external client — ต้องผ่านหัวหน้า (Control ≠ Data layer)

> ⚠️ **ความจริงที่ต้องยอมรับ:** ข้อห้ามข้างบนยัง **ไม่ถูกบังคับในโค้ด Product วันนี้** เพราะยังไม่มีโค้ด  
> → **guard + allowlist = งาน D2** ต้องมีหลักฐานก่อนผ่าน  
> → จนกว่าจะมี guard: `product-produck` ถือว่า **ยังไม่ได้รับสิทธิ์เขียนไฟล์จริง** (D0 → ร่างได้เท่านั้น)

---

## 5. เส้นชัยของงานนี้ (D1 ผ่านเมื่อครบ 5 ข้อ)

| # | เกณฑ์ | วัดด้วย |
|:-:|:--|:--|
| 1 | โปรดัคมี MCP ตัวแยก? Decide standalone vs merge | D1 นี้ §6 วิเคราะห์ 3 ตัวเลือก เลือก 1 พร้อมเหตุผล |
| 2 | มี tools 4 ตัวขั้นต่ำตาม pattern engineering/qa | `product_department_info`, `product_list_features`, `product_create_prd`, `product_prioritize` ครบ 4 ตัวใน draft |
| 3 | Spec ก่อน build ผ่าน 90% บรรทัด | PRD template ครบ: Problem, Why Now, Success Metrics, Requirements P0/P1/P2, In/Out Scope |
| 4 | FR-07 standalone ผ่าน | department MCP test ได้โดยไม่ต้อง CEO/Core MCP — เอกสารระบุ acceptance path 3 ขั้น |
| 5 | Maker ≠ Checker | Owner เป็น checker (ตาม SOP-06) อ่าน D1 นี้ก่อนอนุมัติ D2 |

**Log artifact:** เอกสารนี้พอเป็น `bus/evidence/2026-11-09/product-mcp-d1/` (tarball snapshot)  
**คำสั่งวัด exit code:** Python checker `scripts/goal-loop-product-mcp.py` → exit 0 เมื่อครบ 5 ข้อ + ประสิทธิภาพ 90% guess

**ไม่ผ่านถ้า:** ไม่มีร่าง options · ไม่มี permission scope · ไม่มี 4 tools · ไม่มีเส้นชัย measurable

---

## 6. ทางเลือก 3 ทาง + เหตุผล

### A. Standalone `product_mcp.py` (แนะนำ)

**ทำ:** `solocorp_mcp/departments/product_mcp.py` แบบเดียว engineering/qa (FastMCP `"product"`, department_info + tools)

**ข้อดี:**
- FR-07 100%: standalone ได้ ไม่ต้อง CEO
- สอดคล้อง pattern เดิม Content/Engineering/QA — team คุ้นแล้ว
- หุ้นส่วน control/data แยกชัด (product = decision/spec, ไม่ใช่ engineering)

**ข้อเสีย:**
- +1 process (MCP server count: 8→9)
- ต้อง maintenance แยก (เหมือน engineering/qa อยู่แล้ว)

**Cost:** ~200 บรรทัด (pattern เดียว engineering 4.4k + qa 6.8k)

### B. รวมเข้า `unified-technical` เป็น module ที่ 4

**ทำ:** `solocorp_mcp/unified_technical/modules/product.py` ติดกับ Architect/Eng/QA ใน process เดียวกัน

**ข้อดี:**
- ไม่เพิ่ม process — count เท่าเดิม
- รวม technical + product เป็นสายเดียวกัน (ดูรวม)

**ข้อเสีย:**
- **ปน Control/Data layer** (unified คือ technical data layer แต่ product คือ control/strategy)
- ผิด Two-Tier: product ควร control ผ่าน Head-to-Head ไม่ใช่ technical tool
- FR-07 อ่อน: external client ต้อง connect unified ทั้งก้อนถึงใช้ product

### C. รอ — ยังไม่ทำ Product MCP (คงสถานะเดิม)

**ทำ:** ใช้ Core MCP `solocorp_get_department` + เขียน PRD manual เหมือนเดิม

**ข้อดี:**
- ไม่เสีย effort ตอนนี้ (MVP focus ที่ Content + Git)

**ข้อเสีย:**
- Product ไม่ standalone → ผิด FR-07
- PRD quality ไม่สม่ำเสมอ (ไม่มี centralized tool)
- เกือบตลอดเดือนเหมือน dream

---

## 7. คำแนะนำของ CEO (L4)

**เลือก A — Standalone `product_mcp.py`** 

เหตุผล:
1. ผ่าน FR-07 100% (standalone)
2. Pattern เดียวกับ engineering/qa/content — team รู้แล้ว
3. Control/Data layer แยกชัด: product = spec/control ไม่ใช่ technical data

**ถ้า owner อยากลดจำนวน MCP:** ค่อยยุบทีหลังเป็น Phase 2 (ไม่ใช่ตอนนี้) — เราเพิ่งยืนยันไม่ปิด engineering/qa standalone ตามก่อนหน้านั้น (2026-11-08)

**ลำดับ:**
1. D1 นี้ (วันนี้ 09:00-18:00)
2. Owner อนุมัติ D1 18:00 วันนี้
3. D2 implement `product_mcp.py` 50-150 บรรทัด + test
4. D3 eval ≥20 cases
5. D4 runbook

**ไฟล์อ้างอิง:** PRD §7 (MVP Must-Have #2, #5-9) + ARCHITECTURE §06 (โปรดัค + specialists) + engineering_mcp.py (pattern template)

---

**ผู้ตรวจ (≠ ผู้ทำ):** **Owner (Dr.solodev)** · **วันที่ส่ง:** 2026-11-09 18:00 รอ synthesis  
**สถานะ:** ☑ Draft ส่ง · ☐ ผ่าน (D1) · รอ Owner ตรวจก่อน D2