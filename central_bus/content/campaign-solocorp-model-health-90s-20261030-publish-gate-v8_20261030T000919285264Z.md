# Campaign Publish Gate

- **Campaign:** solocorp-model-health-90s-20261030
- **Version reviewed:** v8
- **Decision:** review_required; human approval is still required.

## Checks
- PASS — dependencies: primary content: พบ draft/script
- PASS — dependencies: visual prompt: พบ visual prompt
- PASS — dependencies: audio cue sheet: audio cue อ้างถึงสคริปต์ล่าสุด
- PASS — claims: source references supplied: พบ 7 รายการ
- REVIEW — claims: source verification: ระบบยังไม่ได้ตรวจสอบแหล่งอ้างอิงโดยอิสระ; ต้องให้มนุษย์ยืนยัน
- REVIEW — media rights: ต้องยืนยันลิขสิทธิ์ภาพ/เพลง/เสียงก่อนเผยแพร่
- REVIEW — redaction: พบข้อมูลที่ต้อง redact หรือให้มนุษย์ตรวจ
- PASS — R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน: 7 รายการ: 20261030, 20261030, 20261030
- PASS — R2 แสดงความล้มเหลวและต้นทุน/เหตุผล: มีรอยแผล
- PASS — R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration): ยังไม่ได้
- PASS — R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง: สะอาด
- PASS — R5 ปิดด้วยคำถามเปิด 1 ข้อ: มีคำถาม

## Client-supplied provenance
- `campaign-solocorp-model-health-90s-20261030-client-generated-dra_20261030T000737274721Z.md; client=Codex; provider=OpenAI; model=GPT-6` (self-reported; not authenticated)
- `campaign-solocorp-model-health-90s-20261030-client-generated-dra_20261030T000807099470Z.md; client=Codex; provider=OpenAI; model=GPT-6` (self-reported; not authenticated)
- `campaign-solocorp-model-health-90s-20261030-client-generated-dra_20261030T000829240043Z.md; client=Codex; provider=OpenAI; model=GPT-6` (self-reported; not authenticated)
- `campaign-solocorp-model-health-90s-20261030-client-generated-vid_20261030T000854033230Z.md; client=Codex; provider=OpenAI; model=GPT-6` (self-reported; not authenticated)

## Redaction and R1–R5 detail
# 🚦 Publish Gate

## ตัวกรองข้อมูล
- 🔒 ถูกตัด `PHONE` ×2 (ตัวอย่าง: `0854033230`)
- 🔒 ถูกตัด `ID_CARD` ×2 (ตัวอย่าง: `61030-000002-01`)
- ⚠️ ต้องคนอนุมัติ `CUSTOMER` ×1 (ตัวอย่าง: `customer data`)

## เกณฑ์ publish (R1-R5)
- ❌ **L1 ไม่มีข้อมูล D2 (secret/พ.ร.บ.ความลับ) หลุด** — 2 รายการ
- ❌ **L2 ไม่มีรายการที่รอคนอนุมัติ** — CUSTOMER
- ✅ **L3 ไม่มีคำที่ห้ามพูด** — ไม่มี
- ✅ **R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน** — 7 รายการ: 20261030, 20261030, 20261030
- ✅ **R2 แสดงความล้มเหลวและต้นทุน/เหตุผล** — มีรอยแผล
- ✅ **R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration)** — ยังไม่ได้
- ✅ **R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง** — สะอาด
- ✅ **R5 ปิดด้วยคำถามเปิด 1 ข้อ** — มีคำถาม

**ผล: ไม่ผ่าน — ต้องแก้ก่อน**