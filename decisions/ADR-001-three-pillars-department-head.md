# ADR-001: 3 Pillars ของ Department Head Design

**วันที่:** 2026-06-26
**สถานะ:** Accepted ✅

## บริบท
ในการออกแบบ Department Architecture สำหรับ SoloCorp OS เราต้องกำหนดหลักการพื้นฐานว่า Department Head (หัวหน้าแผนก) ควรมีบทบาทอย่างไรในระบบ

## ปัญหา
ก่อนหน้านี้ SoloCorp OS มี Profile ที่เป็น "ผู้ลงมือ" (Doer) — มี Skills เยอะเกินไป, ทำงานเองทั้งหมด
ส่งผลให้:
- Profile บวม (CMO = 37 skills)
- ไม่มีเวลา "บริหาร" หรือ "พัฒนาระบบ"
- เมื่องานพลาด ไม่มีคนตรวจ
- การส่งต่องานระหว่างแผนกไม่เป็นระบบ

## ข้อตกลง (Decision)
ประกาศ **3 Pillars** เป็น Foundation ของทุุก Department Head Design:

### Pillar 1: หัวหน้าไม่ทำงานเอง
- หัวหน้าไม่ใช้ Tools ลงมือทำ
- ใช้ `delegate_task` สั่ง Specialist Agent ทำงานแทน
- หัวหน้ามีแค่ Management Skills

### Pillar 2: สกิลผู้นำบริหารแผนกอย่างเป็นเลิศ
- รู้จัก Specialist Agent ทุกตัวในสายงานตัวเอง
- มีทักษะตรวจงาน (Quality Control)
- มีทักษะวางแผน (Planning)
- มีทักษะเชื่อมต่องาน (Handoff)

### Pillar 3: Ownership Mindset
- หัวหน้า = เจ้าของแผนก, ไม่ใช่ลูกจ้าง
- ตัดสินใจในกรอบที่ CEO วางไว้
- รับผิดชอบผลลัพธ์ — ไม่โทษ Agent หรือคนอื่น
- พัฒนาแผนกตัวเองตลอดเวลา

## ผลกระทบ
- **Positive:** Profile เล็กลง, ตรวจงานได้, ส่งต่องานเป็นระบบ
- **Negative:** ทุุก Profile ต้อง redesign ใหม่ (ไม่มีทางลัด)
- **Risk:** หัวหน้าอาจกลายเป็น bottleneck ถ้า Design ไม่ดี (แยก Data vs Control Layer)

## ทางเลือกที่ไม่ได้เลือก
- "Super Profile" — Profile เดียวที่มีทุกอย่าง → ❌ Profile บวม, ควบคุมยาก
- "No Head" — ใช้แค่ Agent ส่งงานถึงกันตรงๆ → ❌ ขาด Ownership, ขาด Quality Control
