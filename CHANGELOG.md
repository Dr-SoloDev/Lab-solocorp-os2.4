# Lab-solocorp-os2.4 — Changelog

> เวอร์ชั่นของระบบ Department Architecture สำหรับ SoloCorp OS

---

## v0.6.1 (2026-06-30)

### Changed
- **ภาษาไทยทุก профиль** — เพิ่ม directive "สื่อสารภาษาไทย" ใน SOUL.md ทุก profile
  - Profile: 06-product, 07-engineering, 08-design, 09-ui-designer, 10-qa, 11-sales, 12-support, 15-content-creator
  - Agent: hermes-sales, hermes-support, hermes-ui-designer (+ ภาษาไทย in communication style)
  - 02-cfo: เพิ่ม metadata "ภาษา: ไทย primary"
- **Model alignment** — Sync model/provider ในทุก profile SOUL.md
  - Qwen 3.7 Max → DeepSeek V4 Pro / GLM-5.2 / Minimax M3 ตาม tier
  - `maxplus` → `custom:maxplus-codex`
- **Main config:** `display.language: en` → `th`
- **README.md:** Fix hierarchy tree — 15-content-creator เป็น sibling ไม่ใช่ child ของ 14-web3
- **INDEX.md:** Add 15-content-creator to Department Heads table

### MoA
- เพิ่ม `default_preset: strategist-moa`
- Tier-based presets: S=strategist-moa, A=architect-moa, B=creator-moa, C=swift-moa
- อัปเกรด architect-moa → Kimi K2.7 Code
- เพิ่ม moa-creator, moa-swift, moa-default, moa-strategist aliases

---

## v0.6.0 (2026-06-30)

### Added
- **15-content-creator "เสก"** — แผนก Content Creation รับผิดชอบงานภาพ/สื่อ/เนื้อหาทุกประเภท
  - Profile: `15-content-creator` (qwen3.7-max, tier S/B)
  - Head SOUL: `hermes-content/SOUL.md` (brief intake, team structure, platform playbook)
  - 10 sub-agent references จาก agency-agents (content, social, twitter, tiktok, video, growth, trend, design)
  - Shared skills: `gen-image` (MaxPlus GPT Image API), `video-use` (video editing)
- **LICENSE** — Custom license (SoloCorp Organization — All Rights Reserved)
- **scripts/ + loop_runner/** — Sanitized absolute paths → relative/env-var

### Changed
- README.md: Hierarchy + profile table → 15 profiles
- CLAUDE.md: Department routing → เพิ่ม Content Creator (เสก)

---

## v0.5.2 (2026-06-30)

### Changed
- **Migrate to Free Pool (VIP3)** — เปลี่ยน API Key จาก pool deepseek → pool free
  - Key "เฮอเมส" — base_url: `/v1/`, ราคาถูกกว่า Chinese pool 4-13x
  - qwen3.7-max: $0.28/M (จากเดิม $3.75 🔥 ถูก 13x!)
- **Model Mapping ปรับใหม่** ตามราคา Free Pool จริง:
  - CEO, CFO, Architect, Engineering, Web3, Legal → `deepseek-v4-pro` ($0.87)
  - CMO, Product, Design, UI-Designer, Orchestrator, Sales → `qwen3.7-max` ($0.28)
  - QA, Support → `deepseek-v4-flash` ($0.28)

### Cost Impact
- ก่อน: ~$50-80/เดือน (Chinese Pool 16×)
- หลัง: ~$10-20/เดือน (Free Pool VIP3)
- Credit คงเหลือ: $1,080 — เพียงพอ 50-100 เดือน

---

## v0.5.1 (2026-06-30)

### Added
- **Deploy 14 profiles สู่ Hermes** — ทุก Department Profile มี config.yaml, routing.yaml, skills/ ครบถ้วน
  - `01-ceo` → `14-web3` พร้อมใช้งานใน Hermes Gateway
  - Web3 skills: solana-dev reference docs (Anchor, Surfpool, security guides)
  - .gitignore: 完善 Python/venv/build/Hermes artifacts
- **pipeline_executor loop** — `loop_runner/loops/pipeline_executor.py` สำหรับคุม pipeline queue
- **scripts/** — `build-profiles.py`, `pipeline_until_score.py`
- **tests/** — Phase test suites 1–4

### Changed
- เอกสารทั้งหมดอัปเดตสถานะ: Design → **Deployed** 🟢
- ARCHITECTURE.md: ซ่อมลิงก์ตาย `profiles/architect/` → `profiles/05-architect/`
- README.md: Profiles status 🟡→🟢, เพิ่ม Phase "Deploy to Hermes" และ "Loop Runner"
- PROJECT.md: File tree สะท้อนโครงสร้างจริง (loop_runner/, scripts/, tests/)
- CHANGELOG.md Roadmap: v1.0.0 "Implement in Hermes" สำเร็จแล้ว

### Fixed
- OpenCode-Zen proxy config ถูกลบ (proxy ล่ม ใช้ MaxPlus แทน)
- session-state-backup cron กลับมาทำงาน正常 (401 resolved)

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

| เวอร์ชั่น | สิ่งที่จะทำ | สถานะ |
|:---------|:-----------|:-----:|
| v0.1–0.2 | Foundation + ADRs + Architecture | ✅ |
| v0.3 | Pipeline Agents (พี่ทรงศักดิ์ team) | ✅ |
| v0.4 | Rename Orchestration → Architect | ✅ |
| v0.5 | 14 Department Profiles + Teams Design | ✅ |
| **v0.5.1** | **Deploy ทั้งหมดสู่ Hermes + เอกสารปัจจุบัน** | **🟢 Done** |
| v0.6 | Central Bus Agent + Context Optimizer | 🔴 Next |
| v0.7 | Pipeline Dashboard + Compliance Gate | ⏳ |
| v1.0 | Production-ready | ⏳ |

## v0.5.2 (2026-06-30)

### Changed
- **Free Pool Migration** — สลับ API Key จาก deepseek pool → Free Pool (VIP3)
  - Key "เฮอเมส" — pool: free, base_url: `/v1/`
  - qwen3.7-max ราคา $0.28/M (ถูกกว่า Chinese pool 13x!)
- **Model Optimization ครั้งใหญ่** — ใช้ Free Pool ราคาจริง:
  - CEO, CFO, Architect, Engineering, Web3, Legal → `deepseek-v4-pro` ($0.87)
  - CMO, Product, Design, UI-Designer, Orchestrator, Sales → `qwen3.7-max` ($0.28)
  - QA, Support → `deepseek-v4-flash` ($0.28)

### Cost Impact
- ก่อน: ~$50-80/เดือน (Chinese Pool 16×)
- หลัง: ~$10-20/เดือน (Free Pool VIP3)
- Credit คงเหลือ: $1,080 — ใช้ได้ 50-100 เดือน
