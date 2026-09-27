# forum-20260927-004

## แผน
แผนทำ Central Bus ให้เขียว: (A) แก้ header 3 loops จาก Authorization Bearer เป็น X-API-Key + audit subscription_audit/pipeline_executor, (B) ใส่ cron loop_runner ทุก 30 นาที + รัน manual 1 รอบ + จัด path cron_central_bus ให้เป็น canonical

## เป้าหมาย
Bus ทำงานสมบูรณ์โดยไม่พัง production: queue 19 ชิ้นระบาย, facts สด, scheduler heartbeat ขยับ, daily_brief ได้เลขสด
