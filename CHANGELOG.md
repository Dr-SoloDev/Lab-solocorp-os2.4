# Lab-solocorp-os2.4 — Changelog

> Version history for SoloCorp OS Department Architecture
> Format: SemVer | Date: YYYY-MM-DD

---

## v0.6.1 (2026-06-30)

### Changed
- **ภาษาไทยทุก profile** — เพิ่ม directive "สื่อสารภาษาไทย" ใน SOUL.md ทุก profile
  - Profile: 06-product, 07-engineering, 08-design, 09-ui-designer, 10-qa,
    11-sales, 12-support, 15-content-creator
  - Agent: hermes-sales, hermes-support, hermes-ui-designer
  - 02-cfo: เพิ่ม metadata "ภาษา: ไทย primary"
- **Model alignment** — Sync model/provider ในทุก profile SOUL.md
  - Qwen 3.7 Max -> DeepSeek V4 Pro / GLM-5.2 / Minimax M3 ตาม tier
  - `maxplus` -> `custom:maxplus-codex`
- **Main config:** `display.language: en` -> `th`
- **README.md:** Fix hierarchy tree — 15-content-creator เป็น sibling ไม่ใช่ child ของ 14-web3
- **INDEX.md:** Add 15-content-creator to Department Heads table

### MoA
- เพิ่ม `default_preset: strategist-moa`
- Tier-based presets: S=strategist-moa, A=architect-moa, B=creator-moa, C=swift-moa
- อัปเกรด architect-moa -> Kimi K2.7 Code
- เพิ่ม moa-creator, moa-swift, moa-default, moa-strategist aliases

---

## v0.6.0 (2026-06-30)

### Added
- **15-content-creator "เสก"** — แผนก Content Creation รับผิดชอบงานภาพ/สื่อ/เนื้อหาทุกประเภท
  - Profile: `15-content-creator` (qwen3.7-max, tier S/B)
  - Head SOUL: `hermes-content/SOUL.md`
  - 10 sub-agent references จาก agency-agents
  - Shared skills: `gen-image`, `video-use`
