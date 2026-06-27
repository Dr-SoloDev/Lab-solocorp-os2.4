# Lab-solocorp-os2.4 — Profile Index

> ดัชนี Profile Design ทั้งหมดในระบบ

---

## Status Legend

| สัญลักษณ์ | ความหมาย |
|:---------:|:---------|
| 🔴 | กำลังออกแบบ |
| ⏳ | รอออกแบบ |
| 🟡 | Design เสร็จ — รอ Implement |
| ✅ | Implement แล้ว |

---

## C-Level

| # | Profile | ชื่อ | รับผิดชอบ | สถานะ |
|:-:|:--------|:----|:----------|:-----:|
| 01 | **CEO** | [เทอโบ (Turbo)](../ceo/SOUL.md) | Vision / Strategy / Final Decision | 🟢 |
| 02 | **CFO** | TBD | การเงิน / งบประมาณ / ลงทุน | ⏳ |
| 03 | **CMO** | TBD | การตลาด / Content / Brand | ⏳ |

## Department Heads

| # | Profile | ชื่อ | รับผิดชอบ | สถานะ |
|:-:|:--------|:----|:----------|:-----:|
| 01 | **Head of Architect** | [พี่ทรงศักดิ์ (Songsak)](architect/01-head-of-architect.md) | สายพานกลางทั้งองค์กร | 🟢 |
| 02 | **Head of Design** | TBD | ออกแบบ / UI / Brand Visual | ⏳ |
| 03 | **Head of Engineering** | TBD | พัฒนา / โค้ด / เทคโนโลยี | ⏳ |
| 04 | **Head of Legal** | TBD | กฎหมาย / Compliance | ⏳ |
| 05 | **Head of Product** | TBD | ผลิตภัณฑ์ / Feature / Roadmap | ⏳ |
| 06 | **Head of QA** | TBD | ทดสอบ / คุณภาพ / Evidence | ⏳ |
| 07 | **Head of Sales** | TBD | ขาย / ลูกค้า / รายได้ | ⏳ |
| 08 | **Head of Support** | TBD | ช่วยเหลือลูกค้า | ⏳ |
| 09 | **Head of UI Designer** | TBD | UI Design เฉพาะทาง | ⏳ |

## Team — Architect Department (พี่ทรงศักดิ์)

| # | Profile | Protocol/Pattern | หน้าที่ | สถานะ |
|:-:|:--------|:-----------------|:-------|:-----:|
| 01 | **[📋 Pipeline Auditor](architect/phee-thongsak/team/01-pipeline-auditor.SOUL.md)** | GNAP + jira-steward + compliance-auditor | Audit Trail, Compliance Check, Evidence | 🔴 |
| 02 | **[🗺️ Routing Config Agent](architect/phee-thongsak/team/02-routing-config-agent.SOUL.md)** | GNAP + MagiC + workflow-architect | Routing Rules, Circuit Breaker, DAG | 🔴 |
| 03 | **[🎛️ Monitor Watchdog](architect/phee-thongsak/team/03-monitor-watchdog.SOUL.md)** | model-watchdog + TeamHero + agents-orchestrator | Health Probe, SLA, Dashboard | 🔴 |
| 04 | **[🧭 Exception Triage Agent](architect/phee-thongsak/team/04-exception-triage-agent.SOUL.md)** | AXME + MagiC + chief-of-staff + workflow-optimizer | Triage, RCA, Auto-Resolve | 🔴 |
| 05 | **[⏰ Cron Pipeline Agent](architect/phee-thongsak/team/05-cron-pipeline-agent.SOUL.md)** | Temporal + n8n | Schedule, Durable Execution | 🔴 |

---

## หมายเหตุ

- แต่ละ Profile = 1 Department Head ที่มีความรู้เฉพาะด้าน
- หัวหน้า **ไม่ทำงานเอง** — สั่งงาน Specialist Agent ผ่าน `delegate_task`
- หัวหน้าต้องมี **Ownership Mindset** — เจ้าของแผนก ไม่ใช่ลูกจ้าง
