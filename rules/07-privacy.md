# 07 — privacy: family-vault (Owner-approved ส่วนตัว, นอก repo)

> **เมื่อแตะ family-vault / private / stories — กฎ 1 หน้านี้เท่านั้น**
> สถานะ: Owner อนุมัติ family-vault ส่วนตัวแล้ว (นอก repo, ห้ามขึ้น git/สาธารณะ)
> หลัก: **SOP > Memory — ถ้าไม่มีคำว่า "อนุมัติ" จาก Owner = ห้ามใช้**

## 1. ขอบเขต

| โซน | คืออะไร | กฎ |
|:---|:--------|:---|
| `family-vault/` | vault ส่วนตัว Owner (อยู่นอก repo) | **ห้ามขึ้น git / ห้าม push / ห้ามเผยแพร่สาธารณะ เด็ดขาด** |
| `family-vault/private/` | เรื่องส่วนตัว/อ่อนไหว | **ห้ามเปิด-ห้ามอ่าน-ห้ามใช้** ถ้าไม่มีคำว่า "อนุมัติ" จาก Owner ใน session นี้ |
| `family-vault/stories/` | วัตถุดิบเล่าเรื่อง | ใช้ทำสคริปต์/วิดีโอ/storytelling ได้ **เฉพาะเมื่อ Owner เซ็น (explicit)** |
| publish ใดๆ ที่แตะ vault | สคริปต์/วิดีโอ/โพสต์/ไฟล์ส่งออก | **ต้องผ่าน Legal check (@legal-tulya) ก่อนเสมอ** |

## 2. กฎเหล็ก 4 ข้อ

1. **family-vault ห้ามขึ้น git/สาธารณะ** — ไม่ add / ไม่ commit / ไม่ push / ไม่แนบไฟล์เข้า bus/evidence ที่เป็น public; ถ้าเผลอก็อปปี้เข้า repo ให้ลบออกจาก working tree ทันทีแล้วแจ้ง Owner (ห้าม commit เพื่อแก้)
2. **private/ = default DENY** — ไม่มีคำว่า "อนุมัติ" = ห้ามอ่านเนื้อหา ห้ามอ้าง ห้ามสรุป ห้ามส่งต่อข้ามแผนก; การขออนุมัติต้องระบุไฟล์ + วัตถุประสงค์ + ขอบเขตการใช้
3. **stories/ = ใช้ได้เมื่อ Owner เซ็นเท่านั้น** — สเซ็นต้อง explicit (ระบุเรื่อง + ใช้ทำอะไร + ช่องทางไหน); ห้ามตีความคำกว้างๆ ว่าเซ็นแล้ว
4. **ทุก publish ต้องผ่าน Legal check** — สคริปต์/วิดีโอ/caption ที่มาจาก stories ต้องให้ Legal ตรวจก่อน publish; ไม่มี Legal pass = ห้ามกด publish

## 3. สิ่งที่ทำได้ / ห้ามทำ

- ✅ อ้างได้แค่ "กฎข้อนี้" (ไฟล์นี้) โดยไม่เปิดเนื้อหา vault
- ✅ เสนอบรรทัด `.gitignore` ป้องกัน (`**/family-vault/**`) โดยไม่แตะ vault
- ❌ ห้าม `read/grep/glob` เนื้อใน `family-vault/private/` ถ้า Owner ไม่อนุมัติ
- ❌ ห้ามแตะ `.env` / secret ใดๆ ภายใต้ข้ออ้าง privacy นี้
- ❌ ห้าม commit ใดๆ จากงานนี้ (read-only + สร้างกฎเท่านั้น)

## 4. ถ้าละเมิด / เจอหลุด

1. หยุดงานทันที → 2. แจ้ง Owner + Legal → 3. ลบสำเนาที่หลุดออกจาก repo working tree (ไม่ commit) → 4. บันทึก incident สั้นๆ (ใคร/อะไร/เมื่อไร) โดยไม่แปะเนื้อหา private

---
*ล็อกโดย Legal (ตุลย์) ตาม Owner approval — family-vault ส่วนตัว นอก repo*
