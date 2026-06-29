# Lab-solocorp-os2.4 — ภาพรวม Architecture

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

## 🏗️ Two-Tier Architecture (การควบคุม vs ข้อมูล)

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

## 📋 โครงสร้างทีม

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

## 📋 ภาพรวม Profiles (ลำดับตามลำดับชั้น)

| # | Profile | ชื่อ | รับผิดชอบ | สถานะ |
|:-:|:--------|:----|:----------|:-----:|
| 01 | **CEO** | [เทอโบ (Turbo)](/home/drsolodev/.hermes/profiles/01-ceo/SOUL.md) | Vision / Strategy / Final Decision | 🟢 |
| 02 | **CFO** | TBD | การเงิน / งบประมาณ / ลงทุน | ⏳ |
| 03 | **CMO** | TBD | การตลาด / Content / Brand | ⏳ |
| 04 | **Orchestrator** | TBD | SoloCorp System Pipeline | ⏳ |
| 05 | **Architect** | [พี่ทรงศักดิ์ (Songsak)](profiles/05-architect/01-head-of-architect.md) | สายพานกลาง / Central Bus | 🟡 |
| 06 | **Product** | TBD | ผลิตภัณฑ์ / Feature / Roadmap | ⏳ |
| 07 | **Engineering** | TBD | พัฒนา / โค้ด / เทคโนโลยี | ⏳ |
| 08 | **Design** | TBD | ออกแบบ / UI / Brand Visual | ⏳ |
| 09 | **UI Designer** | TBD | UI Design เฉพาะทาง | ⏳ |
| 10 | **QA** | TBD | ทดสอบ / คุณภาพ / Evidence | ⏳ |
| 11 | **Sales** | TBD | ขาย / ลูกค้า / รายได้ | ⏳ |
| 12 | **Support** | TBD | ช่วยเหลือลูกค้า | ⏳ |
| 13 | **Legal** | TBD | กฎหมาย / Compliance | ⏳ |
| 14 | **Default** | — | Fallback / Base Profile | ✅ |

## 🔁 Loop Runner (v0.5.0)

Auto-pilot loops ที่ execute จริง — ไม่ใช่แค่ rule ใน SOUL.md

```
loop_runner/
├── state.py          ← SQLite: last_run, failures per loop
├── runner.py         ← base Loop class (interval + execute)
├── main.py           ← cron entry point
└── loops/
    ├── daily_brief.py        L1 — CEO morning report (finance+brain)
    ├── subscription_audit.py L4 — CFO monthly sub scan
    └── brain_auto_commit.py  L4 — auto-commit brain/memory files
```

**Cron:** `*/30 * * * * python3 -m loop_runner.main`

| Loop | Trust | Interval | Action |
|------|-------|----------|--------|
| daily_brief | L1 | 20h | finance+brain → stdout report |
| subscription_audit | L4 | 30d | scan recurring charges |
| brain_auto_commit | L4 | 1h | git commit brain files only |

→ ADR: `decisions/ADR-005-loop-runner.md`

---

## 🎨 Open Design Integration (v0.5.0)

Read-only bridge จาก Central Bus → Open Design daemon (port 41551)

**Permission model:**
| Department | Tools allowed |
|-----------|---------------|
| design | ทุก tool (6 tools) |
| ui_designer | get_artifact, get_file, search_files |
| engineering | get_artifact, get_file, search_files |
| qa | get_artifact, get_file |
| cfo/sales/legal/web3/support | ❌ blocked |

Files: `central_bus/open_design.py`, `bus/system/open_design_config.json`

---

## 🔗 แหล่งข้อมูลหลัก

- **โฟลเดอร์หลัก:** `/home/drsolodev/projects/Lab-solocorp-os2.4/`
- **Git:** [`Dr-SoloDev/Lab-solocorp-os2.4`](https://github.com/Dr-SoloDev/Lab-solocorp-os2.4) (Private)
- **Hermes Profiles:** `/home/drsolodev/.hermes/profiles/<NN-name>/`
- **การกำหนดเวอร์ชัน:** SemVer ผ่าน CHANGELOG.md + Git tags
