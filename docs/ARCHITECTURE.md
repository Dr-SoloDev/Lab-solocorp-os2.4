# Lab-solocorp-os2.4 — Architecture Overview

> **ขอบเขตและสถานะ:** เอกสารนี้อธิบายโครงสร้าง organization/agent และ Central Bus ที่มีอยู่ ส่วน product architecture เป้าหมายของ local-first SoloCorp App, CEO session, MCP registry และ task workflow ให้ยึด [`docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md`](prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md). การประสาน Head-to-Head ภายในแผนกยังใช้ได้; การรับ brief จากมนุษย์และ route งานใน App เป็นอีก flow หนึ่ง. Primary product direction = PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0 (local-first SoloCorp App, MVP = 1 CEO + department MCPs + registry + task queue; app shell/registry/provider flow still **NOT IMPLEMENTED**). Content Creator Pack Phase 1–3 evidence and Concat host status (enabled + handshake verified 2026-11-07, render not yet proven): see §Content Creator Pack below + [`decisions/ADR-032-concat-host-2026-11-07.md`](../decisions/ADR-032-concat-host-2026-11-07.md) (amended). Counts source of truth: README §What is actually in the tree (verified 2026-11-07: 20 profile dirs, 21 agent files) — §Department Profiles counts below (2026-09-27) are historical.

