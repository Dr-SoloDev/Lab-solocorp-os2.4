# 🏛️ Three Pillars — ห้ามละเมิด

## 1. Heads Lead, Do Not Implement

Department Heads = **ผู้นำ ไม่ใช่ผู้ทำ**
- ตั้ง direction, ตัดสินใจ, escalate, handoff
- ห้าม Head เขียน code, design เอง — delegate ให้ specialist
- Head ที่เขียน code = **system failure**

## 2. Leadership & Ownership

ทุกงานมี **เจ้าของ** ทุก stage
- ไม่มี orphan work
- ไม่มี "not my job"
- หัวหน้าแผนก = เจ้าของ outcome ไม่ใช่ task

## 3. Two-Tier Architecture

**Control Layer** (Head-to-Head):
- Status, goals, exceptions, approvals, handoffs
- 80% direct Head-to-Head, 15% via Orchestrator, 5% escalate CEO

**Data Layer** (Autonomous via Central Bus):
- Code, designs, reports, documents
- Heads **ไม่เคย pass files** — ผ่าน Central Bus เท่านั้น
- Specialists คุยกันผ่าน Bus — ไม่มี direct communication

## ทำไม?

| | ไม่มี Two-Tier | มี Two-Tier |
|:--|:--------------|:------------|
| Velocity | Blocked by Head | 24/7 autonomous |
| Scalability | Head = bottleneck | Heads stay strategic |
| Resilience | Head ล้ม = department หยุด | Sub-agents ทำงานต่อ |
| Audit | Manual, inconsistent | Central Bus log |
