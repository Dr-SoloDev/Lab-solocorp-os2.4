# SoloCorp OS v0.3.0+ — Development Plan (ตกผลึกแผน)

> **ร่างโดย:** เทอโบ ไชยศรีรัมย์ (CEO)
> **วันที่:** 2026-06-26
> **แหล่งวัตถุดิบ:** agency-agents (411 templates) + awesome-ai-agents-2026 (340+ tools)
> **ปรัชญา:** SoloCorp OS 100% — agency-agents = วัตถุดิบ คัดลูกทีมให้พี่ทรงศักดิ์

---

## 🧭 ทิศทางเชิงกลยุทธ์ — CEO Decision

### สิ่งที่เราเลือกทำ

| ข้อ | การตัดสินใจ | ที่มา |
|:---:|:------------|:------|
| 1 | **✅ สร้าง 8 Sub-agents เป็นทีมลูกน้องพี่ทรงศักดิ์** | CEO Analysis |
| 2 | **✅ แกน Routing + Audit = GNAP Protocol** (Git-Native 4 JSON files) | awesome-ai-agents-2026 |
| 3 | **✅ Standard Handoff = A2A Protocol** (Google) | awesome-ai-agents-2026 |
| 4 | **✅ Dashboard = TeamHero UI Pattern** | awesome-ai-agents-2026 |
| 5 | **✅ Durable Execution = Temporal** สำหรับ Cron Agent | awesome-ai-agents-2026 |
| 6 | **✅ Central Bus JSON Schema** → Implement จริง | ADR-003 (ที่มีอยู่แล้ว) |

### สิ่งที่เราเลื่อนไปก่อน (ตัดอย่างมีสติ)

| ข้อ | สิ่งที่ตัด | เหตุผล |
|:---:|:----------|:--------|
| 1 | **❌ Entroly (Context Optimizer)** | ต้องติดตั้ง External Service → รอ v0.4.0 |
| 2 | **❌ Compliance Agent (OWASP/Bifrost)** | Compliance จำเป็นตอน Production — ยังไม่ถึง |
|| 3 | **❌ Design Profile หัวหน้าแผนกอื่น (Marketing, Eng, ฯลฯ)** | เปลี่ยนลำดับ — ทำ Core Architect Pipeline ให้เสร็จก่อน |
| 4 | **❌ Implement จริงใน Hermes Profile** | ใช้ SOUL.md Design ก่อน — เมื่อพร้อมค่อย Migrate |

---

## 🏗️ แผนพัฒนา 4 Phase

### Phase 0: ✅ Foundation (v0.1.0–v0.2.0) — **เสร็จแล้ว**

| รายการ | สถานะ |
|:-------|:-----:|
| ADR-001: 3 Pillars | ✅ |
| ADR-002: Two-Tier Architecture | ✅ |
| ADR-003: Central Bus Schema + Protocol | ✅ |
|| Profile #01: Head of Architect (พี่ทรงศักดิ์) | 🟢 Design เสร็จ |
| ARCHITECTURE.md | ✅ |
| research: awesome-ai-agents-2026 (340+ tools) | ✅ |

---

### Phase 1: 🔴 Core Orchestration Sub-agents (v0.3.0)

**เป้าหมาย:** สร้าง SOUL.md สำหรับ 5 Sub-agents หลักที่พี่ทรงศักดิ์ใช้ควบคุม Pipeline

#### Sub-agent 1: 📋 Pipeline Auditor
| หัวข้อ | รายละเอียด |
|:------|:-----------|
| **ภารกิจ** | Audit ทุก Handoff ใน Pipeline — บันทึกประวัติ, ตรวจสอบ Compliance |
| **วัตถุดิบ** | GNAP Protocol (4 JSON files = Audit Trail) + A2A Protocol (Standard Handoff) |
| **ขอบเขต** | ทุก Pipeline ที่วิ่งผ่าน Central Bus — ตรวจสอบ: timestamp, sender, receiver, payload integrity |
| **สร้างจาก** | agency-agents: `jira-workflow-steward` + `compliance-auditor` |
| **Output** | Audit Log (GNAP JSON) + Compliance Report |
| **Priority** | P0 |

