# SoloCorp OS — Fact Table (สำหรับสคริปสื่อทุกตอน)

> Single source of truth — ตัวเลขเปลี่ยน อัปเดทที่นี่ที่เดียว
> ตรวจล่าสุด: 2026-09-28 (เทียบ repo จริงแล้ว)

| เรื่อง | ใช้เลขนี้ | ที่มา |
|:-------|:----------|:------|
| จำนวนแผนก | **19 Dept Heads + R&D Lab** (ห้ามใช้ 18) | `profiles/` |
| จำนวน specialists | **62+** (ห้ามใช้ 55) | `workers/agents/` |
| เวอร์ชันระบบ | **v2.4** (ห้ามใช้ v2.3.1) | `docs/ARCHITECTURE.md` |
| Handoff | **worker poll 5 วิ + cron push 5 นาที** (ห้ามอ้าง <5 วิ end-to-end) | `agent_worker_service.py`, crontab |
| Routing | **`bus/system/routing_rules.json`** (ไม่มีไฟล์ `routing.yaml`) | `bus/system/` |
| อนุมัติผ่าน Discord | **ไม่มี** — ตัดทิ้ง | — |
| ต้นกำเนิด Z580 | ใช้ได้ (มีใน brain) | `brain/session-log.md` |
| วันเริ่ม / พัง 50-60 ครั้ง | ⚠️ repo ไม่มีบันทึก — ต้อง Owner ยืนยันก่อนใช้ | — |

กติกา: claim ใดไม่มีในตารางนี้ → ใส่ `[source file]` กำกับ หรือตัดออก
