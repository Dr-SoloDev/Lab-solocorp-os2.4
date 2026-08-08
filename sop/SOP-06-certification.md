# SOP-06: Certification — ตรวจรับชิ้นงาน agent ผ่านบันได 4 ด่าน

**Owner:** CEO เทอโบ
**Version:** v1.0 (05 ส.ค. 2569 — หลัง incident @changful)
**Applies to:** ทุก agent, CEO, ผู้ตรวจ (Reality Checker / pipeline-auditor / test runner)

## หลักการ

- ผู้ผลิต ≠ ผู้ตรวจ ทุกด่าน (rules/06-certification.md §3)
- สถานะ default = **ยังไม่ผ่าน** — จนกว่าหลักฐานจะถูก attach
- หลักฐานทั้งหมดเก็บที่ `bus/evidence/` (หรือ commit ใน repo)

## Step-by-Step

### 1. ผู้ทำส่งชิ้นงาน
- ส่งชิ้นงานของด่าน + หลักฐานขั้นต่ำ (ตารางด้านล่าง)
- **ห้ามติกช่อง "เสร็จ" เอง** — ส่งแค่ชิ้นงาน + หลักฐาน

### 2. ผู้ตรวจตรวจหลักฐาน (≠ผู้ทำ)
| ด่าน | ผู้ตรวจ | ตรวจอะไร |
|:---:|:-------|:---------|
| D1 | CEO / Owner | ครบ 5 ข้อตามเทมเพลต D1, ขอบเขตสิทธิสมเหตุสมผล |
| D2 | test runner / script | รันซ้ำได้ไหม, ใช้เครื่องมือจริงไหม (ไม่ใช่พิมพ์ตอบ), ≤150 บรรทัด |
| D3 | Reality Checker / pipeline-auditor | ตัวเลขจริงทุกแถว, failure มี root cause, ไม่ cherry-pick, ≥20 งาน |
| D4 | คน / agent คนละตัว | ตาม runbook แล้วได้ผลเหมือนเดิมจริงไหม |

### 3. ผ่าน → อัปเดตสถานะ
- อัปเดต `profiles/CERTIFICATION-REGISTRY.md` (ผู้ตรวจ/CEO เท่านั้น)
- แนบหลักฐาน: commit hash / path ไฟล์ / output test

### 4. ไม่ผ่าน → ส่งคืนพร้อมเหตุผล
- ต้องระบุเหตุผลเฉพาะเจาะจง (ขาดหลักฐานอะไร / เกณฑ์ข้อไหนไม่ผ่าน)
- **ห้าม "ไม่ผ่าน" แบบลอยๆ**

### 5. บันทึก
- หลักฐาน → `bus/evidence/`
- สรุปใน `brain/session-log.md`

## หลักฐานขั้นต่ำต่อด่าน

| ด่าน | หลักฐานขั้นต่ำ |
|:---:|:---------------|
| D1 | ไฟล์หน้าเดียวตาม `sop/TEMPLATE-D1-agent-rationale.md` |
| D2 | output การรันจริง (คำสั่ง + exit code + ผลลัพธ์) — อยู่ใน repo หรือ evidence |
| D3 | ตาราง ≥20 แถวตาม `sop/TEMPLATE-D3-evaluation-table.md` + ลิงก์หลักฐาน |
| D4 | runbook + ผลรันโดยคน/agent คนละตัว |

## Checklist

- [ ] ผู้ตรวจ ≠ ผู้ทำ?
- [ ] หลักฐานครบตามด่าน?
- [ ] ตัวเลขจริง ไม่ใช่คำอธิบายลอยๆ?
- [ ] Registry อัปเดตแล้ว (เฉพาะตอนผ่าน)?
- [ ] เหตุผลส่งคืนเฉพาะเจาะจง (ถ้าไม่ผ่าน)?

## References

- `rules/06-certification.md` — เกณฑ์ + กฎเหล็ก + ตัวอย่าง D3
- `sop/TEMPLATE-D1-agent-rationale.md` — โน้ตหน้าเดียว
- `sop/TEMPLATE-D3-evaluation-table.md` — ตาราง ≥20 งาน
- `profiles/CERTIFICATION-REGISTRY.md` — สถานะทุก agent
