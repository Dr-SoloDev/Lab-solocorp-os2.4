# USAGE — Advisor Agreement FAST (สัญญาที่ปรึกษา)

## ใช้เมื่อไร

ใช้เมื่อ SoloCorp ต้องการแต่งตั้งที่ปรึกษา (Advisor) ที่ให้คำแนะนำเชิงกลยุทธ์ ใช้ความรู้ ความเชี่ยวชาญ หรือ network — โดยให้ค่าตอบแทนเป็นหุ้น (Equity) หรือ Token

**ไม่ใช่สัญญาสำหรับ**: ผู้รับจ้างพัฒนา (ใช้ `consulting-agreement`), พนักงาน (ใช้สัญญาจ้างแรงงาน), หรือผู้รับจ้างทั่วไป (ใช้สัญญาจ้างทำของ)

## ขั้นตอนการใช้งาน

1. กำหนดขอบเขตคำปรึกษา (ข้อ 1.1) ให้ชัดเจน
2. เลือกรูปแบบค่าตอบแทน (ข้อ 3ก Equity / 3ข Token / 3ค Cash) และลบข้อที่ไม่ใช้ออก
3. กรอก Vesting schedule (ข้อ 3ก.2 หรือ 3ข.2) — FAST แนะนำ 2 ปี, Cliff 3-6 เดือน
4. ตัดสินใจเรื่อง Acceleration (ข้อ 3ก.3) — standard สำหรับ startup คือ double-trigger
5. แนบ NDA (ข้อ 7) — แนะนำ `nda-one-way` (เฉพาะที่ปรึกษารักษาความลับ)
6. แนบ IP Assignment Agreement (ข้อ 6) — โดยเฉพาะถ้าที่ปรึกษาจะสร้างผลงานที่เป็นเอกสาร/รายงาน
7. **ต้องให้ CEO + CFO อนุมัติก่อนเซ็น** (equity/token จะมีผลต่อ cap table และ financial planning)

## ใครอนุมัติ

- **ต้อง**: CEO (turbo) — ค่าตอบแทน equity/token มีผลต่อ ownership และ dilution
- **ต้อง**: CFO (meetoo) — review valuation, dilution impact, tokenomics
- legal-tulya (เจ้าของ template)

## ข้อควรระวัง

- **Vesting Schedule**: FAST มาตรฐาน = 2 ปี total, 3-6 เดือน cliff — การปรับเปลี่ยนต้องมีเหตุผล
- **Equity (ข้อ 3ก)**: ต้องตรวจสอบ cap table และ shareholder agreement ก่อนออกหุ้น
- **Token (ข้อ 3ข)**: ต้องตรวจสอบ tokenomics และ vesting schedule ว่า align กับ advisor contribution
- **Tax Implications (ข้อ 3ก.5/3ข.4)**: ที่ปรึกษาอาจต้องเสียภาษีเมื่อหุ้น/Token vest — ต้องแจ้งให้ที่ปรึกษาทราบ
- **IP (ข้อ 6)**: แม้ที่ปรึกษาเป็น advisor ไม่ใช่ developer — ถ้าสร้างเอกสาร/แผนกลยุทธ์ ต้อง ensure ownership
- **Acceleration (ข้อ 3ก.3)**: Double-trigger เป็นมาตรฐานสำหรับ advisor (Change of Control + Termination)
- **การเจรจา**: ที่ปรึกษาอาจขอ vesting schedule หรือค่าตอบแทนที่แตกต่าง — ต้องผ่าน CEO อนุมัติเท่านั้น

## ข้อแนะนำค่าตอบแทนตาม BEST PRACTICE

| Stage | ขอบเขตที่ปรึกษา | Equity Range | Token Range |
|:------|:--------------|:------------:|:-----------:|
| Pre-seed | General Strategic | 0.5% - 1.0% | 0.5% - 1.5% |
| Seed | Technical/Industry | 0.25% - 0.5% | 0.25% - 1.0% |
| Series A+ | Domain-specific | 0.1% - 0.25% | 0.1% - 0.5% |

## อ้างอิง

- FAST Agreement (Founders Advisor Standard Template) — Silicon Valley มาตรฐาน
- ประมวลกฎหมายแพ่งและพาณิชย์
- พ.ร.บ. ความลับทางการค้า พ.ศ. 2545
- คู่มือ: "The Startup Advisor's Playbook" — รวมคำแนะนำเรื่อง equity advisor
- US template reference: FAST Agreement (original by Y Combinator ecosystem)
