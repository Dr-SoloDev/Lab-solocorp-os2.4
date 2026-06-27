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
| `01-ceo` | **CEO** | [เทอโบ ไชยศรีรัมย์ (Turbo)](../01-ceo/SOUL.md) | 🟢 |
| `02-cfo` | **CFO** | TBD | ⏳ |
| `03-cmo` | **CMO** | TBD | ⏳ |

## System / Pipeline

| # | Profile | ชื่อ | สถานะ |
|:-:|:--------|:----|:-----:|
| `04-orchestrator` | **Orchestrator** | TBD | ⏳ |

## Department Heads

| # | Profile | หัวหน้าแผนก | รับผิดชอบ | สถานะ |
|:-:|:--------|:-----------|:----------|:-----:|
| `05-architect` | **Architect** | [พี่ทรงศักดิ์ (Songsak)](05-architect/01-head-of-architect.md) | สายพานกลาง / Central Bus | 🟡 |
| `06-product` | **Product** | TBD | ผลิตภัณฑ์ / Feature / Roadmap | ⏳ |
| `07-engineering` | **Engineering** | TBD | พัฒนา / โค้ด / เทคโนโลยี | ⏳ |
| `08-design` | **Design** | TBD | ออกแบบ / UI / Brand Visual | ⏳ |
| `09-ui-designer` | **UI Designer** | TBD | UI Design เฉพาะทาง | ⏳ |
| `10-qa` | **QA** | TBD | ทดสอบ / คุณภาพ / Evidence | ⏳ |
| `11-sales` | **Sales** | TBD | ขาย / ลูกค้า / รายได้ | ⏳ |
| `12-support` | **Support** | TBD | ช่วยเหลือลูกค้า | ⏳ |
| `13-legal` | **Legal** | TBD | กฎหมาย / Compliance | ⏳ |

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
