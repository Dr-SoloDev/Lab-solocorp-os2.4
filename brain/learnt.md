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

### 🔧 KEY LEARN: Auto-Pilot ≠ Automation — Auto-Pilot = Decision Support
- Bootstrap = ไม่ต้องคิด context → focus ที่ work
- Triage = ไม่ต้องเปิด routing table → เสนอ auto
- Mirror Hook = ไม่ต้อง consciously นึก 3 คำถาม → system remind
- Orchestrator = ไม่ต้อง kickoff pipeline → system ทำ
- Summary = ไม่ต้อง save brain manual → system สรุป
- **5 components = CEO สามารถ focus ที่ L4-L5 decisions ไม่ใช่ routine**

### 🔧 KEY LEARN: Owner Feedback = Friction Signal
- Owner บอก "กฏิกาที่ดีไม่ใช่อันที่ยาว แต่คืออันที่เรายังหาเจอ" → 1 behavior = 1 ไฟล์
- ถ้า Owner รู้สึก friction → มีปัญหาจริง → อย่าเถียง → แก้
- กฏิกาที่ต้องเปิด 6 ไฟล์เพื่อ 1 behavior = failure ไม่ใช่ user error

### 📌 Next
- [🟢] Phase 1-7 Complete ✅
- [🟢] Rules restructured to 5 behavior files ✅
- [🟢] Phase 8: Auto-Pilot (5 components) ✅
- (none — all phases done. ระบบพร้อม operate)

---

## Session 2026-09-25 — บทเรียนสัญญา: เกราะก่อนดาบ

### ❌ What happened (Owner เล่าเอง)
- รับงานโดยไม่เห็นสัญญาก่อน ไม่ได้ตกลงร่วมกัน — เพิ่งได้อ่านสัญญาวันส่งมอบงาน
- โชคดีที่ผู้ว่าจ้างใจดี เห็นความทุ่มเท เลยปล่อยผ่าน — "เสียวสันหลังวาบ"
- ที่ผ่านมา: ไม่มีเอกสารฝั่งเราเลย ไม่มีขอบเขตงาน ไม่มีกำหนดความรับผิดชอบ — "เอาเป็นว่าไม่มีเลย"

### 💡 Insights
1. **สัญญา = เกราะ ไม่ใช่ดาบ** — "เราไม่ได้มีไว้ทำร้ายใคร แต่มีไว้ปกป้องตัวเอง" (คำ Owner — จดไว้เป็นหลักการ)
2. **โชคไม่ใช่ strategy** — ครั้งนี้รอดเพราะใจคน ไม่ใช่เพราะระบบ — "บนโลกธุรกิจไม่มีคำว่าปราณีใคร"
3. **No contract review = รับความเสี่ยงเปล่า** — ต้องเห็นและตกลงสัญญา *ก่อน* เริ่มงาน ทุกครั้ง ไม่มีข้อยกเว้น
4. **Template คือคำตอบ** — ออกแบบครั้งเดียว ใช้ซ้ำทุกงาน (สโคปงาน, เงื่อนไขชำระเงิน, การส่งมอบ/ตรวจรับ, ความรับผิด) — นี่คือที่มาของ "เครื่องมือกลางเอกสาร SoloCorp"
5. **Docling = ขาเข้า, Template = คลังกลาง** — อ่าน TOR ลูกค้าด้วย Docling → เทียบกับ template มาตรฐานของเรา → เจอจุดเสี่ยงก่อนเซ็น

### 📌 Pending
- คลัง template เอกสารมาตรฐาน (Legal นำ: สัญญาจ้าง, ขอบเขตงาน, NDA, ใบเสนอราคา, ตรวจรับ, ใบแจ้งหนี้)
- กฎเหล็ก: ไม่เริ่มงานก่อนตกลงสัญญา — ทุกครั้ง

## Session 2026-10-10 — บทเรียนสแปม 7 วันที่ไม่มีใครเห็น

### ❌ What happened
- `media_daily` ส่ง SKIP inbox หา Owner ทุก 30 นาทีต่อเนื่อง ~7 วัน (28 ก.ย.–10 ต.ค.) — ไม่มีใครทักจน bootstrap วันนี้
- root มีไฟล์ขยะ 67 ไฟล์ (สคริปต์ watchdog ซ้ำ 63 ไฟล์) — `git status` อ่านไม่รู้เรื่องมาพักใหญ่

