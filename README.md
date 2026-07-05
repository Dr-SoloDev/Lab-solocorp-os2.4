================================================================================
  ███████  ██████  ██      ██████  ██████  ██████  ██████  ██████  ██████
  ██      ██    ██ ██      ██   ██ ██   ██ ██   ██ ██   ██ ██   ██      ██
  ███████ ██    ██ ██      ██████  ██████  ██████  ██████  ██████   █████
       ██ ██    ██ ██      ██   ██ ██      ██   ██ ██   ██ ██           ██
  ███████  ██████  ███████ ██   ██ ██      ██   ██ ██   ██ ██      ██████

   ██████  ██████
  ██      ██    ██
   █████  ██    ██
       ██ ██    ██
  ██████   ██████
================================================================================
                     OPERATING SYSTEM  ===  VERSION 2.4
================================================================================

  [ SYSTEM ]  Department Architecture for AI Agents
  [ STATUS ]  Production Deployed     [ ENGINE ]  Hermes Agent Gateway
  [ PLATFORM ]  Hermes + OpenCode + Codex CLI
  [ LICENSE ]  Proprietary — SoloCorp Organization. All Rights Reserved.

================================================================================

What is SoloCorp OS?
================================================================================

SoloCorp OS is an **organizational operating system for AI agents** — a complete
Department Architecture that transforms a single AI into a coordinated workforce
of specialized departments, each with its own Head, team of sub-agents, defined
responsibilities, and clear chains of command.

Instead of a monolithic AI trying to do everything, SoloCorp OS gives you:

  - **15 Departments** — Each with a dedicated Head who owns outcomes
  - **46+ Specialist Agents** — Sub-agents who execute, not just advise
  - **Two-Tier Architecture** — Control flows through Heads; data flows
    autonomously through a Central Bus
  - **Head-to-Head Handoff** — Work moves between departments without
    bottlenecking on a single orchestrator

The architecture is inspired by how real companies scale: clear hierarchy,
delegated authority, and autonomous execution at every level.

Human  →  CEO  →  C-Level  →  Department Heads  →  Specialist Teams


================================================================================
Why SoloCorp OS?
================================================================================

Most AI agent systems suffer from the same problem: they can do everything
but nobody is responsible for anything. SoloCorp OS solves this with three
core principles:

  OWNERSHIP  ─  Every department has a Head who owns outcomes. No orphan
                 work, no ambiguous ownership, no passing the buck.

  DELEGATION ─  Department Heads do not work themselves. They lead.
                 Strategy, direction, escalation — not implementation.
                 Execution belongs to specialist sub-agents.

  ARCHITECTURE ─  Two-Tier design separates control flow (decisions,
                  approvals, status) from data flow (code, designs,
                  reports). Heads stay strategic; work moves fast.


================================================================================
Architecture
================================================================================

                    ┌──────────────────────────────────────┐
                    │           Dr.solodev (Human)          │
                    │             (Owner / Vision)          │
                    └──────────────────┬───────────────────┘
                                       │
                    ┌──────────────────▼───────────────────┐
                    │      CEO — เทอโบ ไชยศรีรัมย์            │
                    │   (Supreme AI Authority / Vision)     │
                    └──────┬──────┬──────┬─────────────────┘
                           │      │      │
              ┌────────────┘      │      └──────────────┐
              ▼                   ▼                     ▼
       ┌──────────┐       ┌──────────┐        ┌──────────────┐
       │ CFO      │       │ CMO      │        │ Orchestrator │
       │ meetoo   │       │ มาร์ค    │        │ พี่วุฒิ      │
       │ Finance  │       │Marketing │        │ Pipeline     │
       └──────────┘       └──────────┘        └──────┬───────┘
                                                      │
                              ┌───────────────────────┼───────────────────┐
                              │                       │                   │
                              ▼                       ▼                   ▼
                    ┌──────────────────┐    ┌──────────────────┐   ┌──────────┐
                    │ 05-Architect     │    │ 06-Product       │   │ 07-Eng   │
                    │ พี่ทรงศักดิ์      │    │ โปรดัค           │   │ ช่างฟูล  │
                    │ Central Bus      │    │ Roadmap / PRD    │   │ Code     │
                    └──────────────────┘    └──────────────────┘   └──────────┘
                    ┌──────────────────┐    ┌──────────────────┐   ┌──────────┐
                    │ 08-Design        │    │ 09-UI Designer   │   │ 10-QA    │
                    │ ครีเอท           │    │ UI Designer      │   │ QA-ทีม   │
                    │ UX / Brand       │    │ Interface        │   │ Testing  │
                    └──────────────────┘    └──────────────────┘   └──────────┘
                    ┌──────────────────┐    ┌──────────────────┐   ┌──────────┐
                    │ 11-Sales         │    │ 12-Support       │   │ 13-Legal │
                    │ เซลส์            │    │ ซัพพอร์ต         │   │ ตุลย์    │
                    │ B2B Pipeline     │    │ Customer Success │   │Compliance│
                    └──────────────────┘    └──────────────────┘   └──────────┘
                    ┌──────────────────┐    ┌──────────────────┐
                    │ 14-Web3          │    │ 15-Content       │
                    │ อัยวา            │    │ เสก              │
                    │ Blockchain/DeFi  │    │ Content/Creative │
                    └──────────────────┘    └──────────────────┘

