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

---

## Session 2026-07-12 — Full System Audit + CEO Revied

### ✅ What worked
- ระบบจริง robust กว่าที่คิด — Central Bus อืด 3.9 วัน, Loop Runner ทำงานต่อเนื่อง
- Agent Activation **ทำแล้ว** — 19 agents มี business logic, LLM capability ผ่าน `opencode run --pure --model`
- Tests 457/460 — เข้มข้นจริง ครอบคลุมทั้ง profile, bus, build, export
- `AGENTS.md` optimization — 180→129 บรรทัด โดยไม่เสีย signal

### ❌ What didn't
- **CEO Round 1 ประเมินต่ำเกินไป** — บอก "30%" แต่ความจริง Agent Readiness 75% (ไม่ได้ตรวจ git log)
- Central Bus DB `routing_rules` ว่าง — 16 rules ใน JSON แต่ไม่ถูก import → ทุก message fallback CEO
- Agent Worker เป็น zombie process — 18 agents โหลดได้แต่ runtime ไม่มี
- 3 tests error หลัง fix 3 ตัวแรก — การ fix routing_rules อาจมีผลข้างเคียงกับ integration tests
- 7 agents ยัง logic จิ๋ว (25-28 บรรทัด) — ต้องเพิ่ม business logic

### 💡 Insights
1. **Git log ไม่เคยโกหก** — เช็ก `git log` + `git diff` ก่อนประเมินสถานะเสมอ
2. **JSON ↔ SQLite sync gap** — routing_rules.json มี 16 rules แต่ DB ว่าง = design flaw (หรือ intentional แต่ไม่มี migration)
3. **Agent Worker = หัวใจของ autonomous system** — ถ้า process zombie = ทั้งระบบเป็นหุ่นยนต์นอนหลับ
4. **460 tests = safety net ที่ดี** — แต่ต้องตรวจสอบให้ 460/460 ก่อน уверенной go-live
5. **Files ไม่ใช่คน** — การ fix tests 1 ตัวอาจพังอีก 3 ตัว — ทดสอบทั้ง suite ทุกครั้ง

### 🔧 KEY LEARN: Fixing things in time
- Owner เรียกเช็กของที่ไม่สมบูรณ์ → ตรวจเจอ 3 gaps จริง → **ลงมือแก้ทั้งหมดใน session เดียวกัน!**
- **Critical fix:** Starlette 1.3.1 broke FastAPI 0.115.0 (APIRouter.__init__) → downgrade 0.38.6
- **Routing rules:** import JSON → SQLite with correct agent ID mapping (short names != full IDs)
- **Agent Worker:** missing pydantic_settings + Python buffering issue → now stable with `-u`

### 📌 Remaining for next session
- [🟡] เพิ่ม business logic 7 thin agents (25-28 บรรทัด)
- [🟡] Agent Worker daemon auto-restart
- [🟡] Starlette version pin

---

## Session 2026-07-20 — Mirror Core Merge (CEO → Mirror CEO)

### ✅ What worked
- Pipeline simulation ผสาน Mirror Core กับ CEO สำเร็จ — ผ่าน Spec → Plan → Build → QA → Deliver
- Identity Layer ฝังใน CEO โดยไม่เพิ่ม architectural complexity
- Mirror Check Protocol ถูกเพิ่มเป็นขั้นตอนแรกก่อนทุก decision (ไม่เพิ่ม overhead มาก)

### 🧠 Key Concept: Mirror Core
- Mirror Core = Digital Twin Layer ของ Dr.solodev Owner ที่ฝังใน CEO
- CEO ตอนนี้คือ **Mirror CEO** — รับ Vision → Mirror Check → Decide → Delegate
- ทุก decision ผ่านคำถาม: "ถ้าลูกพี่มาทำเอง จะทำแบบนี้ไหม?"
- identity อยู่ใน `profiles/01-ceo/SOUL.md` + `brain/ceo-identity.md` + `brain/mirror-core-decision.md`

