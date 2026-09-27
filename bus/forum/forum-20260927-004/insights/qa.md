# qa @ forum-20260927-004

QA มองแผนนี้: การแก้ header เป็น X-API-Key เป็น breaking change ที่ไม่มี regression test รองรับ ถ้ามี caller เก่าที่ยังส่ง Bearer อยู่ จะกลายเป็น 401 ทั้ง pipeline โดยที่ไม่มีใครรู้ตัว — ต้องมี evidence ว่า grep/log ยืนยันว่าไม่มี Bearer client ค้าง ก่อน flip

การ audit subscription_audit/pipeline_executor คือเพิ่ม failure surface ใหม่: ถ้า audit hook ทำงานช้าหรือพัง จะดึงงานจริงจมด้วย ต้องมี try/except แยกและ test ว่า audit ล้มเหลวแล้ว business ยังเดินต่อ

cron ทุก 30 นาที + manual 1 รอบในช่วงเดียวกัน = double-processing risk บน queue 19 ชิ้น ต้องมี idempotency/lock guard และหลักฐานว่าไม่มี i