### 💡 Insights
1. **`except: pass` คือที่ซ่อนบั๊ก** — AttributeError ถูกกลืน 7 วันเต็ม ไม่มี log ไม่มี signal; guard แบบ explicit (`if last is not None`) ดังกว่า try/except ใบ้
2. **SKIP ที่ expected ห้ามแจ้งคน** — dormant จน Pro Day-1 = ไม่ใช่ incident; ทุก alert ต้องถามก่อนว่า "Owner ทำอะไรกับข้อมูลนี้ได้ไหม" ตอบไม่ได้ = อย่าส่ง
3. **`should_run` ต้องไม่มี side effect แต่ต้อง test ผ่าน `execute`** — pure function เทสซ้ำได้ True,True หลอกให้คิดว่าพัง; verify ที่ถูกคือ execute→record→should_run
4. **bootstrap นับ queue ผิด (`high=3` ทั้งที่ไฟล์ว่าง)** — ตัวเลขน่าสงสัยต้องเปิดไฟล์ดูจริงก่อนสั่งงาน (SOP > Memory, Dashboard ที่ผิดแย่กว่าไม่มี)
5. **Head สั่งได้ แต่ถ้า specialist ไม่มี shell CEO ต้องลงมือเอง + จดข้อยกเว้นไว้** — วันนี้ @changful วิเคราะห์ (read-only) CEO apply+verify; หลักฐานแทนคำอ้างทุกครั้ง

### 📌 Pending
- แก้ `session-bootstrap.py` นับ queue ให้ตรง (อ่าน jsonl จริง ไม่ใช่ offset)
- ทบทวน `except: pass` ทั้ง repo (grep) — หาจุดกลืนบั๊กตัวต่อไป

---

## Session 2026-10-15 — แก่นคนตัวเล็ก + อุปมาน้ำ (CEO ↔ Owner, ไม่ลงมือทำ)

### ✅ What happened
- Owner ตกผลึก North Star + หลัก 4 + หมุด 5 + ฟิลเตอร์ 5 ข้อ — บันทึกถาวร `brain/vision-small-people-20261015.md` (DRAFT รอ LOCKED)
- เลือกสนามแรกหมุด 4 = ครีเอเตอร์สายสร้างตัวตน (ไม่เอาสายขายของ); ออนบอร์ด = ผสมถามเบา + แต่งทีมเอง
- Owner อุปมา: riddle ขนมปังตั้งเป๊ะไม่ได้ เหมือนน้ำ (ไหล/นิ่ง/เย็น/ร้อน/แข็ง/ระเหย/เพชฌฆาต/ผู้ช่วยชีวิต)

### 💡 Insights
1. **ภาพในหัวไว้ใจไม่ได้ — ไฟล์ + git ไว้ใจได้** — Owner ห่วงตกผลึกแล้วหาย = สัญญาณให้ฝาก 3 ที่ทันที (ไฟล์แก่น + session-log + learnt) อย่ารอสรุปสวย
2. **ตอบเป๊ะไม่ได้ = สเปก ไม่ใช่ปัญหา** — Q1 (เล่า+นำเสนอ) ไม่มีสูตรตายตัว พลิกได้ไม่สิ้นสุด → ระบบต้องเป็นภาชนะ (รับรูปน้ำได้) ไม่ใช่แม่พิมพ์ (บังคับก้อนเดียว)
3. **คำถามแบบน้ำ > คำถามแบบหิน** — "อะไรทำให้เราเป็นเราตอนนี้?" เช้า/ดึก/ขายดี/ท้อ ตอบไม่เหมือนกันแต่ถูกทั้งคู่ — onboarding ต้องถามเปิด ไม่ใช่ ABCD
4. **รอยแผลคือท่อนที่คนจำได้สุด** — ขนมปังล้มเหลวกี่รอบกว่าจะอร่อย = โครงเรื่องท่อน 2 ที่เชื่อมคน 2 กลุ่ม (เคยล้มแบบเดียวกัน → เดินข้ามสะพานมาหาเอง)
5. **SoloCorp ไม่ขายฝันยอดขาย** — สายขายของวัดยาก ผูกปัจจัยนอกคอนเทนต์ อ้างยอด = ก้ำกึ่งหลอกลวง; สายสร้างตัวตนวัดซื่อสัตย์ (สม่ำเสมอ/ชัด/โอกาสเข้า)

### 📌 Pending
- Owner สั่งล็อก vision-small-people เป็น LOCKED เมื่อพร้อม (เทียบเท่า core-definition-20261010)
- ห้ามใช้ไฟล์นี้เป็นใบสั่งงานจนกว่าจะมีแผนพัฒนาจริง (Budget ledger / Trust boundary / Bus-as-a-Service ยังพักไว้ตามสั่ง)

---

## Session 2026-10-15 (ต่อ) — ย่อยชั้น 2 + ล็อก (Owner สั่ง "เอาข้อ 1 เลย")

### ✅ What happened
- Owner ให้อิสระ CEO นำ → commit c278c2f + push main + inbox 19 แผนก + forum 7/7 → Owner สั่งย่อยชั้น 2
- แปลงจุดเสี่ยง 3 ข้อเป็นกรอบกลาง (§7) แล้วล็อก vision file เป็น LOCKED

