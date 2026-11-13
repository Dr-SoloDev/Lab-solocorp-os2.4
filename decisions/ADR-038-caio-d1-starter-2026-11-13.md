# ADR-038: CAIO Department D1 Starter — ตั้งแผนกกำกับสมอง/โมเดล (DRAFT)

**วันที่:** 2026-11-13
**สถานะ:** DRAFT-UNAPPROVED — Owner ยังไม่เซ็น L5 ห้ามบังคับใช้
**Branch:** `feat/caio-d1-starter` — additive-only
**อ้างอิง:** rules/01-receive (L5 org), rules/06-certification (D0→D1→D2), ADR-030 (open-core), ADR-036/037 (CTO/R&D precedent)

## ตัดสินใจ (DRAFT)

สร้างโครง D1 ของแผนก `20-caio` (พี่ญาณ + พริ้ง + ต้นกล้า) แบบ DRAFT 8 ไฟล์ ยังไม่มีผลบังคับใช้

## เหตุผล

- ไม่มีเจ้าภาพ routing/prompt/eval/token/license กลาง → token บวม + หลอนข้ามแผนก + license หลุด
- แยกเส้นชัด: Content=ของ / CAIO=ไม้บรรทัด / Architect=ชั้นวาง (ไม่ซ้ำ CTO/COO/R&D)

## ขอบเขต D1 (Existing + ใหม่)

- ไฟล์ใหม่: `profiles/20-caio/{HEAD,SOUL,routing.yaml,team/02-pring,team/03-tonkla}` + `skills/@axis/ai-governance/SKILL.md` (open-only) + `.opencode/agents/caio-yaan.md` + ADR นี้
- INDEX.md: append-only เพิ่ม section CAIO (ห้ามแก้แถวเดิม)
- ห้าม: registry update / execution จริง / push engine moat / สั่ง R&D / override QA(SAFE)/Security(BLOCKED)/budget(A6)/audit(A7/A8)
- D0 ทั้งแผนก — งานต่อไปคือ D1 ตรวจผ่าน → D2 `caio_governance_checker.py` 80-120 บรรทัด (`WRITE_ROOT=bus/governance/reports/`)

## Pre-sign checklist (ก่อน Owner เซ็น L5 — ลอก CTO L5)

- [ ] D1 ครบ 5 ข้อ + maker≠checker (CEO/Owner ตรวจ)
- [ ] Placement `20-caio` + reports CEO (+Owner เรื่อง L5) + R&D liaison (ไม่ใช่ยุบ)
- [ ] Bus read-only redacted + audit ไม่ผ่าน CAIO + dual-approval full-text
- [ ] ADR-030 boundary frozen + skill ผ่าน import/path/header scan (0 engine)
- [ ] CFO `no budget` D1/D2 + ceiling/fallback + ledger read-only
- [ ] Counts verify จริง (`ls -d profiles/*/` / `ls .opencode/agents/*.md` / `find skills/@axis -name SKILL.md`) + README/INDEX/ARCHITECTURE ตรงกัน commit เดียว
- [ ] DRAFT watermark ทุกไฟล์ +Writer + rollback (ลบโฟลเดอร์ย้อนได้) + no launch claim