Two-Tier Architecture (Control Layer vs Data Layer)

  ┌───────────────────────────────────────────────────────────────────────┐
  │                     CONTROL LAYER (Head-to-Head)                       │
  │                                                                        │
  │  Status, Goals, Exceptions, Approvals, Handoffs                        │
  │  "Work completed" / "Issue detected" / "Approval needed"               │
  │                                                                        │
  │  Head A ──────────(status/report)──────────→ Head B                    │
  │    ↑                                            ↑                      │
  │    │   Only what's necessary for coordination   │                      │
  └────┼────────────────────────────────────────────┼──────────────────────┘
       │                                            │
       ▼                                            ▼
  ┌───────────────────────────────────────────────────────────────────────┐
  │                      DATA LAYER (Autonomous)                          │
  │                                                                        │
  │  Code, Designs, Reports, Docs, Raw Outputs                             │
  │  → Central Bus / Shared State                                          │
  │                                                                        │
  │  Specialist A ──(write)──→  CENTRAL BUS  ──(notify)──→ Specialist B   │
  │                              ┌──────┐                                  │
  │                              │ Queue│                                  │
  │                              └──────┘                                  │
  │                                                                        │
  │  Heads only see: "Work Item X completed"                               │
  └───────────────────────────────────────────────────────────────────────┘


================================================================================
Badges / Status
================================================================================

  [ PLATFORM ]  Hermes Agent            [ VERSION ]  v0.6.1
  [ ENGINE  ]  Hermes Gateway          [ PROFILES ]  15 Departments
  [ RUNTIME ]  Loop Runner (Cron)      [ AGENTS   ]  46+ Specialists
  [ CLI     ]  OpenCode                [ COMMANDS ]  6 Pipeline Commands
  [ CODEX   ]  Codex CLI Subagents     [ SKILLS   ]  93 Integration Skills

  [ STATUS  ]  Foundation ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰ 100%  (v0.1-v0.5)
  [ STATUS  ]  Profiles   ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰ 100%  (v0.5-v0.5.1)
  [ STATUS  ]  Sub-Agents ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰ 100%  (v0.6.1)
  [ STATUS  ]  Central Bus ▰▰▰▰▰▰▰▰▰▰░░░░░░░░░░  50%  (v0.6)
  [ STATUS  ]  Dashboard  ▰▰▰▰▰▰▰░░░░░░░░░░░░░░  35%  (v0.7)


================================================================================
Quick Start
================================================================================

  # 1. Clone and enter the repository
  git clone https://github.com/Dr-SoloDev/Lab-solocorp-os2.4.git
  cd Lab-solocorp-os2.4

  # 2. Use with OpenCode (recommended)
  opencode

  # 3. Or use @mention to call a specific department head
  opencode "@architect-songsak design pipeline for new feature"
  opencode "@changful implement API endpoint for user registration"
  opencode "@cfo-meetoo วิเคราะห์งบ Q3"

  # 4. Or use with Codex CLI
  python3 scripts/export-codex-agents.py
  codex

  # 5. Run the pipeline
  opencode "/pipeline <feature-name>"

  # 6. Check system status
  opencode "/status"


================================================================================
The Full Team — 15 Department Heads + 46+ Specialist Agents
================================================================================

C-Level Executives
--------------------------------------------------------------------------------

  #01  CEO        เทอโบ (Turbo Chaisriram)     Vision / Strategy / Final Decision
       └── No direct sub-agents — commands through C-Level

  #02  CFO        meetoo                       Finance / Budget / Investment
       ├── Dana          — Bookkeeper & Controller
       ├── Riley         — FP&A Analyst
       └── Morgan        — Financial Analyst

  #03  CMO        มาร์ค                         Marketing / Content / Brand
       ├── Growth Hacker           — Growth loops, A/B testing, funnel optimization
       ├── Social Media Strategist — Brand authority, community building
       └── Content Creator         — SEO content, video scripts, editorial

