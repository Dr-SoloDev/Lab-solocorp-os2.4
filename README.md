<!--
  SoloCorp OS — README
  Designed: 2026-07-07 | UX Funnel: Hook → Try it → Proof → Details
-->

<details>
<summary><strong>SoloCorp OS 2.4</strong> — ASCII banner (click to expand)</summary>

```text
================================================================================
  ███████  ██████  ██       ██████   ██████  ██████  ██████  ██████  
  ██      ██    ██ ██      ██    ██ ██      ██    ██ ██   ██ ██   ██ 
  ███████ ██    ██ ██      ██    ██ ██      ██    ██ ██████  ██████  
       ██ ██    ██ ██      ██    ██ ██      ██    ██ ██   ██ ██      
  ███████  ██████  ███████  ██████   ██████  ██████  ██   ██ ██      

   ██████  ███████  ███████   ██   ██
  ██    ██ ██            ██   ██   ██
  ██    ██ ███████  ███████ █ ███████
  ██    ██      ██  ██      █      ██
   ██████  ███████  ███████        ██
================================================================================
                     OPERATING SYSTEM  ===  VERSION 2.4
================================================================================
```

</details>

# SoloCorp OS

**The Engine for Building Personal Digital Organizations**

SoloCorp OS คือเครื่องจักรสำหรับสร้างองค์กรดิจิทัลส่วนบุคคล — ชั้นล่างเป็นระบบ Multi-Agent กลางที่ใครก็ใส่ตัวตนได้ ชั้นบนคือระบบปฏิบัติการองค์กรที่ผู้ใช้แต่ละคนออกแบบเอง

SoloCorp OS มอบรากฐานสำหรับการประสานงานระหว่าง AI Agents ขณะที่เปิดอิสระให้แต่ละคนออกแบบโครงสร้างองค์กร บทบาท และวิธีดำเนินงานของตนเอง

**One foundation. Unlimited organizational identities.**

> SoloCorp ของเราเป็น Reference Instance หนึ่งตัวอย่าง ไม่ใช่แม่แบบที่คุณต้องทำตาม — ออกแบบองค์กรดิจิทัลของคุณเองได้อย่างอิสระ

> นิยามฉบับเต็ม (LOCKED): [`brain/milestone-core-definition-20261010.md`](./brain/milestone-core-definition-20261010.md)

<!-- Badges: grouped by category for visual hierarchy -->

