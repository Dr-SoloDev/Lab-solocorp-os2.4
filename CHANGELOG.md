# Lab-solocorp-os2.4 — Changelog

> เวอร์ชั่นของระบบออกแบบ Department Architecture

---

## v0.4.0 (2026-06-27)

### Changed
- **Rename Orchestration → Architect** — เปลี่ยนชื่อแผนกจาก Orchestration เป็น Architect
  - โฟลเดอร์: `profiles/orchestration/` → `profiles/architect/`
  - Head Profile: `01-head-of-orchestration.md` → `01-head-of-architect.md`
  - อัปเดตทุก internal link ใน INDEX.md, ARCHITECTURE.md, SOUL.md
  - ล้างไฟล์ต้นทางโฟลเดอร์ `orchestration/` และ `profiles/01-head-of-orchestration.md`

---

## v0.1.0-draft (2026-06-26)

### Added
- วาง Foundation Architecture Design:
  - **3 Pillars** ของ Department Head Design
    - Pillar 1: หัวหน้าไม่ทำงานเอง
    - Pillar 2: Leadership Skills สำหรับบริหารแผนก
    - Pillar 3: Ownership Mindset
  - **Two-Tier Architecture** (Control Layer vs Data Layer)
    - Control Layer → ผ่าน Department Head (Status, Goal, Exception)
    - Data Layer → Auto via Central Bus (Code, Files, Outputs)
  - **แนวทางการแก้ Orchestration Bottleneck**
    - Head-to-Head direct handoff (80% ของเคส)
    - Escalate เท่าที่จำเป็น (5% ของเคส)
- สร้าง Project Structure `Lab-solocorp-os2.4`
  - `ARCHITECTURE.md` — ภาพรวมระบบ
  - `CHANGELOG.md` — บันทึกเวอร์ชั่น (ไฟล์นี้)
  - `decisions/` — ADR (Architecture Decision Records)
  - `profiles/` — Design แต่ละ Profile
  - `reference/` — ข้อมูลอ้างอิง

### Reference
- Google AI (AI Mode) — Two-Tier Architecture & Central Bus insight
- `agency-agents` repo — 411 agent templates, 18 categories
- Skill Inventory — 187 skills ในระบบ Hermes

---

## v0.2.0 (2026-06-26)

### Added
- **Head of Orchestration Profile** — `profiles/01-head-of-orchestration.md` (459 บรรทัด)
  - Identity: พี่ทรงศักดิ์ (Songsak) — Head of Orchestration Department
  - 3 Pillars Compliance: ไม่ทำงานเอง, Leadership Skills, Ownership Mindset
  - Two-Tier Architecture: บทบาทใน Control Layer vs Data Layer
  - 3 Functions หลัก: Goal Alignment, Internal Orchestration, Exception Handling
  - Leadership Skills: agency-agents, subagent-driven-dev, systematic-debugging, plan, handoff-templates
  - Central Bus Ownership: รับผิดชอบ Shared State ขององค์กร
  - Pipeline Design Rules + Handoff Protocol + Escalation Path
  - Implementation Checklist สำหรับ Implement จริง
- **Central Bus Schema + Protocol** — `decisions/ADR-003-central-bus-schema.md` (586 บรรทัด)
  - JSON Schema: departments_state (9 แผนก) + workflow_routing_rules + exception schema
  - Protocol: Input → Process (5 ขั้นตอน) → Output (Notification Template)
  - Handoff Protocol Template สำหรับ Department Heads ทุกคน
  - Pipeline Design Rules: Agent รู้แค่ 2 ทิศทาง, ห้ามคุยข้ามสาย
- **ARCHITECTURE.md** — Profile #01 🔴→🟢 พร้อมลิงก์
- **profiles/INDEX.md** — sync สถานะ

### Changed
- ARCHITECTURE.md: Profile #01 Head of Orchestration จาก 🔴 เป็น 🟢 Design เสร็จ

## v0.3.0 (2026-06-26)

### Added
- **ทีมของพี่ทรงศักดิ์ — 5 Pipeline Agent Profiles** `profiles/orchestration/phee-thongsak/team/`
  - **📋 Pipeline Auditor** (01-pipeline-auditor.SOUL.md) — GNAP Audit Trail + Compliance Checker + Evidence Collection
  - **🗺️ Routing Config Agent** (02-routing-config-agent.SOUL.md) — GNAP Routing Registry + MagiC Circuit Breaker + Workflow DAG
  - **🎛️ Monitor Watchdog** (03-monitor-watchdog.SOUL.md) — Health Probe + SLA Tracking + TeamHero Dashboard + Auto-Recovery
  - **🧭 Exception Triage Agent** (04-exception-triage-agent.SOUL.md) — AXME Auto-Classification + RCA + After Action Review
  - **⏰ Cron Pipeline Agent** (05-cron-pipeline-agent.SOUL.md) — Temporal Durable Execution + n8n Workflow Automation + Schedule Registry
- **ARCHITECTURE.md** — แผนผังทีม + ลิงก์ profiles
- **profiles/INDEX.md** — เพิ่ม 5 Profile ใหม่ในทีม

### Protocols ที่ถูกตกผลึกในระบบ

| Protocol | ใช้ใน | ประโยชน์ |
|:---------|:------|:---------|
| **GNAP** | Pipeline Auditor + Routing Config Agent | Git-Native Audit Trail + Routing Registry |
| **MagiC** | Routing Config Agent + Exception Triage Agent | Circuit Breaker 3 States (CLOSED/OPEN/HALF_OPEN) |
| **model-watchdog** | Monitor Watchdog | Health Probe + Auto-Rollback |
| **TeamHero** | Monitor Watchdog | Dashboard Metric Format |
| **AXME** | Exception Triage Agent | Exception Classification (LOW/MED/HIGH/CRIT) |
| **Temporal** | Cron Pipeline Agent | Durable Execution + Retry Queue |
| **n8n** | Cron Pipeline Agent | Workflow Node-Based Automation (Split/Merge) |

### Reference
- `awesome-ai-agents-2026` repo — cloned และวิจัยแล้ว
- `agency-agents` — 6 ไฟล์ที่เกี่ยวข้อง: jira-steward, compliance-auditor, workflow-architect, agents-orchestrator, chief-of-staff, workflow-optimizer

## Roadmap

| เวอร์ชั่น | สิ่งที่จะทำ |
|:---------|:-----------|
| v0.4.0 | Design Head of Marketing profile |
| v0.5.0 | Design Head of Engineering profile |
| v0.6.0 | Design Head of Design profile |
| v0.7.0 | Design Head of Finance profile |
| v0.8.0 | Design Head of QA profile |
| v0.9.0 | Design Head of Legal profile |
| v0.10.0 | Design Head of Sales profile |
| v1.0.0 | Release — ทุก Profile พร้อมใช้งาน |
