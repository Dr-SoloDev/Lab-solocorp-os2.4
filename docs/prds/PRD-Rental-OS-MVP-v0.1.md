# PRD: Rental OS + Marketplace MVP v0.1

| Meta | Value |
|------|-------|
| **Product** | Rental OS + Marketplace + Trust |
| **Vision** | "ทำให้เจ้าของที่หาผู้เช่า กับผู้เช่าที่หาห้อง ค้นพบกันได้จากข้อมูลที่เชื่อถือได้" |
| **Status** | 🟡 **D1 PASSED** — เอกสาร phase plan พร้อมให้ตัดสินใจ / ยังไม่ใช่สัญญากับ Engineering |
| **Owner** | CEO (เทอโบ ไชยศรีรัมย์) |
| **Architect** | Architect (พี่ทรงศักดิ์) |
| **Engineering** | Engineering (ช่างฟูล) |
| **Scale** | 1 เมือง · หอ 1–5 · ห้อง 50–100 · **0 ลูกค้า** · โหมด Concierge |
| **Target** | Sprint 1 = concurrency guard (ก่อนอย่างอื่น) |
| **เอกสารที่ต้องอ่านคู่กัน** | [ADR-017](../../decisions/ADR-017-room-status-ssot-state-machine.md) · [ADR-018](../../decisions/ADR-018-listing-visibility-derived-read.md) · [ADR-019](../../decisions/ADR-019-rental-mvp-tech-stack.md) |

---

## 1. Problem Statement

ตลาดห้องเช่าเมืองหนึ่งมีปัญหาคลาสสิก 3 อย่าง:

1. **ข้อมูลไม่เชื่อถือ** — รูปเก่า, ราคาไม่จริง, เจ้าของปลอม, เข้าดูแล้วห้องไม่ใช่ห้องที่เห็น
2. **ค้นหาไม่เจอ** — ข้อมูลกระจัดกระจายทั้ง Facebook Groups, ป้ายเช่า, คอนโดเอเจนซี
3. **ติดต่อไม่ต่อ** — เจ้าของไม่ได้คำตอบ, ผู้เช่าหายไป

**ของที่เราทำต่างออกไป:** ไม่ได้ขาย "ความสวยงาม" แต่ขาย **ความน่าเชื่อถือของข้อมูล** — ทุกห้องบอกได้ว่าใครเป็นเจ้าของ (ยืนยันแล้วหรือยัง), ข้อมูลสดแค่ไหน, ครบแค่ไหน

---

## 2. Scope Review — MVP ที่ CEO เสนอ

| # | ของที่ CEO เสนอ | คำตัดสิน | เหตุผล |
|:-:|:---------------|:--------|:--------|
| 1 | หอ / ห้อง | ✅ **เก็บ** | แกนหลัก |
| 2 | ว่าง / ไม่ว่าง | ⚠️ **ขยาย** | "ว่าง/ไม่ว่าง" 2 ค่าไม่พอ — ต้อง 6 สถานะ (ดู §4) เพราะห้องว่างจริงมี 3 แบว: *ว่างแล้วขาย / ซ่อม / เจ้าของยังไม่พร้อม* |
| 3 | รูป | ✅ **เก็บ + เพิ่ม timestamp** | ต้องเก็บ `captured_at` (เวลาถ่าย) แยกจาก `uploaded_at` → ใช้เป็น Trust signal |
| 4 | ราคา / มัดจำ | ✅ **เก็บ + เพิ่ม** | ต้องมี `common_fee` (ค่าส่วนกลาง) + `utilities_note` — **การไม่ซ่อนค่าใช้จ่ายแอบแฝงคือ trust signal ตัวที่ 2** |
| 5 | บิลน้ำไฟง่าย | ⚠️ **ลดรูป** | เหลือเป็น **record เท่านั้น** (period + amount + note) — ไม่ auto-calc ไม่แยกส่วน ไม่แนบรูปบิล (0 ผู้เช่าตอนนี้ = ยังไม่มีอะไรให้คำนวณ) |
| 6 | Public Link 1 ลิงก์/ห้อง | ✅ **เก็บ** | ถูกต้อง — 1 slug ต่อห้อง ใช้ทั้งแชร์ LINE และ SEO |
| 7 | หน้าค้นหารวม | ✅ **เก็บ (SSR)** | ต้องเป็น server-rendered — ถ้าเป็น SPA จะไม่ถูก crawl → ไม่มี organic traffic = ไม่มีลูกค้า |

