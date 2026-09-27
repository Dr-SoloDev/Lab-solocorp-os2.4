# engineering @ forum-20260927-004

ช่างฟูลครับ — มุม engineering ต่อแผนนี้:

1. เปลี่ยน Bearer → X-API-Key เป็น breaking change ถ้ามี client ฝั่งอื่นยังส่ง Bearer อยู่ ทั้ง 3 loops จะ 401 ตอน deploy — ต้องมี compat window ไม่ใช่สลับวันเดียว
2. ใส่ audit ใน subscription_audit / pipeline_executor = เพิ่ม write ลง hot path ของ queue ต้องคิด atomicity ให้ด้วย ว่าถ้า audit fail แต่ business logic ไป commit แล้ว state จะไม่ตรงกัน — อยากได้ fail-open หรือ fail-close ต้องเลือกข้างให้ชัด
3. cron ทุก 30 นาทีต้องกัน re-entry ถ้ารอบก่อนยังไม่จบ (single-flight) และตัว manual run ต้อง idempotent เพราะจะถูกสั่งซ้ำได้ — ควรมี dry-run flag ก่อน
