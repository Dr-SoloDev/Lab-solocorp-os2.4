# Campaign Publish Gate

- **Campaign:** campaign_solocorp_content_creator_60s
- **Version reviewed:** v11
- **Decision:** review_required; human approval is still required.

## Checks
- PASS — dependencies: primary content: พบ draft/script
- PASS — dependencies: visual prompt: พบ visual prompt
- PASS — dependencies: audio cue sheet: audio cue อ้างถึงสคริปต์ล่าสุด
- PASS — claims: source references supplied: พบ 7 รายการ
- REVIEW — claims: source verification: ระบบยังไม่ได้ตรวจสอบแหล่งอ้างอิงโดยอิสระ; ต้องให้มนุษย์ยืนยัน
- REVIEW — media rights: ต้องยืนยันลิขสิทธิ์ภาพ/เพลง/เสียงก่อนเผยแพร่
- REVIEW — redaction: พบข้อมูลที่ต้อง redact หรือให้มนุษย์ตรวจ
- REVIEW — R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน: ไม่มี
- REVIEW — R2 แสดงความล้มเหลวและต้นทุน/เหตุผล: มีรอยแผล
- REVIEW — R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration): ไม่มี — เสี่ยงดูมั่นใจเกินจริง
- PASS — R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง: สะอาด
- PASS — R5 ปิดด้วยคำถามเปิด 1 ข้อ: มีคำถาม

## Client-supplied provenance
- `campaign-campaign_solocorp_content_creator_60s-client-generated_20261030T024039605486Z.md; client=Codex; provider=OpenAI; model=gpt-6-luna` (self-reported; not authenticated)
- `campaign-campaign_solocorp_content_creator_60s-client-generated_20261030T024058771488Z.md; client=Codex; provider=OpenAI; model=gpt-6-luna` (self-reported; not authenticated)
- `campaign-campaign_solocorp_content_creator_60s-client-generated_20261030T025646800100Z.md; client=Codex; provider=OpenAI; model=GPT-6` (self-reported; not authenticated)
- `campaign-campaign_solocorp_content_creator_60s-client-generated_20261030T025927584248Z.md; client=Codex; provider=OpenAI; model=GPT-6` (self-reported; not authenticated)
- `campaign-campaign_solocorp_content_creator_60s-client-generated_20261030T030049668125Z.md; client=Codex; provider=OpenAI; model=GPT-6` (self-reported; not authenticated)

## Redaction and R1–R5 detail
# 🚦 Publish Gate

## ตัวกรองข้อมูล
- ⚠️ ต้องคนอนุมัติ `CUSTOMER` ×4 (ตัวอย่าง: `client_generated`)

## เกณฑ์ publish (R1-R5)
- ✅ **L1 ไม่มีข้อมูล D2 (secret/พ.ร.บ.ความลับ) หลุด** — สะอาด
- ❌ **L2 ไม่มีรายการที่รอคนอนุมัติ** — CUSTOMER
- ✅ **L3 ไม่มีคำที่ห้ามพูด** — ไม่มี
- ❌ **R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน** — ไม่มี
- ❌ **R2 แสดงความล้มเหลวและต้นทุน/เหตุผล** — มีรอยแผล
- ❌ **R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration)** — ไม่มี — เสี่ยงดูมั่นใจเกินจริง
- ✅ **R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง** — สะอาด
- ✅ **R5 ปิดด้วยคำถามเปิด 1 ข้อ** — มีคำถาม

**ผล: ไม่ผ่าน — ต้องแก้ก่อน**