#### Sub-agent 2: 🗺️ Routing Config Agent
| หัวข้อ | รายละเอียด |
|:------|:-----------|
| **ภารกิจ** | ตั้งค่าและดูแล Workflow Routing Rules บน Central Bus |
| **วัตถุดิบ** | GNAP Protocol (Routing config = 4 JSON files) + MagiC (DAG + Circuit Breaker) |
| **ขอบเขต** | Routing Rules สำหรับทุก Department — จัดการ Dependency, Condition, Auto-Route Flag |
| **สร้างจาก** | agency-agents: `workflow-architect` |
| **Output** | Routing Rules Config + Circuit Breaker Config |
| **Priority** | P0 |

#### Sub-agent 3: 🎛️ Monitor Watchdog
| หัวข้อ | รายละเอียด |
|:------|:-----------|
| **ภารกิจ** | ตรวจสอบสถานะ Pipeline แบบ Real-time — Alert เมื่อผิดปกติ |
| **วัตถุดิบ** | model-watchdog (auto-rollback) + TeamHero UI (Dashboard) + Langfuse (Observability) |
| **ขอบเขต** | Health check ทุก Sub-agent + Central Bus State + Pipeline SLA |
| **สร้างจาก** | agency-agents: `agents-orchestrator` (ปรับ) |
| **Output** | Dashboard Data + Health Report + Auto-Rollback Trigger |
| **Priority** | P1 |

#### Sub-agent 4: 🧭 Exception Triage Agent
| หัวข้อ | รายละเอียด |
|:------|:-----------|
| **ภารกิจ** | จัดการ Exception ทุกประเภท — วิเคราะห์, แก้ไขพื้นฐาน, หรือ Escalate |
| **วัตถุดิบ** | AXME (crash recovery + kill switch) + MagiC (circuit breaker) |
| **ขอบเขต** | Exception types: BLOCKER, TIMEOUT, DATA_CONFLICT, ROUTE_FAILURE — วิเคราะห์ Root Cause |
| **สร้างจาก** | agency-agents: `chief-of-staff` + `workflow-optimizer` |
| **Output** | Resolution Report / Escalation Request |
| **Priority** | P1 |

#### Sub-agent 5: ⏰ Cron Pipeline Agent
| หัวข้อ | รายละเอียด |
|:------|:-----------|
| **ภารกิจ** | จัดการ Scheduled Tasks — Cron Jobs, Scheduled Pipelines, Batch Processing |
| **วัตถุดิบ** | Temporal (Durable Execution) + n8n (Workflow Automation Pattern) |
| **ขอบเขต** | งานที่ต้องทำงานตามเวลา: Daily Report, Weekly Backup, Monthly Cleanup |
| **สร้างจาก** | สร้างใหม่ 100% |
| **Output** | Cron Schedule + Execution History + Durable Workflow |
| **Priority** | P2 |

---

### Phase 2: 🔴 Central Bus + Enablers (v0.4.0)

**เป้าหมาย:** Implement Central Bus จริง + เพิ่ม Sub-agents เสริม

#### Sub-agent 6: 🚌 Central Bus Agent
| หัวข้อ | รายละเอียด |
|:------|:-----------|
| **ภารกิจ** | ตัวกลาง Data Layer — รับ Input, Validate, Update State, Route Notification |
| **วัตถุดิบ** | ADR-003 Schema + A2A Protocol (Google) — Standard Agent-to-Agent Protocol |
| **ขอบเขต** | Implement JSON Schema + Protocol ขั้นตอนที่ 1-5 จาก ADR-003 |
| **สร้างจาก** | สร้างใหม่ตาม ADR-003 |
| **Output** | Central Bus State JSON + Notification + Routing Trigger |

#### Sub-agent 7: 🧹 Context Optimizer Agent
| หัวข้อ | รายละเอียด |
|:------|:-----------|
| **ภารกิจ** | บีบอัดข้อมูลก่อนส่งให้พี่ทรงศักดิ์ — ลด Token, เพิ่ม Context Window |
| **วัตถุดิบ** | Entroly (Context Engineering — 78% token reduction) |
| **ขอบเขต** | สรุป Pipeline Status, Exception, Report — ให้สั้น กระชับ ก่อนส่ง Head |
| **สร้างจาก** | สร้างใหม่ |
| **Output** | Compressed Summary / Status Digest |

