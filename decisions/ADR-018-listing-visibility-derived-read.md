# ADR-018: Listing Visibility = Derived Read (ไม่ทำ Sync) + Transactional Outbox เมื่อจำเป็น

**วันที่:** 2026-10-05
**สถานะ:** Proposed (รอ CEO เทอโบ อนุมัติ)
**ผู้เสนอ:** Architect (พี่ทรงศักดิ์)
**เกี่ยวข้อง:** ADR-017 (Room status SSOT)

---

## 1. บริบท — คำถามที่ CEO ถาม

> *"sync Listing auto แบบ event-driven อย่างไร"*

CEO คาดหวังว่าจะมี entity `Listing` ที่ sync จาก `Room` แบบ event-driven โดยอัตโนมัติ

**คำตอบของ Architect: MVP นี้ไม่ควรมีตาราง `listing` เลย**

เหตุผลสั้น: Listing visibility เป็น **pure function** ของ `rooms.status` การทำ projection เพิ่มจึงสร้าง *lag* และ *bug class* ใหม่ โดยไม่ได้ประโยชน์ที่ 50–100 ห้อง

---

## 2. ข้อเสนอ (Decision)

### 2.1 Phase 1 (MVP) — **ไม่มีตาราง Listing**

หน้าค้นหาสาธารณะอ่านจาก `rooms` ตรง ๆ พร้อม filter:

```sql
SELECT r.*, b.name, b.subdistrict
  FROM rooms r
  JOIN buildings b ON b.id = r.building_id
 WHERE r.status = 'AVAILABLE'
   AND r.is_publishable = true
   AND b.subdistrict = :ย่าน
   AND r.rent_price BETWEEN :ต่ำ AND :สูง
   AND r.area_sqm >= :ขนาดต่ำ
   AND r.room_type = :ประเภท
 ORDER BY r.updated_at DESC;
```

**"auto-publish / auto-unpublish" = เงื่อนไขใน WHERE clause** ไม่ใช่ job

| สถานการณ์ | ผลลัพธ์ |
|:----------|:--------|
| เจ้าของตั้งห้อง AVAILABLE | ห้องโผล่ทันทีในหน้าค้นหา (ไม่มี lag) |
| ผู้เช่าจองสำเร็จ | ห้องหายจากหน้าค้นหา **ทันทีใน transaction เดียว** |
| เจ้าของกด block | ห้องหายทันที |

**ตัดปัญหาไปทั้งชั้น:** ไม่มี drift, ไม่มี lag, ไม่มี job ล้ม, ไม่มี reconciliation, ไม่ต้องอ่านโค้ด event handler เพื่อรู้ว่า listing ถูกซ่อนหรือไม่

### 2.2 Index ที่จำเป็น

```sql
CREATE INDEX idx_rooms_marketplace ON rooms (status, is_publishable, rent_price, area_sqm);
CREATE INDEX idx_rooms_building    ON rooms (building_id);
```

ที่ 50–100 ห้อง index นี้เกินพอมาก — query จะอยู่ในระดับ **< 10ms**

### 2.3 Phase 2 (ยังไม่ทำ) — เมื่อต้องการ denormalize

**เงื่อนไขที่จะย้ายไป Phase 2** (ต้องเกิดอย่างใดอย่างหนึ่ง):
1. ห้อง > 2,000 ห้อง
2. ต้องการ **faceted search / sort ตามคะแนนความน่าเชื่อถือ**
3. ต้องการ cache หน้าค้นหาเป็นชิ้น (CDN edge caching) โดยไม่กลัวข้อมูลค้าง

ถึงตอนนั้น ให้ใช้ **Transactional Outbox** — ไม่ใช่ event bus ตรง ๆ:

```
┌─────────────── DB TRANSACTION ───────────────┐
│  UPDATE rooms SET status = 'RESERVED'         │
│  INSERT reservations (...)                     │
│  INSERT room_events (...)                      │
│  INSERT outbox (event_id, topic, payload,      │
│                 status='PENDING')   ◄──────────┼── ข้อความถูก commit พร้อมกันเสมอ
└───────────────────────────────────────────────┘
                     │
                     ▼
        worker: SELECT ... WHERE status='PENDING'
                     │  upsert listing_projection (idempotent by event_id)
                     ▼
        status='PROCESSED'  →  projection ใช้อ่าน
                     │
        ┕ cron (ทุก 5 นาที) reconciliation:
           เทียบ listing_projection กับ rooms
           เจอ drift → repair + alert หา me
```

