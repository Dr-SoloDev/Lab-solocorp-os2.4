# USAGE — Privacy Policy PDPA (นโยบายความเป็นส่วนตัว)

## ใช้เมื่อไร

ใช้เมื่อ SoloCorp ให้บริการที่เก็บรวบรวมข้อมูลส่วนบุคคลของผู้ใช้ ไม่ว่าจะเป็น SaaS, API, dApp, หรือแพลตฟอร์มใด ๆ

**จำเป็นต้องมีนโยบายความเป็นส่วนตัวเสมอ ถ้าบริการเก็บข้อมูลส่วนบุคคล** — ตาม พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 (PDPA)

## ขั้นตอนการใช้งาน

1. กรอก [ชื่อบริษัท], [อีเมล DPO], [ที่อยู่], [เว็บไซต์]
2. ปรับตารางวัตถุประสงค์ในข้อ 2 ให้ตรงกับ use case จริง
3. ตรวจสอบรายชื่อผู้ให้บริการภายนอกในข้อ 3.1 — ต้องมี DPA กับทุกราย
4. ถ้ามีบริการ Web3 → เก็บข้อ 1.4 และข้อ 6 (Disclaimer เรื่อง blockchain immutability)
5. ถ้าไม่มีบริการ Web3 → สามารถลบข้อ 1.4 ได้
6. ติดตั้ง cookie consent banner (ข้อ 7)
7. ให้ external counsel ทบทวนก่อนเผยแพร่ (`requires_external_counsel: true`)

## การ Integrate

- **ใน Service**: แสดงนโยบายให้ผู้ใช้เข้าถึงได้ตลอดเวลา ลิงก์จาก footer, settings page
- **ใน ToS**: อ้างอิงในข้อ 9 (หรือข้อที่เกี่ยวข้อง)
- **Cookie Banner**: ต้องมี cookie consent management (ใช้ cookieyes, osano หรือ custom)
- **DPA (Data Processing Addendum)**: ถ้าบริการทำหน้าที่เป็น data processor ให้ลูกค้า ต้องมี DPA แยกต่างหาก

## ใครอนุมัติ

- legal-tulya (เจ้าของ template)
- ต้องมี external counsel review ก่อน deploy
- DPO (ถ้ามี) ควรร่วมตรวจสอบ

## ข้อควรระวัง

- ต้องมี cookie consent mechanism จริง ไม่ใช่แค่เขียนในนโยบาย
- ถ้าใช้ Google Analytics: ต้องมี lawful basis (consent สำหรับการตลาด, legitimate interest สำหรับ analytics) และต้องมี GA4 privacy settings ที่ถูกต้อง
- Blockchain immutability disclaimer (ข้อ 6) — สำคัญสำหรับ Web3: ไม่สามารถลบข้อมูลจาก blockchain ได้แม้ผู้ใช้ขอใช้ right to deletion
- ต้องมี DPA กับผู้ให้บริการคลาวด์และผู้ให้บริการทุกรายที่ประมวลผลข้อมูลแทนเรา (AWS, GCP, Stripe, etc.)
- กรอกข้อมูล DPO: ถ้าเป็น SoloCorp ที่ไม่มี DPO ยังไม่ผิดกฎหมาย แต่ควรตั้งผู้รับผิดชอบและแจ้งช่องทางติดต่อ

## อ้างอิง

- พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 (PDPA) มาตรา 19-29
- ประกาศคณะกรรมการคุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2565
- US template reference: Common Paper Privacy Policy, Standard Privacy Policy Framework
