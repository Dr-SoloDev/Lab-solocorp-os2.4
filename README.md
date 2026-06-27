# SoloCorp OS 2.4

> **ระบบ Department Architecture สำหรับ Hermes Agent**
> Human → CEO → C-Level → Orchestrator → Department Heads (→ Agents)

## Hierarchy

```
Dr.solodev (Human/Owner)
  └── CEO (เทอโบ — Supreme AI Authority)
       ├── CFO (วาเลอร์ — การเงิน/งบประมาณ)
       ├── CMO (วิวิด — การตลาด/Content)
       ├── Orchestrator (SoloCorp System Pipeline)
       └── Department Heads
            ├── 05-architect  — พี่ทรงศักดิ์ (สายพานกลาง)
            ├── 06-product    — TBD
            ├── 07-engineering — TBD
            ├── 08-design     — TBD
            ├── 09-ui-designer — TBD
            ├── 10-qa         — TBD
            ├── 11-sales      — TBD
            ├── 12-support    — TBD
            └── 13-legal      — TBD
                   └── 14-default (Fallback)
```

## Core Principles

1. **3 Pillars** — หัวหน้าไม่ทำงานเอง, Leadership Skills, Ownership Mindset
2. **Two-Tier Architecture** — Control Layer (Head) vs Data Layer (Central Bus)
3. **Head-to-Head Handoff** — 80% ส่งตรง, 5% Escalate

## Profile Order (Hermes)

| ลำดับ | Profile Directory | ชื่อ | สถานะ |
|:----:|:-----------------|:----|:-----:|
| 01 | `01-ceo` | เทอโบ CEO | 🟢 |
| 02 | `02-cfo` | TBD | ⏳ |
| 03 | `03-cmo` | TBD | ⏳ |
| 04 | `04-orchestrator` | TBD | ⏳ |
| 05 | `05-architect` | พี่ทรงศักดิ์ | 🟡 |
| 06 | `06-product` | TBD | ⏳ |
| 07 | `07-engineering` | TBD | ⏳ |
| 08 | `08-design` | TBD | ⏳ |
| 09 | `09-ui-designer` | TBD | ⏳ |
| 10 | `10-qa` | TBD | ⏳ |
| 11 | `11-sales` | TBD | ⏳ |
| 12 | `12-support` | TBD | ⏳ |
| 13 | `13-legal` | TBD | ⏳ |
| 14 | `default` | Fallback | ✅ |

## Status

| Phase | Version | Status |
|:------|:-------:|:------:|
| Foundation | v0.1.0–v0.2.0 | ✅ |
| Core Sub-agents | v0.3.0 | ✅ |
| Central Bus + Enablers | v0.4.0 | ✅ |
| Dashboard + Compliance | v0.5.0 | 🔴 |
| Department Expansion | v1.0.0 | ⏳ |

## Docs

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — ภาพรวมระบบ + Hierarchy Order
- [`profiles/INDEX.md`](profiles/INDEX.md) — ดัชนี Profiles ทั้งหมด (เรียงตาม Hierarchy)
- [`CHANGELOG.md`](CHANGELOG.md) — บันทึกการเปลี่ยนแปลง
- [`decisions/`](decisions/) — ADR (Architecture Decision Records)

---

*SoloCorp OS — System First, Everything Follows*
