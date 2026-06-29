# SoloCorp OS 2.4 — คู่มือเริ่มต้น

> สำหรับผู้ที่เข้ามาใหม่และต้องการเข้าใจระบบทั้งหมดอย่างรวดเร็ว

---

## SoloCorp OS คืออะไร

SoloCorp OS คือ **โครงสร้างองค์กร AI agent** ที่ออกแบบมาเพื่อ startup ที่ต้องการให้ AI ทำงานแทนทีมจริง ไม่ใช่แค่เป็น chatbot ตอบคำถาม

แนวคิดหลักคือ: แทนที่จะให้ AI ทำทุกอย่างคนเดียว ระบบนี้แบ่ง AI ออกเป็น "แผนก" — แต่ละแผนกมีหัวหน้าที่มีความรู้เฉพาะทาง และมีทีม specialist agent คอยทำงานให้

---

## ทำไมถึงต้องมีระบบนี้

ปัญหาของ AI agent ทั่วไปคือ "ทำทุกอย่างได้หมด แต่ไม่มีใครรับผิดชอบอะไรจริงๆ" SoloCorp OS แก้ปัญหานี้ด้วยการ:

- **กำหนด Ownership** — แต่ละแผนกมีหัวหน้าที่ "เป็นเจ้าของ" งานชัดเจน
- **Delegate ไม่ใช่ Do** — หัวหน้าแผนกไม่ทำงานเอง สั่งงานผ่าน specialist team
- **Head-to-Head Handoff** — งานส่งต่อระหว่างแผนกผ่านหัวหน้า ไม่ปะปนกัน

---

## โครงสร้าง Hierarchy

```
Dr.solodev (Human/Owner)
  └── เทอโบ — CEO (ตัดสินใจสูงสุด, Vision)
       ├── meetoo — CFO (การเงิน, งบประมาณ)
       ├── มาร์ค — CMO (การตลาด, Content)
       ├── Hermes — Orchestrator (ประสานระบบ)
       └── Department Heads (05–14)
```

Human เป็นเจ้าของระบบ สั่งงานผ่าน CEO เท่านั้น CEO กระจายงานลงมาตาม chain of command ของตัวเอง

---

## Two-Tier Architecture

ระบบแยกการไหลของข้อมูลออกเป็นสองชั้น:

**Control Layer** — หัวหน้าคุยกับหัวหน้า: ส่ง status, อนุมัติ, escalate เมื่อจำเป็น

**Data Layer (Central Bus)** — งานจริง (โค้ด, design, รายงาน) ไหลผ่าน Central Bus โดยอัตโนมัติ ไม่ผ่านหัวหน้า หัวหน้าเห็นแค่ว่า "งานเสร็จแล้ว" ไม่ต้องส่งไฟล์เอง

---

## แต่ละแผนกทำอะไร

| # | แผนก | หัวหน้า | หน้าที่ |
|:-:|:-----|:--------|:--------|
| 01 | **CEO** | เทอโบ | Vision และ Final Decision ของบริษัท |
| 02 | **CFO** | meetoo | การเงิน, งบประมาณ, การลงทุน |
| 03 | **CMO** | มาร์ค | การตลาด, Content, Brand |
| 04 | **Orchestrator** | Hermes | ประสาน pipeline และ cross-department workflow |
| 05 | **Architect** | พี่ทรงศักดิ์ | ดูแล Central Bus — routing, monitoring, exception handling |
| 06 | **Product** | โปรดัค | Feature roadmap, PRD, ส่งต่อ Engineering |
| 07 | **Engineering** | ช่างฟูล | พัฒนาระบบ backend/frontend/architecture |
| 08 | **Design** | ครีเอท | UX Research, UX Architecture, Visual Design System |
| 09 | **UI Designer** | UI-Designer | Interface และ Component Library ระดับ pixel |
| 10 | **QA** | QA-ทีม | ทดสอบ API, Accessibility, วิเคราะห์ผลทดสอบ |
| 11 | **Sales** | เซลส์ | B2B deal strategy, pipeline analytics, outbound |
| 12 | **Support** | ซัพพอร์ต | ดูแลลูกค้า, analytics, executive summaries |
| 13 | **Legal** | ตุลย์ | Compliance audit, legal document review, client intake |
| 14 | **Web3** | อัยวา | Smart contracts, security audit, DeFi/Solana |

แต่ละแผนกมี specialist team 3–5 agent ที่รับงานจากหัวหน้าโดยตรง

---

## สถานะปัจจุบัน

ระบบอยู่ในขั้น **deployed** — profiles ทั้ง 14 แผนก deploy สู่ Hermes Profiles จริงแล้ว, loop runner ทำงานบน cron

| Phase | สถานะ |
|:------|:-----:|
| Foundation — ADRs, CEO Profile, Architecture | ✅ เสร็จ |
| Architect Department (พี่ทรงศักดิ์ + 5 pipeline agents) | ✅ เสร็จ |
| Department Profiles ทั้ง 14 แผนก + Teams | ✅ Deploy สู่ Hermes |
| Loop Runner (auto-pilot cron) | ✅ ทำงานจริงทุก 30 นาที |
| Central Bus Agent + Context Optimizer | 🔴 ยังไม่เริ่ม |
| Pipeline Dashboard + QA Gate | ⏳ รอ |

งานถัดไปที่สำคัญที่สุดคือการสร้าง **Central Bus** ซึ่งเป็นหัวใจของ Data Layer

---

## โครงสร้าง Repo

```
|`Lab-solocorp-os2.4/
├── profiles/
│   ├── INDEX.md              # ดัชนี profiles ทั้งหมด — เริ่มอ่านที่นี่
│   ├── 01-ceo/ → 14-web3/   # แต่ละแผนก: SOUL.md + config + skills + team/
│   └── default/              # Fallback profile
├── loop_runner/              # Auto-pilot cron loops (รันทุก 30 นาที)
│   ├── main.py               # Cron entry point
│   ├── runner.py             # Base Loop class
│   ├── state.py              # SQLite persistent state
│   └── loops/                # daily_brief, brain_auto_commit, pipeline_executor
├── scripts/                  # Utility scripts (build-profiles, pipeline utils)
├── tests/                    # Phase test suites (phase 1–4)
├── decisions/                # ADR (Architecture Decision Records)
├── bus/                      # Central Bus design docs
├── central_bus/              # Central Bus implementation
├── ARCHITECTURE.md           # ภาพรวมระบบและ design principles
├── README.md                 # Hierarchy + สถานะ + team listings
├── CHANGELOG.md              # บันทึกการเปลี่ยนแปลง
└── PROJECT.md                # คู่มือเริ่มต้น (ไฟล์นี้)
```

**จุดเริ่มต้นแนะนำ:**
1. อ่าน `ARCHITECTURE.md` เพื่อเข้าใจ design principles
2. ดู `profiles/INDEX.md` เพื่อรู้ว่ามี agent ใดบ้างและสถานะปัจจุบัน
3. เปิด `profiles/01-ceo/SOUL.md` เพื่อดูตัวอย่าง profile ที่ implement แล้ว
4. ดู `profiles/05-architect/` เพื่อดูตัวอย่างแผนกที่ออกแบบครบสมบูรณ์ที่สุด

---

*SoloCorp OS — System First, Everything Follows*