System Pipeline
--------------------------------------------------------------------------------

  #04  Orchestrator  พี่วุฒิ (Wut)              Cross-Department Pipeline
       ├── Project Shepherd     — Multi-team project management
       ├── Studio Producer      — Creative portfolio management
       └── Studio Operations    — SOP design, vendor management

  #05  Architect     พี่ทรงศักดิ์ (Songsak)     Central Bus / Routing / Monitoring
       ├── Pipeline Auditor          — Audit trail, compliance check
       ├── Routing Config Agent      — Routing rules, circuit breaker
       ├── Monitor Watchdog          — Health probe, SLA tracking
       ├── Exception Triage Agent    — Auto-classification, RCA
       └── Cron Pipeline Agent       — Scheduled execution, retry queue

Product & Engineering
--------------------------------------------------------------------------------

  #06  Product       โปรดัค                     Feature Roadmap / PRD / Delivery
       ├── Alex (Product Manager)     — Lifecycle from discovery to launch
       ├── Product Feedback Synthesizer — Multi-channel feedback analysis
       └── Product Sprint Prioritizer  — Agile planning, dependency management

  #07  Engineering   ช่างฟูล                     Backend / Frontend / Architecture
       ├── สถาปนิกแบ็กเอนด์           — Scalable backend, database, API
       ├── นักพัฒนาอาวุโส             — Full-stack, Laravel, Livewire, Three.js
       └── สถาปนิกซอฟต์แวร์          — Domain-driven design, microservices

  #08  Design        ครีเอท                      UX Research / Brand Visual
       ├── นักวิจัย UX               — Usability testing, behavioral research
       ├── สถาปนิก UX                — Design systems, layout frameworks
       └── นักออกแบบ UI              — Visual design, WCAG AA, design tokens

  #09  UI Designer   UI Designer                Interface / Component Library
       ├── UI Designer              — Pixel-perfect visual design system
       ├── UX Architect             — CSS design system, component hierarchy
       └── UX Researcher            — Quantitative UX research, usability testing

Quality & Testing
--------------------------------------------------------------------------------

  #10  QA            QA-ทีม                      Testing / Quality / Evidence
       ├── API Tester               — Functional, performance, security testing
       ├── Accessibility Auditor    — WCAG 2.2 compliance, assistive technology
       └── Test Results Analyzer    — Statistical modeling, go/no-go decisions

Revenue & Customer
--------------------------------------------------------------------------------

  #11  Sales         เซลส์                       B2B Deal Strategy / Pipeline
       ├── Deal Strategist         — MEDDPICC qualification, competitive positioning
       ├── Pipeline Analyst        — Revenue operations, forecast accuracy
       └── Outbound Strategist     — Signal-based prospecting, reply rate

  #12  Support       ซัพพอร์ต                   Customer Success / Analytics
       ├── Support Responder       — First-contact resolution, 2-hour SLA
       ├── Analytics Reporter      — KPI dashboards, customer segmentation
       └── Executive Summary Generator — SCQA framework, executive-ready

Legal & Compliance
--------------------------------------------------------------------------------

  #13  Legal         ตุลย์                        Law / Compliance / Contracts
       ├── Compliance Auditor      — SOC 2, ISO 27001, HIPAA, PCI-DSS
       ├── Legal Document Review   — Contract review, risk assessment
       └── Legal Client Intake     — Conflict check, case data collection

Blockchain & Content
--------------------------------------------------------------------------------

  #14  Web3          อัยวา                       Blockchain / DeFi / Solana
       ├── Smart Contract Engineer     — Solidity/Anchor, gas optimization
       ├── Blockchain Security Auditor — Manual audit, Slither/Mythril/Echidna
       ├── DeFi Protocol Analyst       — Tokenomics, on-chain analytics
       └── Solana Developer            — Anchor programs, Web3.js

  #15  Content       เสก                         Content / Creative / Media
       Creator
       ├── References 10 specialist profiles from agency-agents library
       ├── Platforms: LinkedIn, TikTok, Instagram, YouTube, Reddit
       ├── Skills: gen-image, video-use, content production
       └── Full creative pipeline from concept to distribution


================================================================================
OpenCode Agents
================================================================================

