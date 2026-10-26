# Campaign Publish Gate

- **Campaign:** campaign_proof_ch1_power_of_one
- **Version reviewed:** v6
- **Decision:** review_required; human approval is still required.

## Checks
- PASS — dependencies: primary content: พบ draft/script
- PASS — dependencies: visual prompt: พบ visual prompt
- PASS — dependencies: audio cue sheet: audio cue อ้างถึงสคริปต์ล่าสุด
- PASS — claims: source references supplied: พบ 9 รายการ
- REVIEW — claims: source verification: ระบบยังไม่ได้ตรวจสอบแหล่งอ้างอิงโดยอิสระ; ต้องให้มนุษย์ยืนยัน
- REVIEW — media rights: ต้องยืนยันลิขสิทธิ์ภาพ/เพลง/เสียงก่อนเผยแพร่
- REVIEW — redaction: พบข้อมูลที่ต้อง redact หรือให้มนุษย์ตรวจ
- REVIEW — R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน: ไม่มี
- REVIEW — R2 แสดงความล้มเหลวและต้นทุน/เหตุผล: มีรอยแผล
- PASS — R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration): ยังไม่ได้
- PASS — R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง: สะอาด
- PASS — R5 ปิดด้วยคำถามเปิด 1 ข้อ: มีคำถาม

## Redaction and R1–R5 detail
# 🚦 Publish Gate

## ตัวกรองข้อมูล
- 🔒 ถูกตัด `PHONE` ×1 (ตัวอย่าง: `0868188329`)
- ⚠️ ต้องคนอนุมัติ `CUSTOMER` ×12 (ตัวอย่าง: `ลูกค้า ความเร็ว และคุณภาพเมื่อเทียบทางเล`)
- ⚠️ ต้องคนอนุมัติ `MONEY` ×1 (ตัวอย่าง: `cost.

Chapter 1`)
- 🚫 คำที่ห้ามพูด: `production-ready` (เปรียบเทียบโดยไม่มี benchmark)

## เกณฑ์ publish (R1-R5)
- ❌ **L1 ไม่มีข้อมูล D2 (secret/พ.ร.บ.ความลับ) หลุด** — 1 รายการ
- ❌ **L2 ไม่มีรายการที่รอคนอนุมัติ** — CUSTOMER, MONEY
- ❌ **L3 ไม่มีคำที่ห้ามพูด** — production-ready
- ❌ **R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน** — ไม่มี
- ❌ **R2 แสดงความล้มเหลวและต้นทุน/เหตุผล** — มีรอยแผล
- ✅ **R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration)** — ยังไม่ได้
- ✅ **R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง** — สะอาด
- ✅ **R5 ปิดด้วยคำถามเปิด 1 ข้อ** — มีคำถาม

**ผล: ไม่ผ่าน — ต้องแก้ก่อน**