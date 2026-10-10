# 🛡️ Data Governance — กันข้อมูลปนถาวร (หลักการสาธารณะ)

> หลักการ: **โรงงาน ≠ สินค้า** — ข้อมูลลูกค้าห้ามเป็นส่วนหนึ่งของระบบเด็ดขาด
> เอกสารนี้เก็บเฉพาะหลักการ + taxonomy + กฎ (ขายได้ด้วย "privacy by design")
> รายละเอียดเฉพาะ (paths, ตาราง findings, audit log) อยู่ชั้น private — ติดต่อ Owner

## 1. Taxonomy — 2 แกน (ทุกข้อมูลต้องมีป้ายทั้งคู่)

**แกน X — งานของใคร (workstream):**
`SOLOCORP-CORE` (ตัวระบบ) · `CUSTOMER-{รหัส}` (งานลูกค้า ห้ามเข้าระบบ!) ·
`PERSONAL` (ของใช้ส่วนตัว) · `OWN-BIZ` (ธุรกิจตัวเอง) · `VERSION` (อัปเดต/รีลีส)

**แกน Y — ชั้นความลับ (sensitivity):**
`PUB` (เปิดได้) · `INT` (ภายใน) · `CONF` (ลับ: ชื่อ/บัตร/เบอร์/บิล/เงินรายบุคคล)

## 2. กฎเหล็ก 5 ข้อ (บังคับ)

1. **Tag ตอนเขียน** — ทุก fact/dispatch/evidence/memory entry ต้องมี `workstream` + `sensitivity`
   (ไม่มี = ผิดกฎ, default เป็น `CONF` ถ้าไม่แน่ใจ)
2. **ห้าม wildcard read** — `"keys": ["*"]` ถูกแบน ถม key ที่ต้องใช้ทีละตัว
3. **Redact ตรงประกอบ prompt** — ฟังก์ชันกลาง `redact_pii()` ตัวเดียว: ตัดบัตร/เบอร์/ชื่อออกก่อนส่งโมเดล
   ส่งยอดรวมได้ ส่งรายบุคคลห้าม (tier ฟรีที่ train ต่อ = ห้ามแตะ CONF เด็ดขาด)
4. **Evidence เก็บน้อย** — เก็บผลลัพธ์ (pass/fail/ตัวเลข) ไม่เก็บ payload ดิบที่มีข้อมูลธุรกิจ
5. **Memory แยกงาน** — `session-log` ขึ้นต้น entry ด้วย `[WORKSTREAM]` + มีดัชนีแยกงาน
   (agent จะได้ไม่หยิบความจำงาน A ไปปนงาน B)

## 3. ที่เก็บ 3 ชั้น (แยกขาดกัน)

| ชั้น | อะไร | ที่ไหน |
|---|---|---|
| Public | หลักการ, taxonomy, กฎ (เอกสารนี้) | repo สาธารณะนี้ |
| Private | customer paths, findings, audit log (metadata ไม่ใช่ PII) | repo private แยก (ไม่มีลิงก์ถึงกัน) |
| Local เท่านั้น | ข้อมูลลูกค้าจริง, ตาราง pseudonym, API keys | HDD เข้ารหัส 2 ชุด · ซิงก์ด้วย age/gpg ห้ามใช้ git |

## 4. Enforcement (ไม่พึ่งความจำคน)

| จุด | วิธี |
|---|---|
| pre-commit | สแกน PII (บัตร 13 หลัก standalone + เบอร์มือถือ) — เจอคือ block |
| CI | ตรวจ bus write ใหม่ต้องมี tag ครบ 2 แกน |
| Prompt builders | เรียก `redact_pii()` ก่อนส่งทุกครั้ง (grep ตรวจได้) |
| รายไตรมาส | audit 1 รอบ: สแกนซ้ำ + ดูงานขยะ + ทบทวน tag |
