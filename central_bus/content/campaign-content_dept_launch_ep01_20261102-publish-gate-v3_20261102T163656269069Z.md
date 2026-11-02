# Campaign Publish Gate

- **Campaign:** content_dept_launch_ep01_20261102
- **Version reviewed:** v3
- **Decision:** review_required; human approval is still required.

## Checks
- PASS — dependencies: primary content: พบ draft/script
- PASS — dependencies: visual prompt: พบ visual prompt
- PASS — dependencies: audio cue sheet: audio cue อ้างถึงสคริปต์ล่าสุด
- PASS — claims: source references supplied: พบ 5 รายการ
- REVIEW — claims: source verification: ระบบยังไม่ได้ตรวจสอบแหล่งอ้างอิงโดยอิสระ; ต้องให้มนุษย์ยืนยัน
- REVIEW — media rights: ต้องยืนยันลิขสิทธิ์ภาพ/เพลง/เสียงก่อนเผยแพร่
- REVIEW — redaction: พบข้อมูลที่ต้อง redact หรือให้มนุษย์ตรวจ
- REVIEW — R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน: ไม่มี
- PASS — R2 แสดงความล้มเหลวและต้นทุน/เหตุผล: มีรอยแผล
- PASS — R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration): ยังไม่รู้
- REVIEW — R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง: พบคำต้องห้าม
- PASS — R5 ปิดด้วยคำถามเปิด 1 ข้อ: มีคำถาม

## Client-supplied provenance
- `campaign-content_dept_launch_ep01_20261102-client-generated-vide_20261102T163655480558Z.md; client=Codex external Responses API client; provider=OpenAI; model=GPT-6` (self-reported; not authenticated)

## Redaction and R1–R5 detail
# 🚦 Publish Gate

## ตัวกรองข้อมูล
- ⚠️ ต้องคนอนุมัติ `VENDOR` ×1 (ตัวอย่าง: `เทียบกับโปรไฟล์แผนก`)

## เกณฑ์ publish (R1-R5)
- ✅ **L1 ไม่มีข้อมูล D2 (secret/พ.ร.บ.ความลับ) หลุด** — สะอาด
- ❌ **L2 ไม่มีรายการที่รอคนอนุมัติ** — VENDOR
- ✅ **L3 ไม่มีคำที่ห้ามพูด** — ไม่มี
- ❌ **R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน** — ไม่มี
- ✅ **R2 แสดงความล้มเหลวและต้นทุน/เหตุผล** — มีรอยแผล
- ✅ **R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration)** — ยังไม่รู้
- ❌ **R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง** — พบคำต้องห้าม
- ✅ **R5 ปิดด้วยคำถามเปิด 1 ข้อ** — มีคำถาม

**ผล: ไม่ผ่าน — ต้องแก้ก่อน**