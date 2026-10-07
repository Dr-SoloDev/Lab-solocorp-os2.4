# ADR-017: Room Status = Single Source of Truth + State Machine + Race Guard

**วันที่:** 2026-10-05
**สถานะ:** Proposed (รอ CEO เทอโบ อนุมัติ → Accepted)
**ผู้เสนอ:** Architect (พี่ทรงศักดิ์)
**เกี่ยวข้อง:** ADR-002 (Two-Tier), ADR-018 (Listing Visibility), ADR-019 (Tech Stack)
**บริบท:** Rental OS + Marketplace (เมืองเดียว, หอ 1–5, 50–100 ห้อง, 0 ลูกค้า, โหมด concierge)

---

## 1. บริบท

CEO กำหนดหลัก **"Single source of truth ที่ Room status"** และ Closed Loop:

```
หลังบ้านเจ้าของ → Room.status = AVAILABLE → auto-publish ลง Marketplace
                                  ↓ ผู้เช่าจอง
                              RESERVED → OCCUPIED → หลุดจาก Marketplace อัตโนมัติ
```

ความเสี่ยงที่ต้องกัน **ก่อนเขียนโค้ด** เพราะเป็นสิ่งที่แก้ย้อนหลังยากที่สุดในระบบจอง:

1. **Double-booking** — ผู้เช่า 2 คนกดจองห้องเดียวกันพร้อมกัน → ห้องถูกสัญญาสองครั้ง
2. **ห้องค้างสถานะ** — Reservation ที่ไม่มีวันหมดอายุ → ห้องติด `RESERVED` ถาวร ขายไม่ได้
3. **สถานะกำพร้า** — "ว่าง" มีความหมายเดียว แต่ห้องว่างจริงมี 3 แบบ (ว่างแล้วขาย / ซ่อม / เจ้าของยังไม่พร้อม)

---

## 2. ข้อเสนอ (Decision)

### 2.1 `rooms.status` เป็น enum เดียว — ไม่แยก field

| Status | ความหมาย | โผล่บน Marketplace? |
|:-------|:---------|:-------------------|
| `DRAFT` | ยังไม่ครบข้อมูลขั้นต่ำ | ❌ |
| `AVAILABLE` | ว่าง + พร้อมปล่อยเช่า | ✅ |
| `RESERVED` | ถูกจอง + มี `reserved_until` | ❌ |
| `OCCUPIED` | มี Lease active | ❌ |
| `MAINTENANCE` | ว่างแต่ปิด (ซ่อม / ยังไม่พร้อมปล่อยเช่า) | ❌ |
| `ARCHIVED` | เลิกให้เช่า / ห้องรื้อ | ❌ |

> **ทำไมไม่แยก `lifecycle` × `occupancy` เป็น 2 field**
> DDD จะแนะนำให้แยก แต่ MVP นี้ทีมเล็ก — enum เดียวอ่านง่ายกว่า และ "ห้องว่างแต่ไม่ขาย" ถูกแก้ด้วย `MAINTENANCE` แล้ว
> **เงื่อนไขการแยก field:** ถ้าภายหลังต้องแยก "ปิดเพื่อซ่อม" ออกจาก "เจ้าของยังไม่อยากขาย" ให้เพิ่ม `MAINTENANCE` reason code — **ยังไม่ต้องเปลี่ยนเป็น 2 field**

### 2.2 `visible_on_marketplace` เป็น **Derived** — ห้ามเก็บเป็น column

```sql
visible = (rooms.status = 'AVAILABLE')
      AND rooms.is_publishable          -- owner toggle (override ได้)
      AND rooms.required_fields_complete -- คำนวณจาก completeness checklist
```

เหตุผล: ถ้าเก็บ `is_visible` เป็น column ต้อง sync ให้ตรงเสมอ = แหล่งกำเนิดบั๊กชนิดที่แย่ที่สุด
(ดู ADR-018 เรื่องการไม่ต้อง sync Listing)

---

## 3. State Machine

```
                    ┌──────────────────────────────────────┐
                    │                                      │
   complete_req     ▼        reserve(tenant, ttl)         │
  ┌─────────┐  ┌───────────┐ ─────────────────▶ ┌────────────┐
  │  DRAFT  │─▶│ AVAILABLE │                      │  RESERVED  │
  └─────────┘  └───────────┘ ◀───── expire ───────┴────────────┘
                    │  ▲          (reserved_until ผ่าน)      │
                    │  │ cancel                            │ confirm_lease
      block /       │  │                                    │ (+ Lease active)
      maintenance   │  │                                    ▼
                    ▼  │                                ┌──────────┐
              ┌──────────────┐                         │ OCCUPIED │
              │ MAINTENANCE  │ ◀──── block ────────────┤          │
              └──────────────┘      (ยกเลิกสัญญา/       └──────────┘
                    │  unblock          ผู้เช่าออก)            │
                    ▼  │                                      │ lease end
              ┌───────────┐                                   │ / move_out
              │ AVAILABLE │◀───────────────────────────────────┘
              └───────────┘

  ทุกสถานะ (ยกเว้น ARCHIVED) ──archive──▶ ┌──────────┐
                                            │ ARCHIVED │ (terminal ใน MVP)
                                            └──────────┘
```

