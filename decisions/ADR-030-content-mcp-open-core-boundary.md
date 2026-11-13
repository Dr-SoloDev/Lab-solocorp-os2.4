# ADR-030: Licensing + Open-Core Boundary ของ Content Creator MCP — ส่วนไหนเปิด ส่วนไหนปิด

**วันที่:** 2026-11-02
**สถานะ:** Accepted ✅ — Owner (L5) ตัดสินในการปรึกษาเชิงกลยุทธ์ 2 พ.ย. 69
**Owner:** Dr.solodev (L5 — ตัดสิน licensing) · Alex (PM — บันทึก)
**ที่มา:** Owner เสนอแยก Content Creator MCP ออกจาก repo หลักเป็นโปรดักต์อิสระ + โมเดลทำเงินเลี้ยงระบบ (2 พ.ย. 69) — คำถาม licensing "MIT ที่เคยแจกไปจะปิดได้ไหม" ถูกตรวจสอบแล้ว
**เกี่ยวกับ:** PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0 §7 Post-MVP Commercial Direction · Phase 3 / FR-07 (standalone) · ADR-029 (rank อำนาจ) · เอกสารกลยุทธ์ [`docs/plans/CONTENT-MCP-STRATEGY-v1.0.md`](../docs/plans/CONTENT-MCP-STRATEGY-v1.0.md)

---

## บริบท

Owner ต้องการให้ Content Creator MCP เป็น **ผลิตภัณฑ์ที่แยกขาด** — พัฒนาเป็นโมเดลธุรกิจได้ โดย:
ไม่ (จำเป็นต้อง) เปิด source ทั้งหมด, ต่อเข้ากับ SoloCorp OS ได้ตามเดิมผ่าน MCP, ปล่อยฟรีช่วงแรก, อาจเก็บ subscription ในอนาคต
— เพราะไม่มีโมเดลทำเงิน = ไม่มีกำลังพัฒนาระบบต่อ

PRD v1.0 §7 อนุมัติทิศทางนี้ไว้แล้ว (*"premium flagship department MCPs"*, *"decide which modules are open-source individually"*) — ADR นี้จึงเป็นการ **เร่ง sequencing ไม่ใช่ pivot**

---

## ข้อเท็จจริงที่ตรวจสอบแล้ว (2026-11-02)

| # | ข้อเท็จจริง | วิธีตรวจสอบ | ผล |
|:-:|:--|:--|:--|
| 1 | โค้ด `solocorp_mcp/departments/` เขียนโดยคนเดียว | `git log --format='%an' -- solocorp_mcp/departments/` | **Dr.SoloDev คนเดียว** — ไม่มี external contributor ถือ copyright |
| 2 | โค้ด MCP ใหม่มีอายุใน git ตั้งแต่ | `git log --diff-filter=A` | **2026-10-26** (pilot) → สถาปัตยกรรมปัจจุบัน 2026-11-02 — ช่วงสั้นมาก |
| 3 | Repo ปัจจุบัน | ตามที่ Owner ยืนยัน | **private** — โค้ดสถาปัตยกรรมใหม่ไม่เคยถูก MIT ครอบ (เว้นข้อ 4) |
| 4 | ✅ **ปิดแล้ว (2026-11-13):** Owner ยืนยัน repo public + pushed (origin Dr-SoloDev/Lab-solocorp-os2.4, มี main + feat/cto-phase1-wave1@1c410e1 บน public) → **YES** — snapshot ช่วง departments/ public อยู่ใต้ MIT ถาวร แต่เป็นโค้ด immature (pilot 2026-10-26 → arch 2026-11-02) ไม่กระทบแผน open-core |
| 5 | Fork เก่าที่กระจัดกระจายอยู่ | โครง repo ก่อนยกเครื่อง | ถือเฉพาะ **เวอร์ชันก่อนสถาปัตยกรรม MCP** — ไม่มี code path เดียวกับตัว product ปัจจุบัน |

**สรุปกฎหมาย:** เจ้าของลิขสิทธิ์ (คนเดียว) relicensing งานตัวเองได้เสมอ MIT ที่เคยแจกไปมีผลแค่ snapshot ที่ผู้รับได้รับ ใช้ของเก่าต่อได้ แต่เอาไปอัพเดทเป็นเวอร์ชันใหม่ของ Owner ไม่ได้ — **ไม่มีภาระผูกพันขวางการแยก repo แบบ closed**

---

## การตัดสินใจ

### 1. เส้นแบ่ง Open-Core

| ส่วน | License | เหตุผลเชิงธุรกิจ |
|:--|:--|:--|
| **MCP adapter / protocol contract / tool interface** (ตัวต่อ, การ declare capability) | **เปิด — MIT** | คือ funnel — ใครก็ลองต่อได้ ยิ่งคนใช้มากยิ่งเห็นเรา ไม่มีใครจ่ายเงินซื้อ protocol shell เพราะลอกเลียนง่าย |
| **Content engine** — workflows, prompts, templates, media pipeline, premium capability | **ปิด — proprietary** | คือ moat จริง — คุณภาพ output ที่ tune มา นี่คือสิ่งที่คนจะจ่ายในอนาคต |
| **SoloCorp OS repo หลัก** (Central Bus, profiles, rules, แผนกอื่น) | **คง MIT เดิม** ตามที่ประกาศไว้ | แผนกอื่นยังฟรี + open source — ไม่เปลี่ยน (Owner ยืนยัน) |

### 2. กติกาตอนแยก repo (ทำพร้อมกันใน initial commit)

