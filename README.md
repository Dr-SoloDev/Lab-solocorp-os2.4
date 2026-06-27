# SoloCorp OS 2.4

> **ระบบออกแบบ Department Architecture สำหรับ Hermes Agent**
> Human → CEO → C-Level → Department Heads → Specialist Agents

## Hierarchy

```
Dr.solodev (Human/Owner)
  └── CEO (เทอโบ — Supreme AI Authority)
       ├── CFO (การเงิน/งบประมาณ)
       ├── CMO (การตลาด/Content)
       └── Department Heads
            ├── Architect (พี่ทรงศักดิ์ — สายพานกลาง)
            ├── Design
            ├── Engineering
            ├── Legal
            ├── Product
            ├── QA
            ├── Sales
            ├── Support
            └── UI Designer
```

## Core Principles

1. **3 Pillars** — หัวหน้าไม่ทำงานเอง, Leadership Skills, Ownership Mindset
2. **Two-Tier Architecture** — Control Layer (Head) vs Data Layer (Central Bus)
3. **Head-to-Head Handoff** — 80% ส่งตรง, 5% Escalate

## Status

| Phase | Version | Status |
|:------|:-------:|:------:|
| Foundation | v0.1.0–v0.2.0 | ✅ |
| Core Sub-agents | v0.3.0 | ✅ |
| Central Bus + Enablers | v0.4.0 | ✅ |
| Dashboard + Compliance | v0.5.0 | 🔴 |
| Department Expansion | v1.0.0 | ⏳ |

## Docs

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — ภาพรวมระบบ
- [`profiles/INDEX.md`](profiles/INDEX.md) — ดัชนี Profiles ทั้งหมด
- [`CHANGELOG.md`](CHANGELOG.md) — บันทึกการเปลี่ยนแปลง
- [`decisions/`](decisions/) — ADR (Architecture Decision Records)

---

*SoloCorp OS — System First, Everything Follows*