**Status:**
[![version](https://img.shields.io/badge/version-v2.4.0--pre--release-%23FF6B35?style=flat-square)](https://github.com/Dr-SoloDev/Lab-solocorp-os2.4/releases/tag/v2.4.0-pre)
[![status](https://img.shields.io/badge/status-pre--release-%23FF6B35?style=flat-square)](https://github.com/Dr-SoloDev/Lab-solocorp-os2.4/releases)
[![Copilot Setup Steps](https://github.com/Dr-SoloDev/Lab-solocorp-os2.4/actions/workflows/copilot-setup-steps.yml/badge.svg)](https://github.com/Dr-SoloDev/Lab-solocorp-os2.4/actions/workflows/copilot-setup-steps.yml)
[![license](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

**Design:**
[![2-layer](https://img.shields.io/badge/2--layer-core%20%2B%20instance-blue?style=flat-square)](#solocorp-os)
[![model-agnostic](https://img.shields.io/badge/model--agnostic-any%20LLM-orange?style=flat-square)](https://github.com/Dr-SoloDev/Lab-solocorp-os2.4)

**Platform:**
[![packs](https://img.shields.io/badge/product%20packs-3%20available-%23E74C3C?style=flat-square)](#product-packs)
[![platform](https://img.shields.io/badge/platform-Hermes%20%2B%20OpenCode%20%2B%20Codex%20%2B%20Grok-orange?style=flat-square)](https://github.com/Dr-SoloDev/Lab-solocorp-os2.4)
[![grok](https://img.shields.io/badge/Grok%20pack-AGENTS.md%20%2B%20.grok-black?style=flat-square)](docs/GROK-SUPPORT.md)

> **License:** [MIT](LICENSE) — เอาไปใช้ ปรับ แจก ขายต่อได้อิสระ ขอแค่เก็บ copyright ไว้
> ⭐ ถ้าชอบ ฝากกด **Star** เป็นกำลังใจ — แล้วเอาทีมของคุณมาอวดใน [Discussions](https://github.com/Dr-SoloDev/Lab-solocorp-os2.4/discussions)!

## 🌱 หนึ่งแกน หลายตัวตน

SoloCorp OS เกิดจากแกนเดียวกัน แต่**ไม่จำเป็นต้องเหมือนกัน** — fork ไป เปลี่ยนชื่อ
ปรับแผนก เพิ่มลดได้ตามใจ ขอแค่ให้มัน*เข้ากับตัวคุณ* ระบบที่ดีคือระบบที่เจ้าของใช้แล้ว
มีความสุข ไม่ใช่ระบบที่เหมือนต้นฉบับที่สุด — *แตกต่างไม่แตกแยก เป็นตัวของตัวเอง*

ดูวัฒนธรรมการแบ่งปันที่ [`COMMUNITY.md`](./COMMUNITY.md) 💬

---

## Try it in 30 seconds

```bash
git clone https://github.com/Dr-SoloDev/Lab-solocorp-os2.4.git
cd Lab-solocorp-os2.4
opencode "@ceo-turbo เริ่มกันเลย"
```

**For GitHub Copilot Cloud Agent:** Merge `.github/workflows/copilot-setup-steps.yml` to default branch.
See [`COPILOT-SETUP.md`](./COPILOT-SETUP.md) for the full guide.

**Or export all profiles as Codex CLI sub-agents:**
```bash
python3 scripts/export-codex-agents.py
codex
```

**Or use Grok Build CLI (project pack):**
```bash
source .venv/bin/activate && export PYTHONPATH=.
grok
# then: /status  ·  /route <request>  ·  /pipeline <feature>
```
See [`docs/GROK-SUPPORT.md`](./docs/GROK-SUPPORT.md) and [`.grok/README.md`](./.grok/README.md).

### Pipeline Commands (once inside)

| Command | Action |
|:--------|:-------|
| `/pipeline <feature>` | Run SoloCorp full cycle |
| `/handoff <from> <to> <task>` | Structured department handoff |
| `/status` | View pipeline health |
| `/audit [scope]` | Inspect audit trail |
| `/deploy` | Deploy profiles and config |
| `/brain <context>` | Save session to brain memory |
| `/workspace [dept] [task]` | Open department workspace (แยกแชทพร้อมตัวตน+บริบท) |

🏢 **Multi-chat workspaces:** 1 แผนก = 1 แชท — ดู [`docs/OPENCODE-GUIDE.md`](./docs/OPENCODE-GUIDE.md) (คน+agent อ่านได้ในไฟล์เดียว)

---

## What is SoloCorp OS?

SoloCorp OS is an **organizational operating system for AI agents** — a complete Department Architecture that gives every unit of work an owner, a specialist executor, and a defined handoff path.

Instead of a monolithic AI trying to do everything, SoloCorp OS gives you:

- **20 Departments** — Each with a dedicated Head who owns outcomes, not just tasks
- **55+ Specialist Agents** — Sub-agents who execute; Heads who lead
- **Two-Tier Architecture** — Control flows Head-to-Head; data flows autonomously through a Central Bus
- **Clear Chain of Command** — Human → CEO → C-Level → Department Heads → Specialist Teams

The design is inspired by how real companies scale: clear hierarchy, delegated authority, and autonomous execution at every level. No orphan work. No ambiguous ownership.

---

## The Problem We Solve

Monolithic AI agents break down as complexity grows:

- **Context collapse** — a single AI juggling 15+ concerns loses depth; no specialist ownership
- **No accountability chain** — when one prompt does everything, there is no clear owner
- **Throughput ceiling** — every request bottlenecks through one context window
- **Implicit handoffs** — coordination is unstructured; work gets lost or silently dropped

SoloCorp OS replaces that single point of failure with a structured department hierarchy — each unit of work has a named owner, a specialist executor, and an explicit handoff path through the Central Bus.

---

## Key Features

| Feature | Description |
|:--------|:------------|
| **Ownership Model** | Every department has a Head who owns outcomes |
| **Delegation by Design** | Heads direct, escalate, and hand off — they do not implement |
| **Two-Tier Architecture** | Control layer separated from data layer |
| **Central Bus** | Async-first message routing between departments |
| **Head-to-Head Handoff** | Work moves between departments without bottleneck |
| **Skills Library** | Versioned skills integrated across departments (catalog in `skills/`) |
| **21 OpenCode Agents** | Department heads + specialists, all `@mention`-ready |
| **Codex CLI Export** | All profiles exportable as Codex CLI sub-agents |
| **xGov Governance** | RFC → ADR → Guard Gates protocol |
| **Loop Runner** | Cron auto-pilot — scheduled execution every 30 min |

---

## Reference Instance: SoloCorp Organization

> ส่วนนี้ทั้งหมด — Architecture, Chain of Command, Department Roster และตัวเลข —
> คือองค์กรตัวอย่างที่ผู้สร้างประกอบขึ้นเพื่อพิสูจน์วิสัยทัศน์ ไม่ใช่ข้อบังคับของทุก instance
> (ตัวเลขคือสถานะจริง: 20 departments · 61 specialist profiles · 21 OpenCode agents)

### Architecture

```mermaid
graph TD
    Human["Human<br/>(Dr.solodev — Owner / Vision)"]
    CEO["CEO<br/>เทอโบ ไชยศรีรัมย์<br/>Supreme AI Authority"]
    CFO["CFO<br/>meetoo<br/>Finance / Budget"]
    CMO["CMO<br/>มาร์ค<br/>Marketing / Brand"]
    Orch["Orchestrator<br/>พี่วุฒิ<br/>Pipeline Coordination"]
    Arch["Architect<br/>พี่ทรงศักดิ์<br/>Central Bus / Routing"]
    Prod["Product<br/>โปรดัค<br/>Roadmap / PRD"]
    Eng["Engineering<br/>ช่างฟูล<br/>Backend / Frontend"]
    Des["Design<br/>ครีเอท<br/>UX / Brand Visual"]
    UI["UI Designer<br/>UI Designer<br/>Interface / Components"]
    QA["QA<br/>QA-ทีม<br/>Testing / Quality"]
    Sales["Sales<br/>เซลส์<br/>B2B Pipeline"]
    Sup["Support<br/>ซัพพอร์ต<br/>Customer Success"]
    Legal["Legal<br/>ตุลย์<br/>Compliance / Contracts"]
    Web3["Web3<br/>อัยวา<br/>Blockchain / DeFi / Solana"]
    Content["Content Creator<br/>เสก<br/>Content / Creative / Media"]
    NetEng["Network Engineer<br/>นีต<br/>Network / Infrastructure"]
    CyberSec["Cyber Security<br/>ซาย<br/>Threat / Vulnerability / IR"]
    Psych["Psychology<br/>จิต<br/>Behavior / Econ / Org"]
    COO["COO<br/>กิจ (Kit)<br/>Daily Operations"]
    RD["R&D Lab<br/>Lead Researcher<br/>Research / Prototyping"]

    Human --> CEO
    CEO --> COO
    CEO --> CFO
    CEO --> CMO
    CEO --> Orch
    Orch --> Arch
    Orch --> Prod
    Orch --> Eng
    Orch --> Des
    Orch --> UI
    Orch --> QA
    Orch --> Sales
    Orch --> Sup
    Orch --> Legal
    Orch --> Web3
    Orch --> Content
    Orch --> NetEng
    Orch --> CyberSec
    Orch --> Psych
    Orch --> RD
```

**Two-Tier Architecture**

```
CONTROL LAYER (Head-to-Head)
  Status · Goals · Exceptions · Approvals · Handoffs
  Head A ──(status/report)──→ Head B

DATA LAYER (Autonomous)
  Code · Designs · Reports · Raw Outputs
  Specialist A ──(write)──→ CENTRAL BUS ──(notify)──→ Specialist B
                                 └── Queue
```

---

### The Team

#### C-Level Executives

| # | Role | Name | Responsibility |
|:-:|:-----|:-----|:--------------|
| 01 | CEO | เทอโบ (Turbo Chaisriram) | Vision, Strategy, Final Decision |
| 02 | CFO | meetoo | Finance, Budget, Investment |
| 03 | CMO | มาร์ค (Mark) | Marketing, Content, Brand |

#### System Pipeline

| # | Role | Name | Responsibility |
|:-:|:-----|:-----|:--------------|
| 02 | COO | กิจ (Kit) | Daily Operations, L1–L3 Gatekeeper |
| 04 | Orchestrator | พี่วุฒิ (Wut) | Cross-Department Pipeline Coordination |
| 05 | Architect | พี่ทรงศักดิ์ (Songsak) | Central Bus, Routing, Monitoring |

#### Product & Engineering

| # | Role | Name | Responsibility |
|:-:|:-----|:-----|:--------------|
| 06 | Product | โปรดัค (Produck) | Feature Roadmap, PRD, Delivery |
| 07 | Engineering | ช่างฟูล (Changful) | Backend, Frontend, Architecture |
| 08 | Design | ครีเอท (Kreet) | UX Research, Brand Visual |
| 09 | UI Designer | UI Designer | Interface, Component Library |

#### Quality, Revenue & Customer

| # | Role | Name | Responsibility |
|:-:|:-----|:-----|:--------------|
| 10 | QA | QA-ทีม (QA Team) | Testing, Quality, Evidence |
| 11 | Sales | เซลส์ (Sales) | B2B Deal Strategy, Pipeline |
| 12 | Support | ซัพพอร์ต (Support) | Customer Success, Analytics |

#### Legal, Blockchain, Content & Research

| # | Role | Name | Responsibility |
|:-:|:-----|:-----|:--------------|
| 13 | Legal | ตุลย์ (Tul) | Compliance, Contracts, Law |
| 14 | Web3 | อัยวา (Aywa) | Blockchain, DeFi, Solana |
| 15 | Content Creator | เสก (Sek) | Content, Creative, Media |
| 16 | Network Engineer | นีต (Neet) | Network Design, Infrastructure, CDN, VPN |
| 17 | Cyber Security | ซาย (Sai) | Threat Detection, Vulnerability, Incident Response |
| 18 | Psychology | จิต (Jit) | User Behavior, Behavioral Economics, Org Psychology |
| 19 | R&D Lab | Lead Researcher | Research, Prototyping |

**Total: 20 Department Heads · 61 Specialist Profiles · 21 OpenCode Agents** (reference snapshot — verified from repo)

---

## Product Packs — v2.4.0 Pre-release

Three departments now available as **standalone packs** — deploy them into your own agent workflow without importing the entire OS.

| Pack | Head | What It Does | Specialists |
|:-----|:-----|:-------------|:-----------:|
| **CFO Pack** `@cfo-meetoo` | meetoo | Budget control · Financial analysis · Audit trail · Tax strategy · FP&A | 5 |
| **Legal Pack** `@legal-tulya` | ตุลย์ (Tul) | Contract review · License compliance · Risk assessment · Data governance | 3 |
| **Content Creator Pack** `@content-creator-sek` | เสก (Sek) | Multi-platform content · Video production · Copywriting · Visual creation | 10 |

Each pack ships with **SOUL.md** identity, **sub-agent team**, **routing rules**, and **skills library**.

> `@mention` any head to begin. No setup required.

---

## Development Status

| Phase | Content | Version | Status |
|:------|:--------|:-------:|:------:|
| Foundation | ADRs + CEO Profile + Architecture | v0.1–v0.2 | Complete |
| Pipeline Agents | Architect team — 5 pipeline agents | v0.3 | Complete |
| Department Profiles | 18 Department Heads + Teams | v0.5 | Complete |
| Deploy to Hermes | All profiles deployed to Hermes | v0.5.1 | Complete |
| Sub-agent Teams | 42 specialist agents deployed | v0.6.1 | Complete |
| Central Bus | FastAPI daemon + SQLite WAL + Guard + AAR | v0.6 | Complete |
| Multi-Platform Support | Hermes · OpenCode · Claude Code · Codex CLI | v0.7 | In Progress |
| Dashboard + Compliance | Pipeline Dashboard + Audit trail | v0.7 | Planned |
| **Product Packs** | **CFO · Legal · Content Creator** | **v2.4.0** | **Pre-release** |
| Public Launch | GTM · Content Campaign · Skill Docs | v0.7 | In Progress |
| Loop Runner | Cron auto-pilot — every 30 min | v0.5+ | Active |

**Overall Progress**

```
Foundation      ████████████████████ 100%
Profiles        ████████████████████ 100%
Sub-Agents      ████████████████████ 100%
Central Bus     ████████████████████ 100%
Multi-Platform  ████████░░░░░░░░░░░░  40%
Public Launch   ████████░░░░░░░░░░░░  40%
Dashboard       ███████░░░░░░░░░░░░░  35%
```

---

## Qualify for Early Access

Product Packs are in **controlled pre-release**. Not everyone should use SoloCorp OS — and that's by design.

```
1. Clone the repo
2. Open with `opencode`
3. @mention the pack head you want to evaluate
4. The head will run a 3-question qualification gate
```

```bash
# Example: qualify for CFO Pack
opencode "@cfo-meetoo เริ่ม qualification gate สำหรับ CFO Pack"
```

> **You are not a customer. You are a potential operator.**  
> SoloCorp OS doesn't sell software. It deploys organizational capability.

---

## Get Started

The fastest path to a working multi-agent team:

1. Clone the repo and open with `opencode`
2. Start a conversation — the CEO (เทอโบ) routes your request to the right department
3. Use `@mention` to reach a Head directly for specific work
4. Run `/pipeline <feature>` for a full cross-department cycle

**Reference docs:**

- `profiles/INDEX.md` — Index of all 20 department profiles and specialist teams
- `ARCHITECTURE.md` — System design, principles, and flow
- `PROJECT.md` — Getting started guide for newcomers
- `CHANGELOG.md` — Version history and release notes
- `COPILOT-SETUP.md` — GitHub Copilot Cloud Agent integration guide
- `decisions/` — Architecture Decision Records (ADRs)
- `dist/codex/README-CODEX-CLI.md` — Codex CLI export guide

---

<div align="center">

**SoloCorp OS — System First, Everything Follows**  
Proprietary software &copy; SoloCorp Organization. All Rights Reserved.  
Free for personal and educational use.  
Built by Dr.SoloDev &amp; เทอโบ ไชยศรีรัมย์

</div>
