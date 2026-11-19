# ADR-037: AXIS = C-Suite + AI-Native OS (Bus + Orchestrator + Psychology + Memory)

**วันที่:** 2026-11-13
**สถานะ:** Accepted — Owner รับรองหลักการ (session 2026-11-13, ต่อจากถอดเทป C-Suite 46 นาที)
**Maker:** CEO เทอโบ (Turbo) — strategy + doctrine
**Checker:** @legal-tulya (governance) + @architect-songsak (architecture) — ต้องตรวจก่อนอ้างเป็น launch claim
**เกี่ยวกับ:** ADR-001 (3 Pillars) · ADR-002 (Two-Tier) · ADR-003 (Bus Schema) · ADR-033 (AXIS Rebrand) · transcript `สร้างองค์กรเอไอด้วยโครงสร้างซีสวีท.m4a` interim 0:00-4:43

---

## บริบท

1. สัมมนา `สร้างองค์กรเอไอด้วยโครงสร้างซีสวีท` (46:21 นาที, interim transcript `/tmp/opencode/transcript-ซีสวีท-interim.md`) สรุปแก่น 5 นาทีแรก:
   - องค์กรสเกลเล็กทำทุกอย่างแบบ flat ได้ แต่สเกลร้อยคน / ร้อย agents ต้องมี C-Suite กัน chaos
   - C-Level ถอนตัวจากงานรายวันไม่ใช่ privilege แต่กัน `cognitive load` เต็ม (RAM/แท็บเบราว์เซอร์เต็ม)
   - LLM มีข้อจำกัดเดียวกันคือ `context window` — จึงต้องมีลำดับชั้น
   - JD ของ C-Suite เอาไป hire คนหรือ hire AI ได้เลย

2. SoloCorp OS / AXIS Framework สร้างมา 2 ปี มีครบ C-Suite อยู่แล้ว (20 departments, 58 specialists, `brain/ceo-memory.json`) + มีส่วนที่บริษัทมนุษย์ไม่มี: Central Bus, Orchestrator, Psychology, Organizational Memory

3. Owner รับรองหลักการใน session นี้: **AXIS = C-Suite + AI-Native OS** — ให้บันทึกเป็น ADR ใหม่

## การตัดสินใจ

**หลักการถาวร (L5 doctrine):**

> **AXIS คือ C-Suite ที่รันบน AI-Native OS — เอา accountability แบบ C-Suite มา + เติม Bus + Orchestrator + Psychology + Memory ที่บริษัทมนุษย์ไม่มี**

AI-Native OS ประกอบด้วย 4 ส่วน (ย้อนกลับได้ทีละส่วน, หลักการย้อนไม่ได้โดยไม่ผ่าน Owner):

1. **Bus (Central Bus :8099)** — nervous system: Data Layer (code/designs/reports) วิ่งผ่าน Bus, Control Layer (status/goal/handoff) คุย Head-to-Head; Specialists ห้ามคุยข้ามกรมตรง (ADR-002, ADR-003)
2. **Orchestrator (พี่วุฒิ)** — scheduler/handoff: 80% direct, 15% via Orchestrator, 5% escalate CEO; Loop Runner + queue + audit trail
3. **Psychology (จิต)** — behavioral layer: User Behavior + Behavioral Econ + Org Health; C-Suite มนุษย์ไม่มีกรมนี้
4. **Memory (brain/ + bus.db facts)** — organizational memory: `ceo-identity.md` + `ceo-memory.json` + `session-log.md` + `learnt.md` + Bus facts; แก้ปัญหา Head ลืม / session หลุด

## เหตุผล

- **Cognitive load = Context window:** เหตุผลเดียวกับ transcript — Head ต้องอยู่สูงเพื่อเหลือที่คิดภาพใหญ่; Bus + Memory ทำให้ Head อยู่สูงโดยไม่หลุด (เห็น dashboard + audit ไม่ใช่หอคอยงาช้าง)
- **Accountability at scale:** จาก startup 5 คน (flat) → 100 agents (hierarchical) — C-Suite คือตัวกัน orphan work; AXIS เพิ่ม owner ทุกงาน + audit ทุก handoff (Pillar 3: Ownership)
- **ไม่ประดิษฐ์ใหม่:** ใช้ JD ที่พิสูจน์มา 100 ปีเป็น blueprint สร้าง AI agent ประจำตำแหน่งได้ทันที — ลดเวลาออกแบบ org ใหม่
- **ต่างจาก C-Suite มนุษย์ตรงที่ตรวจสอบได้:** กฎ `ห้ามรายงานเสร็จโดยไม่มีหลักฐาน / connected ≠ current / maker≠checker` (rules/06) ทำให้ C-Suite AI ตรวจได้ทุกด่าน

## Mapping ทางการ (ผูกกับ org ปัจจุบัน)

