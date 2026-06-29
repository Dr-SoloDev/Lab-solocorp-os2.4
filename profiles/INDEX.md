# Lab-solocorp-os2.4 — Profile Index

> ดัชนี Profile ทั้งหมดในระบบ SoloCorp OS
> ลำดับตาม Hierarchy: CEO → CFO → CMO → Orchestrator → Architect → Product → Engineering → Design → UI-Designer → QA → Sales → Support → Legal → Default

---

## Status Legend

| สัญลักษณ์ | ความหมาย |
|:---------:|:---------|
| 🔴 กำลังออกแบบ / ระหว่าง Implement |
| ⏳ รอออกแบบ |
| 🟡 Design เสร็จ — รอ Implement |
| ✅ Implement แล้ว |
| 🟢 ใช้งานจริง |

---

## C-Level

| # | Profile | ชื่อ | สถานะ |
|:-:|:--------|:----|:-----:|
| `01-ceo` | **CEO** | [เทอโบ ไชยศรีรัมย์ (Turbo)](01-ceo/SOUL.md) | 🟢 |
| `02-cfo` | **CFO** | [meetoo](02-cfo/SOUL.md) | 🟢 |
| `03-cmo` | **CMO** | [มาร์ค](03-cmo/SOUL.md) | 🟢 |

## System / Pipeline

| # | Profile | ชื่อ | สถานะ |
|:-:|:--------|:----|:-----:|
| `04-orchestrator` | **Orchestrator** | [Hermes-Orchestrator](04-orchestrator/SOUL.md) | 🟢 |

## Department Heads

| # | Profile | หัวหน้าแผนก | รับผิดชอบ | สถานะ |
|:-:|:--------|:-----------|:----------|:-----:|
| `05-architect` | **Architect** | [พี่ทรงศักดิ์ (Songsak)](05-architect/01-head-of-architect.md) | สายพานกลาง / Central Bus | 🟢 |
|| `06-product` | **Product** | [โปรดัค](06-product/SOUL.md) | ผลิตภัณฑ์ / Feature / Roadmap | 🟢 |
|| `07-engineering` | **Engineering** | [ช่างฟูล](07-engineering/SOUL.md) | พัฒนา / โค้ด / เทคโนโลยี | 🟢 |
|| `08-design` | **Design** | [ครีเอท](08-design/SOUL.md) | ออกแบบ / UI / Brand Visual | 🟢 |
|| `09-ui-designer` | **UI Designer** | [UI-Designer](09-ui-designer/SOUL.md) | UI Design เฉพาะทาง | 🟢 |
|| `10-qa` | **QA** | [QA-ทีม](10-qa/SOUL.md) | ทดสอบ / คุณภาพ / Evidence | 🟢 |
|| `11-sales` | **Sales** | [เซลส์](11-sales/SOUL.md) | ขาย / ลูกค้า / รายได้ | 🟢 |
|| `12-support` | **Support** | [ซัพพอร์ต](12-support/SOUL.md) | ช่วยเหลือลูกค้า | 🟢 |
|| `13-legal` | **Legal** | [ตุลย์](13-legal/SOUL.md) | กฎหมาย / Compliance | 🟢 |

| `14-web3` | **Web3 & DeFi** | [อัยวา](14-web3/SOUL.md) | Blockchain/DeFi/Solana | 🟢 |

## Base Profile

| # | Profile | สถานะ |
|:-:|:--------|:-----:|
| `default` | **Default (Fallback)** | ✅ |

---

## Team — Architect Department (พี่ทรงศักดิ์)