### 3.1 Transition Table (guard บังคับทุกครั้ง)

| From | Action | To | Guard (ต้องผ่านหมด) |
|:-----|:-------|:---|:--------------------|
| `DRAFT` | `complete_requirements` | `AVAILABLE` | ครบ: building, `rent_price`, `deposit`, รูป ≥ 1, `area_sqm`, `room_type` |
| `AVAILABLE` | `reserve` | `RESERVED` | CAS: `status='AVAILABLE'` **AND** `version = ?` (ดู §4) |
| `RESERVED` | `expire` (job) | `AVAILABLE` | `now() > reserved_until` |
| `RESERVED` | `cancel` | `AVAILABLE` | ต้องมี `reason` — **ห้ามลบ reservation ทิ้ง** (เก็บเป็น `CANCELLED`) |
| `RESERVED` | `confirm_lease` | `OCCUPIED` | ต้องมี `Lease` ที่ `status='ACTIVE'` |
| `OCCUPIED` | `move_out` | `AVAILABLE` | `lease.end_date < today` หรือ owner ยกเลิกแต่ต้องมี reason |
| `*` | `block` | `MAINTENANCE` | ต้องมี reason |
| `MAINTENANCE` | `unblock` | `AVAILABLE` | — |
| `*` | `archive` | `ARCHIVED` | — |

### 3.2 กฎเหล็ก

1. **ทุก transition ต้อง emit domain event** `room.status_changed(from, to, actor, reason, at)` เขียนลง `room_events` (append-only)
2. **ห้าม hard delete reservation** — `status ∈ HELD | CANCELLED | EXPIRED | CONVERTED`
3. **ห้าม skip state** — ไม่มี `AVAILABLE → OCCUPIED` ต้องผ่าน `RESERVED` เสมอ (กันเช่าแบบ walk-in นอกระบบ)
4. **`reserved_until` บังคับ** — สร้าง `HELD` ที่ไม่มี TTL = ห้องตายถาวร

---

## 4. Race Condition — Defense in Depth 3 ชั้น

ปัญหา: ผู้เช่า A และ B เปิดหน้าเดียวกัน กด "จอง" พร้อมกัน

```
        t0        t1              t2                    t3
   A: โหลดหน้า  กดจอง ────────►  UPDATE... rowcount=1 ──► สำเร็จ
   B: โหลดหน้า  กดจอง ────────►  UPDATE... rowcount=0 ──► 409 "ถูกจองแล้ว"
                          ▲
                  atomic single statement
                  (ไม่มี SELECT แล้วค่อย UPDATE)
```

### ชั้นที่ 1 — Partial Unique Index (บังคับที่ระดับ DB — bypass ไม่ได้)

```sql
CREATE UNIQUE INDEX uq_reservation_single_held
  ON reservations (room_id)
  WHERE status = 'HELD';
```

หนึ่งห้อง = มี `HELD` ได้ **ไม่เกิน 1 รายการ** เสมอ ไม่ว่าโค้ดชั้นบนจะเขียนผิดแค่ไหน
(สำคัญ: `status='HELD'` เท่านั้น — ปล่อยให้เก็บ `CANCELLED`/`EXPIRED` ไว้ในประวัติได้)

### ชั้นที่ 2 — Conditional UPDATE (Atomic Compare-and-Set)

```sql
UPDATE rooms
   SET status       = 'RESERVED',
       reserved_until = :ttl,
       version      = version + 1,
       updated_at   = now()
 WHERE id      = :room_id
   AND status  = 'AVAILABLE'
   AND version = :expected_version;   -- optimistic lock
```

- `rowcount = 0` → มีคนชนะไปแล้ว → คืน **HTTP 409** พร้อมข้อความ `"ห้องนี้ถูกจองไปก่อนหน้านี้แล้ว"`
- ทำเป็น **statement เดียว** — ห้าม `SELECT` แล้วค่อย `UPDATE` (ถ้าแยกสอง statement จะมี race window ตรงกลาง)
- ครอบทั้ง `UPDATE rooms` + `INSERT reservations` + `INSERT room_events` ใน **transaction เดียว**

### ชั้นที่ 3 — Idempotency + UX

- ทุก request จองต้องมี `Idempotency-Key` (UUID) — กดซ้ำ/ retry จะได้ผลเดิม ไม่สร้าง reservation ซ้ำ
- 409 ต้องแสดง **"ห้องนี้เพิ่งถูกจองไป — ดูห้องใกล้เคียง"** + deep link กลับหน้าค้นหา (concierge mode: ประสบการณ์ไม่ดี = เสียลูกค้า)
- ห้าม `SELECT ... FOR UPDATE` ใน MVP — row lock ยัง deadlock-prone เมื่อมี expiry job ชนกับกดจอง

### 4.1 หลักฐานที่ต้องส่งมา (D2 evidence — ไม่รับคำว่า "เสร็จ" ที่ไม่มี)

