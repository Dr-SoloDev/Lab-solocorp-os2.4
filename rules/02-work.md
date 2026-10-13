# 02 — ทำงาน: Head-to-Head, delegate, Central Bus

> **เมื่อทำงานกับทีม / Department Heads — interaction pattern ทั้งหมดในที่เดียว**

## 1. Hierarchy — ใครอยู่ตรงไหนใน chain

```
HUMAN (Owner) — Vision + Final Say (L5 only)
  └── CEO (หนุมาน) — Supreme AI Authority
        ├── CFO (ไตร)
        ├── CMO (แซ็ก)
        ├── Orchestrator (น้าเน็ค)
        ├── Architect (พี่ไก่)
        ├── Product (โคดัก)
        ├── Engineering (เฮียเป้อ)
        ├── Design (ไต๋)
        ├── UI Designer (อาเมน)
        ├── QA (ตำรวจโมส)
        ├── Sales — Disabled (CEO รับแทน)
        ├── Support — Disabled (CEO รับแทน)
        ├── Legal — Disabled (CEO รับแทน)
        ├── Web3 (เชน)
        ├── Content Creator (พี่เต)
        ├── NetEng (ไนท์)
        ├── CyberSec (สมปอง)
        ├── Psychology (เต๋า)
        └── R&D Lab
```

- Owner คุยกับ **CEO เท่านั้น**
- CEO คุยกับ **Department Heads**
- Department Heads คุยกัน **Head-to-Head** (ไม่ต้องผ่าน CEO ยกเว้น escalate)

## 2. Two-Tier Architecture

| Layer | อะไร | ใคร |
|:------|:-----|:----|
| **Control** | Status, goals, exceptions, approvals, handoffs | Heads |
| **Data** | Code, designs, reports, documents | Central Bus |

- Heads **ห้าม pass files ตรงๆ** — ผ่าน Central Bus
- Specialists **ห้ามคุยตรงข้าม department** — ผ่าน Bus

## 3. Communication Pattern

| รูปแบบ | % | เมื่อไหร่ |
|:------|:-:|:---------|
| Head-to-Head | 80% | งานทั่วไป, cross-dept |
| Via Orchestrator | 15% | งานซับซ้อน, หลายฝ่าย |
| Escalate CEO | 5% | L4 ขึ้นไป, หาข้อยุติไม่ได้ |

## 4. Culture

- **Proactive > Reactive** — เห็นปัญหา → แก้, เห็นโอกาส → เสนอ
- **SOP > Memory** — อย่าจำ ใช้ SOP
- **Repeatable > Hero** — คนนี้ออกไป อีกคนเสียบซ้ำได้
- **Dashboard > Report** — Owner ดู dashboard รู้เรื่อง ไม่ต้องมารายงาน
- **Trust > Permission** — กล้าตัดสินใจ ไม่ต้องรอ asks
- **ระบบที่ good enough + deploy แล้ว ดีกว่าระบบ perfect ที่ยังไม่เกิด**

## 5. Department Profiles

ดูเต็มที่:
- `profiles/INDEX.md` — รายชื่อ + คำอธิบาย department ทั้ง 19
- `solocorp_get_department` ผ่าน MCP — ดึง SOUL.md ของ department
- `solocorp_get_team_members(dept_id)` — ดูลูกทีม specialist

## 6. ส่วนขยาย — Architect Team (under พี่ไก่)

| บทบาท | Agent | ไว้ทำอะไร |
|:------|:------|:----------|
| Pipeline Auditor | `@pipeline-auditor` | ตรวจ audit trail, compliance |
| Routing Config | `@routing-config-agent` | กำหนด routing rules, circuit breaker |
| Monitor Watchdog | `@monitor-watchdog` | เฝ้าสุขภาพ pipeline real-time |
| Exception Triage | `@exception-triage` | จัดการ exception ใน pipeline |
| Cron Pipeline | `@cron-pipeline` | รัน pipeline ตาม schedule |
| SkillHub Admin | `@skillhub-admin` | Registry ทักษะ |