| # | Profile | Protocol/Pattern | หน้าที่ | สถานะ |
|:-:|:--------|:-----------------|:-------|:-----:|
| 01 | **[📋 Pipeline Auditor](05-architect/phee-thongsak/team/01-pipeline-auditor.SOUL.md)** | GNAP + jira-steward + compliance-auditor | Audit Trail, Compliance Check, Evidence | 🔴 |
| 02 | **[🗺️ Routing Config Agent](05-architect/phee-thongsak/team/02-routing-config-agent.SOUL.md)** | GNAP + MagiC + workflow-architect | Routing Rules, Circuit Breaker, DAG | 🔴 |
| 03 | **[🎛️ Monitor Watchdog](05-architect/phee-thongsak/team/03-monitor-watchdog.SOUL.md)** | model-watchdog + TeamHero + agents-orchestrator | Health Probe, SLA, Dashboard | 🔴 |
| 04 | **[🧭 Exception Triage Agent](05-architect/phee-thongsak/team/04-exception-triage-agent.SOUL.md)** | AXME + MagiC + chief-of-staff + workflow-optimizer | Triage, RCA, Auto-Resolve | 🔴 |
| 05 | **[⏰ Cron Pipeline Agent](05-architect/phee-thongsak/team/05-cron-pipeline-agent.SOUL.md)** | Temporal + n8n | Schedule, Durable Execution | 🔴 |

> **หมายเหตุ:** paths ภายใน repo ใช้เฉพาะสำหรับ design docs จริง — ไม่ใช่ symlink ไปยัง Hermes profiles จริง

---

## หมายเหตุ

- Profile naming convention: `NN-name` (NN = ลำดับ Hierarchy)
- แต่ละ Profile = 1 Department Head ที่มีความรู้เฉพาะด้าน
- หัวหน้า **ไม่ทำงานเอง** — สั่งงาน Specialist Agent ผ่าน `delegate_task`
- หัวหน้าต้องมี **Ownership Mindset** — เจ้าของแผนก ไม่ใช่ลูกจ้าง

---

## ทีมในแต่ละแผนก

### 02 — CFO (meetoo)

| # | Agent | สถานะ |
|:-:|:------|:-----:|
| 01 | [dana](02-cfo/meetoo/team/01-dana.SOUL.md) | 🔴 |
| 02 | [riley](02-cfo/meetoo/team/02-riley.SOUL.md) | 🔴 |
| 03 | [morgan](02-cfo/meetoo/team/03-morgan.SOUL.md) | 🔴 |

### 03 — CMO (mark)

| # | Agent | สถานะ |
|:-:|:------|:-----:|
| 01 | [growth-hacker](03-cmo/mark/team/01-growth-hacker.SOUL.md) | 🔴 |
| 02 | [social-media-strategist](03-cmo/mark/team/02-social-media-strategist.SOUL.md) | 🔴 |
| 03 | [content-creator](03-cmo/mark/team/03-content-creator.SOUL.md) | 🔴 |

### 04 — Orchestrator

| # | Agent | สถานะ |
|:-:|:------|:-----:|
| 01 | [project-shepherd](04-orchestrator/orchestrator/team/01-project-shepherd.SOUL.md) | 🔴 |
| 02 | [studio-producer](04-orchestrator/orchestrator/team/02-studio-producer.SOUL.md) | 🔴 |
| 03 | [studio-operations](04-orchestrator/orchestrator/team/03-studio-operations.SOUL.md) | 🔴 |

### 06 — Product (produck)

| # | Agent | สถานะ |
|:-:|:------|:-----:|
| 01 | [product-manager](06-product/produck/team/01-product-manager.SOUL.md) | 🔴 |
| 02 | [product-feedback-synthesizer](06-product/produck/team/02-product-feedback-synthesizer.SOUL.md) | 🔴 |
| 03 | [product-sprint-prioritizer](06-product/produck/team/03-product-sprint-prioritizer.SOUL.md) | 🔴 |

### 07 — Engineering (changful)