#### Architecture Upgrade: Central Bus Implementation

```text
┌────────────────────────────────────────────────────────────┐
│                    🎼 พี่ทรงศักดิ์                            │
│          (Head of Architect — Control Layer)            │
│                                                             │
│  สั่งงานผ่าน → 📋 🗺️ 🎛️ 🧭 ⏰ (5 Sub-agents)              │
└──────────────────────┬─────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────┐
│  📦 CENTRAL BUS AGENT (🚌 Data Layer - v0.4.0)              │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Marketing │→│ Engineer │→│   QA     │→│  Design  │→...│
│  │  Agent    │  │  Agent   │  │  Agent   │  │  Agent   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                             │
│  ข้างใน Bus:                                                │
│  ├── JSON Schema (Shared State)                             │
│  ├── GNAP Audit Trail (Git-based)                          │
│  ├── A2A Handoff Protocol                                  │
│  └── Watchdog + Circuit Breaker                            │
└────────────────────────────────────────────────────────────┘
```

---

### Phase 3: 🔴 Dashboard + Compliance (v0.5.0)

**เป้าหมาย:** มองเห็น Pipeline ทั้งระบบ + เริ่ม Governance

| Sub-agent | วัตถุดิบ | รายละเอียด |
|:----------|:---------|:-----------|
| 🖥️ Pipeline Dashboard | TeamHero UI + Langfuse Tracing | Web Dashboard แสดงสถานะ Pipeline Real-time |
| 🧪 QA Validation Gate | model-watchdog + OWASP Top 10 | Auto-rollback ถ้า Pipeline ล้ม — Safety Check |
| ⚖️ Compliance Agent | OWASP Top 10 + Bifrost | Governance — ตรวจสอบ Agent Behavior |
| 📊 Reporting Agent | Langfuse + LangSmith | Generate Pipeline Analytics Report |

---

### Phase 4: 🔴 Department Expansion (v1.0.0)

**เป้าหมาย:** สร้าง Department Head Profiles ที่เหลือ + เชื่อมเข้า Central Bus

| Profile | Priority | หมายเหตุ |
|:--------|:--------:|:---------|
| 02 — Head of Marketing | P0 | วาง Content Pipeline ให้เสร็จ |
| 03 — Head of Engineering | P0 | รับ Code Pipeline ต่อจาก Marketing |
| 04 — Head of Design | P1 | หลังจาก Engineering มีงานป้อน |
| 05 — Head of Finance | P1 | ควบคุมงบประมาณ |
| 06 — Head of QA | P1 | Gate สุดท้ายก่อน Launch |
| 07 — Head of Legal | P2 | Compliance + Legal Review |
| 08 — Head of Sales | P2 | ขายของ + Revenue |
| 09 — Head of Product | P1 | กำหนด Feature Roadmap |

---

## 🗺️ Timeline (ประมาณการ)

| Phase | เวอร์ชั่น | ระยะเวลา | เนื้อหา |
|:------|:---------:|:--------:|:--------|
| **Phase 0** | v0.1.0–v0.2.0 | ✅ เสร็จ | Foundation + Profile #01 + ADRs |
| **Phase 1** | **v0.3.0** | **~3-4 วัน** | **5 Sub-agents SOUL.md** |
| **Phase 2** | v0.4.0 | ~5-7 วัน | Central Bus Implement + 2 Sub-agents เสริม |
| **Phase 3** | v0.5.0 | ~3-5 วัน | Dashboard + Compliance + QA Gate |
| **Phase 4** | v1.0.0 | ~7-14 วัน | 9 Department Heads + เชื่อม Bus |

> **รวม:** ~20-30 วันถึง v1.0.0 (ขึ้นอยู่กับความพร้อม Implement จริง)

---

## 📦 สิ่งที่ต้องสร้างใน Phase 1 (Work Immediately)

