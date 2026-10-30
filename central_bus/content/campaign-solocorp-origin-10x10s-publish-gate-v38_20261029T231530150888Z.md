# Campaign Publish Gate

- **Campaign:** solocorp-origin-10x10s
- **Version reviewed:** v38
- **Decision:** review_required; human approval is still required.

## Checks
- PASS — dependencies: primary content: พบ draft/script
- PASS — dependencies: visual prompt: พบ visual prompt
- PASS — dependencies: audio cue sheet: audio cue อ้างถึงสคริปต์ล่าสุด
- PASS — claims: source references supplied: พบ 18 รายการ
- REVIEW — claims: source verification: ระบบยังไม่ได้ตรวจสอบแหล่งอ้างอิงโดยอิสระ; ต้องให้มนุษย์ยืนยัน
- REVIEW — media rights: ต้องยืนยันลิขสิทธิ์ภาพ/เพลง/เสียงก่อนเผยแพร่
- REVIEW — redaction: พบข้อมูลที่ต้อง redact หรือให้มนุษย์ตรวจ
- PASS — R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน: 1 รายการ: scripts/render_campaign_media_local.py
- PASS — R2 แสดงความล้มเหลวและต้นทุน/เหตุผล: มีรอยแผล
- PASS — R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration): ยังไม่ได้
- PASS — R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง: สะอาด
- PASS — R5 ปิดด้วยคำถามเปิด 1 ข้อ: มีคำถาม

## Client-supplied provenance
- `campaign-solocorp-origin-10x10s-client-generated-video_script-2e_20261029T230324782144Z.md; client=codex; provider=openai; model=gpt-6` (self-reported; not authenticated)
- `campaign-solocorp-origin-10x10s-client-generated-video_script-93_20261029T231301234823Z.md; client=codex; provider=openai; model=gpt-6` (self-reported; not authenticated)

## Redaction and R1–R5 detail
# 🚦 Publish Gate

## ตัวกรองข้อมูล
- 🔒 ถูกตัด `ID_CARD` ×20 (ตัวอย่าง: `7012604994099`)
- ⚠️ ต้องคนอนุมัติ `CUSTOMER` ×12 (ตัวอย่าง: `customer data`)

## เกณฑ์ publish (R1-R5)
- ❌ **L1 ไม่มีข้อมูล D2 (secret/พ.ร.บ.ความลับ) หลุด** — 1 รายการ
- ❌ **L2 ไม่มีรายการที่รอคนอนุมัติ** — CUSTOMER
- ✅ **L3 ไม่มีคำที่ห้ามพูด** — ไม่มี
- ✅ **R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน** — 1 รายการ: scripts/render_campaign_media_local.py
- ✅ **R2 แสดงความล้มเหลวและต้นทุน/เหตุผล** — มีรอยแผล
- ✅ **R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration)** — ยังไม่ได้
- ✅ **R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง** — สะอาด
- ✅ **R5 ปิดด้วยคำถามเปิด 1 ข้อ** — มีคำถาม

**ผล: ไม่ผ่าน — ต้องแก้ก่อน**