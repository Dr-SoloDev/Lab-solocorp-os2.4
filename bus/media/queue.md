# Media Queue — คิวเจนรายสัปดาห์ (Owner เคาะแล้วเท่านั้นถึงยิงได้)

> กติกา: `media_daily` ยิงเฉพาะแถว `✅ approved` วันละไม่เกิน **2 ท่อน (เช้า)**
> pilot-first: ท่อนแรกของ EP ใหม่ต้องผ่าน Owner ก่อนเสมอ

## EP: ClawForge (scripts: bus/media/clawforge/scripts.md)

| ท่อน | เวลา | สถานะ | request_id | หมายเหตุ |
|:----|:-----|:------|:-----------|:---------|
| 1 | 00:00-00:10 | ✅ approved (pilot) | — | ยิงก่อน 1 ท่อน Owner ดูแล้วค่อย batch |
| 2 | 00:10-00:20 | ⏳ pending | — | — |
| 3 | 00:20-00:30 | ⏳ pending | — | — |
| 4-11 | … | ⏳ pending | — | เคาะหลัง pilot ผ่าน |

## Keepalive (ก่อนออกหาลูกค้า 1 นาที)
- [ ] เครื่องเปิดทิ้ง + เสียบปลั๊ก (ห้าม sleep)
- [ ] Chrome เปิดแท็บ flow.google.com ค้าง (ล็อกอินอยู่)
- [ ] กลับมาเช็ค inbox human queue ว่ามี alert เสียไหม