**กฎเหล็กของ outbox (ข้อนี้ทำให้หายจริงถ้าไม่มี):**
- ✅ event เขียน **ใน transaction เดียว** กับ domain change
- ❌ ห้าม publish event จากโค้ดหลัง `commit()` (dual-write bug — DB สำเร็จ event หาย)
- ✅ consumer ต้อง idempotent (dedupe ด้วย `event_id`)
- ✅ ต้องมี reconciliation job เสมอ — outbox อย่างเดียวไม่พอ

---

## 3. ทางเลือกที่พิจารณาแล้วไม่เลือก

| ทางเลือก | เหตุผลที่ไม่เลือก |
|:---------|:-------------------|
| `Listings` table + sync ทุกครั้ง | เพิ่ม bug class (drift) โดยไม่ได้ประโยชน์ที่ scale นี้ |
| Redis cache หน้าค้นหา | ต้อง invalidate ถูกจังหวะ — ถ้าพลาด = แสดงห้องที่จองแล้ว |
| Trigger ใน DB sync ไป table อื่น | ยากเทสต์ ยาก audit ไม่เห็นใน event log |
| Event bus (Kafka/NATS) | Over-engineering หนักสำหรับ 50 ห้อง — operational cost ไม่คุ้ม |
| Elasticsearch | ไม่จำเป็นจนกว่าจะ > 2,000 ห้อง + faceted filter ซับซ้อน |

---

## 4. Trade-off ที่ยอมรับ

| เราเลือก | แลกกับ |
|:---------|:------|
| ความเรียบง่าย + ไม่มี drift | ไม่มี read model สำหรับ analytics ข้ามเมือง/ข้ามภาษา |
| Query ตรงจาก `rooms` | ถ้าอนาคตอยากเก็บ "จำนวนห้องว่างแยกตามย่าน" เร็วมาก ต้องค่อย denormalize |
| ไม่มี event consumer ตอนนี้ | ตอน Phase 2 ต้องเพิ่ม worker + reconciliation (ราคาถูกถ้าทำตอนนั้น) |

> **ข้อสังเกต:** การที่ *ไม่* สร้าง event pipeline ตอนนี้ คือการ **เก็บบันทึก** — domain event (`room_events`) ถูกเขียนไว้แล้วตาม ADR-017 ดังนั้น Phase 2 ไม่ต้องแตะ business logic ใด ๆ เพิ่ม มีแค่ consumer อ่าน event ย้อนหลังได้ (backfill ได้ด้วย)

---

## 5. ผลกระทิชผล

| # | ผลกระทบ | ระดับ | การชดเชย |
|:-:|:---------|:------|:----------|
| 1 | ห้องที่จองแล้วอาจยังโผล่ในหน้า cache/CDN ถ้าวันหลังเพิ่ม cache | 🟢 Low | Phase 2 cache ได้ ตอนนี้ไม่ cache หน้าค้นหาเลย |
| 2 | ไม่มี event log สำหรับ external consumer (เช่น ส่ง LINE แจ้งเตือน) | 🟡 Medium | `room_events` ใน ADR-017 รับหน้าที่แทน — อ่านจากตารางนั้นได้ |
| 3 | ทีมอาจคาดหวังว่าจะเห็นตาราง `listings` ใน design | 🟢 Low | ระบุชัดใน PRD + เหตุผล |

---

## 6. เอกสารที่เกี่ยวข้อง

- [ADR-017](./ADR-017-room-status-ssot-state-machine.md) — Room status SSOT + state machine
- [ADR-019](./ADR-019-rental-mvp-tech-stack.md) — Tech stack MVP
- [PRD-Rental-OS-MVP-v0.1](../docs/prds/PRD-Rental-OS-MVP-v0.1.md)

---

> **Owner = Architect. Pipeline พัง = ฉันรับผิดชอบ.**
> สถานะ: 🟡 Proposed — รอ CEO อนุมัติ