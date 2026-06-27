# Lab-solocorp-os2.4 — Architecture Overview

> ระบบออกแบบ Department Architecture สำหรับ SoloCorp OS
> เริ่มต้น: 2026-06-26

## 🏛️ 3 Pillars ของ Department Head Design

```
╔══════════════════════════════════════════╗
║       1.  ไม่ทำงานเอง                    ║
║          (Delegate, Not Do)             ║
╠══════════════════════════════════════════╣
║       2.  สกิลผู้นำบริหารแผนก            ║
║          (Leadership & Management)      ║
╠══════════════════════════════════════════╣
║       3.  OWNERSHIP MINDSET             ║
║          (เจ้าของแผนก ไม่ใช่ลูกจ้าง)      ║
╚══════════════════════════════════════════╝
```

## 🏗️ Two-Tier Architecture (Control vs Data)

```
┌────────────────────────────────────────────────┐
│          CONTROL LAYER (ผ่านหัวหน้า)             │
│                                                 │
│  Status, Goal, Exception, Approval, Handoff     │
│  → "งานเสร็จแล้ว" "มีปัญหา" "ขออนุมัติ"         │
│                                                 │
│  🧑‍💼 Head A ──(status)──→ 🧑‍💼 Head B         │
│       ↑                       ↑                 │
│       │  เท่าที่จำเป็นเท่านั้น  │                 │
└───────┼───────────────────────┼─────────────────┘
        ↓                       ↓
┌────────────────────────────────────────────────┐
│          DATA LAYER (Auto - ไม่ผ่านหัวหน้า)     │
│                                                 │
│  Code, Design, Reports, Docs, Raw Outputs       │
│  → "Central Bus / Shared State"                 │
│                                                 │
│  [Agent A] ──(write)──→ 📦 CENTRAL BUS          │
│                           └──(notify)──→ [Agent B]
│                                                 │
│  หัวหน้าเห็นแค่: "Work Item X completed ✓"      │
└────────────────────────────────────────────────┘
```

## 📋 Team Structure

### Architect Department — ทีมของพี่ทรงศักดิ์

พี่ทรงศักดิ์ (Head of Architect) มีทีม 5 Pipeline Agents ที่ช่วยดูแลสายพาน:

```
┌─────────────────────────────────────────────────────────────┐
│              พี่ทรงศักดิ์ (Head of Architect)                   │
│                ─── Owner of Central Bus ───                  │
├───────────┬──────────┬──────────┬──────────┬────────────────┤
│  📋        │  🗺️      │  🎛️      │  🧭      │  ⏰            │
│ Pipeline   │ Routing  │ Monitor  │Exception │ Cron Pipeline │
│ Auditor    │Config    │Watchdog  │Triage    │ Agent         │
│            │Agent     │          │Agent     │               │
├───────────┼──────────┼──────────┼──────────┼────────────────┤
│ GNAP      │ GNAP     │ model-   │ AXME     │ Temporal      │
│ Audit     │ MagiC    │ watchdog │ MagiC    │ n8n           │
│ Trail     │ Routing  │ TeamHero │ CoS/WO   │ Workflows     │
└───────────┴──────────┴──────────┴──────────┴────────────────┘
```

| # | Agent | Protocol/Pattern | Mission |
|:-:|:------|:-----------------|:--------|
| 1 | [📋 Pipeline Auditor](profiles/architect/phee-thongsak/team/01-pipeline-auditor.SOUL.md) | GNAP + jira-steward + compliance-auditor | ตรวจสอบ audit trail ทุก handoff |
| 2 | [🗺️ Routing Config Agent](profiles/architect/phee-thongsak/team/02-routing-config-agent.SOUL.md) | GNAP + MagiC + workflow-architect | กำหนดเส้นทาง + circuit breaker |
| 3 | [🎛️ Monitor Watchdog](profiles/architect/phee-thongsak/team/03-monitor-watchdog.SOUL.md) | model-watchdog + TeamHero + agents-orchestrator | เฝ้าสุขภาพ pipeline real-time |
| 4 | [🧭 Exception Triage Agent](profiles/architect/phee-thongsak/team/04-exception-triage-agent.SOUL.md) | AXME + MagiC + chief-of-staff + workflow-optimizer | กู้ชีพ pipeline — 80% auto-resolve |
| 5 | [⏰ Cron Pipeline Agent](profiles/architect/phee-thongsak/team/05-cron-pipeline-agent.SOUL.md) | Temporal + n8n | สั่งรัน pipeline ตาม schedule |

> **Key Design**: 5 Agents นี้ไม่ทำงานคนเดียว — พี่ทรงศักดิ์เป็นคนสั่ง แต่ละ Agent มี Mission เฉพาะ:
> - 📋 ตรวจสอบ **หลัง** handoff → **Pipeline Auditor**
> - 🗺️ กำหนด **ก่อน** pipeline เริ่ม → **Routing Config Agent**
> - 🎛️ เฝ้าระหว่าง pipeline วิ่ง → **Monitor Watchdog**
> - 🧭 จัดการ exception → **Exception Triage Agent**
> - ⏰ รันตาม schedule → **Cron Pipeline Agent**

## 📋 ภาพรวม Profiles

| # | Profile | หัวหน้าแผนก | สถานะ |
|---|---------|-----------|--------|
| 01 | CEO | [เทอโบ (Turbo)](profiles/../ceo/SOUL.md) | 🟢 Design เสร็จ |
| 02 | CFO | TBD | ⏳ รอ |
| 03 | CMO | TBD | ⏳ รอ |
| 04 | **Architect** | [พี่ทรงศักดิ์ (Songsak)](profiles/architect/01-head-of-architect.md) | 🟢 Design เสร็จ — รอ Implement |
| 05 | Design | TBD | ⏳ รอ |
| 06 | Engineering | TBD | ⏳ รอ |
| 07 | Legal | TBD | ⏳ รอ |
| 08 | Product | TBD | ⏳ รอ |
| 09 | QA | TBD | ⏳ รอ |
| 10 | Sales | TBD | ⏳ รอ |
| 11 | Support | TBD | ⏳ รอ |
| 12 | UI Designer | TBD | ⏳ รอ |

## 🔗 Source of Truth

- **Directory Root:** `/home/drsolodev/projects/Lab-solocorp-os2.4/`
- **Git:** TBD
- **Versioning:** SemVer ผ่าน CHANGELOG.md + Git tags
