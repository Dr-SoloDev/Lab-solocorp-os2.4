# ADR-019: Rental OS MVP — Tech Stack + Forbidden Scope

**วันที่:** 2026-10-05
**สถานะ:** Proposed — ⚠️ **ต้องให้ CEO เทอโบ + ช่างฟูล ตัดสินสิ่งแรกก่อน build**
**ผู้เสนอ:** Architect (พี่ทรงศักดิ์)
**เกี่ยวข้อง:** ADR-017, ADR-018

---

## 1. บริบท

CEO เสนอ *"Next.js + Supabase/Postgres + LINE Notify + upload slip + map search"*
แต่โค้ดใน repo นี้เป็น **Python** (`central_bus/` เป็น FastAPI) และทีม Engineering ประกาศ skill หลักเป็น **Laravel / Livewire / FluxUI**

→ ต้องตัดสินใจก่อน ไม่งั้นจะเสียเวลา rewrite

---

## 2. ข้อเสนอ (Decision) — แนะนำ **Laravel 11 + Livewire + PostgreSQL**

| Layer | เลือก | เหตุผล |
|:------|:------|:--------|
| Framework | **Laravel 11 + PHP 8.3** | Auth / Queue / Transaction / Migration / Scheduler อยู่ในกล่อง — ไม่ต้องเขียนเอง |
| UI หลังบ้าน | **Livewire 3 + FluxUI** | ไม่ต้องเขียน API layer + ไม่ต้องแยก state — ทีมเล็กเร็วที่สุด |
| UI หน้าสาธารณะ | **Blade (SSR) + Tailwind** | 🔑 **SEO** — หน้าค้นหาต้องถูก Google/Line OA crawl → **ห้ามเป็น SPA** |
| Database | **PostgreSQL 16** | ต้องการ partial unique index (ADR-017 ชั้นที่ 1) + row locking + `EXCLUDE` constraint ภายหลัง |
| Hosting | **Fly.io หรือ Railway** (1 region) + managed Postgres | 0 ลูกค้า = ไม่ต้อง over-provision; ปิดได้ถ้าล้มเหลว |
| Object storage | **Cloudflare R2** (S3-compatible) | รูปห้อง — ไม่เก็บ binary ใน DB |
| Notification | **LINE Messaging API** (⚠️ ไม่ใช่ LINE Notify) | LINE Notify ถูก deprecate — Messaging API ส่ง 1:1 ได้ + เก็บ LINE ID ของผู้เช่าได้ |
| Search | **SQL `WHERE` + composite index** | 50–100 ห้อง ไม่ต้อง Elasticsearch (ADR-018 §2.2) |
| Map | **ไม่ทำใน MVP** | ตัด — ใช้ filter ย่าน/ราคา/ขนาดแทน |
| Monitoring | Sentry (free) + Laravel Pulse | error ที่เจ้าของเจอเอง ดีกว่าลูกค้าเจอ |

### 2.1 ทำไมไม่ Next.js + Supabase

| เหตุผล | ผลกระทบ |
|:------|:--------|
| **ทีมชุ่ฟูลถูกฝึก Laravel/Livewire มา 10 ปี** | ความเร็วขึ้นเหนือความขอบสวยของ stack |
| **Next.js = ต้องมี backend แยกอีกตัว** (auth, business logic, migration) | ทีมเล็กต้องดูแล 2 stack + 2 deploy = ช้าลง |
| **Next.js SSR ก็ต้องมี Postgres/API อยู่ดี** | Supabase ครอบ auth ซึ่งผู้เช่า MVP **ไม่ต้อง login** |
| **Supabase coupling ยากถอด** | ย้ายทีหลังแพงกว่า |
| **Product นี้ไม่ต้อง realtime** | ไม่ได้ใช้จุดแข็งของ Supabase |

> ⚠️ **ถ้า CEO ยืนยัน Next.js: ต้องมีคนไม่ใช่ชุ่ฟูล build backend** ไม่งั้น scope จะพอง (เป็น 2 เท่า)

### 2.2 ทางเลือกสำรอง (ถ้าอยากยึดภาษา Python)

**FastAPI + HTMX + Jinja2 + PostgreSQL**
- ✅ ได้ข้อดีเดียวกันเรื่อง concurrency (Postgres CAS)
- ✅ ใช้ skill เดียวกับ repo นี้
- ❌ ทีมไม่ได้ประกาศ Python เป็น frontend stack → ต้องเรียน HTMX เพิ่ม
- ❌ Upload รูป + admin CRUD ต้องเขียนเยอะกว่า Livewire

