# PRD: AXIS Default Executive v1.1

| Field | Value |
|:--|:--|
| Product | AXIS App — Default Executive bundle |
| Version | v1.1 (ใหม่ — ไม่แตะ PRD เก่า) |
| Status | **Owner-approved (L5 decision) — 2026-11-22** |
| Supplements (ไม่แทนที่) | `PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md` (ยังเป็น source of truth ของ local-first app + MVP scope) |
| Maker | Product — โปรดัค (Head of Product) |
| Checker | Architect + Legal (ยังไม่ตรวจ — รอ sign-off) |
| Date | 2026-11-22 |

> เอกสารนี้ล็อกคำตัดสิน Owner เรื่อง Default Executive ลง PRD เพียงอย่างเดียว ไม่เปลี่ยน MVP scope เดิม ไม่แตะ PRD เก่า

---

## 1. Decision Log (L5 — Owner อนุมัติ 2026-11-22)

> **L5 evidence:** Owner อนุมัติในแชท session 2026-11-22 — คำสั่ง Owner วันที่ 2026-11-22: "โอเคให้ล็อก Default Executive…" (Default = Axis ก้อนเดียว + CTO primary เต็มตัว) — Maker (Product) บันทึกคำตัดสินลง PRD นี้เท่านั้น ไม่ได้อนุมัติเอง
>
> L5 Approval — Dr.solodev (Owner), 22/11/2026 22:00 (Asia/Bangkok):
> "อนุมัติ L5: Default Executive" — Default Executive = Axis ก้อนเดียว (CEO→CTO→COO) + CTO primary
> Session: chat 2026-11-22 (Owner approval message 22:00)

| # | คำตัดสิน Owner | รายละเอียด |
|:-:|:--|:--|
| 1 | **Default Executive = Axis ก้อนเดียว** | `CEO → (CTO ∥ COO)` — CTO ∥ COO เป็น peer C-Level ใต้ CEO ผูกเป็น bundle ดีฟอลต์ก้อนเดียว เปิดแอปมามีชุดนี้เลย ไม่ต้องเลือก module — CTO own pipeline เทคนิค, COO own handoff gate บน Bus, catalog โดน CEO route แล้ว COO check (งาน non-tech ไม่ต้อง transit ผ่าน CTO — กัน bottleneck) |
| 2 | **หน้าโล่งแบบ Gemini** | First-run / home แสดงช่องบรีฟหลัก `Where should we start?` + `@ connectors` + ตัวเลือก `Auto` + `mic` — ไม่มีรายการแผนกยาวๆ บังหน้า |
| 3 | **ป้ายหน้าโชว์แค่ Axis** | หน้าแรกแสดงป้ายเดียวว่า `Axis` (Default Executive) ไม่ลิสต์รายชื่อแผนกย่อย |
| 4 | **Catalog เสียบเพิ่มตาม context** | แผนกอื่นอยู่นอกก้อน Default เป็น catalog module — ระบบเสียบเพิ่มเมื่อ context ของงานเรียกหา (user ขอชัด / CEO route ว่าต้องใช้) ไม่ใช่เปิดมาพร้อมกันหมด |

**ผลผูกพัน:** ตั้งแต่วันที่อนุมัตินี้ Default = Axis bundle ข้างต้น จนกว่า Owner จะเปลี่ยนด้วย L5 ใหม่

---

## 2. โฟลว์ Default Executive (CEO → (CTO ∥ COO))

```text
User brief (Where should we start? + @ + Auto + mic)
  └── CEO — บรีฟหลัก เจ้าของ brief + strategy + final call
        ├── CTO ═ peer C-Level ใต้ CEO — own pipeline เทคนิค (Architect / Engineering / QA ใน process เดียว)
        ├── COO ═ peer C-Level ใต้ CEO — own handoff gate บน Central Bus (audit trail, compliance, evidence)
        └── Catalog modules — CEO route ตาม context → COO check handoff (non-tech ไม่ transit ผ่าน CTO)
```

| ชั้น | หน้าที่ | หมายเหตุ |
|:--|:--|:--|
| **CEO** | รับบรีฟหลักจาก user, วาง strategy, route, final call | เจ้าของ brief เพียงจุดเดียว — user ไม่ต้องเลือกว่าจะคุยกับใคร |
| **CTO** | peer C-Level ใต้ CEO — own pipeline เทคนิค 3 แกน (Architect / Engineering / QA) | รายงาน CEO ตรง — งานเทคนิคผ่าน CTO, งาน non-tech ไม่ต้อง transit ผ่าน CTO (กัน bottleneck) |
| **COO** | peer C-Level ใต้ CEO — own handoff gate บน Central Bus (audit trail, compliance, evidence) | Gatekeeper L1–L3 — ทุก handoff (รวม catalog ที่ CEO route มา) ต้องผ่าน COO check ถึงไหลต่อ |
| **Catalog** | แผนกนอกก้อน (Content, Sales, Legal, Web3, ฯลฯ) เสียบเพิ่มเมื่อ context ต้องการ | CEO route ตาม context → COO check — ไม่วิ่งผ่าน CTO |

