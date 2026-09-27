# 🏛️ Forum Room — Spec ฝั่ง OpenCode (port จาก Hermes, ไม่แตะฝั่ง Hermes)

> ต้นคิด: Owner — "อยากได้มุมมองจากหลากหลายด้าน เพราะตกผลึกด้านเดียวทำให้มองข้ามมุมสำคัญ"
> สถานะ: SPEC LOCKED (2026-09-25) — รอ Owner ไฟเขียวบิลด์
> ต้นฉบับ: `/home/drsolodev/solocorp-os/context/agents/forum_room/prompt.md` (อ่านอย่างเดียว ไม่แตะ)

## หลักการ (คำ Owner — ล็อกไว้)
1. **ห้องนี้ไม่ลงมือทำ** — ผลิตแค่มุมมอง (ideas / ข้อเสนอ / ข้อกังวล) ในสายงานตัวเองเท่านั้น
2. **CEO โยนแผน+เป้าหมายลงกลางห้อง** — ไม่ฟิกฟอร์แมต แผนงานเป้าหมายวางตรงกลาง ใครหยิบไปคิดมุมตัวเอง
3. **รับหมด กรองทีหลัง** — รอบแรกห้ามวิจารณ์ข้ามทีม เก็บทุกมุมก่อน
4. **ตกผลึก 2 ชั้น** — ชั้น 1: Forum ปั่นรวมเป็น synthesis / ชั้น 2: **CEO + Owner มาย่อยด้วยกัน** (คนตัดสินใจขั้นสุดท้ายคือ Owner+CEO ไม่ใช่ห้อง)
5. ขนาน ไม่รอคิว — ครบทุกมุมหรือครบเวลา → สรุปทันที ไม่รอ

## Flow
```
CEO โยน forum.proposal (แผน+เป้าหมาย) ลงกลางห้อง
  → แจกขนานไปทุก Manager (CFO/CMO/Architect/Orchestrator/Legal/+อื่นๆ)
  → แต่ละมุมคิดในสายตัวเอง → ส่ง forum.insight กลับ (สั้น กระชับ ผูกมุมตัวเอง)
  → Forum ปั่นรวม → forum.synthesis (เก็บจุดดี ถอดจุดเสีย โชว์จุดขัดแย้ง ไม่ตัดสิน)
  → CEO + Owner ย่อยชั้น 2 ด้วยกัน → ตัดสินใจทิศ
```

## ของที่ต้องบิลด์ (ฝั่ง Lab-solocorp-os2.4)
1. `scripts/inbox.py` — CLI กลาง (send/list/read/reply/archive/stats) + `bus/inbox/` 19 แผนก + routes (รากฐาน — forum ใช้ส่ง/เก็บ insight)
2. `workers/forum_room.py` — ตัวจัดเวที: รับ proposal → fan-out `think()` ขนาน → รวม synthesis (ไม่ตัดสินเอง)
3. `/forum` command — CEO เรียกเปิดเวทีจาก session ได้เลย
4. เวทีแรก (ของจริง): ถาม 4 แผนก (Legal/Sales/Finance/Product) เรื่องที่ตั้ง DocOps → ได้คำตอบ + พิสูจน์ระบบในตัว

## Build log
- 2026-09-26 ~00:46 — ✅ ชิ้น 1 เสร็จ: `scripts/inbox.py` (port inbox.sh → Python, file-based, 19 แผนก + routes.json) — เทสต์ครบวงจร send→list→read→reply→archive ผ่าน, ข้อความเทสต์เก็บเข้า archived แล้ว, queue ว่าง 0 ค้าง
- 2026-09-26 ~01:xx — ✅ ชิ้น 2 เสร็จ: `workers/forum_room.py` (proposal → fan-out think ขนาน → synthesis ชั้น 1) + เจอ+ซ่อมโมเดล: `stealth/ox-alpha` ตาย → default เป็น `opencode/muse-spark-1.3-contributor-free` (เทสต์ผ่าน) + `BaseAgent.think` รับ model ได้แล้ว
- 2026-09-26 ~01:xx — ✅ เวทีจริงครั้งแรก forum-20260926-003 (DocOps อยู่ใต้ทีมไหน, เชิญ legal/sales/cfo/product): 4/4 ตอบ เอกฉันท์ B (shared service ใต้ COO + Legal กำกับ) — synthesis อยู่ที่ bus/forum/forum-20260926-003/ — รอ Owner+CEO ย่อยชั้น 2

## กติกาเดิมที่เก็บมา (จาก prompt.md ต้นฉบับ)
- insight สั้น ผูกมุมตัวเอง / ไม่วิจารณ์ข้ามทีมรอบแรก รอบสองค่อยถกจุดขัดแย้ง
- รับผ่าน inbox, ส่งต่อผ่าน central bus events (forum.*) — ฝั่งเราปรับเป็น bus/inbox + central_bus queue

## สถาปัตยกรรมที่ CEO ตัดสินใจ (2026-09-25 — ตอบคำถาม Owner: ต้องพึ่ง Bus ไหม?)
**ตอบ: Forum เดินได้โดยไม่พึ่ง busd — Bus เป็นสมุดบัญชี ไม่ใช่เครื่องยนต์**

| ชั้น | อะไร | พึ่งอะไร | ดับแล้วเป็นไง |
|:---|:---|:---|:---|
| เครื่องยนต์ (คิด) | OpenCode native — CEO session สั่ง Task subagents ขนาน (แต่ละตัวโหลด SOUL แผนก) | โมเดล+tools ใน session | session จบ = เวทีเลิก (ปกติ) |
| สมุดบัญชี (จำ) | `bus/inbox/` ไฟล์ + `scripts/inbox.py` CLI — บันทึก proposal/insight/synthesis ทุกชิ้น | แค่ filesystem | ไม่ดับ (ไฟล์อยู่บน disk) |
| ทางด่วน (async) | Central Bus queue/API — ส่งงานข้ามเวลา/ข้าม session | busd :8099 | ดับก็ได้ — forum ยังเดิน file-based แล้วค่อย sync |

เหตุผล: busd ดับ/worker ไม่เดิน = forum ที่พึ่ง Bus จะตายตาม — แต่มุมมอง (ของมีค่าจริง) เกิดจาก LLM calls ซึ่ง OpenCode มีให้ native อยู่แล้ว เลยแยกกัน: **คิดด้วย OpenCode, จำด้วยไฟล์, ส่งข่าวด้วย Bus (ถ้ามี)**
- ทรัพยากรที่ใช้: Task subagents ใน session (ไม่เสีย key นอก) / headless ใช้ `workers/think()` ผ่าน opencode CLI
- คุม cost: เชิญเฉพาะแผนกเกี่ยว (ไม่เหมา 19 ทุกเวที), insight สั้น (ตามกติกาเดิม), timeout แล้วสรุปเลย
- Phase 1 (ตอนนี้): file-based ทั้งหมด — inbox CLI + forum worker + /forum
- Phase 2 (ทีหลัง): bus-backed mode — forum job ผ่าน queue + worker (ต้องปลุก worker ก่อน)
