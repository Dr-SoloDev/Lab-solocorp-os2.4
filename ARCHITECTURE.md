# Lab-solocorp-os2.4 — Architecture Overview

> System Architecture for SoloCorp OS
> Designed: 2026-06-26 | Last Updated: 2026-07-05 | Version: 2.4

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Three Pillars of Department Head Design](#three-pillars-of-department-head-design)
3. [Two-Tier Architecture](#two-tier-architecture)
4. [Hierarchy & Chain of Command](#hierarchy--chain-of-command)
5. [Department Profiles (15)](#department-profiles)
6. [Specialist Sub-Agents (46+)](#specialist-sub-agents)
7. [Communication Protocols](#communication-protocols)
8. [Loop Runner](#loop-runner)
9. [Open Design Integration](#open-design-integration)
10. [Key Design Decisions](#key-design-decisions)

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
              └── Department Heads (05-15)
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
                   └── 15-Content Creator (เสก)
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

### Department Heads (05-15)

| # | Profile | Head | Responsibility | Status |
|:-:|:--------|:-----|:--------------|:------:|
| 05 | Architect | พี่ทรงศักดิ์ (Songsak) | Central Bus, Routing, Monitoring | Active |
| 06 | Product | โปรดัค | Feature Roadmap, PRD, Delivery | Active |
| 07 | Engineering | ช่างฟูล | Backend, Frontend, Architecture | Active |
| 08 | Design | ครีเอท | UX Research, Brand Visual | Active |
| 09 | UI Designer | UI-Designer | Interface, Component Library | Active |
| 10 | QA | QA-ทีม | Testing, Quality, Evidence | Active |
| 11 | Sales | เซลส์ | B2B Deal Strategy, Pipeline | Active |
| 12 | Support | ซัพพอร์ต | Customer Success, Analytics | Active |
| 13 | Legal | ตุลย์ | Compliance, Contracts, Law | Active |
| 14 | Web3 | อัยวา | Blockchain, DeFi, Solana | Active |
| 15 | Content Creator | เสก | Content, Creative, Media | Active |

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

**Total: 15 Department Heads + 46+ Specialist Sub-Agents = 61+ Active Members**

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
      └── brain_auto_commit.py   L4 — Auto-commit brain/memory files
```

**Cron:** `*/30 * * * * python3 -m loop_runner.main`

| Loop | Trust Lvl | Interval | Action |
|:-----|:---------|:---------|:-------|
| daily_brief | L1 | 20h | Finance + brain data → stdout report |
| subscription_audit | L4 | 30d | Scan recurring charges and subscriptions |
| brain_auto_commit | L4 | 1h | Git commit brain files when changes detected |

> ADR: `decisions/ADR-005-loop-runner.md`

---

## Open Design Integration

A read-only bridge from Central Bus to Open Design daemon (port 41551).

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
- **Hermes Profiles:** `~/.hermes/profiles/<NN-name>/`
- **Agent Templates:** `agency-agents` library (411 templates, 18 categories)
- **Skills:** 93 skills in Hermes system
- **Versioning:** SemVer via CHANGELOG.md + Git tags

---

*SoloCorp OS — System First, Everything Follows*