1. **License ใหม่ตั้งแต่ commit แรก** ของ repo ใหม่ — ห้ามมี MIT header หลุดตามมา
2. ล้าง `LICENSE` / README badge / package metadata ที่อ้าง MIT ใน commit เดียวกัน (hygiene ไม่ใช่งานทีหลัง)
3. **เอกสาร interop contract เปิดแยกต่างหาก** — วิธีต่อ MCP client เข้ากับโมดูลต้องอ่านได้โดยไม่ต้องเข้าถึงโค้ดปิด (PRD: standalone ต้อง connect ได้, *value* ต่างหากที่เป็น closed)
4. **ขีดเส้นในเอกสารก่อน split** — รายการไฟล์/โฟลเดอร์ไหนเขื้อ open ไหน closed ต้องนิ่งก่อน initial commit ไม่ใช่ตัดสินใจตอน move ไฟล์

### 3. ลำดับเวลา — ผูกกับ PRD Phase 3 ห้ามทำเป็นงานขนาน

```
Phase 1–2  สร้าง SoloCorp App shell + vertical slice (ตาม PRD เดิม — ยัง NOT STARTED)
Phase 3    แยก repo Content MCP  ← จุดนี้แหละ พิสูจน์ standalone (FR-07) ไปในตัว
Phase 4    Closed Beta + community evidence
Post-Beta  ตัดสินใจ pricing ด้วยหลักฐาน (ห้ามก่อนหน้านั้น)
```

### 4. ความสัมพันธ์กับ strategy doc

การปล่อย free-first, quality floor, และ 90-day review อยู่ใน [`CONTENT-MCP-STRATEGY-v1.0.md`](../docs/plans/CONTENT-MCP-STRATEGY-v1.0.md) — ADR นี้ครอบเฉพาะ **บรรทัดกฎหมาย/ขอบเขตเปิด-ปิด** สองฉบับห้ามเขียนเกินกัน (ตาม rank ของ ADR-029)

---

## เหตุผล

1. **Protocol shell ขายไม่ได้ คุณภาพ output ขายได้** — MCP server ตัว Adapter ลอกได้ในไม่กี่ชั่วโมง แต่ content engine ที่ผ่านการทดสอบแล้วลอกไม่ได้ ปิดผิดจุด = เปิด moat ทิ้ง
2. **เปิด adapter = การตลาดฟรี** — ทุกคนที่ต่อ MCP เข้าคือ lead ของคุณ สอดคล้อง distribution strategy ของ free-first
3. **ไม่มีภาระผูกพันจาก MIT** — copyright คนเดียว (ข้อเท็จจริง 1) + โค้ดใหม่ไม่เคย public (ข้อ 3) + fork เก่าถือของเก่าที่ไม่มีมูลค่า (ข้อ 5) — ตรวจสอบแล้วทั้งหมด
4. **ผูกกับ Phase 3 เพื่อกัน focus ตายสองทาง** — app ยังไม่เริ่ม ถ้าแยก repo เป็นงานขนาน = แบ่งกำลัง ผูกกับ gate ที่มีอยู่แล้วได้งานเดียวสองผล

---

## ผลกระทบที่ต้องรู้

1. **ถ้าข้อ 4 (เคย push ตอน public) เป็นจริง** — snapshot ช่วงนั้น MIT ถาวร แต่เป็นโค้ดยังไม่เป็นชิ้นเป็นอัน → ไม่กระทบแผน แค่บันทึกไว้ใน ADR นี้
2. **คนที่ fork ของเก่าอยู่จะไม่ได้ฟีเจอร์ใหม่** — ต้องสื่อสารใน release notes ของ repo ใหม่ว่า license เปลี่ยน เวอร์ชันเก่าคงเดิม (MIT)
3. **CI/docs ต้องแยกตาม** — repo ใหม่ต้องมี CI, README, license ของตัวเอง ตั้งแต่วันแรก ห้าม depend on repo หลักแอบแฝง
4. **แผนกอื่นไม่กระทบ** — คง MIT ใน repo หลักตามเดิม ไม่มีการถอยหลัง open source ของแผนกอื่น

---

## งานที่ต้องทำต่อ

- [x] Owner ยืนยันข้อ 4: เคย push `solocorp_mcp/departments/` ตอน repo public ไหม (ตอบครั้งเดียวจบ แล้ว update ตารางข้อเท็จจริงใน ADR นี้) (Owner ยืนยัน 2026-11-13: YES public+pushed)
- [ ] รายการไฟล์ open/closed (boundary list) — เขียนนิ่งก่อน split
- [ ] ทำ repo split **ที่ PRD Phase 3** — license ใหม่ตั้งแต่ commit แรก + ล้าง MIT reference พร้อมกัน
- [ ] ตรวจ CI + README ของ repo ใหม่ไม่ depend repo หลัก
- [ ] แจ้งใน release notes ของ repo ใหม่: เวอร์ชันเก่า = MIT เหมือนเดิม, เวอร์ชันใหม่ = proprietary

---

## References

- [`docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md`](../docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md) — §4 Principles (open-core direction) · §7 Post-MVP Commercial · Phase 3 · FR-07
- [`docs/plans/CONTENT-MCP-STRATEGY-v1.0.md`](../docs/plans/CONTENT-MCP-STRATEGY-v1.0.md) — free-first, quality floor, 90-day review
- `LICENSE` (repo ปัจจุบัน — MIT) · `AGENTS.md` → Current Product Direction (bullet 2026-11-02)
- ADR-029 (rank อำนาจระหว่างเอกสาร) · ADR-024 (identity pivot — บริบททีม)
