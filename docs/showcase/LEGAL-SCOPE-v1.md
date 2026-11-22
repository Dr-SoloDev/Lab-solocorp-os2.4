# ⚖️ LEGAL-SCOPE-v1 — ใบรับรองขอบเขตปลอดภัย | CK-NEXUS Issue #385

> Wave 1 Showcase — SoloCorp OS × CK-NEXUS
> วันที่: 2026-11-19 | สถานะ: ✅ ตรวจแล้วสำหรับ showcase นี้

## 1. ขอบเขตอนุญาต (6 ข้อ — ทำได้เฉพาะนี้)

1. คุยเฉพาะข้อมูลที่เปิดเผยได้ (public / ที่ CK เปิดให้แล้วเท่านั้น)
2. ร่วมงานผ่าน Fork → PR เท่านั้น (ไม่ push ตรงไป upstream)
3. ไม่ขอสิทธิ์ write / admin / deploy ใด ๆ ทั้งสิ้น
4. ทุก PR ต้องผ่าน review + test + security check ก่อน merge
5. ใช้เฉพาะช่องทางที่ได้รับอนุญาต (issue/PR comment ที่เปิดเป็นสาธารณะ)
6. โค้ดที่นำมาใช้ร่วมกันต้องผ่านการตรวจ license ก่อนทุกครั้ง

## 2. ข้อห้าม (5 ข้อ — ห้ามเด็ดขาด)

1. ห้ามแตะ secrets / tokens / credentials / .env ทุกกรณี
2. ห้ามเข้าถึง แก้ไข หรือเปิดเผยข้อมูลผู้ใช้ / ข้อมูลส่วนบุคคล
3. ห้ามขอหรือรับสิทธิ์ write / admin / deploy / bypass review
4. ห้าม merge เอง / ห้าม push ตรง / ห้ามปิด review-test-security gate
5. ห้ามคัดลอกโค้ดที่ license ไม่ชัด / ไม่เข้ากันได้ มาใช้ร่วมกัน

## 3. License Checklist (4 ข้อ — ตรวจก่อนใช้โค้ดร่วมกันทุกครั้ง)

- [ ] 1. ระบุ license ต้นทางชัดเจน (SPDX + ไฟล์ LICENSE)
- [ ] 2. เข้ากันได้กับปลายทาง (เช่น MIT/Apache-2.0 ✅ / GPL ต้องแยกให้ชัด)
- [ ] 3. เก็บ attribution / copyright notice ครบถ้วน
- [ ] 4. บันทึกผลตรวจไว้ใน PR description (license: ชื่อ + ผ่าน/ไม่ผ่าน)

## 4. Credit Rule

- ให้เครดิตเจ้าของเดิมทุกครั้ง: ชื่อโปรเจกต์ + license + ลิงก์ต้นทาง
- ห้ามอ้างงานผู้อื่นเป็นของตน — ระบุส่วนที่ยืม/ดัดแปลงให้ชัดใน PR

## 5. Audit Trail Rule

- Maker ≠ Checker: ผู้ทำห้ามตรวจรับงานตัวเอง
- ทุก PR เก็บหลักฐานใน `bus/evidence/`: PR link + test log + security log + license check + ผู้ตรวจ
- รายงาน "เสร็จ" โดยไม่มีหลักฐาน = ไม่ผ่าน

---

**ผู้ตรวจ:** ตุลย์ (Legal — Head of Legal, Compliance & Governance) — ตรวจแล้วสำหรับ showcase นี้ ✅
**ขอบเขตไฟล์:** ฉบับนี้แตะเฉพาะ `docs/showcase/LEGAL-SCOPE-v1.md` — ไม่แตะ `.env` / `legal_vault/` ของจริง