- **LICENSE** — Custom license (SoloCorp Organization — All Rights Reserved)
- **scripts/ + loop_runner/** — Sanitized absolute paths -> relative/env-var

### Changed
- README.md: Hierarchy + profile table -> 15 profiles
- CLAUDE.md: Department routing -> เพิ่ม Content Creator (เสก)

---

## v0.5.2 (2026-06-30)

### Changed
- **Migrate to Free Pool (VIP3)** — เปลี่ยน API Key จาก pool deepseek -> pool free
  - Key "เฮอเมส" — base_url: `/v1/`, ราคาถูกกว่า Chinese pool 4-13x
  - qwen3.7-max: $0.28/M (จากเดิม $3.75 — ถูก 13x!)
- **Model Mapping ปรับใหม่** ตามราคา Free Pool จริง:
  - CEO, CFO, Architect, Engineering, Web3, Legal -> `deepseek-v4-pro` ($0.87)
  - CMO, Product, Design, UI-Designer, Orchestrator, Sales -> `qwen3.7-max` ($0.28)
  - QA, Support -> `deepseek-v4-flash` ($0.28)

### Cost Impact
- ก่อน: ~$50-80/เดือน (Chinese Pool 16x)
- หลัง: ~$10-20/เดือน (Free Pool VIP3)
- Credit คงเหลือ: $1,080 — เพียงพอ 50-100 เดือน

---

## v0.5.1 (2026-06-30)

### Added
- **Deploy 14 profiles สู่ Hermes** — ทุก Department Profile มี config.yaml, routing.yaml, skills/ ครบถ้วน
  - 01-ceo -> 14-web3 พร้อมใช้งานใน Hermes Gateway
  - Web3 skills: solana-dev reference docs (Anchor, Surfpool, security guides)
  - .gitignore: Python/venv/build/Hermes artifacts
- **pipeline_executor loop** — `loop_runner/loops/pipeline_executor.py`
- **scripts/** — `build-profiles.py`, `pipeline_until_score.py`
- **tests/** — Phase test suites 1-4

### Changed
- เอกสารทั้งหมดอัปเดตสถานะ: Design -> Deployed
- ARCHITECTURE.md: ซ่อมลิงก์ตาย `profiles/architect/` -> `profiles/05-architect/`
- README.md: Profiles status อัปเดต, เพิ่ม Phase "Deploy to Hermes" และ "Loop Runner"
- PROJECT.md: File tree สะท้อนโครงสร้างจริง (loop_runner/, scripts/, tests/)
- CHANGELOG.md Roadmap: v1.0.0 "Implement in Hermes" สำเร็จแล้ว

### Fixed
- OpenCode-Zen proxy config ถูกลบ (proxy ล่ม ใช้ MaxPlus แทน)
- session-state-backup cron กลับมาทำงาน正常 (401 resolved)

---

## v0.5.0 (2026-06-28)

### Added
- **Loop Engineering infrastructure** (inspired by cobusgreyling/loop-engineering)
  - `loop_runner/state.py` — SQLite persistent state
  - `loop_runner/runner.py` — base Loop class with failure tracking
  - `loop_runner/loops/daily_brief.py` — L1: CEO morning brief
  - `loop_runner/loops/subscription_audit.py` — L4: CFO monthly subscription scan
  - `loop_runner/loops/brain_auto_commit.py` — L4: auto-commit brain files
  - `loop_runner/main.py` — cron entry point (`*/30 * * * *`)
- **Central Bus Open Design bridge** — Read-only bridge to Open Design (port 41551)
  - `central_bus/open_design.py` — Department permission guard
  - `bus/system/open_design_config.json` — dept-to-tools mapping
- **14-web3 — อัยวา (Head of Web3 & DeFi)** — `profiles/14-web3/SOUL.md`
  - Identity: อัยวา — Head of Web3 & DeFi, รายงานตรงต่อ CEO
  - 3 Pillars: ไม่ทำงานเอง, Security First, Ownership Mindset
  - Rules: Security audit ก่อน deploy, on-chain decisions ผ่าน CFO
- **ทีมของอัยวา — 4 Web3 Specialist Profiles:**
  - Smart Contract Engineer (Solidity/Anchor, gas optimization)
  - Blockchain Security Auditor (Slither/Mythril/Echidna)
  - DeFi Protocol Analyst (tokenomics, on-chain analytics)
  - Solana Developer (Anchor programs, Web3.js)
- **Sync 13 Department Profiles** จาก Hermes — SOUL.md สำหรับทุก Department Head
- **ทีมของทุกแผนก** — Operational Team Agents ใน 11 แผนก
- **INDEX.md** — เพิ่ม Section ทีมทุกแผนก + ลิงก์ครบ 14 Department

### Fixed
- `daily_brief` loop parser: fallback finance/brain scripts return Thai text — switched to regex extraction
- Runway critical alert: triggers เมื่อ runway < 6 months

### Cleared
- Finance DB reset (test data removed)

### Changed
- Agent names sync ให้ตรงกับ Hermes: CFO=meetoo, CMO=มาร์ค, Legal=ตุลย์
- เอกสารทั้งหมดแปลเป็นภาษาไทย

---

## v0.4.0 (2026-06-27)

### Changed
- **Rename Orchestration -> Architect** — เปลี่ยนชื่อแผนกจาก Orchestration เป็น Architect
  - โฟลเดอร์: `profiles/orchestration/` -> `profiles/architect/`
  - Head Profile: `01-head-of-orchestration.md` -> `01-head-of-architect.md`
  - อัปเดตทุก internal link ใน INDEX.md, ARCHITECTURE.md, SOUL.md
  - ล้างไฟล์ต้นทางโฟลเดอร์ `orchestration/` และ `profiles/01-head-of-orchestration.md`

---

## v0.3.0 (2026-06-26)

### Added
- **ทีมของพี่ทรงศักดิ์ — 5 Pipeline Agent Profiles** `profiles/architect/phee-thongsak/team/`
  - Pipeline Auditor — GNAP Audit Trail + Compliance Checker
  - Routing Config Agent — GNAP Routing + MagiC Circuit Breaker
  - Monitor Watchdog — Health Probe + SLA Tracking + Dashboard
  - Exception Triage Agent — AXME Classification + RCA + Auto-Resolve
  - Cron Pipeline Agent — Temporal Durable Execution + n8n Workflows
- **ARCHITECTURE.md** — แผนผังทีม + ลิงก์ profiles
- **profiles/INDEX.md** — เพิ่ม 5 Profile ใหม่ในทีม

### Protocols ที่ถูกตกผลึกในระบบ

| Protocol | ใช้ใน | ประโยชน์ |
|:---------|:------|:---------|
| GNAP | Pipeline Auditor + Routing Config Agent | Git-Native Audit Trail + Routing Registry |
| MagiC | Routing Config Agent + Exception Triage Agent | Circuit Breaker 3 States |
| model-watchdog | Monitor Watchdog | Health Probe + Auto-Rollback |
| TeamHero | Monitor Watchdog | Dashboard Metric Format |
| AXME | Exception Triage Agent | Exception Classification |
| Temporal | Cron Pipeline Agent | Durable Execution + Retry Queue |
| n8n | Cron Pipeline Agent | Workflow Node-Based Automation |

---

## v0.2.0 (2026-06-26)

### Added
- **Head of Architecture Profile** — First complete Department Head design
  - Identity: พี่ทรงศักดิ์ (Songsak)
  - 3 Pillars Compliance, Two-Tier Architecture
  - 3 Functions: Goal Alignment, Orchestration, Exception Handling
  - Central Bus Ownership, Pipeline Design Rules
- **Central Bus Schema + Protocol** — ADR-003 (586 บรรทัด)
  - JSON Schema: departments_state (9 แผนก) + routing rules
  - Handoff Protocol Template สำหรับทุก Department Head
  - Pipeline Design Rules

### Changed
- ARCHITECTURE.md: Profile #01 จาก Design เป็น Complete

---

## v0.1.0-draft (2026-06-26)

### Added
- **Foundation Architecture Design:**
  - 3 Pillars: Head doesn't work, Leadership Skills, Ownership Mindset
  - Two-Tier Architecture: Control Layer vs Data Layer
  - Head-to-Head direct handoff (80%), Escalate (5%)
- **Project Structure:**
  - ARCHITECTURE.md, CHANGELOG.md, decisions/ADRs, profiles/

### Reference
- Google AI — Two-Tier Architecture & Central Bus insight
- `agency-agents` repo — 411 agent templates, 18 categories
- Skill Inventory — 187 skills ในระบบ Hermes

---

## Roadmap

| Version | Focus | Status |
|:--------|:------|:------:|
| v0.1 | Foundation Architecture + CEO Profile | Complete |
| v0.2 | Architect Head Profile + Central Bus Schema | Complete |
| v0.3 | Pipeline Agents (Architect team — 5 agents) | Complete |
| v0.4 | Rename Orchestration -> Architect | Complete |
| v0.5 | 14 Department Profiles + Teams + Loop Runner + Web3 | Complete |
| v0.5.1 | Deploy All Profiles to Hermes Gateway | Complete |
| v0.5.2 | Free Pool Migration + Model Optimization | Complete |
| v0.6.0 | Content Creator Department (15th profile) | Complete |
| v0.6.1 | Thai Language Alignment + MoA Presets | Complete |
| **v0.6** | **Central Bus Agent + Context Optimizer** | **Next** |
| **v0.7** | **Pipeline Dashboard + Compliance Gate** | **Planned** |
| **v1.0** | **Production-ready Release** | **Planned** |

---

*SoloCorp OS — System First, Everything Follows*
