# SoloCorp OS 2.4

> **ระบบ Department Architecture สำหรับ Hermes Agent**
> Human → CEO → C-Level → Orchestrator → Department Heads (→ Agents)

## Hierarchy

```
Dr.solodev (Human/Owner)
  └── CEO (เทอโบ — Supreme AI Authority)
       ├── CFO (meetoo — การเงิน/งบประมาณ)
       ├── CMO (มาร์ค — การตลาด/Content)
       ├── Orchestrator (Hermes — System Pipeline)
       └── Department Heads
            ├── 05-architect   — พี่ทรงศักดิ์ (สายพานกลาง)
            ├── 06-product     — โปรดัค
            ├── 07-engineering — ช่างฟูล
            ├── 08-design      — ครีเอท
            ├── 09-ui-designer — UI-Designer
            ├── 10-qa          — QA-ทีม
            ├── 11-sales       — เซลส์
            ├── 12-support     — ซัพพอร์ต
            ├── 13-legal       — ตุลย์
            └── 14-web3        — อัยวา (Blockchain/DeFi/Solana)
                   └── default (Fallback)
```

## Core Principles

1. **3 Pillars** — หัวหน้าไม่ทำงานเอง, Leadership Skills, Ownership Mindset
2. **Two-Tier Architecture** — Control Layer (Head) vs Data Layer (Central Bus)
3. **Head-to-Head Handoff** — 80% ส่งตรง, 5% Escalate

## Profile Order (Hermes)

| ลำดับ | Profile Directory | ชื่อ | สถานะ |
|:----:|:-----------------|:----|:-----:|
| 01 | `01-ceo` | เทอโบ CEO | 🟢 |
| 02 | `02-cfo` | meetoo | 🟡 |
| 03 | `03-cmo` | มาร์ค | 🟡 |
| 04 | `04-orchestrator` | Hermes-Orchestrator | 🟡 |
| 05 | `05-architect` | พี่ทรงศักดิ์ | ✅ |
| 06 | `06-product` | โปรดัค | 🟡 |
| 07 | `07-engineering` | ช่างฟูล | 🟡 |
| 08 | `08-design` | ครีเอท | 🟡 |
| 09 | `09-ui-designer` | UI-Designer | 🟡 |
| 10 | `10-qa` | QA-ทีม | 🟡 |
| 11 | `11-sales` | เซลส์ | 🟡 |
| 12 | `12-support` | ซัพพอร์ต | 🟡 |
| 13 | `13-legal` | ตุลย์ | 🟡 |
| 14 | `14-web3` | อัยวา | 🟡 |
| — | `default` | Fallback | ✅ |

## Status

| Phase | เนื้อหา | สถานะ |
|:------|:--------|:-----:|
| Foundation (v0.1–0.2) | ADRs + CEO Profile + Architecture | ✅ |
| Core Sub-agents (v0.3) | 5 Pipeline Agents ของพี่ทรงศักดิ์ | ✅ |
| All Dept Profiles (v0.5) | 14 Department Heads + ทีมทั้งหมด | ✅ |
| Central Bus (v0.6) | Central Bus Agent + Context Optimizer | 🔴 |
| Dashboard + Compliance (v0.7) | Pipeline Dashboard + QA Gate | ⏳ |
| Implement in Hermes (v1.0) | Deploy จริงทุก Profile | ⏳ |

## Teams

