# Campaign Publish Gate

- **Campaign:** campaign_synth_codex_01
- **Version reviewed:** v1
- **Decision:** review_required; human approval is still required.

## Checks
- PASS — dependencies: primary content: พบ draft/script
- REVIEW — dependencies: visual prompt: ยังไม่มี visual prompt
- PASS — dependencies: audio cue sheet: audio cue อ้างถึงสคริปต์ล่าสุด
- PASS — claims: source references supplied: พบ 1 รายการ
- REVIEW — claims: source verification: ระบบยังไม่ได้ตรวจสอบแหล่งอ้างอิงโดยอิสระ; ต้องให้มนุษย์ยืนยัน
- REVIEW — media rights: ต้องยืนยันลิขสิทธิ์ภาพ/เพลง/เสียงก่อนเผยแพร่
- PASS — redaction: ไม่พบรายการค้างตรวจ
- REVIEW — R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน: ไม่มี
- REVIEW — R2 แสดงความล้มเหลวและต้นทุน/เหตุผล: ไม่มีรอยแผล
- REVIEW — R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration): ไม่มี — เสี่ยงดูมั่นใจเกินจริง
- PASS — R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง: สะอาด
- REVIEW — R5 ปิดด้วยคำถามเปิด 1 ข้อ: ไม่มีคำถาม

## Client-supplied provenance
- `campaign-campaign_synth_codex_01-client-generated-article-ee9197_20261029T180200284565Z.md; client=codex; provider=maxplus; model=gpt-6-luna` (self-reported; not authenticated)

## Redaction and R1–R5 detail
# 🚦 Publish Gate

## ตัวกรองข้อมูล
- ✅ ไม่พบข้อมูลที่ต้องกรอง

## เกณฑ์ publish (R1-R5)
- ✅ **L1 ไม่มีข้อมูล D2 (secret/พ.ร.บ.ความลับ) หลุด** — สะอาด
- ✅ **L2 ไม่มีรายการที่รอคนอนุมัติ** — ไม่มี
- ✅ **L3 ไม่มีคำที่ห้ามพูด** — ไม่มี
- ❌ **R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน** — ไม่มี
- ❌ **R2 แสดงความล้มเหลวและต้นทุน/เหตุผล** — ไม่มีรอยแผล
- ❌ **R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration)** — ไม่มี — เสี่ยงดูมั่นใจเกินจริง
- ✅ **R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง** — สะอาด
- ❌ **R5 ปิดด้วยคำถามเปิด 1 ข้อ** — ไม่มีคำถาม

**ผล: ไม่ผ่าน — ต้องแก้ก่อน**