**Architect เลือก: Laravel (เร็วกว่า) — แต่ให้ช่างฟูลเป็นคนตัดสิน**

---

## 3. ขอบเขตห้าม (Forbidden Scope) — ห้ามทำจนกว่าจะถึงเกณฑ์

| ❌ ห้ามทำ | เหตุผล | 🔓 ปลดล็อกเมื่อ |
|:----------|:-------|:---------------|
| **Payment gateway / รับเงินในระบบ** | 0 transaction — ธุรกิจจริงเกิดนอกระบบ (เงินสด/โอน) · เพิ่ม compliance + integration cost | มี 20+ lease ที่จ่ายผ่านระบบจริง |
| **Upload slip ในระบบ** | concierge รับสลิปทาง LINE ได้ — ไม่ต้องมี UI ให้ผู้ใช้ตอนนี้ | มีผู้เช่าเข้าใช้จริง ≥ 10 คน |
| **แชทในระบบ** | ต้องมี moderation + SLA 24/7 — ทีมไม่มี — คุยกันทาง LINE แทน | มี support SLA ที่เขียนเป็นตัวเลขได้ |
| **รีวิว / ดาว / rating** | ดาวที่มี 0 รีวิว = noise; รีวิวปลอมทำลาย trust ทั้งแพลตฟอร์ม — คุณสมบัติคือ "ข้อมูลที่เชื่อถือได้" ไม่ใช่คะแนน | N ≥ 200 completed leases |
| **Blacklist / บล็อกผู้เช่า** | เป็นข้อกล่าวหาข้อมูลส่วนบุคคล → ต้องมีฐานผู้ใช้จริง + นโยบาย PDPA | เจ้าของ 5 หอ ขอเอง + Legal อนุมัติ |
| **Smart lock / IoT** | hardware + support cost — ไม่ใช่ core value | เจ้าของรายใหญ่จ่ายเอง |
| **Escrow / รับเงินแทนเจ้าของ** | ต้องใบอนุญาต/กฎหมาย | ไม่อยู่ใน roadmap |
| **e-signature สัญญา** | integration cost — concierge ทำเองได้ | มีสัญญารูปแบบมาตรฐาน |
| **คำนวณบิลน้ำไฟอัตโนมัติ** | 0 ผู้เช่า — billing เดินหลังเข้าอยู่ = ซับซ้อนขึ้นมาก | มี lease active 30+ |
| **Map search** | แพงกว่าคุณค่าที่จะได้ตอนนี้ — filter ย่านพอแล้ว | ผู้ใช้ถามหาห้องเฉพาะย่าน > 30% |
| **แยกเมืองที่ 2 / multi-tenant** | เจาะลอด 1 เมืองแล้วค่อยขยาย | มีเจ้าของนอกเมืองสัญญาแล้ว |

---

## 4. สิ่งที่ต้องเตรียมก่อน Build

| # | สิ่งที่ต้องมี | ใครทำ | สถานะ |
|:-:|:-------------|:------|:------|
| 1 | LINE Messaging API channel + access token | @นีต (NetEng) | ⬜ |
| 2 | Cloudflare R2 bucket + CORS policy | @นีต (NetEng) | ⬜ |
| 3 | Hosting + managed Postgres + domain | @นีต + @meetoo (CFO งบ) | ⬜ |
| 4 | PDPA consent copy (ภาษาไทย) | @ตุลย์ (Legal) | ⬜ |
| 5 | ข้อมูลห้องจริง 5 ห้อง + รูปจริง (pilot) | @เซลส์ / Ops | ⬜ |
| 6 | Stack final approval (Laravel vs Python) | CEO เทอโบ | ⬜ |

---

## 5. Trade-off

| เลือก | ได้ | ต้องจ่าย |
|:------|:---|:---------|
| Laravel monolith | เร็วมาก, คนเดียวดูแลได้ทั้งระบบ, transaction ไม่ต้องรอ network hop | ถ้าวันหลังต้องแยก service → ต้องแยกออก (แต่ domain model ออกแบบให้พร้อมแล้ว) |
| ไม่มี payment | ไม่มี compliance/chargeback | ยอมรับว่าธุรกิจเกิดนอกระบบ → ต้องมี concierge SOP รองรับ |
| ไม่มี listing table | ไม่มี drift | ต้องยอมรับว่า query ตรง rooms |

---

> **Owner = Architect.**
> 🟡 Proposed — **checkpoint #1 คือให้ CEO ตัดสินเรื่อง stack ก่อนแตะโค้ด**