### 05 — Architect (พี่ทรงศักดิ์)

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [📋 Pipeline Auditor](profiles/05-architect/phee-thongsak/team/01-pipeline-auditor.SOUL.md) | ตรวจสอบทุก handoff ใน pipeline — บันทึกประวัติ, ตรวจ compliance, รับรองว่า payload ครบถ้วน | 🔴 |
| 02 | [🗺️ Routing Config Agent](profiles/05-architect/phee-thongsak/team/02-routing-config-agent.SOUL.md) | กำหนดเส้นทางงานระหว่างแผนก — ออกแบบ routing rules, เงื่อนไข, circuit breaker ป้องกันระบบล่ม | 🔴 |
| 03 | [🎛️ Monitor Watchdog](profiles/05-architect/phee-thongsak/team/03-monitor-watchdog.SOUL.md) | เฝ้า pipeline real-time — ตรวจ health ทุก agent, SLA, แจ้งเตือนและ rollback เมื่อผิดปกติ | 🔴 |
| 04 | [🧭 Exception Triage Agent](profiles/05-architect/phee-thongsak/team/04-exception-triage-agent.SOUL.md) | หน่วยกู้ชีพ — รับ exception, แยกแยะระดับความรุนแรง, แก้ไขอัตโนมัติ หรือ escalate ให้พี่ทรงศักดิ์ | 🔴 |
| 05 | [⏰ Cron Pipeline Agent](profiles/05-architect/phee-thongsak/team/05-cron-pipeline-agent.SOUL.md) | รัน pipeline ตาม schedule — durable execution ด้วย Temporal, retry อัตโนมัติ, ไม่มีงานหาย | 🔴 |

### 02 — CFO (meetoo)

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [Dana](profiles/02-cfo/meetoo/team/01-dana.SOUL.md) | นักบัญชีและผู้ควบคุมการเงิน — ดูแลบัญชีรายวัน, ปิดงบรายเดือน, ระบบควบคุมภายใน | 🔴 |
| 02 | [Riley](profiles/02-cfo/meetoo/team/02-riley.SOUL.md) | FP&A Analyst — จัดทำ budget, rolling forecast, วิเคราะห์ variance และส่งสัญญาณเตือนเมื่อผลเบี่ยงเป้า | 🔴 |
| 03 | [Morgan](profiles/02-cfo/meetoo/team/03-morgan.SOUL.md) | Financial Analyst — สร้าง financial model, scenario analysis, cash-flow insight เพื่อ C-suite | 🔴 |

### 03 — CMO (มาร์ค)

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [Growth Hacker](profiles/03-cmo/mark/team/01-growth-hacker.SOUL.md) | ออกแบบ growth loop — A/B testing, viral mechanics, funnel optimization ขับเคลื่อนด้วยข้อมูล | 🔴 |
| 02 | [Social Media Strategist](profiles/03-cmo/mark/team/02-social-media-strategist.SOUL.md) | สร้าง brand authority บน LinkedIn/Twitter — community building, thought leadership, เชื่อม social กับ B2B pipeline | 🔴 |
| 03 | [Content Creator](profiles/03-cmo/mark/team/03-content-creator.SOUL.md) | สร้าง content ทุกช่องทาง — SEO content, video scripts, editorial ที่ engage และ convert | 🔴 |

### 04 — Orchestrator (Hermes)

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [Project Shepherd](profiles/04-orchestrator/orchestrator/team/01-project-shepherd.SOUL.md) | จัดการโครงการข้ามสายงาน — ประสานทีม, บริหาร timeline และ risk, ให้ทุก stakeholder เดินทิศเดียวกัน | 🔴 |
| 02 | [Studio Producer](profiles/04-orchestrator/orchestrator/team/02-studio-producer.SOUL.md) | บริหาร portfolio โครงการสร้างสรรค์มูลค่าสูง — เชื่อม vision กับเป้าธุรกิจ, รักษาความสัมพันธ์ executive | 🔴 |
| 03 | [Studio Operations](profiles/04-orchestrator/orchestrator/team/03-studio-operations.SOUL.md) | ปฏิบัติการประจำวัน — ออกแบบ SOP, บริหาร vendor, เพิ่มประสิทธิภาพกระบวนการ ≥95% | 🔴 |

### 06 — Product (โปรดัค)

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [Alex — Product Manager](profiles/06-product/produck/team/01-product-manager.SOUL.md) | ดูแล product lifecycle ตั้งแต่ discovery ถึง launch — PRD, Opportunity Assessment, เชื่อม user/business/engineering | 🔴 |
| 02 | [Product Feedback Synthesizer](profiles/06-product/produck/team/02-product-feedback-synthesizer.SOUL.md) | รวบรวม user feedback จากทุกช่องทาง — แปลง qualitative เป็น priority เชิงปริมาณ ด้วย RICE/MoSCoW/Kano | 🔴 |
| 03 | [Product Sprint Prioritizer](profiles/06-product/produck/team/03-product-sprint-prioritizer.SOUL.md) | Agile sprint planning — จัดลำดับ feature, จัดการ dependency/risk, เพิ่ม team velocity และ business value | 🔴 |