### 2.1 สิ่งที่ "เกิน" — ตัดออกได้อีก (ทั้งหมดยังไม่ต้อง)

| ตัดออก | แทนที่ด้วย |
|:-------|:----------|
| Map search | filter: ย่าน · ราคา · ขนาด · ประเภทห้อง |
| Upload slip | ส่งสลิปทาง LINE (concierge รับเอง) |
| อัปโหลดรูปไม่จำกัด | จำกัด 6 รูป/ห้อง |
| คำนวณบิลน้ำไฟ | จดเป็น note |
| Login/สมัครสมาชิกผู้เช่า | ผู้เช่า **ไม่ต้อง login** — ใช้ phone/LINE เป็นตัวระบุ |
| รายงาน/analytics dashboard | หน้า "ห้องว่างวันนี้" แบบเรียบง่าย |
| ประวัติการเช่าหลายรอบ | เก็บแค่ lease ปัจจุบัน |

### 2.2 สิ่งที่ **ขาด** — ต้องเพิ่มก่อน build (5 ข้อ)

| # | ขาดอะไร | ทำไมต้องมา | ตัดสิน |
|:-:|:--------|:-------------|:------|
| 1 | **`inquiries` (คำถาม/นัดดู)** | Closed Loop ของ CEO มี "ติดต่อ/นัดดู" แต่ scope ไม่มี — ถ้าไม่มีที่เก็บ ประวัติการคุยกับลูกค้าหายทั้งหมด และนับ conversion ไม่ได้ | 🔴 **เพิ่ม — ต้องมี** |
| 2 | **`tenants` (ผู้สนใจ/ผู้เช่า)** | "ผู้เช่าที่หาห้อง" ต้องเป็น record ไม่งั้นวงจรขาดตรงระหว่าง "ค้นหา" กับ "จอง" — ไม่ต้อง login แต่ต้องรู้ว่าใครคือใคร | 🔴 **เพิ่ม — ต้องมี** |
| 3 | **`reserved_until` (TTL ของการจอง)** | จองแล้วเปลี่ยนใจ → ห้องติด RESERVED ถาวร ขายไม่ได้ = **ฆ่าลูกค้าตัวเอง** | 🔴 **เพิ่ม — ต้องมี** (ดู ADR-017) |
| 4 | **`MAINTENANCE` status** | ห้องว่างแต่ซ่อม/ยังไม่พร้อมขาย — ถ้าไม่มีจะโผล่บน Marketplace แล้วลูกค้าเสียเวลานัดดู | 🔴 **เพิ่ม — ต้องมี** |
| 5 | **PDPA consent + data retention** | เก็บรูปเอกสาร + เบอร์โทร + LINE ID = personal data — ไม่มี consent คือความเสี่ยงทางกฎหมายทันที | 🔴 **เพิ่ม — ต้องมี** (ดู §9 ความเสี่ยง 3) |

---

## 3. Architecture Overview

