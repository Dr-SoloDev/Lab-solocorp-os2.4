# Campaign Publish Gate

- **Campaign:** campaign_mcp_pilot_llm_04
- **Version reviewed:** v4
- **Decision:** review_required; human approval is still required.

## Checks
- PASS — dependencies: primary content: พบ draft/script
- PASS — dependencies: visual prompt: พบ visual prompt
- PASS — dependencies: audio cue sheet: audio cue อ้างถึงสคริปต์ล่าสุด
- PASS — claims: source references supplied: พบ 4 รายการ
- REVIEW — claims: source verification: ระบบยังไม่ได้ตรวจสอบแหล่งอ้างอิงโดยอิสระ; ต้องให้มนุษย์ยืนยัน
- REVIEW — media rights: ต้องยืนยันลิขสิทธิ์ภาพ/เพลง/เสียงก่อนเผยแพร่
- PASS — redaction: ไม่พบรายการค้างตรวจ
- PASS — R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน: 3 รายการ: tests/test_content_mcp.py, tests/test_mcp_stdio.py, b5f2cf5
- PASS — R2 แสดงความล้มเหลวและต้นทุน/เหตุผล: มีรอยแผล
- PASS — R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration): ยังไม่รู้
- PASS — R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง: สะอาด
- PASS — R5 ปิดด้วยคำถามเปิด 1 ข้อ: มีคำถาม

## Client-supplied provenance
- `campaign-campaign_mcp_pilot_llm_04-client-generated-article-b675_20261030T073652687821Z.md; client=perch-desktop-saffron; provider=perch-roost; model=glm-5.3-flash-starter` (self-reported; not authenticated)

## Redaction and R1–R5 detail
# 🚦 Publish Gate

## ตัวกรองข้อมูล
- ✅ ไม่พบข้อมูลที่ต้องกรอง

## เกณฑ์ publish (R1-R5)
- ✅ **L1 ไม่มีข้อมูล D2 (secret/พ.ร.บ.ความลับ) หลุด** — สะอาด
- ✅ **L2 ไม่มีรายการที่รอคนอนุมัติ** — ไม่มี
- ✅ **L3 ไม่มีคำที่ห้ามพูด** — ไม่มี
- ✅ **R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน** — 3 รายการ: tests/test_content_mcp.py, tests/test_mcp_stdio.py, b5f2cf5
- ✅ **R2 แสดงความล้มเหลวและต้นทุน/เหตุผล** — มีรอยแผล
- ✅ **R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration)** — ยังไม่รู้
- ✅ **R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง** — สะอาด
- ✅ **R5 ปิดด้วยคำถามเปิด 1 ข้อ** — มีคำถาม

**ผล: ผ่าน — พร้อม publish**