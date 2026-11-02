# Campaign Publish Gate

- **Campaign:** content_dept_launch_ep01_20261102
- **Version reviewed:** v26
- **Decision:** review_required; human approval is still required.

## Checks
- PASS — dependencies: primary content: พบ draft/script
- PASS — dependencies: visual prompt: พบ visual prompt
- PASS — dependencies: audio cue sheet: audio cue อ้างถึงสคริปต์ล่าสุด
- PASS — claims: source references supplied: พบ 7 รายการ
- REVIEW — claims: source verification: ระบบยังไม่ได้ตรวจสอบแหล่งอ้างอิงโดยอิสระ; ต้องให้มนุษย์ยืนยัน
- REVIEW — media rights: ต้องยืนยันลิขสิทธิ์ภาพ/เพลง/เสียงก่อนเผยแพร่
- REVIEW — redaction: พบข้อมูลที่ต้อง redact หรือให้มนุษย์ตรวจ
- PASS — media: latest Concat render is complete and current: render, script, cue sheet, and sound delivery match
- REVIEW — media: Earshot review matches latest render: review the latest Concat output with sound_review_campaign_audio
- PASS — R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน: 1 รายการ: git 19b5e59
- PASS — R2 แสดงความล้มเหลวและต้นทุน/เหตุผล: มีรอยแผล
- PASS — R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration): ยังไม่รู้
- PASS — R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง: สะอาด
- PASS — R5 ปิดด้วยคำถามเปิด 1 ข้อ: มีคำถาม

## Client-supplied provenance
- `campaign-content_dept_launch_ep01_20261102-client-generated-vide_20261102T165030525056Z.md; client=Codex external Responses API client; provider=OpenAI; model=GPT-6` (self-reported; not authenticated)

## Redaction and R1–R5 detail
# 🚦 Publish Gate

## ตัวกรองข้อมูล
- 🔒 ถูกตัด `PHONE` ×10 (ตัวอย่าง: `66666666666`)
- 🔒 ถูกตัด `ID_CARD` ×10 (ตัวอย่าง: `7012604994099`)
- 🔒 ถูกตัด `PATH` ×8 (ตัวอย่าง: `/home/drsolodev/.opencode/concat/config/`)
- ⚠️ ต้องคนอนุมัติ `CUSTOMER` ×7 (ตัวอย่าง: `client_generated`)

## เกณฑ์ publish (R1-R5)
- ❌ **L1 ไม่มีข้อมูล D2 (secret/พ.ร.บ.ความลับ) หลุด** — 3 รายการ
- ❌ **L2 ไม่มีรายการที่รอคนอนุมัติ** — CUSTOMER
- ✅ **L3 ไม่มีคำที่ห้ามพูด** — ไม่มี
- ✅ **R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน** — 1 รายการ: git 19b5e59
- ✅ **R2 แสดงความล้มเหลวและต้นทุน/เหตุผล** — มีรอยแผล
- ✅ **R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration)** — ยังไม่รู้
- ✅ **R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง** — สะอาด
- ✅ **R5 ปิดด้วยคำถามเปิด 1 ข้อ** — มีคำถาม

**ผล: ไม่ผ่าน — ต้องแก้ก่อน**