```
┌──────────────────────── หลังบ้านเจ้าของ (Livewire) ────────────────────────┐
│  Buildings ─┬─ Rooms ─┬─ RoomPhotos                                         │
│             │         ├─ room_events (append-only audit)                   │
│             │         ├─ Inquiries ──── Tenants                            │
│             │         ├─ Reservations ─┐                                   │
│             │         └─ Leases ──┐    │  (CAS update — ADR-017 §4)        │
│             └─ UtilityBills      │    │                                    │
└─────────────────────────────────┼────┼────────────────────────────────────┘
                                  │    │
                    ⚡ transaction เดียว (Postgres)
                                  │    ▼
              ┌────────────────────────────────────────┐
              │  rooms.status  ◄══ SSOT ══►            │
              │  DRAFT │ AVAILABLE │ RESERVED │        │
              │  OCCUPIED │ MAINTENANCE │ ARCHIVED     │
              └───────────────────┬────────────────────┘
                                  │  derived read (ไม่ sync — ADR-018)
                                  ▼
              ┌────────────────────────────────────────┐
              │  Marketplace (Blade SSR — SEO)          │
              │  WHERE status='AVAILABLE' AND publishable│
              │  /search  ·  /r/{slug}  (1 link/ห้อง)   │
              └───────────────────┬────────────────────┘
                                  │ กดจอง
                                  ▼
              ┌────────────────────────────────────────┐
              │  POST /reserve  ── 200 │ 409 (ถูกชนไป) │
              │  Idempotency-Key + reserved_until (3 วัน)│
              │  → queue job: ส่ง LINE แจ้งเจ้าของ      │
              └────────────────────────────────────────┘

หลุดจาก Marketplace = status เปลี่ยน → WHERE ไม่ match → หายทันที (ไม่มี lag)
```

---

## 4. Domain Model + State Machine (สรุป)