SoloCorp OS ships with a complete OpenCode configuration and 20 agent
definitions — 15 department heads plus 5 architect pipeline specialists.

  .opencode/
  ├── agents/             20 agents
  │   ├── ceo-turbo.md              CEO (default agent)
  │   ├── cfo-meetoo.md             CFO
  │   ├── cmo-mark.md               CMO
  │   ├── orchestrator-wut.md       Orchestrator
  │   ├── architect-songsak.md      Architect
  │   ├── product-produck.md        Product
  │   ├── engineering-changful.md   Engineering
  │   ├── design-kreet.md           Design
  │   ├── ui-designer.md            UI Designer
  │   ├── qa.md                     QA
  │   ├── sales.md                  Sales
  │   ├── support.md                Support
  │   ├── legal-tulya.md            Legal
  │   ├── web3-aywa.md              Web3
  │   ├── content-creator-sek.md    Content Creator
  │   ├── pipeline-auditor.md       Pipeline Auditor (Architect)
  │   ├── routing-config-agent.md   Routing Config (Architect)
  │   ├── monitor-watchdog.md       Monitor Watchdog (Architect)
  │   ├── exception-triage.md       Exception Triage (Architect)
  │   └── cron-pipeline.md          Cron Pipeline (Architect)
  ├── commands/            SoloCorp workflow commands
  └── skills/              93 skills (Symlink to Hermes)

Usage:

  # Default = CEO (เทอโบ) — routes to the right department
  opencode

  # @mention a department head directly
  opencode "@architect-songsak ออกแบบ pipeline สำหรับ feature ใหม่"
  opencode "@changful implement API endpoint for user registration"
  opencode "@cfo-meetoo วิเคราะห์งบ Q3"
  opencode "@qa review test results for sprint 5"

Built-in Pipeline Commands:

  /pipeline <feature>    Run the SoloCorp pipeline full cycle
  /handoff <from> <to>   Structured handoff between departments
  /status                View overall pipeline health
  /audit [scope]         Inspect audit trail
  /deploy                Deploy profiles and config
  /brain <context>       Save session to brain memory


================================================================================
Codex CLI Subagents
================================================================================

All SoloCorp profiles can be exported as Codex CLI custom sub-agents:

  # Export all agents
  python3 scripts/export-codex-agents.py

  # Validate only (no export)
  python3 scripts/export-codex-agents.py --validate-only

  # Start Codex and spawn the agents you need
  codex

Full usage guide: `dist/codex/README-CODEX-CLI.md`


================================================================================
Profile Order (Hermes Gateway)
================================================================================

  #   Profile Directory      Name                    Status
  --  ---------------------  ----------------------  ------
  01  01-ceo                 เทอโบ CEO               Active
  02  02-cfo                 meetoo                  Active
  03  03-cmo                 มาร์ค                   Active
  04  04-orchestrator        พี่วุฒิ (Wut)           Active
  05  05-architect           พี่ทรงศักดิ์             Active
  06  06-product             โปรดัค                  Active
  07  07-engineering         ช่างฟูล                 Active
  08  08-design              ครีเอท                  Active
  09  09-ui-designer         UI-Designer             Active
  10  10-qa                  QA-ทีม                  Active
  11  11-sales               เซลส์                   Active
  12  12-support             ซัพพอร์ต                Active
  13  13-legal               ตุลย์                   Active
  14  14-web3                อัยวา                   Active
  15  15-content-creator     เสก                    Active
  --  default                Fallback                Active


================================================================================
Development Status
================================================================================

  Phase                          Content                                  Status
  ------------------------------  --------------------------------------  ------
  Foundation (v0.1-v0.2)          ADRs + CEO Profile + Architecture       Complete
  Pipeline Agents (v0.3)          Architect team — 5 pipeline agents      Complete
  Department Profiles (v0.5)      15 Department Heads + Teams             Complete
  Deploy to Hermes (v0.5.1)       All profiles deployed to Hermes         Complete
  Sub-agent Teams (v0.6.1)        42 specialist agents deployed           Complete
  Central Bus (v0.6)              Central Bus Agent + Context Optimizer   In Design
  Dashboard + Compliance (v0.7)   Pipeline Dashboard + QA Gate            Planned
  Loop Runner (v0.5+)             Cron auto-pilot running every 30 min    Active


================================================================================
Documentation
================================================================================

  ARCHITECTURE.md        System architecture, design principles, flow
  PROJECT.md             Getting started guide (for newcomers)
  profiles/INDEX.md      Index of all 15 department profiles
  CHANGELOG.md           Version history and release notes
  decisions/             Architecture Decision Records (ADRs)
  dist/codex/            Codex CLI export guide


================================================================================
  SoloCorp OS — System First, Everything Follows

  Proprietary software (c) SoloCorp Organization. All Rights Reserved.
  Built by Dr.SoloDev & เทอโบ ไชยศรีรัมย์
================================================================================