### 1. SOUL.md — 📋 Pipeline Auditor
ใช้ GNAP Protocol (4 JSON files) เป็น Audit Trail:
- `gnap-audit.json` — ทุก Handoff ถูกบันทึก
- `gnap-roster.json` — ใครอยู่ใน Pipeline บ้าง
- `gnap-tasks.json` — Task Queue
- `gnap-workflows.json` — Workflow Definition

**Agency-agents วัตถุดิบ:** `jira-workflow-steward` (Task Tracking) + `compliance-auditor` (Audit Check)

### 2. SOUL.md — 🗺️ Routing Config Agent
Routing Rules บน Central Bus + Circuit Breaker Pattern จาก MagiC

**Agency-agents วัตถุดิบ:** `workflow-architect` (Pipeline Design)

### 3. SOUL.md — 🎛️ Monitor Watchdog
model-watchdog pattern: Health Probe → ผิดปกติ → Rollback Config

**Agency-agents วัตถุดิบ:** `agents-orchestrator` (ปรับ Monitoring)

### 4. SOUL.md — 🧭 Exception Triage Agent
AXME pattern: Exception → Classify → Resolve / Escalate

**Agency-agents วัตถุดิบ:** `chief-of-staff` + `workflow-optimizer`

### 5. SOUL.md — ⏰ Cron Pipeline Agent
Temporal Pattern: Durable Execution, Retry, History

**สร้างใหม่ 100%** — ไม่มีใน agency-agents

---

## ⚠️ ความเสี่ยง + ปัจจัยที่ต้องติดตาม

| ความเสี่ยง | ผลกระทบ | แนวทางรับมือ |
|:----------|:--------|:-------------|
| **GNAP Protocol ยังไม่ Stable** | High | ใช้เป็น Design Reference — Adapt ได้ |
| **A2A Protocol (Google) เพิ่งออก** | Medium | Monitor Google ADK Docs — ปรับตาม |
| **8 Sub-agents กิน Token เยอะ** | Medium | Context Optimizer ใน Phase 2 |
| **พี่ทรงศักดิ์รับ Sub-agents ไม่ไหว** | High | จำกัด Sub-agents ให้ Escalate เฉพาะ P0 |
| **การ Implement จริงใน Hermes Profile** | Medium | Phase 1 = SOUL.md Design ก่อน — ไม่ Implement |

---

## 📝 สรุป CEO

**แผนนี้เปลี่ยน Roadmap เดิม (ที่บอกว่า Design Marketing ก่อน) โดยสิ้นเชิง**

เหตุผล CEO:
> "เราไม่สามารถออกแบบ Department Head อื่นได้ ถ้า Orchestration Pipeline ยังไม่นิ่ง"
> — เทอโบ ไชยศรีรัมย์

**Phase 1 (v0.3.0)** = จุดเปลี่ยนสำคัญที่สุด:
- สร้างทีมลูกน้องให้พี่ทรงศักดิ์ 5 คน ผ่าน SOUL.md
- ใช้ GNAP + A2A เป็น Standard Protocol แทน Custom
- ใช้ model-watchdog + AXME + Temporal เป็น Enabler Technology

**เมื่อ Phase 1 เสร็จ → พี่ทรงศักดิ์มีทีมลูกน้องทำงานแทน**
**จากนั้น Phase 2-4 ต่อยอดได้เร็วขึ้นอย่างน้อย 2x**

---

## ✅ คำสั่ง CEO — รอ Dr.Solodev อนุมัติ

| ลำดับ | รายการ | อนุมัติ? |
|:-----:|:-------|:-------:|
| 1 | **Phase 1 v0.3.0** — สร้าง 5 Sub-agents SOUL.md | ⬜ |
| 2 | **GNAP Protocol** เป็น Audit Trail Standard | ⬜ |
| 3 | **A2A Protocol** เป็น Handoff Standard | ⬜ |
| 4 | **เลื่อน Marketing Profile ไป Phase 4** (เปลี่ยน Roadmap เดิม) | ⬜ |
| 5 | **Central Bus Implement → Phase 2 (v0.4.0)** | ⬜ |

---

*SoloCorp OS — ตกผลึกแผน 26 June 2026*
*"Pipeline over Mesh, Orchestrate Never Operate"*
