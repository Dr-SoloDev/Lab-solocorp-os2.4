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