### 💡 Insights
1. **น้ำต้องมีตลิ่ง** — ยืดหยุ่นโดยไม่มีกรอบกลาง = ท่วม (consistency หาย/โทนแตก/สื่อพลาด); กรอบกลางที่ดีมี 3 ชั้น: โทนที่เจ้าของเลือกเอง + ขั้นต่ำที่ระบบค้ำ + นิยามคำที่ห้ามตีความผิด
2. **เดาได้แต่ห้ามเงียบ** — No spec=no build ไม่ได้ห้ามเดา แต่ห้ามเอาสิ่งที่เดาไปรันเลย; สิ่งที่เดา = draft spec + ต้องโชว์ + ต้องแก้ได้ใน 1 แตะ; ความนิ่งของ user = red flag ไม่ใช่ consent (กันถอนตัวเงียบ)
3. **สะอาดตั้งแต่ต้นถูกกว่าแก้ทีหลัง** — origin log + checklist 1 หน้าตอนนี้ ถูกกว่าคดี IP ตอนเปิด MIT; เก็บน้อย/เคลมน้อย = ฐาน compliance ที่ legal วางให้แล้ว
4. **คำถามที่ยังไม่ถึงเวลา = เก็บ ไม่ใช่ทิ้ง** — CFO ถามรายได้ดีมาก แต่ Owner สั่งพัก Budget/Revenue ไว้ก่อน = จดไว้ในโน้ต (§7) ไม่ใช่ปัดตก

### 📌 Pending
- ประกาศ follow-up ถึง __all__ ว่า vision ล็อก + กรอบ 3 ข้อแล้ว
- วันหยิบไปทำจริง: กรอบ 3 ข้อนี้คือ acceptance criteria ของงานออกแบบ (ไม่ใช่แค่หลักลอย)

---

> **ที่มา:** fork `darinsupanikorn-rgb` (PR #19) — บทเรียนจากการติดตั้ง OmniVoice บน RTX 4050
> merge เข้า upstream 21 ต.ค. 2026 · ปรับคำเรียก Owner ให้เข้ากับของเรา
## Session 2026-10-19 — ห้ามเรียก Owner ว่า "เอ็ง"

### ❌ What happened
- CEO เรียก Owner ด้วยคำว่า "เอ็ง" ซ้ำหลายครั้งใน session ที่คุยเรื่องสนามแรก + ติดตั้ง OmniVoice — ไม่ตรงกับระดับความเป็นทางการที่ Owner กำหนด

### 💡 Insights
1. **Owner = L5, เรียก "Owner" หรือ "Dr.solodev" เท่านั้น** — ห้ามใช้ "เอ็ง", "หนู", "ตัวเอง" ในการอ้างถึง Owner หรือผู้ที่กำลังคุย
2. **คำเลียนเสียงไม่ใช่เรื่องเล็ก** — ถ้อยค์คือส่วนหนึ่งของ identity ของ agent; ผิดคำเดียว = ผิดทั้ง relationship

### 📌 Pending
- บันทึกลง `brain/ceo-identity.md` ด้วย (กันลืมข้าม session)

## Session 2026-10-19 — Voice Clone Skill (OmniVoice)

### ✅ What worked
- ติดตั้ง OmniVoice บน RTX 4050 Laptop 6GB **สำเร็จ** — ใช้ VRAM จริงแค่ 1.96GB จาก 6GB, RTF 0.36 (num_step=16)
- ครั้งแรกคิดว่า VRAM 6GB จะตึง → **คลาดเคลื่อน เหลือเฟือกว่าที่คาดมาก** การเดา VRAM โดยไม่วัด = เดาเปล่า
- โคลนเสียงมนุษย์จาก mp4 7.5 วิ → ผลลัพธ์ **"เหมือนเลย"** (ยืนยันโดยตัวมนุษย์เอง)
- วิธีตรวจว่ามีเพลงปนโดยไม่ต้องฟัง: มองหาเฟรมที่เป็น **ดิจิทัลซิเมนซ์ (-180 dB)** — ถ้ามีช่วงเงียบสนิทแปลว่าไม่มีเพลงคลุม

### 💡 Insights
1. **script อยู่ใน Temp = สัญญาณว่าจะพัง** — ควรย้าย venv ไปที่ถาวรกว่า หรือมี repair step ใน skill (ทำแบบหลังไปแล้ว)
2. **prompt cache เปลี่ยนความเร็ว 4 เท่า** — ครั้งแรก 11.89 วิ (รวม Whisper transcribe + encode) ครั้งที่สอง 2.93 วิ
3. **เสียงต้นแบบเป็นของจริงของ Owner = สินทรัพย์ ใช้ซ้ำได้ทั้งช่อง** — เก็บเป็น skill ไม่ใช่แค่ครั้งเดียว
4. **สคริปต์ต้องหาไฟล์จาก cwd ก่อน script dir** — ตอนแรกมองแต่ script dir เลย fail ทั้งที่ไฟล์อยู่ตรงหน้า

### 📌 Pending
- **ย้าย venv ออกจาก `Temp/`** — Windows ล้างเมื่อไหร่ skill พังทันที (มนุษย์ยังไม่อนุมัติให้ย้าย 4GB)
- ทดสอบ `--setup` กับไฟล์เสียงรูปแบบอื่น (mp3, m4a)
- ทดสอบ speed=0.9 ตอนพูดเร็วเกิน

### Skill ที่สร้าง
- `.opencode/skills/voice-clone/SKILL.md` + `clone.py` — เรียกใช้: "ทำวิดีโอด้วยเสียงนี้"