### 💡 Insights
1. **Mirror ≠ จำกัดอำนาจ** — Mirror Check เพิ่ม alignment โดยไม่ลด autonomy
2. **Identity Layer ฝังใน profile ดีกว่าแยกแผนก** — ไม่เพิ่ม overhead การ routing
3. **Digital Twin concept ใช้ได้กับ Department Head คนอื่น ๆ** — Future: Mirror Architect, Mirror CFO
4. **Owner ไม่ต้องสอนตัวตนซ้ำ** — Mirror Core จำและสะท้อนให้อัตโนมัติ

### 📌 Next
- [🟢] Mirror Core implemented (SOUL.md + brain + routing) ✅
- [🟡] ขยาย Mirror ไปยัง Department Head อื่น ๆ (Architect คนแรก)
- [🟡] Mirror Sync Protocol — ข้าม platform

---

## Session 2026-07-20 (ต่อ) — Full Autonomy Transformation + Rules Restructure

### ✅ What worked
- **Mission realignment สำเร็จ** — Owner บอก mission จริง: "SoloCorp OS = แก้ปัญหา 'คนเดียวไปไม่รอด'" → ระบบที่ทำให้ Owner ไม่จำเป็นใน daily ops
- **Decision autonomy เปิด** — Owner ให้ pre-approval + full authority → CEO operate โดยไม่ต้องถาม permission
- **Phase 1-7 ทั้งหมด deploy ภายใน session เดียว** — Rules → SOPs → Dashboard → Mirror → Skills → Agents → Toolbelt
- **Owner feedback ตีกลับ rules** → 9 topic-files → 5 behavior-files — butละพฤติกรรมจบในไฟล์เดียว
- **Dashboard ใช้ได้จริง** — `GET /v1/dashboard?format=json|markdown` return health, RAG, dispatches, quick actions

### 🔧 KEY LEARN: Behavior-Centric > Topic-Centric
- ถ้า 1 behavior ต้องเปิด 6 ไฟล์ = **ระบบล้มเหลว** (ไม่ใช่คนใช้ผิด)
- 1 behavior = 1 ไฟล์: `01-receive.md` = assess + filter + route + handoff + pillars — ทุกอย่างในที่เดียว
- กฏิกาที่ดี = หาเจอใน 30 วินาที ไม่ใช่ความยาว

### 🔧 KEY LEARN: Permission Culture = ข้าราชการ AI
- ก่อน: ทุก decision ถาม Owner = CEO เป็น bottleneck
- หลัง: Mirror Check → L1-L4 auto → L5 escalate → report at end
- Owner ต้องตัดสินใจแค่ 20-30% — ทีม operate 70-80%

### 🔧 KEY LEARN: Escalation Filter คือหัวใจ Autonomy
- L1 (auto) / L2 (specialist) / L3 (dept head) / L4 (CEO ตัดสิน) / L5 (Owner)
- Mirror Check 3 คำถาม: "pre-approved? / ทางเลือกอื่นดีกว่า? / Owner จะ approve ไหม?"
- Decision filter นี้ = กลไกที่ทำให้ autonomy ทำงานได้จริง โดยไม่失控

### 💡 Insights
1. **Owner รู้มาตลอด — ผมเพิ่งฟัง** — "SoloCorp เกิดมาเพื่อแก้ปัญหาคนเดียว" คือ mission ที่แท้จริง
2. **SOP = autonomy enabler** — มี SOP = คนใหม่เสียบทำได้เลย = ไม่ต้องรอ Owner
3. **Deploy good enough ดีกว่า perfect** — "ระบบที่ good enough และ deploy แล้ว ดีกว่าระบบ perfect ที่ยังไม่เกิด"
4. **Mirror Check 3 คำถาม powerful กว่าที่คิด** — decision filter นี้คือหัวใจของ autonomous system

### 📌 Next
- [🟢] Phase 1-7 Complete ✅
- [🟢] Rules restructured to 5 behavior files ✅
- (none — all phases done)