### 07 — Engineering (ช่างฟูล)

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [สถาปนิกแบ็กเอนด์](profiles/07-engineering/changful/team/01-สถาปนิกแบ็กเอนด์.SOUL.md) | ออกแบบ backend ที่ scale ได้ — database architecture, API design, cloud infra, query <20ms | 🔴 |
| 02 | [นักพัฒนาอาวุโส](profiles/07-engineering/changful/team/02-นักพัฒนาอาวุโส.SOUL.md) | Full-stack senior dev — Laravel, Livewire, FluxUI, Three.js, animation และ micro-interaction | 🔴 |
| 03 | [สถาปนิกซอฟต์แวร์](profiles/07-engineering/changful/team/03-สถาปนิกซอฟต์แวร์.SOUL.md) | Domain-driven design — microservices/modular monolith/event-driven, วิเคราะห์ trade-offs, เขียน ADR | 🔴 |

### 08 — Design (ครีเอท)

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [นักวิจัย UX](profiles/08-design/kreet/team/01-nak-wijai-ux.SOUL.md) | วิจัยพฤติกรรมผู้ใช้ — usability testing, เชื่อม user data กับ design decision ให้ทีมทำงานบนหลักฐาน | 🔴 |
| 02 | [สถาปนิก UX](profiles/08-design/kreet/team/02-sathapanig-ux.SOUL.md) | UX Architecture — Design Systems, Layout Frameworks, Component Structures ที่ Dev นำไปใช้ได้จริง | 🔴 |
| 03 | [นักออกแบบ UI](profiles/08-design/kreet/team/03-nak-aukbaep-ui.SOUL.md) | Visual Design Systems — Component Library, pixel-perfect, WCAG AA, Design Tokens พร้อม Dev spec | 🔴 |

### 09 — UI Designer

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [UI Designer](profiles/09-ui-designer/ui-designer/team/01-ui-designer.SOUL.md) | Interface ระดับ pixel — Visual Design System, Component Library, Responsive Framework, Dev-ready spec | 🔴 |
| 02 | [UX Architect](profiles/09-ui-designer/ui-designer/team/02-ux-architect.SOUL.md) | CSS Design System + Layout Framework — Component Hierarchy ที่ scale ได้, รองรับ Light/Dark Theme | 🔴 |
| 03 | [UX Researcher](profiles/09-ui-designer/ui-designer/team/03-ux-researcher.SOUL.md) | วิจัย UX เชิงปริมาณและคุณภาพ — Usability Testing, แปลง User Insights เป็น design recommendation | 🔴 |

### 10 — QA (QA-ทีม)

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [API Tester](profiles/10-qa/qa-team/team/01-api-tester.SOUL.md) | ทดสอบ API ครบวงจร — functional, performance, security (OWASP Top 10), automated test suite บน CI/CD | 🔴 |
| 02 | [Accessibility Auditor](profiles/10-qa/qa-team/team/02-accessibility-auditor.SOUL.md) | ตรวจ accessibility ตามมาตรฐาน WCAG 2.2 — automated tools + assistive technology testing + code-level fix | 🔴 |
| 03 | [Test Results Analyzer](profiles/10-qa/qa-team/team/03-test-results-analyzer.SOUL.md) | วิเคราะห์ผลทดสอบด้วย statistical modeling — go/no-go release recommendation, quality trend tracking | 🔴 |

