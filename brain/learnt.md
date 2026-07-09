# 📚 CEO Learnt — Lessons & Insights

> CEO เรียนรู้จากทุก session — บทเรียนนี้อยู่ยืนยงข้าม platform

---

## Session 2026-07-08 — ระบบ CEO Memory ครั้งแรก

### ✅ What worked
- `brain/ceo-memory.json` + Central Bus Facts = CEO จำองค์กรได้
- Cross-platform MCP configs (.claude, .codex, .cursor) ใช้ relative path ได้
- Private repo = เก็บ .env.example + API key ใน git ได้ ไม่ต้องกังวล leak
- bootstrap-ceo.sh = สั่งเดียวจบ clone → boot

### ❌ What didn't
- `/v1/observe` format ผิดจากที่คาด (ต้องใช้ `source_agent` + `task_id` + `payload` — ไม่ใช่ `agent_id` + `message`)
- 55+ specialist agents ยังเป็นแค่ profile — สั่งไปแล้วไม่มีคนรับ
- Central Bus facts หายเมื่อ bus.db ถูกลบ (volatile)

### 💡 Insights
1. **CEO ต้องรู้จักตัวเองก่อนถึงบริหารทีมได้** — identity manifest คือรากฐาน
2. **File-based memory อยู่รอดข้าม platform** แต่ต้องมี auto-load protocol
3. **Agent Activation > Agent Creation** — มี profile แล้วต้องทำให้มีตัวตน
4. **ทีมไม่ต้องพร้อมทุกคนพร้อมกัน** — เริ่มที่ 5 กรมหลักก่อน (CFO, Architect, Engineering, Product, Orchestrator)

### 📌 Pending for next session
- Agent Activation System — P0
- CEO Auto-Load Protocol — P0
- Department API Keys — P1
- Agent Worker Service — P1

---

## Session 2026-07-09 — Agent Activation Go-Live

### ✅ What worked
- blueprint + ADR = Owner ไว้ใจให้ CEO เดินหน้าได้เอง
- Command Handoff template — สั่งงานชัด มี deadline มี checkpoint
- การ delegate ทันทีโดยไม่ลังเล = Decision Velocity ตาม SOUL

### ❌ What didn't
- ยังไม่ถึง checkpoint — ต้องรอดูว่าแต่ละกรมส่งงานตรง deadline ไหม
- Agent Worker Service ยังไม่มี spec — critical path สำหรับ Phase 1

### 💡 Insights
1. **Owner ตัดสินใจเร็วถ้ามี blueprint ชัด** — อย่าให้ Owner ดูเฉพาะปัญหา ให้เสนอทางเลือก + recommendation
2. **Command Handoff ใช้ template = professional** — delegation ≠ abandonment
3. **July Pre-Activation = buffer สำคัญ** — ถ้าตกรีบปรับ plan ได้ก่อน August

### 📌 Pending for next session (updated)
- W1 Checkpoint 2026-07-16
- Build Agent Worker Service
- สร้าง OpenCode agent configs 5 กรม
- Dry Run W4