| # | Agent | สถานะ |
|:-:|:------|:-----:|
| 01 | [สถาปนิกแบ็กเอนด์](07-engineering/changful/team/01-สถาปนิกแบ็กเอนด์.SOUL.md) | 🔴 |
| 02 | [นักพัฒนาอาวุโส](07-engineering/changful/team/02-นักพัฒนาอาวุโส.SOUL.md) | 🔴 |
| 03 | [สถาปนิกซอฟต์แวร์](07-engineering/changful/team/03-สถาปนิกซอฟต์แวร์.SOUL.md) | 🔴 |

### 08 — Design (kreet)

| # | Agent | สถานะ |
|:-:|:------|:-----:|
| 01 | [nak-wijai-ux](08-design/kreet/team/01-nak-wijai-ux.SOUL.md) | 🔴 |
| 02 | [sathapanig-ux](08-design/kreet/team/02-sathapanig-ux.SOUL.md) | 🔴 |
| 03 | [nak-aukbaep-ui](08-design/kreet/team/03-nak-aukbaep-ui.SOUL.md) | 🔴 |

### 09 — UI Designer

| # | Agent | สถานะ |
|:-:|:------|:-----:|
| 01 | [ui-designer](09-ui-designer/ui-designer/team/01-ui-designer.SOUL.md) | 🔴 |
| 02 | [ux-architect](09-ui-designer/ui-designer/team/02-ux-architect.SOUL.md) | 🔴 |
| 03 | [ux-researcher](09-ui-designer/ui-designer/team/03-ux-researcher.SOUL.md) | 🔴 |

### 10 — QA

| # | Agent | สถานะ |
|:-:|:------|:-----:|
| 01 | [api-tester](10-qa/qa-team/team/01-api-tester.SOUL.md) | 🔴 |
| 02 | [accessibility-auditor](10-qa/qa-team/team/02-accessibility-auditor.SOUL.md) | 🔴 |
| 03 | [test-results-analyzer](10-qa/qa-team/team/03-test-results-analyzer.SOUL.md) | 🔴 |

### 11 — Sales

| # | Agent | สถานะ |
|:-:|:------|:-----:|
| 01 | [deal-strategist](11-sales/sales/team/01-deal-strategist.SOUL.md) | 🔴 |
| 02 | [pipeline-analyst](11-sales/sales/team/02-pipeline-analyst.SOUL.md) | 🔴 |
| 03 | [outbound-strategist](11-sales/sales/team/03-outbound-strategist.SOUL.md) | 🔴 |

### 12 — Support

| # | Agent | สถานะ |
|:-:|:------|:-----:|
| 01 | [support-responder](12-support/support/team/01-support-responder.SOUL.md) | 🔴 |
| 02 | [analytics-reporter](12-support/support/team/02-analytics-reporter.SOUL.md) | 🔴 |
| 03 | [executive-summary-generator](12-support/support/team/03-executive-summary-generator.SOUL.md) | 🔴 |

### 13 — Legal (tulya)

| # | Agent | สถานะ |
|:-:|:------|:-----:|
| 01 | [compliance-auditor](13-legal/tulya/team/01-compliance-auditor.SOUL.md) | 🔴 |
| 02 | [legal-document-review](13-legal/tulya/team/02-legal-document-review.SOUL.md) | 🔴 |
| 03 | [legal-client-intake](13-legal/tulya/team/03-legal-client-intake.SOUL.md) | 🔴 |

### 14 — Web3 (อัยวา)

| # | Agent | สถานะ |
|:-:|:------|:-----:|
| 01 | [smart-contract-engineer](14-web3/aywa/team/01-smart-contract-engineer.SOUL.md) | 🟡 |
| 02 | [blockchain-security-auditor](14-web3/aywa/team/02-blockchain-security-auditor.SOUL.md) | 🟡 |
| 03 | [defi-protocol-analyst](14-web3/aywa/team/03-defi-protocol-analyst.SOUL.md) | 🟡 |
| 04 | [solana-developer](14-web3/aywa/team/04-solana-developer.SOUL.md) | 🟡 |