**Model เต็ม:** ดู [ADR-017 §5](../../decisions/ADR-017-room-status-ssot-state-machine.md#5-data-model-จุดที่ต้องเผื่อตั้งแต่แรก)

```
buildings ──< rooms ──< room_photos
                 │
                 ├──< inquiries >── tenants
                 ├──< reservations >── tenants
                 ├──< leases >── tenants
                 ├──< utility_bills
                 └──< room_events   (append-only — audit trail)
```

**State machine (6 สถานะ):**

```
   complete_req          reserve(ttl)
  ┌─────────┐  ──────▶ ┌───────────┐ ─────────▶ ┌────────────┐
  │  DRAFT  │           │ AVAILABLE │             │  RESERVED  │
  └─────────┘           └───────────┘ ◀──────────┴────────────┘
                              ▲  ▲        expire / cancel       │
                              │  └──────────────────────────────┘
                   block      │  unblock
                    ┌──────────▼────────┐   confirm_lease   ┌──────────┐
                    │  MAINTENANCE      │ ────────────────▶ │ OCCUPIED │
                    └───────────────────┘                   └──────────┘
                          (ซ่อม/ยังไม่พร้อมขาย)                    │ lease end
                                                                  ▼
                                                            AVAILABLE
```

**กฎเหล็ก 4 ข้อ:**
1. `visible_on_marketplace` = **derived** จาก `status` — ห้ามเก็บเป็น column
2. ทุก transition ต้องเขียน `room_events` (append-only)
3. ห้าม hard delete reservation · ห้าม skip `RESERVED`
4. `reserved_until` บังคับทุก `HELD`

---

## 5. Race Condition — เจ็บที่นี่แล้วจะแก้ยากที่สุด

```
        t0        t1              t2                      t3
   A: โหลดหน้า  กดจอง ────────▶ UPDATE … rowcount=1 ──▶ ✅ สำเร็จ
   B: โหลดหน้า  กดจอง ────────► UPDATE … rowcount=0 ──▶ ⚠️ 409
                            ▲
                    atomic single statement
```

### 3 ชั้นป้องกัน

| ชั้น | กลไก | ทำไมต้องมี |
|:----|:-----|:----------|
| 1 | `CREATE UNIQUE INDEX uq_reservation_single_held ON reservations(room_id) WHERE status='HELD'` | **บังคับระดับ DB — โค้ดชั้นบนเขียนผิดก็ไม่ผ่าน** |
| 2 | Atomic CAS: `UPDATE rooms SET status='RESERVED' WHERE id=? AND status='AVAILABLE' AND version=?` | ทำเป็น statement เดียว — ห้าม SELECT แล้วค่อย UPDATE (มี race window ตรงกลาง) |
| 3 | `Idempotency-Key` + UX ตอน 409 | กดซ้ำไม่สร้างซ้ำ · 409 ต้องบอกทางออก = "ดูห้องใกล้เคียง" |

**หลักฐานที่ต้องส่ง (D2 — ไม่รับคำว่า "เสร็จ" ที่ไม่มี):**
ยิง 50 requests พร้อมกัน → ต้องได้ **1×200 + 49×409** และ `reservations(HELD) == 1`

---

## 6. Tech Stack (สรุป — เหตุผลเต็มใน ADR-019)

| Layer | เลือก | ⚠️ ตัดสินใจ |
|:------|:------|:------------|
| Framework | **Laravel 11 + PHP 8.3** | 🔴 CEO ต้องยืนยัน (แนะนำ Laravel) |
| UI หลังบ้าน | **Livewire 3 + FluxUI** | ✅ |
| UI หน้าสาธารณะ | **Blade SSR + Tailwind** — ห้าม SPA | ✅ SEO บังคับ |
| DB | **PostgreSQL 16** — ต้องการ partial unique index | ✅ |
| Storage | **Cloudflare R2** | ✅ |
| Notify | **LINE Messaging API** (ไม่ใช่ LINE Notify — ตัวเดิมถูก deprecate) | ✅ |
| Search | SQL WHERE + composite index | ✅ |
| Map | **ไม่ทำ** | ✅ ตัดแล้ว |

> **ทำไมไม่ Next.js + Supabase:** ทีมชุ่ฟูลถูกฝึก Laravel/Livewire มา 10 ปี · Next.js ต้องมี backend แยกอีกตัว (ทีมเล็กดูแล 2 stack) · ผู้เช่า MVP ไม่ต้อง login จึงไม่ได้ใช้ auth ของ Supabase

---

## 7. Trust Layer Phase 1 — Verified Facts (ยังไม่มี rating)

> **หลัก: Facts ที่ตรวจสอบได้ > คะแนนที่ไม่มีคนให้**
> MVP นี้ **ไม่มีดาว ไม่มีรีวิว** — เพราะดาวที่มี 0 รีวิวคือ noise และรีวิวปลอมจะทำลาย trust ทั้งแพลตฟอร์ม

### 7.1 Trust Signals 4 ชั้น (เรียงตามความสำคัญจริง)

| Tier | Signal | แสดงบนหน้าอะไร | Phase 1 ทำอะไร |
|:-----|:-------|:--------------|:------------|
| **A** | 🏠 **เจ้าของยืนยันแล้ว** | หน้าห้อง + หน้าค้นหา | ส่งบัตร/ทะเบียนบ้าน → `owners.identity_verified_at` — **ห้ามแสดงเลขบัตร** เด็ดขาด |
| **B** | 🕒 **ความสดของข้อมูล** | หน้าห้อง | "อัปเดตล่าสุด 2 วันที่แล้ว" + สี: 🟢 <7 วัน · 🟡 <30 วัน · ⚪ >30 วัน — **ความเก่าคือคำเตือน ไม่ใช่คำโฆษณา** |
| **C** | ✅ **ความครบของข้อมูล** | หน้าห้อง | checklist % (ราคา/มัดจำ/รูป≥3/พิกัด/ขนาด/ค่าส่วนกลาง) |
| **D** | 📷 **รูปมีที่มา** | หน้าห้อง | `captured_at` (เวลาถ่ายจริง) ≠ `uploaded_at` + ผูกรูปกับ `room_id` กันรูปห้องอื่น/รูปเก่า |

### 7.2 Anti-Scam Card (ต้นทุนต่ำ ผลสูงสุด)

การ์ด 3 บรรทัดใต้ปุ่ม "ติดต่อเจ้าของ" — ทำงานกว่า rating ในเวลานี้ทันที:

```
🛡️ ข้อมูลนี้มาจากเจ้าของที่ยืนยันตัวตนแล้ว
💰 ระบุราคาเช่า ค่ามัดจำ และค่าใช้จ่ายรายเดือนครบ — ไม่มีค่าใช้จ่ายแอบแฝง
📅 แนะนำนัดดูห้องก่อน แล้วค่อยโอนค่ามัดจำ
```

### 7.3 เมื่อไหร่才ค่อยมี Rating

| เงื่อนไข | ค่าขั้นต่ำ |
|:--------|:-----------|
| completed leases สะสม | ≥ 200 |
| มีระบบตรวจจับรีวิวปลอม | ต้องมา |
| มีคนดูแล moderation | ต้องมี |
| แยกรีวิวของเจ้าของ vs ผู้เช่า | ต้องแยก |

---

## 8. Closed Loop — เทียบกับของเดิม

| ขั้นตอนของ CEO | สถานะ MVP | หมายเหตุ |
|:----------------|:-----------|:----------|
| หลังบ้าน: Property/Rooms | ✅ | |
| Tenants/Rent | ✅ | Tenant ไม่ต้อง login |
| Water/Electric/Billing | ⚠️ ลดรูป | record เท่านั้น ไม่ auto-calc |
| Payment | ❌ ไม่ทำ | เกิดนอกระบบ (ADR-019 §3) |
| Repair | ❌ ไม่ทำ | ใช้ `MAINTENANCE` status แทน — พอสำหรับ MVP |
| Report | ⚠️ ง่าย | หน้า "ห้องว่างวันนี้" |
| สถานะ AVAILABLE | ✅ | SSOT |
| auto-publish → Marketplace | ✅ | = derived read ไม่ต้อง sync |
| ผู้เช่าค้นหา/filter | ✅ SSR | ไม่มี map |
| ติดต่อ/นัดดู | ✅ `inquiries` | + ส่ง LINE แจ้งเจ้าของ |
| จอง RESERVED | ✅ + TTL | CAS guard 3 ชั้น |
| เช่า OCCUPIED | ✅ | ต้องมี Lease |
| หลุดจาก Marketplace อัตโนมัติ | ✅ | ไม่มี lag ไม่มี job |

---

## 9. ความเสี่ยง Architecture 3 ข้อ

### R1 🔴 CRITICAL — Double-booking (ห้องถูกสัญญา 2 ครั้ง)

| | |
|:--|:--|
| **สถานการณ์** | ผู้เช่า 2 คนกดจองห้องเดียวกันพร้อมกัน → ห้องถูกจอง 2 ครั้ง |
| **ผลกระทบ** | หายตายทางธุรกิจ: เจ้าของเสียผู้เช่า 1 คน · ผู้เช่าเสียเงิน/เวลา · **trust ทั้งแพลตฟอร์มพัง** — เกิดครั้งเดียวพอก็ข่าวป่า |
| **Mitigation** | 3 ชั้น ตาม ADR-017 §4 — DB constraint + atomic CAS + idempotency key |
| **หลักฐานยืนยัน** | Concurrency test N=50 → ต้องได้ 1×200 + 49×409 (**บังคับใน Sprint 1**) |
| **Owner** | @changful (ทำ) · @phee-thongsak (ตรวจ audit trail) |

### R2 🟠 HIGH — Listing Drift / Visibility ผิด

| | |
|:--|:--|
| **สถานการณ์** | DB commit สำเร็จแต่ event หาย (dual-write) → ห้องที่จองแล้วยังโผล่บน Marketplace |
| **ผลกระทบ** | ลูกค้าเสียเวลานัดดู → เจ้าของได้คำตอบว่า "จองแล้ว" → ประสบการณ์แย่ = เสียลูกค้าถาวร |
| **Mitigation** | 🔑 **MVP ไม่ทำ sync เลย** — visibility = derived read ตรงจาก `rooms.status` (ADR-018) = **ไม่มี code path ที่จะ drift ได้** |
| **ถ้าวันหลังต้อง sync** | Transactional Outbox (เขียน event ใน transaction เดียวกัน) + idempotent consumer + **reconciliation job ทุก 5 นาที** |
| **Owner** | @changful · Architect (ออกแบบ ADR) |

### R3 🟠 HIGH — PDPA / Personal Data

| | |
|:--|:--|
| **สถานการณ์** | เก็บรูปเอกสารยืนยันตัวตน + เบอร์โทร + LINE ID ของผู้เช่า/ผู้สนใจ โดยไม่มี consent / purpose / retention |
| **ผลกระทบ** | ผิดกฎหมาย + เสียชื่อ — **และ trust คือสินค้าหลัก ถ้าเราผิด PDPA ความน่าเชื่อถือที่เราขายก็หายไปเอง** |
| **Mitigation** | 1. consent checkbox + ข้อความ purpose ก่อนเก็บ · 2. เก็บเท่าที่จำเป็น · 3. กำหนด retention + ลบเมื่อครบ · 4. รูปเอกสารต้องเข้าถึงได้เฉพาะเจ้าของห้องนั้นเท่านั้น · 5. **ไม่แสดงเลขบัตรแม้แต่ที่เดียว** |
| **Blocker** | ⛔ ต้องให้ @ตุลย์ (Legal) เขียน consent copy ก่อนเก็บเอกสารจริง |
| **Owner** | @tulya (Legal) · @changful (implement) |

> **ข้อสังเกตเชิงหลักการ:** R1–R3 ไม่ใช่เรื่องซับซ้อนทางเทคนิค แต่เป็นเรื่องที่ **ถ้าเกิดแล้วแก้ต้นทุนสูงกว่าที่จะป้องกันตั้งแต่แรก** — เลยต้องเขียนลง PRD ตั้งแต่ Sprint 1 ไม่ใช่ปล่อยท้าย

---

## 10. Checkpoints ก่อนสั่ง @changful Build

| # | Checkpoint | ใครอนุมัติ | สถานะ | ถ้ายังไม่ผ่าน |
|:-:|:-----------|:-----------|:------|:----------------|
| **C1** | **Tech stack: Laravel vs Python** | CEO เทอโบ + ช่างฟูล | ⛔ **OPEN** | **ห้ามเริ่มโค้ด** — Architect แนะนำ Laravel |
| C2 | Domain model + state machine | CEO (SSOT คือ Room) | ✅ [ADR-017](../../decisions/ADR-017-room-status-ssot-state-machine.md) | — |
| C3 | Listing = derived read (ไม่ sync) | Architect | ✅ [ADR-018](../../decisions/ADR-018-listing-visibility-derived-read.md) | — |
| C4 | PDPA consent copy + retention policy | @ตุลย์ (Legal) | ⛔ **OPEN** | บล็อกเฉพาะฟีเจอร์เก็บเอกสาร — อย่าอื่นทำได้ |
| C5 | Hosting + R2 + LINE Messaging API key | @นีต (NetEng) | ⛔ OPEN | ทำ local ได้ก่อน แต่ต้องมีก่อน Sprint 3 |
| C6 | ข้อมูลห้องจริง 5 ห้อง (pilot) | @เซลส์ / Ops | ⛔ OPEN | บล็อกการทดสอบ end-to-end |
| C7 | งบโฮสติ้ง/โดเมน | @meetoo (CFO) | ⛔ OPEN | — |
| C8 | Reservation TTL = 3 วัน | CEO | ⛔ OPEN | ดูคำถามเปิด Q1 |

---

## 11. Checklist สำหรับ @changful — ลำดับการ Build

### 🔴 Sprint 1 — Foundation + Concurrency Guard (ทำก่อนอย่างอื่นเด็ดขาด)

- [ ] **T1** Migrations: `buildings, rooms, room_photos, tenants, inquiries, reservations, leases, utility_bills, room_events`
- [ ] **T2** ⭐ Partial unique index `uq_reservation_single_held ... WHERE status='HELD'`
- [ ] **T3** Eloquent models + casts (`status` enum, เงินเป็น `integer` บาท — **ห้าม float**)
- [ ] **T4** `RoomStatusService` — transition guard + emit domain event → **unit test ทุก transition รวม case ต้อง fail**
- [ ] **T5** `ReservationService::reserve()` — atomic CAS + 409 + `Idempotency-Key`
- [ ] **T6** ⭐ **Concurrency test N=50 → assert exactly 1×200 + 49×409** · นี่คือ **D2 evidence หลัก**
- [ ] **T7** Reservation expiry job (`reserved_until` ผ่าน → auto revert `AVAILABLE`)
- [ ] **T8** Composite index หน้าค้นหา (ADR-018 §2.2)

### 🟠 Sprint 2 — หลังบ้านเจ้าของ

- [ ] **T9** CRUD Buildings / Rooms + validation ข้อมูลขั้นต่ำ (`DRAFT → AVAILABLE` gate)
- [ ] **T10** อัปโหลดรูป → Cloudflare R2 (จำกัด 6/ห้อง, บันทึก `captured_at`)
- [ ] **T11** หน้า admin filter ตาม status + action block/unblock/archive
- [ ] **T12** `Inquiries` CRUD + ส่ง LINE Messaging API แจ้งเจ้าของ
- [ ] **T13** หน้า "ห้องว่างวันนี้" (report ง่าย)

### 🟡 Sprint 3 — Marketplace (หน้าสาธารณะ)

- [ ] **T14** ⭐ หน้าค้นหา **Blade SSR** + filter (ย่าน/ราคา/ขนาด/ประเภท) — ตรวจว่า HTML มีข้อมูลห้องจริงใน source (SEO test)
- [ ] **T15** หน้าห้อง `/r/{slug}` (1 link/ห้อง — ใช้แชร์ LINE ได้)
- [ ] **T16** Trust UI: owner badge · staleness badge · completeness % · anti-scam card
- [ ] **T17** ปุ่มจอง → 200/409 + **UX ตอน 409 ต้องมี deep link "ดูห้องใกล้เคียง"**
- [ ] **T18** Sentry + Laravel Pulse

### 🟢 Sprint 4 — บิล + Pilot

- [ ] **T19** `UtilityBills` — record only (period/amount/note) **ไม่ auto-calc**
- [ ] **T20** หน้า admin `room_events` (audit trail viewer)
- [ ] **T21** Seed ข้อมูลจริง 5 ห้อง + ทดสอบ concierge flow จริง

### ⛔ ห้ามทำในทุก Sprint (ดู ADR-019 §3)

`payment` · `upload slip` · `แชทในระบบ` · `รีวิว/ดาว` · `blacklist` · `smart lock` · `escrow` · `e-signature` · `auto-calc บิล` · `map search` · `multi-city`

---

## 12. คำถามเปิดที่ต้องให้ CEO ตอบ

| # | คำถาม | Architect แนะนำ |
|:-:|:-------|:---------------|
| **Q1** | จองเก็บห้องไว้กี่วันก่อนดีพัล? | **3 วัน** |
| **Q2** | MVP จองเข้าอนาคตได้ไหม? | **ไม่** — ถ้าจะทำต้องเพิ่ม overlap check (เตรียม field ไว้แล้วใน ADR-017) |
| **Q3** | เจ้าของต้องการอะไรเป็น "ห้องว่างวันนี้"? | ยังไม่ถาม รอ concierge ทำจริงแล้วค่อยดู |

---

## 13. Certification Gate (ตาม rules/06-certification.md)

| ด่าน | ของ | สถานะ |
|:-----|:-----|:------|
| **D1** | เอกสาร 1 หน้า: why / ใครทำ / scope | ✅ **PASSED** = เอกสารนี้ |
| **D2** | Agent 50–150 บรรทัดที่เรียก tool จริง + run output + exit code | ⬜ คือ **T6 concurrency test** |
| **D3** | ตาราง eval ≥ 20 งาน: expected vs actual + root cause | ⬜ หลัง Sprint 1 |
| **D4** | คนอื่น reproduce ได้จาก runbook | ⬜ หลัง Pilot |

> **Maker ≠ Checker:** @changful ทำ = maker · Architect (พี่ทรงศักดิ์) ตรวจ = checker · @phee-thongsak ตรวจ audit trail

---

> **"สถาปัตยกรรมที่ดีไม่ใช่ตัวที่เยอะที่สุด แต่คือตัวที่พลาดยากที่สุดตอนคุณอยู่ในระบบไม่ได้ดูจอ"**
>
> Owner = Architect (พี่ทรงศักดิ์) · Pipeline พัง = ฉันรับผิดชอบ
> สถานะ: 🟡 D1 PASSED — รอ **C1 (stack)** เพื่อสั่ง @changful