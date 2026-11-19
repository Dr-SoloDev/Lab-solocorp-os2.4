# D1 — CTO Triage Checker (cto-triage-checker, propose-only)

> สถานะจริง: โค้ดยังไม่มี — เอกสารนี้คือแผน ไม่ใช่หลักฐาน implementation
> (กัน overclaim แบบ incident 05 ส.ค. 69 — รายงาน "เสร็จ" ไม่มีหลักฐาน = failure ร้ายแรงสุด)
> ระดับ: D1 (ห้ามเขียนโค้ด) · maker: CEO · checker: Owner (ต้องไม่ใช่ maker)
> 2026-11-13 (Owner): ข้ามลายเซ็น L5 ทั้งหมดไปก่อน — D1/D2 เดินด้วย checker อนุมัติเท่านั้น ไม่รอ L5 ไม่รอ charter เซ็น

## 1. งานคืออะไร

รับ topic ภาษาธรรมชาติ 1 เรื่อง → เปิด `profiles/cto/ROUTING_MATRIX.md` เทียบกฎ A1–A12 → ตอบ 3 อย่างที่วัดได้:
`routed_to` (Architect / Engineering / QA / triage-reject) + `reason` (อ้างมาตรา A_) + handoff draft 1 ไฟล์ —
**ไม่ implement ไม่ approve ไม่ enforce ไม่เขียนโค้ด ไม่แก้ config ไม่ deploy**

## 2. ทำไมต้อง agent (script แทนไม่ได้)

- ต้องอ่าน 2 แหล่งต่อ 1 งาน (topic + matrix 12 ข้อมีเงื่อนไขซ้อน) + ตัดสิน owner-per-domain ภาษาธรรมชาติ — regex/script ตายตัวทำไม่ได้
- ต้อง "ลงมือ": เขียน draft report จริง + ตรวจไฟล์จริง (เทียบ matrix ตรงๆ) — ไม่ใช่แค่ตอบข้อความ
- โดเมนlint นี้ไม่มีใครทำ: QA อัดผลเทส, Product เขียน PRD, Legal เขียน review — ของ CTO คือตรวจเส้นทางก่อนงานวิ่ง

## 3. ตัวไหน + เครื่องมืออะไร

- `scripts/d2_cto_triage_probe.py` (D2, 80–120 บรรทัด ≤150): เรียก `cto_route(topic)` (read-only, มีจริงใน `axis_mcp/departments/cto_mcp.py`) 20 topics (bus/build/qa/triage + นอก scope Product/R&D ต้องตก triage/reject) → เทียบตาราง owner ใน ROUTING_MATRIX §1 → เขียน `result.json` + `tool-calls.jsonl`
- เครื่องมือ: `read_file` (อ่าน matrix + target), `write_file` (เขียน report), `run_command` อ่านอย่างเดียว (`test -f`, `grep -c`, `sha256sum`) — **ไม่ใช้** web/render/publish/LLM write ใดๆ
- รันจริง: `python3 scripts/d2_cto_triage_probe.py --topics 20` ต้อง exit 0 (ไม่ใช่พิมพ์ตอบ)

## 4. ขอบเขตสิทธิ (hard stop — ตัวไหนแหก = FAIL ทันที)

- อ่าน: `profiles/cto/**`, `ROUTING_MATRIX.md`, Bus read-only
- เขียน: **เฉพาะ** `bus/dispatch/CTO-*/` (draft) + `bus/evidence/<date>/d2-cto/` (หลักฐาน) — นอกนั้นห้ามแตะ
- ห้าม 12 ข้อ (ลอก A1–A12): ห้ามเขียนโค้ด/แก้ config/deploy เอง · ห้าม override QA FAIL (A2) / Security BLOCKED (A3) · ห้ามเป็น final approver (A5) · ห้ามเริ่มงานไม่มี Allocation Code (A6) · ห้ามแตะ audit trail (A7) · ห้ามข้าม Auditor (A8) · ห้ามยุ่ง Product/R&D · ห้ามแตะ `legal_vault/**` แบบ write · ห้ามอัปเดต registry เอง · ห้าม commit/push
- หมายเหตุซื่อสัตย์: guard ข้างบนยังไม่บังคับในโค้ด (policy ยัง DRAFT) = D2 ต้องบังคับเองด้วย allowlist path + fail-closed

## 5. เส้นชัย (6 ข้อ — ผู้ตรวจรันสคริปต์ตรวจ ไม่ใช่ฟังรายงาน)

1. อ่าน matrix + target จริง (log มี `read_file` ครบ)
2. รัน 20 topics ถูก owner 100% (เทียบ §1) + DENY ทุกเคส = STOP ไม่ override
3. เขียน report จริงใต้ `bus/dispatch/CTO-*/` + `bus/evidence/<date>/d2-cto/`
4. มี verdict pass/fail รายข้อ + อ้างมาตรา A_ ทุกข้อ
5. ไม่มีไฟล์ใหม่นอก 2 dirs (snapshot `find` ก่อน/หลัง)
6. exit 0 + `tool-calls.jsonl` ครบ 1 บรรทัด/1 call

---
*D1 by CEO — รอ Owner (checker) อนุมัติก่อนลงมือ D2 (bars: rules/06-certification.md §2)*
