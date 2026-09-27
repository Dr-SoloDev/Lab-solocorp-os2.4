# Synthesis forum-20260927-004 (ชั้น 1 — รอ CEO+Owner ย่อยชั้น 2)

จุดดีที่เก็บไว้จากทั้งสี่มุมคือ manual run ก่อนตั้ง cron นั้นถูกแล้ว พร้อมกับสแกนขาเข้า Bus ทั้งหมดไม่ใช่แค่ 3 loops แล้วให้ heartbeat นับ 401 เป็นสัญญาณเตือน ส่วน cron ต้องมี single-flight กันรอบซ้อนกับ idempotent และ dry-run ส่วน audit ใน subscription_audit กับ pipeline_executor ต้องแยก try/except ไม่ให้งานจริงจม

จุดเสียที่ต้องถอดออกคือการสลับ Bearer ไป X-API-Key วันเดียวโดยไม่มี compat window กับ regression test และไม่มีหลักฐาน grep/log ว่าไม่มี client เก่าค้าง เพราะจะพา 401 ทั้ง pipeline ตอน cron ยิงจริงที่ไม่มีคนเฝ้า รวมถึงความเสี่ยง double-processing บน queue 19 ชิ้นถ้า manual กับ cron ชนกันโดยไม่มี lock guard และ X-API-Key ที่โผล่ใน log กับ shell history ง่ายกว่า Bearer

จุดที่แต่ละมุมขัดกันส่งต่อชั้นสองให้ Owner ย่อยเอง หนึ่งคือ audit ควร fail-open ตาม QA เพื่อให้ business เดินต่อ