> System Architecture for SoloCorp OS
> Designed: 2026-06-26 | Last Updated: 2026-11-07 | Version: 2.4

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Three Pillars of Department Head Design](#three-pillars-of-department-head-design)
3. [Two-Tier Architecture](#two-tier-architecture)
4. [Hierarchy & Chain of Command](#hierarchy--chain-of-command)
5. [Department Profiles (19)](#department-profiles)
6. [Specialist Sub-Agents (62+)](#specialist-sub-agents)
7. [Communication Protocols](#communication-protocols)
8. [Loop Runner](#loop-runner) (4 Loops)
9. [Agent Worker Service](#agent-worker-service)
10. [LLM Provider](#llm-provider)
11. [Open Design Integration](#open-design-integration) (Deprecated)
12. [Content Creator Pack — Local Video Pipeline](#content-creator-pack--local-video-pipeline-phase-13-2026-11-07)
13. [Key Design Decisions](#key-design-decisions)

---

## Design Principles

The SoloCorp OS architecture is governed by these core principles:

**Principle 1: Heads Lead, Agents Execute**

Department Heads are leaders, not doers. They set direction, make decisions,
and manage exceptions. Execution is delegated to specialist sub-agents. A
Head who is writing code or designing screens is a system failure.

**Principle 2: Head-to-Head Communication**

When work needs to move between departments, the transfer happens between
Heads directly — not through a central orchestrator. This eliminates the
single-point-of-failure bottleneck. 80% of handoffs are direct; only 5%
require escalation.

**Principle 3: Two-Tier Separation**

Control flow (decisions, status, approvals) and data flow (code, designs,
reports) are architecturally separated. Heads work in the Control Layer;
sub-agents work in the Data Layer through the Central Bus.

**Principle 4: Ownership at Every Level**

Every piece of work has a named owner at every stage. There is no orphan
work, no "not my job," and no ambiguity about who is responsible.

**Principle 5: Autonomous Execution**

Once a Head delegates a task, the work executes autonomously. The Head is
notified on completion or when an exception occurs. Otherwise, the system
runs itself.

**Principle 6: Audit Everything**

Every handoff, every decision, every status change is logged to the audit
trail. The Pipeline Auditor ensures compliance and traceability.

---

## Three Pillars of Department Head Design

Every Department Head profile in SoloCorp OS is built on three
non-negotiable pillars:

```
  ┌────────────────────────────────────────────────────────────┐
  │                                                             │
  │    PILLAR 1:  Do Not Work Yourself                          │
  │               (Delegate, Not Do)                            │
  │                                                             │
  │    The Head's job is to lead — not to implement.            │
  │    Delegate everything except: strategy, decisions,         │
  │    escalations, and cross-department handoffs.              │
  │                                                             │
  ├────────────────────────────────────────────────────────────┤
  │                                                             │
  │    PILLAR 2:  Leadership & Management Skills                │
  │               (บริหารแผนก)                                   │
  │                                                             │
  │    Every Head must master: delegation, team management,     │
  │    cross-department communication, strategic thinking,      │
  │    and escalation handling.                                 │
  │                                                             │
  ├────────────────────────────────────────────────────────────┤
  │                                                             │
  │    PILLAR 3:  Ownership Mindset                             │
  │               (เจ้าของแผนก ไม่ใช่ลูกจ้าง)                     │
  │                                                             │
  │    Heads own outcomes — not tasks. Quality, delivery,       │
  │    team health, and continuous improvement are theirs.      │
  │    There is no "that's not my job."                         │
  │                                                             │
  └────────────────────────────────────────────────────────────┘
```

---

## Two-Tier Architecture

The most important architectural decision in SoloCorp OS: control and data
are separate layers.

### Control Layer (Head-to-Head)

This layer carries status, goals, exceptions, approvals, and handoffs.
It is deliberate communication between Department Heads — structured,
minimal, and purposeful.

```
  ┌────────────────────────────────────────────────────────────────┐
  │                    CONTROL LAYER                               │
  │                    (ผ่านหัวหน้า — Head-to-Head)                  │
  │                                                                │
  │  What flows: Status, Goals, Exceptions, Approvals, Handoffs    │
  │  Examples: "Work completed" / "Issue detected" / "Approval"    │
  │                                                                │
  │  ┌────────┐         ┌────────┐         ┌────────┐             │
  │  │ Head A │──(1)──→│ Head B │──(2)──→│ Head C │             │
  │  └────────┘         └────────┘         └────────┘             │
  │       ↑                                        ↑              │
  │       │  Minimal. Only what's needed.           │              │
  │       │  80% direct, 15% via Orchestrator,      │              │
  │       │  5% escalate to CEO                     │              │
  └───────┼────────────────────────────────────────┼──────────────┘
          │                                        │
          ▼                                        ▼
```

### Data Layer (Autonomous via Central Bus)

This layer carries code, designs, reports, documents, and raw outputs.
It flows autonomously through the Central Bus — Heads never pass files.

```
  ┌────────────────────────────────────────────────────────────────┐
  │                     DATA LAYER                                 │
  │                     (Auto — ไม่ผ่านหัวหน้า)                      │
  │                                                                │
  │  What flows: Code, Designs, Reports, Docs, Raw Outputs         │
  │  Medium: Central Bus / Shared State                            │
  │                                                                │
  │  ┌────────────┐    ┌──────────────┐    ┌────────────┐         │
  │  │ Specialist │──→│ CENTRAL BUS  │──→│ Specialist │         │
  │  │ Agent A    │    │              │    │ Agent B    │         │
  │  └────────────┘    │  ┌────────┐  │    └────────────┘         │
  │                    │  │ Queue  │  │                            │
  │                    │  └────────┘  │                            │
  │                    │  ┌────────┐  │                            │
  │  ┌────────────┐    │  │ Audit  │  │    ┌────────────┐         │
  │  │ Specialist │──→│  │ Trail  │  │──→│ Specialist │         │
  │  │ Agent C    │    │  └────────┘  │    │ Agent D    │         │
  │  └────────────┘    └──────────────┘    └────────────┘         │
  │                                                                │
  │  Heads only see: "Work Item X completed ✓"                     │
  │  No file passing. No status meetings. No bottlenecks.          │
  └────────────────────────────────────────────────────────────────┘
```

### Why Two-Tier?

| Aspect | Without Two-Tier | With Two-Tier |
|:-------|:-----------------|:--------------|
| **Velocity** | Blocked by Head availability | Work flows autonomously 24/7 |
| **Scalability** | Heads become bottlenecks | Heads stay strategic |
| **Resilience** | Head failure stops department | Sub-agents keep executing |
| **Audit** | Manual, inconsistent | Central Bus logs everything |
| **Context** | Heads drown in detail | Heads see only what matters |

---

## Hierarchy & Chain of Command

```
  Dr.solodev (Human / Owner)
    └── CEO (เทอโบ — Supreme AI Authority / Vision)
         ├── CFO (meetoo — Finance / Budget)
         ├── CMO (มาร์ค — Marketing / Content / Brand)
         └── Orchestrator (พี่วุฒิ — System Pipeline Coordination)
               └── Department Heads (05-19)
                     ├── 05-Architect (พี่ทรงศักดิ์)
                    ├── 06-Product (โปรดัค)
                    ├── 07-Engineering (ช่างฟูล)
                    ├── 08-Design (ครีเอท)
                    ├── 09-UI Designer
                    ├── 10-QA (QA-ทีม)
                    ├── 11-Sales (เซลส์)
                    ├── 12-Support (ซัพพอร์ต)
                    ├── 13-Legal (ตุลย์)
                    ├── 14-Web3 (อัยวา)
                    ├── 15-Content Creator (เสก)
                    ├── 16-Network Engineer (นีต)
                     ├── 17-Cyber Security (ซาย)
                     ├── 18-Psychology (จิต)
                     └── 19-R&D Lab (Lead Researcher)
```

**Communication Flow Rules:**

| Rule | Description |
|:-----|:------------|
| Human → CEO | Human speaks only through CEO |
| CEO → C-Level | CEO commands CFO, CMO, Orchestrator |
| C-Level → Heads | Orchestrator coordinates all Department Heads |
| Head → Head | Direct handoff for cross-department work (80%) |
| Head → Agent | Head delegates execution to specialist sub-agents |
| Agent → Head | Agent reports completion or exceptions only |
| Agent → Agent | NEVER direct — always through Central Bus |

---

## Department Profiles

### C-Level (01-04)

| # | Profile | Head | Responsibility | Status |
|:-:|:--------|:-----|:--------------|:------:|
| 01 | CEO | เทอโบ (Turbo Chaisriram) | Vision, Strategy, Final Decision | Active |
| 02 | CFO | meetoo | Finance, Budget, Investment | Active |
| 03 | CMO | มาร์ค | Marketing, Content, Brand | Active |
| 04 | Orchestrator | พี่วุฒิ (Wut) | System Pipeline Coordination | Active |

### Department Heads (05-19)

| # | Profile | Head | Responsibility | Status |
|:-:|:--------|:-----|:--------------|:------:|
| 05 | Architect | พี่ทรงศักดิ์ | Central Bus, Routing, Monitoring | Active |
| 06 | Product | โปรดัค | Feature Roadmap, PRD, Delivery | Active |
| 07 | Engineering | ช่างฟูล | Backend, Frontend, Architecture | Active |
| 08 | Design | ครีเอท | UX Research, Brand Visual | Active |
| 09 | UI Designer | UI Designer | Interface, Component Library | Active |
| 10 | QA | QA-ทีม | Testing, Quality, Evidence | Active |
| 11 | Sales | เซลส์ | B2B Deal Strategy, Pipeline | Active |
| 12 | Support | ซัพพอร์ต | Customer Success, Analytics | Active |
| 13 | Legal | ตุลย์ | Compliance, Contracts, Law | Active |
| 14 | Web3 | อัยวา | Blockchain, DeFi, Solana | Active |
| 15 | Content Creator | เสก | Content, Creative, Media | Active |
| 16 | Network Engineer | นีต | Network, Infrastructure, VPN, CDN, DNS | Active |
| 17 | Cyber Security | ซาย | Threat Detection, Incident Response | Active |
| 18 | Psychology | จิต | User Behavior, Cognitive Bias, Org Health | Active |
| 19 | R&D Lab | Lead Researcher | Curiosity-driven research, experimental prototypes | Active |

### Base Profile

| # | Profile | Status |
|:-:|:--------|:------:|
| — | Default (Fallback) | Active |

---

## Specialist Sub-Agents

### 02 — CFO Department (Team of meetoo)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | Dana | Bookkeeper & Controller — daily accounting, monthly close, internal controls | Active |
| 02 | Riley | FP&A Analyst — budget, rolling forecast, variance analysis | Active |
| 03 | Morgan | Financial Analyst — financial models, scenario analysis, cash-flow insight | Active |

### 03 — CMO Department (Team of มาร์ค)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | Growth Hacker | Growth loops, A/B testing, viral mechanics, funnel optimization | Active |
| 02 | Social Media Strategist | LinkedIn/Twitter brand authority, community, B2B pipeline | Active |
| 03 | Content Creator | Multi-channel content, SEO, video scripts, editorial | Active |

### 04 — Orchestrator Department (Team of พี่วุฒิ)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | Project Shepherd | Cross-functional project management, timeline and risk | Active |
| 02 | Studio Producer | Creative portfolio management, executive relationships | Active |
| 03 | Studio Operations | Daily operations, SOP design, vendor management, efficiency | Active |

### 05 — Architect Department (Team of พี่ทรงศักดิ์)

| # | Agent | Role | Protocol/Pattern | Status |
|:-:|:------|:-----|:-----------------|:------:|
| 01 | Pipeline Auditor | Audit trail, compliance check, evidence collection | GNAP + jira-steward + compliance-auditor | Active |
| 02 | Routing Config Agent | Routing rules, circuit breaker, workflow DAG | GNAP + MagiC + workflow-architect | Active |
| 03 | Monitor Watchdog | Health probe, SLA tracking, dashboard, auto-recovery | model-watchdog + TeamHero + agents-orchestrator | Active |
| 04 | Exception Triage Agent | Auto-classification, RCA, auto-resolve (80%) | AXME + MagiC + chief-of-staff + workflow-optimizer | Active |
| 05 | Cron Pipeline Agent | Scheduled execution, durable retry queue | Temporal + n8n | Active |

### 06 — Product Department (Team of โปรดัค)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | Alex — Product Manager | Product lifecycle from discovery to launch, PRD, opportunity assessment | Active |
| 02 | Product Feedback Synthesizer | Multi-channel feedback analysis, RICE/MoSCoW/Kano prioritization | Active |
| 03 | Product Sprint Prioritizer | Agile sprint planning, dependency/risk management, velocity | Active |

### 07 — Engineering Department (Team of ช่างฟูล)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | สถาปนิกแบ็กเอนด์ | Backend architecture, database design, API, cloud infra (<20ms queries) | Active |
| 02 | นักพัฒนาอาวุโส | Full-stack senior dev — Laravel, Livewire, FluxUI, Three.js | Active |
| 03 | สถาปนิกซอฟต์แวร์ | Domain-driven design, microservices, event-driven, ADRs | Active |

### 08 — Design Department (Team of ครีเอท)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | นักวิจัย UX | User behavior research, usability testing, data-driven design decisions | Active |
| 02 | สถาปนิก UX | UX architecture, design systems, layout frameworks, component structures | Active |
| 03 | นักออกแบบ UI | Visual design systems, component library, WCAG AA, design tokens | Active |

### 09 — UI Designer Department

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | UI Designer | Pixel-perfect visual design system, component library, responsive framework | Active |
| 02 | UX Architect | CSS design system + layout framework, component hierarchy, light/dark theme | Active |
| 03 | UX Researcher | Quantitative/qualitative UX research, usability testing, design recommendations | Active |

### 10 — QA Department (Team of QA-ทีม)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | API Tester | Full-cycle API testing — functional, performance, security (OWASP Top 10) | Active |
| 02 | Accessibility Auditor | WCAG 2.2 compliance, automated tools + assistive technology testing | Active |
| 03 | Test Results Analyzer | Statistical modeling, go/no-go recommendations, quality trend tracking | Active |

### 11 — Sales Department (Team of เซลส์)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | Deal Strategist | B2B deal strategy, MEDDPICC qualification, competitive positioning | Active |
| 02 | Pipeline Analyst | Revenue operations, pipeline velocity, deal quality scoring, forecast | Active |
| 03 | Outbound Strategist | Signal-based prospecting, buying intent, reply rate optimization | Active |

### 12 — Support Department (Team of ซัพพอร์ต)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | Support Responder | First-contact resolution (85%), 2-hour response SLA | Active |
| 02 | Analytics Reporter | KPI dashboards, automated reports, customer segmentation | Active |
| 03 | Executive Summary Generator | SCQA framework, 325-475 words, measurable impact | Active |

### 13 — Legal Department (Team of ตุลย์)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | Compliance Auditor | SOC 2, ISO 27001, HIPAA, PCI-DSS — gap analysis to certification | Active |
| 02 | Legal Document Review | Contract review, agreement analysis, severity-based risk assessment | Active |
| 03 | Legal Client Intake | Screening, case data collection, conflict of interest check | Active |

### 14 — Web3 Department (Team of อัยวา)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | Smart Contract Engineer | Solidity/Anchor, gas optimization, upgrade patterns, test coverage >=90% | Active |
| 02 | Blockchain Security Auditor | Pre-deploy audit, manual review + Slither/Mythril/Echidna | Active |
| 03 | DeFi Protocol Analyst | DeFi market analysis, tokenomics design, on-chain analytics, risk | Active |
| 04 | Solana Developer | Anchor programs (Rust), Web3.js/Solana.js, devnet/mainnet deploy | Active |

### 15 — Content Creator Department (Team of เสก)

| # | Agent | Reference | Status |
|:-:|:------|:---------|:------:|
| 01 | Content Specialist | Referenced from agency-agents library | Active |
| 02-10 | Social, Twitter, TikTok, Video, Growth, Trend, Design + others | Referenced from agency-agents library | Active |

### 16 — Network Engineering Department (Team of นีต)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | Network Architect | Network topology design, BGP/OSPF routing, datacenter interconnects | Design |
| 02 | Infrastructure Engineer | Cloud provisioning (AWS/GCP/DO), load balancer, CDN, DNS via IaC | Design |
| 03 | Network Ops | 24/7 monitoring, incident response, SLA tracking, bandwidth optimization | Design |
| 04 | MCP Builder | MCP server design & implementation — expose SoloCorp OS to external coding agents | Design |

### 17 — Cyber Security Department (Team of ซาย)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | Threat Analyst | SIEM monitoring, threat hunting, IOC classification, threat intel reports | Design |
| 02 | Vulnerability Assessor | Vulnerability scans, CVSS scoring, OWASP compliance, patch prioritization | Design |
| 03 | Incident Responder | Full IR lifecycle, containment, forensics, RCA, playbooks | Design |
| 04 | Red Team Operator | Offensive security — MCP auth bypass, Central Bus abuse, SOUL.md integrity, HackAgent campaigns | Design |

### 18 — Psychology Department (Team of จิต)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | User Behavior Analyst | Cognitive bias mapping, UX psychology, heatmap/session analysis, behavioral segmentation | Design |
| 02 | Behavioral Economist | Nudge theory, prospect theory, pricing psychology, choice architecture | Design |
| 03 | Organizational Psychologist | AI agent team health, communication patterns, conflict resolution, motivation systems | Design |

### 19 — R&D Lab (Team of Lead Researcher)

| # | Agent | Role | Status |
|:-:|:------|:-----|:------:|
| 01 | Lead Researcher | รับไอเดีย → จัดทีม → ลงมือ — ปกป้องทีมจากระบบ | Active |
| 02 | AI Research Scientist | ติดตาม frontier AI — ทดลอง tech ใหม่ๆ ก่อนใคร | Active |
| 03 | Prototyper / Builder | เปลี่ยน idea → prototype เร็วที่สุดเท่าที่จะทำได้ | Active |
| 04 | Experiment Designer | ออกแบบ methodology, metrics, evaluation | Active |
| 05 | Tool Smith | สร้าง tooling — scraper, automation, integration | Active |
| 06 | Knowledge Curator | บันทึก, จัดระเบียบ, แชร์ความรู้จากแล็บ | Active |
| 07 | Wild Card | ทำทุกอย่างที่ไม่มีตำแหน่งรองรับ — special request โดยตรง | Active |

**Total: 19 Department Heads + 62+ Specialist Sub-Agents = 81+ Active Members**

---

## Communication Protocols

### Head-to-Head Handoff Protocol

When work moves between departments, the sending Head sends a structured
handoff to the receiving Head:

```json
{
  "handoff": {
    "from": "Head of Product",
    "to": "Head of Engineering",
    "work_item": "PRD-2026-042-billing-v2",
    "status": "ready",
    "artifacts": ["central_bus/work_items/PRD-042/"],
    "deadline": "2026-07-15",
    "priority": "high"
  }
}
```

### Pipeline Audit Log

Every handoff is logged by the Pipeline Auditor:

```json
{
  "audit_entry": {
    "id": "audit-20260705-001",
    "timestamp": "2026-07-05T10:30:00Z",
    "type": "handoff",
    "from": "06-product",
    "to": "07-engineering",
    "status": "delivered",
    "payload_hash": "a1b2c3d4..."
  }
}
```

### Routing Rules (Circuit Breaker)

The Routing Config Agent manages three states:

| State | Meaning | Action |
|:------|:--------|:-------|
| CLOSED | Normal operation | Route all requests |
| OPEN | Department unhealthy | Block requests, notify Head |
| HALF_OPEN | Testing recovery | Allow limited traffic |

### Exception Classification (AXME)

| Severity | Meaning | Response |
|:---------|:--------|:---------|
| LOW | Non-blocking | Log and continue |
| MEDIUM | Needs attention | Notify Head within 1 hour |
| HIGH | Blocking | Notify Head immediately |
| CRIT | System down | Escalate to CEO, page on-call |

---

## Loop Runner

The Loop Runner is a cron-based auto-pilot that executes recurring tasks
without human intervention.

```
  loop_runner/
  ├── state.py          SQLite: last_run, failures per loop
  ├── runner.py         Base Loop class (interval + execute)
  ├── main.py           Cron entry point
  └── loops/
      ├── daily_brief.py         L1 — CEO morning report (finance+brain)
      ├── subscription_audit.py  L4 — CFO monthly subscription scan
      ├── brain_auto_commit.py   L4 — Auto-commit brain/memory files
      └── pipeline_executor.py   L4 — Pull queue → LLM execute → update status
```

**Cron:** `*/30 * * * * cd /data/projects/Lab-solocorp-os2.4 && .venv/bin/python -m loop_runner.main >> logs/loop_runner_cron.log 2>&1` (installed 2026-09-27; was missing → scheduler silent 2026-08-26–09-27)

**Loops (2026-09-28):** daily_brief (20h) · subscription_audit (30d) · brain_auto_commit (1h) · pipeline_executor (30m) · **media_daily (date-gate ≥06:00, ≤2 segs/day, approved-only)** — fires Flow generations via `workers/flowkit_bridge.py` (dormant until Pro Day-1), logs `bus/media/credits.md`, alerts inbox `__human__` on failure.

**Reliability (2026-09-27):** `main.py` has fcntl single-flight lock (overlapping runs SKIP) + `--dry-run` flag. Loops fetch Bus via `X-API-Key` header with JSON body `{"agent_id":…, "keys":["*"]}` and normalize fact shape `{key,value}` → `{id,content}` (fail-open). busd accepts `X-API-Key` primary + legacy `Authorization: Bearer` compat until 2026-10-04.

| Loop | Trust Lvl | Interval | Action |
|:-----|:---------|:---------|:-------|
| daily_brief | L1 | 20h | Finance + brain data → stdout report |
| subscription_audit | L4 | 30d | Scan recurring charges and subscriptions |
| brain_auto_commit | L4 | 1h | Git commit brain files when changes detected |
| pipeline_executor | L4 | 30m | Pull queue → LLM execute → update status |

> ADR: `decisions/ADR-005-loop-runner.md`

---

## Agent Worker Service

The Agent Worker Service (`workers/agent_worker_service.py`) is the runtime
engine that activates agents. It polls the Central Bus queue, routes tasks
to the correct agent worker, executes the task, and reports results back.

```
  1. Poll ───→ Central Bus queue (/v1/context) ───→ 2. Route to Agent
                                                          ↓
  4. Report ←── Mark queue status + notify CEO  ←── 3. Execute task
```

### Architecture

| Step | Component | Description |
|:-----|:----------|:------------|
| Poll | `poll_queue()` | Fetch pending (routed) tasks from Central Bus, max 3 per cycle |
| Route | `self.agents` dict | 18 registered agents covering all departments + R&D Lab |
| Execute | `agent.execute()` | Each agent processes the task via its domain-specific logic |
| Report | `mark_completed()` / `report_to_ceo()` | Update queue status + notify CEO on completion/failure |

**Key properties:**
- Poll interval: 5s (configurable)
- Max concurrent tasks: 3 (asyncio.Semaphore)
- Stale recovery: processing tasks >5min reset to routed (crash tolerance)
- All agents run in-process via asyncio

### Files

- `workers/agent_worker_service.py` — Main service daemon
- `workers/agents/` — Individual agent implementations (18 agents)
- `workers/__init__.py` — Package init

---

## LLM Provider

All agent workers use `workers/llm_provider.py` for LLM inference.

### Configuration

| Parameter | Value |
|:----------|:------|
| CLI | `opencode run --agent <agent> --model <model>` — **ห้ามใส่ flag ที่ `opencode run --help` ไม่มี** (เช่น `--pure` ที่ถูกถอดใน v2.1.4 → ล้มทั้ง chain) |
| Agent | `OPENCODE_AGENT` หรือ `plan` (read-only) — subprocess ไม่มีใครกด allow ถ้าใช้ agent ที่มี shell/write โมเดลจะขอ permission แล้วค้าง |
| Default model | `opencode-go/muse-spark-1.3-contributor` (2026-11-12, subscription Opencode Go, 1M context — 200K → 1M) |
| Fallback chain | muse-spark-1.3 (subscription) → deepseek-v4.1-flash → nemotron-3.5-lightning → nemotron-3-ultra → big-pickle → mimo-v2.6-flash (`MODEL_FALLBACKS`; dead names in `DEAD_MODELS` map straight to chain; `Model not found` **และ** `Model unavailable` (v2.1.4) ข้ามทันที) |
| Max concurrent | 3 (asyncio.Semaphore) |
| Timeout | 60s per call |
| Max retries | 3 per model (exponential backoff) |
| Prompt transport | stdin (prevents shell injection) |

### Usage

```python
from workers.llm_provider import think

result = await think(
    prompt="Write a PRD for billing v2",
    system_prompt="คุณคือ Product Manager ของ SoloCorp",
    max_tokens=800,
    agent="product-produck",  # ใส่ชื่อ agent → รู้ว่าใครกินโควตา (ledger)
)
```

### Token / quota accounting

ทุก call ถูกวัดและบันทึก — ดูรายละเอียดที่ **[`docs/TOKEN-ACCOUNTING.md`](TOKEN-ACCOUNTING.md)**

| ชั้น | ทำอะไร | ไฟล์ |
|:----|:-------|:-----|
| วัด | ทุก call มี `--session ses_llm…` ของเราเอง → อ่าน `tokens`/`cost` จริงจาก `opencode.db` (`session_message`) | `workers/token_ledger.py` |
| บันทึก | append 1 บรรทัด JSONL ต่อ call (สำเร็จ/ล้ม, model, agent, duration, tokens, cost) | `bus/system/token-ledger.jsonl` |
| เพดาน | รายวัน: requests / output tokens / cost — เกินแล้ว **ไม่ยิง LLM** (ค่าเริ่มต้น 400 / 2M / $1) | env `SOLOCORP_LLM_DAILY_*` |
| ล็อก | เจอ 429/402 → จำเวลา reset → call ถัดไปจบใน ~1 ms ไม่ยิงซ้ำ | `bus/system/llm_quota.json` |

```bash
python scripts/token-report.py --sessions 5   # วันนี้ทั้ง org กินเท่าไร ใครกิน
```

### Cross-Reference

- `workers/llm_provider.py` — LLM inference wrapper
- `workers/token_ledger.py` — token/quota accounting (usage, budget, lock)
- `loop_runner/loops/pipeline_executor.py` — Uses `think()` for queue tasks

---

## Open Design Integration (Deprecated)

> ⚠️ **DEPRECATED** — This bridge was never connected to a live daemon. The
> port 41551 bridge is inactive and should not be relied upon. The Agent
> Worker Service (`workers/agent_worker_service.py`) is the replacement for
> task execution.

A read-only bridge from Central Bus to Open Design daemon (port 41551) — never
operational.

**Permission Model:**

| Department | Tools Allowed |
|:-----------|:--------------|
| design | All tools (6 tools) |
| ui_designer | get_artifact, get_file, search_files |
| engineering | get_artifact, get_file, search_files |
| qa | get_artifact, get_file |
| cfo, sales, legal, web3, support | Blocked |

**Files:** `central_bus/open_design.py`, `bus/system/open_design_config.json`

---

## Content Creator Pack — Local Video Pipeline (Phase 1-3, 2026-11-07)

> Current-direction update only (2026-11-07). Principles/pillars/hierarchy above unchanged. Product direction source of truth remains PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.

**Pattern:** BYOM (Bring Your Own Model) + Local-First MCP + Publish Gate. The Content Creator MCP is a department MCP usable standalone from an external client (PRD §6.1); in the planned SoloCorp App it is the first integrated module (PRD §6.2/MVP scope). The MCP stores artifacts without publishing and never auto-approves: every publication requires recorded human approval for the exact campaign version.

**Governed call chain (Phase 2):** `ingest → script → visual → cue → render → gate → human approval` — see [`docs/plans/CONTENT-PHASE2-GOVERNED-CALL-GRAPH.md`](plans/CONTENT-PHASE2-GOVERNED-CALL-GRAPH.md). Skill = guidance, engine = `content_service` + CLI; per-scene (local) vs continuous (Concat) paths never mix.

**Local-only renderer (Phase 1 + 3, proven on this host):** `render_campaign_media_local` — Piper (`th_TH-tsync2-medium`, CC BY-NC-SA 3.0 non-commercial, internal draft only) + FFmpeg CLI direct (provider `ffmpeg-cli`, `execution_mode: local_ffmpeg_cli`; ffmpeg-skill bridge stores plan only, never executes). Supports 6×15s (90s) or 10×10s (100s); per-step `steps` 5/5 with timestamps (`input_validation`, `piper_tts`, `synthetic_visuals`, `ffmpeg_assembly`, `output_audit`), opt-in fallback (`tts_fallback`/`visual_fallback`, default `abort`, any use → `degraded: true` + failing gate check), non-blocking exclusive lock (second caller fails immediately). See [`docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md`](runbooks/CONTENT-LOCAL-MEDIA-RENDER.md) Phase 3 Features.

**Concat path — enabled + handshake verified, render NOT proven (2026-11-07):** History: Concat 0.2.8 AppImage exists on this host but the FUSE mount is denied (`fusermount3 Operation not permitted`, exit 127), which blocked the original launch. Per [`decisions/ADR-032-concat-host-2026-11-07.md`](../decisions/ADR-032-concat-host-2026-11-07.md) **as amended 2026-11-07**, the `--appimage-extract` path succeeded instead: `squashfs-root` (362M) at `/home/drsolodev/.opencode/concat/`, `AppRun` = concat 0.2.8, `concat` MCP `enabled` in `opencode.json`, and the MCP handshake was verified on 2026-11-07 (tools respond; `project_list()` → `[]`). **Still NOT proven: `render_campaign_with_concat` has never been run on this host** — no render proof; if the handshake fails, the fallback is Option 1 disable. **Do not claim Concat rendering works on this host today.** Local-media renders do not need Concat. See also [`docs/MEDIA-TOOLKIT.md`](MEDIA-TOOLKIT.md) (Concat wording updated 2026-11-07).

**Phase 1–3 evidence (frozen campaigns, 2026-11-07 — do not touch):**

- Phase 1 `campaign_synth_phase1_20261107` v5 — SHA-256 `ef3b282fc3ed69a58064c336e780a75f79094c0d54c36ffdbe406c23837c28bb` — [`central_bus/content/ceo-phase1-completed-20261107_20261107T031659522762Z.md`](../central_bus/content/ceo-phase1-completed-20261107_20261107T031659522762Z.md)
- Phase 2 `campaign_synth_phase2_20261107` v7 — SHA-256 `60d855b1203c5a86593c451236f03fd70bd79afa3193eb54f458f702cd0aca9b` — [`central_bus/content/ceo-phase2-completed-20261107.md`](../central_bus/content/ceo-phase2-completed-20261107.md)
- Phase 3 `campaign_synth_phase3_20261107` v7 — SHA-256 `192ba6c5e0b0c74dcd02f262df5f8771e399a8573b220e75e267531f48a7cc32` — [`central_bus/content/ceo-phase3-completed-20261107_20261107T051235733316Z.md`](../central_bus/content/ceo-phase3-completed-20261107_20261107T051235733316Z.md)

All three: 1080×1920 30fps 90s H.264/AAC 48kHz, −16.0 LUFS, `gate_passed: false`, `published: false`; provenance `client_supplied_unverified`, provider/model null; Piper non-commercial. Approval status differs: **phase 1 v5 has a recorded human approval** (2026-11-07T03:19:06Z, approval record `central_bus/content/campaign-campaign_synth_phase1_20261107-approval-v5_20261107T031906146707Z.json`, for that exact v5 SHA only, with `gate_passed: false` + 7 explicit overrides; approval does not publish — `published` remains false and the normal publish gate has not passed); **phase 2 and phase 3 remain `approved_version: null` with no approval recorded** (`review_required`). Tests 65 passed (see runbook Verification). Full render detail in runbook §Phase 3 Render Evidence.

**Explicit NOT done (do not upgrade these to done):**

- Degraded publication: **NO-GO** pending architect D1 waiver + real degraded render on throwaway campaign (Phase 3 completion record; degraded render can never present as clean pass).
- Concat render proof: MCP handshake is verified (2026-11-07) but `render_campaign_with_concat` has never been run on this host — no render proof; fallback if the handshake fails is Option 1 disable.
- Certification: D3 not passed (operational E2E runs, not independent D3/D4); SoloCorp App shell/registry/provider flow not implemented (PRD Phase 1 gate open).

---

## Key Design Decisions

All significant architectural decisions are documented as Architecture
Decision Records (ADRs) in the `decisions/` directory:

| ADR | Title | Status |
|:----|:------|:------:|
| ADR-001 | AI Agent Department Architecture | Approved |
| ADR-002 | Two-Tier Architecture — Control vs Data Layer | Approved |
| ADR-003 | Central Bus Schema + Protocol | Approved |
| ADR-004 | Department Head Design Standards | Approved |
| ADR-005 | Loop Runner — Cron-Based Auto-Pilot | Approved |

---

## Sources & References

- **Repository:** `Lab-solocorp-os2.4` (Private — Dr-SoloDev)
- **OpenCode Profiles:** `profiles/` — Department Heads + Specialist agents
- **Worker Service:** `workers/agent_worker_service.py` — Queue-to-agent runtime
- **LLM Provider:** `workers/llm_provider.py` — OpenCode run inference
- **Agent Templates:** `agency-agents` library (411 templates, 18 categories)
- **Versioning:** SemVer via CHANGELOG.md + Git tags

---

*SoloCorp OS — System First, Everything Follows*
