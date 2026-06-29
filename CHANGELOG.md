# Lab-solocorp-os2.4 — Changelog

> เวอร์ชั่นของระบบออกแบบ Department Architecture

---

## v0.5.0 (2026-06-28)

### Added
- **loop_runner/** — Loop Engineering infrastructure (inspired by cobusgreyling/loop-engineering)
  - `state.py` — SQLite persistent state (last_run, failures per loop)
  - `runner.py` — base Loop class with `should_run()` / `execute()` + failure tracking
  - `loops/daily_brief.py` — L1: CEO morning brief (finance + brain → report, runway warning)
  - `loops/subscription_audit.py` — L4: CFO monthly subscription scan
  - `loops/brain_auto_commit.py` — L4: auto-commit brain/memory files when git changes detected
  - `main.py` — cron entry point (`*/30 * * * * python3 -m loop_runner.main`)
- **central_bus/open_design.py** — Read-only bridge to Open Design daemon (port 41551)
  - Department permission guard (design/ui_designer/engineering/qa)
  - Convenience wrappers: `get_artifact`, `get_file`, `search_files`, `list_files`
- **bus/system/open_design_config.json** — dept→tools mapping for open-design MCP

### Fixed
- `daily_brief` loop parser: fallback finance/brain scripts return Thai text (not JSON) — switched to regex extraction
- Runway critical alert: triggers 🚨 when runway < 6 months

### Cleared
- Finance DB reset (old test data removed — 5 transactions, 3 projects)

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

## v0.5.0 (2026-06-28)

### Added
- **14-web3 — อัยวา (Head of Web3 & DeFi)** — `profiles/14-web3/SOUL.md`
  - Identity: อัยวา — Head of Web3 & DeFi, รายงานตรงต่อ CEO (เทอโบ)
  - 3 Pillars: ไม่ทำงานเอง, Security First, Ownership Mindset
  - Rules: Security audit ก่อน deploy เสมอ, ทุก on-chain decision ผ่าน CFO ก่อน
- **ทีมของอัยวา — 4 Web3 Specialist Profiles** `profiles/14-web3/aywa/team/`
  - **⛓️ Smart Contract Engineer** (01) — Solidity/Anchor, gas optimization, upgrade patterns
  - **🛡️ Blockchain Security Auditor** (02) — Manual audit + Slither/Mythril/Echidna + Attack simulation
  - **📊 DeFi Protocol Analyst** (03) — Protocol research, tokenomics design, on-chain analytics
  - **⚡ Solana Developer** (04) — Anchor programs, Web3.js/Solana.js, devnet/mainnet deploy
- **Sync 13 Department Profiles** จาก Hermes — SOUL.md สำหรับทุก Department Head
- **ทีมของทุกแผนก** — เพิ่ม Operational Team Agents ใน 11 แผนก (CFO, CMO, Orchestrator, Product, Engineering, Design, UI, QA, Sales, Support, Legal)
- **INDEX.md** — เพิ่ม Section ทีมทุกแผนก + ลิงก์ครบ 14 Department

### Changed
- Agent names sync ให้ตรงกับ Hermes: CFO=meetoo, CMO=มาร์ค, Legal=ตุลย์
- เอกสารทั้งหมดแปลเป็นภาษาไทย

---

## Roadmap

| เวอร์ชั่น | สิ่งที่จะทำ |
|:---------|:-----------|
| v0.6.0 | Central Bus Agent + Context Optimizer (Phase 2) |
| v0.7.0 | Pipeline Dashboard + Compliance Gate (Phase 3) |
| v1.0.0 | Implement Profiles จริงใน Hermes — ทุก Department พร้อมใช้งาน |