### 11 — Sales (เซลส์)

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [Deal Strategist](profiles/11-sales/sales/team/01-deal-strategist.SOUL.md) | กลยุทธ์ปิดดีล B2B — ใช้ MEDDPICC คัดกรอง deal, วางตำแหน่งแข่งขัน, เพิ่ม win rate | 🔴 |
| 02 | [Pipeline Analyst](profiles/11-sales/sales/team/02-pipeline-analyst.SOUL.md) | Revenue Operations — วิเคราะห์ pipeline velocity, deal quality scoring, forecast accuracy | 🔴 |
| 03 | [Outbound Strategist](profiles/11-sales/sales/team/03-outbound-strategist.SOUL.md) | Signal-based outbound — ออกแบบ prospecting จาก buying intent, วัดผลด้วย reply rate และ meeting booked | 🔴 |

### 12 — Support (ซัพพอร์ต)

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [Support Responder](profiles/12-support/support/team/01-support-responder.SOUL.md) | ด่านหน้าลูกค้าทุกช่องทาง — first-contact resolution 85%, ตอบกลับภายใน 2 ชั่วโมง | 🔴 |
| 02 | [Analytics Reporter](profiles/12-support/support/team/02-analytics-reporter.SOUL.md) | แปลง raw data เป็น insight — KPI dashboards, รายงานอัตโนมัติ, customer segmentation | 🔴 |
| 03 | [Executive Summary Generator](profiles/12-support/support/team/03-executive-summary-generator.SOUL.md) | สรุป executive-ready — McKinsey SCQA framework, 325-475 คำ, impact วัดได้ + next steps ชัดเจน | 🔴 |

### 13 — Legal (ตุลย์)

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [Compliance Auditor](profiles/13-legal/tulya/team/01-compliance-auditor.SOUL.md) | ตรวจสอบมาตรฐานความปลอดภัย — SOC 2, ISO 27001, HIPAA, PCI-DSS ตั้งแต่ gap analysis ถึง certification | 🔴 |
| 02 | [Legal Document Review](profiles/13-legal/tulya/team/02-legal-document-review.SOUL.md) | ตรวจสอบเอกสารกฎหมาย — สัญญา, ข้อตกลง, ระบุความเสี่ยงตามระดับ severity พร้อมสรุปให้ทนาย | 🔴 |
| 03 | [Legal Client Intake](profiles/13-legal/tulya/team/03-legal-client-intake.SOUL.md) | รับลูกค้าทางกฎหมาย — คัดกรอง, รวบรวมข้อมูลคดี, ตรวจ conflict of interest, ส่งต่อทนาย | 🔴 |

### 14 — Web3 (อัยวา)

| # | Agent | หน้าที่ | สถานะ |
|:-:|:------|:--------|:-----:|
| 01 | [⛓️ Smart Contract Engineer](profiles/14-web3/aywa/team/01-smart-contract-engineer.SOUL.md) | เขียน Solidity/Anchor — gas optimization, upgrade pattern, test coverage ≥90% ก่อนส่ง audit | 🟡 |
| 02 | [🛡️ Blockchain Security Auditor](profiles/14-web3/aywa/team/02-blockchain-security-auditor.SOUL.md) | audit contract ก่อน deploy — manual review + Slither/Mythril/Echidna + attack simulation | 🟡 |
| 03 | [📊 DeFi Protocol Analyst](profiles/14-web3/aywa/team/03-defi-protocol-analyst.SOUL.md) | วิเคราะห์ DeFi market — tokenomics design, on-chain analytics, risk assessment | 🟡 |
| 04 | [⚡ Solana Developer](profiles/14-web3/aywa/team/04-solana-developer.SOUL.md) | Solana specialist — Anchor programs (Rust), Web3.js/Solana.js, deploy devnet/mainnet | 🟡 |

## Docs

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — ภาพรวมระบบ + Hierarchy Order
- [`profiles/INDEX.md`](profiles/INDEX.md) — ดัชนี Profiles ทั้งหมด (เรียงตาม Hierarchy)
- [`CHANGELOG.md`](CHANGELOG.md) — บันทึกการเปลี่ยนแปลง
- [`decisions/`](decisions/) — ADR (Architecture Decision Records)

---

*SoloCorp OS — System First, Everything Follows*