```
คำสั่งพิสูจน์: ยิง N=50 requests จองห้องเดียวกันพร้อมกัน
ผลที่ต้องได้:  exactly 1 × HTTP 200 (RESERVED)
               exactly 49 × HTTP 409
               reservations(HELD) count == 1
               room_events(status_changed) count == 1
```

---

## 5. Data Model (จุดที่ต้องเผื่อตั้งแต่แรก)

```
buildings
  id, name, address, subdistrict, lat, lng, owner_name, notes

rooms
  id, building_id FK, code, floor, room_type, area_sqm,
  rent_price (int บาท), deposit (int บาท), common_fee (int บาท, nullable),
  utilities_note, slug UNIQUE, is_publishable, status ENUM, version INT,
  reserved_until TIMESTAMPTZ NULL, created_at, updated_at

room_photos
  id, room_id FK, path, captured_at, is_cover, sort_order
  -- captured_at ≠ uploaded_at → ใช้ timestamp จริงใน Trust Layer (ดู ADR ใน PRD §9)

tenants                    -- คนละคนกับ user ของระบบ: ผู้เช่าไม่ต้อง login
  id, display_name, phone, line_id, identity_verified_at NULL, created_at

inquiries
  id, room_id FK, tenant_id FK, channel(enum), message, viewing_at NULL,
  status ENUM(NEW|CONTACTED|VIEWING_SCHEDULED|VIEWED|RESERVED|LOST), created_at

reservations
  id, room_id FK, tenant_id FK, status ENUM(HELD|CANCELLED|EXPIRED|CONVERTED),
  reserved_until TIMESTAMPTZ, cancel_reason NULL, idempotency_key UNIQUE, created_at

leases
  id, room_id FK, tenant_id FK, start_date, end_date, rent_price, deposit,
  status ENUM(ACTIVE|ENDED|CANCELLED), created_at

utility_bills
  id, room_id FK, lease_id FK NULL, period (YYYY-MM),
  water_amount, elec_amount, total_amount, note, bill_photo_path NULL, created_at
  -- MVP: record เท่านั้น ไม่ auto-calc / ไม่แยกส่วน

room_events               -- append-only audit
  id, room_id FK, event_type, from_status, to_status, actor, reason,
  payload JSONB, created_at
```

> **`start_date` / `end_date` ต้องมีตั้งแต่แรก (แม้ MVP ไม่ใช้)** — ถ้าวันหลังต้องจองเข้าอนาคต/ต่อสัญญา จะต้อง backfill และ migrate ข้อมูลจริง = เสี่ยงกว่าการใส่ field ว่างตั้งแต่วันแรก

---

## 6. ผลกระทบ

### เชิงบวก
| ผล | เหตุผล |
|:---|:------|
| Double-booking เป็นไปไม่ได้ | DB constraint บังคับ ไม่พึ่งวินัยโค้ด |
| Trace ได้ 100% | `room_events` append-only ทุก transition |
| ห้องไม่ค้าง | TTL + expiry job บังคับ |
| Listing ไม่ drift | visibility derive จาก status (ADR-018) |

### เชิงลบ / ต้นทุน
| ต้นทุน | การชดเชย |
|:------|:----------|
| ต้องเขียน domain service + event log ทุก transition | เป็น pattern เดียว เขียนครั้งเดียวใช้ทุก action |
| `version` optimistic lock ต้องส่งมาจาก client | ยอมรับ — ถ้ามาผิด → 409 ปลอดภัย |
| Reservation ต้องมี TTL | ต้องตั้ง policy ว่าจองเก็บกี่วัน (แนะนำ 3 วัน) |

---

## 7. สิ่งที่ยังไม่ตัดสิน (ต้องถาม CEO)

| # | คำถาม | แนะนำ |
|:-:|:-------|:------|
| Q1 | จองเก็บห้องไว้กี่วันก่อนดีพัล? | **3 วัน** (ทดแทนมาตรฐานมหาวิทยาลัย/คอนโด) |
| Q2 | MVP จองเข้าอนาคตได้ไหม? | **ไม่** — จองเฉพาะเข้าเดือนนี้/ถัดไป; ถ้าจะทำตั้งแต่แรกต้องเพิ่ม overlap check |
| Q3 | Deposit จะเก็บในระบบไหม? | **เก็บเป็นตัวเลข + note** ไม่ track สถานะ (เจ้าของจดเอง) |

---

## 8. เอกสารที่เกี่ยวข้อง

- [ADR-002](./ADR-002-two-tier-control-vs-data.md) — Two-Tier (Control vs Data)
- [ADR-018](./ADR-018-listing-visibility-derived-read.md) — Listing visibility
- [ADR-019](./ADR-019-rental-mvp-tech-stack.md) — Tech stack MVP
- [PRD-Rental-OS-MVP-v0.1](../docs/prds/PRD-Rental-OS-MVP-v0.1.md)

---

> **Owner = Architect. ถ้า Pipeline นี้พัง ฉันรับผิดชอบ.**
> สถานะ: 🟡 Proposed — รอ CEO อนุมัติก่อนสั่ง @changful build