| C-Level | AXIS Head | หมายเหตุ |
|:---|:---|:---|
| CEO | เทอโบ | Mirror CEO / Digital Twin + Final Say L4 |
| COO | กิจ | L1-L3 gatekeeper — แยก daily ops จาก strategy |
| CFO | meetoo | Finance/Budget |
| CMO | มาร์ค | Marketing/Brand |
| CTO/CIO | เวคเตอร์ (CTO primary) + พี่ทรงศักดิ์ Architect | Bus + Routing + MCP (ADR-036) |
| CPO | โปรดัค | Roadmap/PRD — D3 ผ่านแล้ว (ADR-033 C3) |
| VPEng | ช่างฟูล | Backend/Frontend — ใช้ผ่าน @cto primary 1 release |
| CDO | ครีเอท + UI Designer | Design system |
| CQO | QA-ทีม | กรมเต็ม — ใช้ผ่าน @cto primary 1 release |
| CRO | เซลส์ | B2B Deal/Pipeline |
| CCO (Customer) | ซัพพอร์ต | Customer Success |
| CCO (Content) | เสก | Content/Creative — D2 ผ่านตัวแรก |
| CLO | ตุลย์ | Compliance/Contracts + Governance checker |
| CISO | ซาย | Threat/IR |
| CIO Infra | นีต | Network/VPN/CDN/DNS + MCP Builder |
| Chief Web3 | อัยวา | Blockchain/DeFi/Solana |
| **AI-Native only: Orchestrator** | พี่วุฒิ | ไม่มีในบริษัทมนุษย์ — pipeline coordinator |
| **AI-Native only: Psychology** | จิต | Behavior/Econ/Org Health |
| **AI-Native only: Memory/Bus** | System (Bus + brain/) | Organizational memory |
| Chief Scientist | R&D Lab | Owner-direct |

## ผลกระทบ

- `profiles/` — เพิ่ม `profiles/C-SUITE-MAPPING.md` (ตารางบน) + อ้าง ADR นี้ใน SOUL ทุกกรม (ไม่เปลี่ยน head/identity — ตามหลัก `โค้ดขึ้นแกนกลาง อัตลักษณ์แยกสาขา` SOP-07)
- `rules/` — ไม่เปลี่ยน behavior (01-receive routing ยังเดิม); เพิ่มอ้างอิง ADR-037 ใน `01-receive.md §3` ตอน route ว่า Head คือ C-Level
- `opencode.json` — ไม่เปลี่ยน keys (CTO migration ADR-036 เดินต่อตามเดิม)
- `docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md` — ยังเป็น source of truth ของ product; ADR นี้เป็น org doctrine ไม่ทับ product scope
- Trademark — ยังติด C2 ของ ADR-033: ใช้ "AXIS" เป็น working brand เท่านั้น จนกว่า Legal formal review เสร็จ; ห้ามอ้าง ™/launch claim จาก ADR นี้

## สิ่งที่ ADR นี้ NOT ครอบ (ห้ามอ่านเกิน)

- ไม่เปลี่ยน headcount / rename Head / ปิดกรมใด
- ไม่เปลี่ยน code behavior / Bus schema / MCP contract
- ไม่ publish / ไม่ approve campaign ใด (transcript full 46 นาทียังถอดไม่เสร็จ — insight เต็มรอ `transcript-ซีสวีท-full.md`)
- ไม่แทน D-certification: Head ใดยัง D0 ก็ยัง D0 (maker≠checker, rules/06)

## งานต่อ

- [ ] @architect-songsak — สร้าง `profiles/C-SUITE-MAPPING.md` + ผูก SOUL อ้าง ADR-037 (Wave เดียวกับ CTO Phase1 Wave1 ได้, ห้ามแตะ `legal_vault/**`)
- [ ] @orchestrator-wut — ตรวจ Handoff template ว่าสะท้อน accountability แบบ C-Suite ครบ (owner/artifacts/deadline/receiver confirm)
- [ ] @legal-tulya — ตรวจ ADR นี้ + บันทึก C2 trademark note ว่ายังไม่ clearance (กันอ้างเกิน)
- [ ] @content-creator-sek — เมื่อถอดเทปเต็มเสร็จ ตัดเป็น JD รายตำแหน่ง (hire คนหรือ hire AI) อ้าง mapping นี้
- [ ] CEO — อัปเดต `brain/ceo-memory.json` sessions + `profiles/CERTIFICATION-REGISTRY.md` (ไม่ติ๊กผ่านด่านใดจาก ADR นี้)

## References

- Interim transcript: `/tmp/opencode/transcript-ซีสวีท-interim.md` (0:00-4:43, 82 segs, small Thai)
- Full audio: `/data/Videos/สร้างองค์กรเอไอด้วยโครงสร้างซีสวีท.m4a` (33MB, 2781s) — full transcription running (`/tmp/opencode/asr_work/segments.jsonl`)
- ADR-001/002/003/033/036 — pillars, two-tier, bus, rebrand concerns, CTO migration
- `rules/01-receive.md`, `rules/02-work.md`, `rules/06-certification.md`
- `brain/ceo-identity.md`, `brain/ceo-memory.json`