**หลักลดความซับซ้อน:** ลดจำนวน MCP Server ที่ต้องต่อพร้อมกันให้น้อยสุด — Default รันแค่ก้อน Executive (+ Bus/registry/host ที่เป็น runtime) ส่วน catalog ต่อเมื่อถูกเรียกใช้จริง

---

## 3. CTO Primary Sign-off (primary `@cto`, alias เดิม 1 release per ADR-039)

| รายการ | ค่า |
|:--|:--|
| คำตัดสิน | **CTO = primary เต็มตัวใต้ CEO** — routing สายเทคนิคชี้ primary `@cto`, alias เดิมอยู่ได้ 1 release per ADR-039 (ADR-036 ถูก supersede แล้ว — authority ปัจจุบัน = ADR-039, ADR-038 เป็นประวัติ) |
| อ้างอิง | ADR-036 (superseded — ประวัติการรวม Architect+Engineering+QA เป็น `axis_mcp/cto`, namespaces เดิม) · ADR-037 (AXIS = C-Suite + AI-Native OS) · ADR-038 (rollback — ประวัติ) · ADR-039 (re-apply 2026-11-19 — Owner ขอชื่อ `cto` กลับ, namespace `cto` อีกครั้ง; authority ปัจจุบัน) |
| ระดับการตัดสิน | **L5 — Owner เซ็นแล้ว (2026-11-22)** พร้อมกับ Default Executive นี้ — หลักฐานดู §1 L5 evidence |
| ผล | Routing สายเทคนิคชี้ `@cto` เป็น primary (alias เดิม `@architect-songsak` / `@changful` / `@qa` อยู่ได้ 1 release ตาม ADR-039) — งานเทคนิคใต้ CEO ผ่าน CTO ไม่วิ่งแยก 3 สายเหมือนเดิม |

---

## 4. ข้อยกเว้น Standalone (ไม่ขัดคำเดิม)

- **ก้อน Default เป็น bundle — ข้อยกเว้นได้:** CEO+CTO+COO ใน Default ผูกกันเป็นชุด เปิดแอปใช้พร้อมกัน ไม่ต้องพิสูจน์ standalone แยกก้อนภายใน bundle
- **Catalog แผนกอื่นยัง standalone เหมือนเดิม:** แผนกนอกก้อน Default (Content Creator และทุก department MCP) ยังต้องใช้ได้เดี่ยวๆ จาก compatible MCP client ภายนอก โดยไม่พึ่ง CEO MCP หรือ SoloCorp App — ตามหลัก `Department independence` ใน PRD MVP v1.0 §4 ข้อ 2 ไม่เปลี่ยนแปลง
- สองข้อนี้ไม่ขัดกัน: ข้อยกเว้น bundle ใช้กับก้อน Default เท่านั้น ไม่ลามไปยกเลิก standalone ของ catalog
- standalone keys `engineering` / `qa` ใน `opencode.json` อยู่ใต้เงื่อนไข Wave-3 ADR-036 — ถอดได้ก็ต่อเมื่อครบทั้ง 4 ข้อ (CTO เขียว 48 ชม. / ไม่มี caller 7 วัน / CEO-Owner sign-off / rollback พร้อม) ก่อนครบเงื่อนไขคง keys ไว้

---

## 5. Non-goals (v1.1 นี้ไม่ทำ)

1. ไม่เปลี่ยน MVP scope / architecture เป้าหมายใน PRD MVP v1.0
2. ไม่แตะ PRD เก่า — ไฟล์เก่า frozen
3. ไม่แตะ `legal_vault/**`, pricing/billing, hosted multi-user (ยังเป็น later phase)
4. ไม่อนุมัติ publish/monetization ใดๆ เพิ่ม — รอ Architect + Legal checker sign-off เอกสารนี้ก่อนอ้างเป็น launch claim

---

## 6. Acceptance (เอกสารนี้ถือว่าล็อกเมื่อ…)

- [x] Owner L5 อนุมัติ Default = Axis ก้อนเดียว (2026-11-22) — หลักฐาน §1 L5 evidence
- [x] Owner L5 เซ็น CTO primary เต็มตัว (2026-11-22) — หลักฐาน §1 L5 evidence
- [ ] Checker: Architect ตรวจ (flow + ADR-036..039 อ้างถูกต้อง + ไม่ขัด Two-Tier)
- [ ] Checker: Legal ตรวจ (bundle exception เขียนชัด ไม่ล้าง standalone เดิม)
- [ ] ไฟล์วางที่ `docs/prds/PRD-AXIS-DEFAULT-EXECUTIVE-v1.1.md` ไม่ทับไฟล์เก่า

---

*Source of truth ลำดับ: PRD MVP v1.0 (app + scope) → PRD v1.1 นี้ (Default Executive + CTO primary) → ADRs (036–039) เป็นหลักฐานทางเทคนิค*
