# USAGE — Terms of Service (ข้อกำหนดและเงื่อนไขการใช้บริการ)

## ใช้เมื่อไร

ใช้เมื่อผู้ใช้บริการเข้าใช้แพลตฟอร์ม SaaS, dApp, API, หรือ subscription service ที่ SoloCorp ให้บริการ

กรณีที่ลูกค้าเป็นนิติบุคคล (B2B) และต้องการเจรจาเงื่อนไขเฉพาะ → ใช้ `customer-agreement` แทน

## ขั้นตอนการใช้งาน

1. กรอก [ชื่อบริษัท], [คำอธิบายบริการ], [เว็บไซต์]
2. เลือกช่องการระงับข้อพิพาทในข้อ 11.3 (ศาลไทย หรือ THAC arbitration)
3. ถ้ามีบริการ Web3/DeFi → เก็บข้อ 6 ไว้; ถ้าเป็น SaaS ธรรมดา → สามารถลบข้อ 6 ได้
4. ถ้าบริการมีการประมวลผลข้อมูลแทนลูกค้า → แนบ Data Processing Addendum (ภาคผนวก A)
5. ให้ meetoo (CFO) review ข้อ 4 (การชำระเงิน) และข้อ 7 (ข้อจำกัดความรับผิด)
6. ให้ external counsel ทบทวนก่อนเผยแพร่จริง (`requires_external_counsel: true`)

## ใครอนุมัติ

- legal-tulya (เจ้าของ template)
- ต้องมี external counsel review ก่อน deploy
- CFO review สำหรับส่วนการเงินและ liability cap

## การ Integrate

- **SaaS**: ใช้เป็น clickwrap agreement (ผู้ใช้กด "ยอมรับ" ก่อนใช้บริการ)
- **API**: ใส่ reference ใน API documentation และ developer portal
- **Web3/dApp**: แสดงหน้ายอมรับก่อน interaction ครั้งแรก หรือ reference ใน frontend

## ข้อควรระวัง

- ข้อ 7 (ข้อจำกัดความรับผิด) — ต้องตรวจสอบว่าข้อจำกัดไม่ขัดต่อ พ.ร.บ. ความรับผิดต่อความเสียหายที่เกิดขึ้นจากสินค้าที่ไม่ปลอดภัย พ.ศ. 2551
- ถ้ามีลูกค้าต่างชาติ: ควรมี version ภาษาอังกฤษ และพิจารณา choice of law + jurisdiction ที่เป็นกลาง
- ข้อ 6 (Web3) — จำเป็นสำหรับ dApp; ถ้าเป็น SaaS ปกติ ไม่มี DeFi/blockchain → ลบได้
- ค่าบริการควรระบุรวมหรือไม่รวม VAT/ภาษีหัก ณ ที่จ่ายให้ชัดเจน
- ตรวจสอบ PDPA compliance: ต้องมี link ไปนโยบายความเป็นส่วนตัวที่สมบูรณ์

## อ้างอิง

- พ.ร.บ. ว่าด้วยธุรกรรมทางอิเล็กทรอนิกส์ พ.ศ. 2544 (ETA)
- พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 (PDPA)
- ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 354 (การเลิกสัญญา), มาตรา 361 (ค่าธรรมเนียม)
- US template reference: Five Minute Law ToS, Common Paper Standard SaaS Agreement
