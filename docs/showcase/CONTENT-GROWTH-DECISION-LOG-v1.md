# 📓 Decision Log — Content Growth Plan v1 (M1 → M6)

> **กฎ:** ทุกการตัดสินใจลงที่นี่ 1 บรรทัดต่อ 1 เรื่อง — ใครตัดสิน เมื่อไร ทำไม กระทบใคร
> **Owner:** เสก (Head of Content — เจ้าของ Decision Log) · **ผู้ประสาน:** พี่วุฒิ (Orchestrator)
> **Branch:** `feat/content-growth-phase1` · **Savepoint:** `save-sek-rail-20261120` (c3b2d5d)
> **สถานะไฟล์:** append-only — ห้ามแก้ entry เก่า ผิดให้เพิ่ม entry ใหม่ที่อ้าง entry เดิม
> **Checker:** QA + Legal ตรวจทุก entry ก่อนนับ milestone PASS

---

## D-001 — 2026-11-20 · แผน Phase 1 ปิด + เปิด Loop M2–M6 (Orchestrator)

- **โดย:** พี่วุฒิ (Orchestrator — ประสานตามคำสั่ง Owner ลุยยาวเป็น Loop จนกว่า M2–M6 ครบ)
- **ตัดสินใจ:** รับแผน `CONTENT-GROWTH-PLAN-v1.md` (§7) เป็นฐาน Loop — เริ่ม M2 ทันที (readiness checklist + progress rail เขียนไฟล์อย่างเดียว ไม่ commit)
- **เหตุผล:** Owner อนุมัติลุยยาว ไม่ต้องขออนุมัติเพิ่ม เว้นเจอ stop condition (§6 ของ progress rail) — M1 ปิดแล้ว (commit a7fc1ad · gate ไม่แตะ · paid call 0 · QA ผ่าน)
- **หลักฐาน gate ไม่แตะ (รอบนี้):** `git diff c3b2d5d..HEAD -- axis_mcp/ profiles/ | head` = ว่างสำหรับ gate/renderer (มีแค่ docs/showcase 2 ไฟล์ Phase 1 ที่ commit แล้ว + 5 ไฟล์ใหม่ที่ยังไม่ commit) — รายละเอียดดู `git status --short`
- **paid call รอบนี้:** 0 ครั้ง (2 ไฟล์ M2 เป็น workflow doc — ไม่มี `generate_image` ไม่มี render)
- **กระทบ:** Content (เสก+Media Editor — Maker) · QA+Legal+Architect (Checker) · commit เป็นงาน Orchestrator หลังตรวจครบเท่านั้น

## D-002 — 2026-11-20 · M2 readiness checklist DRAFT เสร็จ (Maker: เสก)

- **โดย:** เสก (Head of Content — เจ้าของ Phase 2 งาน 2.2)
- **ตัดสินใจ:** ออก `CONTENT-GROWTH-PHASE2-READINESS-CHECKLIST-v1.md` v1.0 (17 ข้อ A–F) — สถานะ DRAFT รอ QA+Legal
- **เหตุผล:** แปลง Rule 1/3/4/5 ของเสกเป็นใบเช็กตรวจซ้ำได้ (ไอเดีย readiness gate + capability gate เบา ๆ — เขียนใหม่ ไม่ก๊อปโค้ด)
- **หลักฐานใช้กับบรีฟจริง:** `campaign_growth_m2_demo_90s` Brief v1 — ✅ READY 17/17 (เคส 1) + รอบซ้อม v0-draft จับตกข้อ 8 ได้ (เคส 2 — D-004)
- **approved_by (paid call):** ไม่มี — รอบนี้ไม่มี paid call ใด ๆ (ไม่ต้องมีลายเซ็น)
- **กระทบ:** Kawee/Film/Art/Sound/Media Editor/Ink — ทุกเลนต้องผ่านใบนี้ก่อนรับงานรอบ 2.4

## D-003 — 2026-11-20 · M3 progress rail DRAFT เสร็จ (Maker: Media Editor)

- **โดย:** Media Editor (เลนรวม — เจ้าของ Phase 2 งาน 2.1)
- **ตัดสินใจ:** ออก `CONTENT-GROWTH-PHASE2-PROGRESS-RAIL-v1.md` v1.0 (steps 5 ขั้น + timestamp + time-box รวม ≤60 นาที + stop conditions 4 ข้อ) — สถานะ DRAFT รอ QA+Architect
- **เหตุผล:** เอา steps 5 ขั้นที่มีอยู่แล้วใน `render_campaign_media_local` มารายงานให้เสกเห็นโดยไม่ถามเลน (ไม่สร้าง tracking ใหม่ ไม่แก้ renderer ไม่แก้ gate)
- **หลักฐาน steps ตรง renderer:** ชื่อ 5 ขั้นสะกดตรง `content_service.render_campaign_media_local` (`input_validation / piper_tts / synthetic_visuals / ffmpeg_assembly / output_audit`) — QA ตรวจซ้ำได้ด้วย grep
- **approved_by (paid call):** ไม่มี — รอบนี้ไม่มี render ไม่มี paid call
- **กระทบ:** เสก (อ่าน task_get_status ตาม §3) · Architect (ตรวจว่า task tracking เดิมพอ ไม่ต้องแก้)

## D-004 — 2026-11-20 · BLOCKED ซ้อม 1 รอบ — จับตกข้อ 8 ได้ ( closed in 1 round )

- **โดย:** เสก (Rule 5 — BLOCKED ต้องจบใน 1 รอบ)
- **สาเหตุ:** `campaign_growth_m2_demo_90s` Brief v0-draft ไม่ระบุ `visual_dependency` (ตก readiness ข้อ 8)
- **ทางเลือก:** A) ยืนยัน — ระบุ `visual_dependency: false` ใน v1 ภายในรอบเดียว (ไม่รอรอบ 2)
- **ผล:** ปิด BLOCKED ใน 1 รอบ (closed_in_one_round: true) → v1 ผ่าน 17/17 (D-002 เคส 1)
- **กระทบ:** Kawee (เลนเดียวที่เกี่ยว — เลนอื่นจ่ายได้ตามกฎข้อ 2 ของใบเช็ก)

## D-005 — 2026-11-20 · ส่ง Checker (Maker ≠ Checker — รอผล)

- **โดย:** พี่วุฒิ (Orchestrator — ประสาน handoff)
- **ตัดสินใจ:** ส่ง M2/M3 DRAFT (D-002 + D-003) ให้ Checker 3 ฝ่ายพร้อมกัน:
  1. QA-ทีม — ตรวจ gate ไม่แก้ / 17 ข้ออ้าง SOUL จริง / steps 5 ชื่อตรง renderer / 2 เคสตรวจซ้ำได้ → ออก QA PASS/FAIL
  2. Legal (ตุลย์) — ตรวจ license guard (5c/14) + ไม่มี paid call ไม่มี secrets → อ้าง LEGAL-SCOPE-v1 + rules/04-safety.md
  3. Architect (พี่ทรงศักดิ์) — ตรวจ progress rail ไม่ต้องแก้ task tracking / ถ้าต้องแก้ต้องมี ADR
- **กฎ:** ไฟล์อย่างเดียว ไม่ commit จนกว่า QA+Legal (+Architect สำหรับ progress rail) เซ็น PASS — commit เป็นงาน Orchestrator หลังตรวจครบ (ตามแผน §7 ข้อ 5)
- **ถ้า Checker ตก:** กลับมาแก้เป็น version ใหม่ (ของเก่าอยู่ครบ — version refine) ไม่แก้ทับ

---

## แนว M4–M6 (ยังไม่เริ่ม — จองเลขไว้กันสับสน)

| ID จอง | เรื่อง | เงื่อนไขเริ่ม |
|:-------|:-------|:--------------|
| D-006 | M4 ingest ประตูรับของนอก (Art/Ink) | หลัง M2+M3 PASS (DRAG-01 ปลด) |
| D-007 | M5 ชิ้นจริง end-to-end ผ่าน gate (วัดรอบแก้/เวลา) | หลัง M4 พร้อม — ไม่ผ่านไม่ขยับ Phase 3 |
| D-008 | M6 adapter ตัวแรก + ADR paid-call + ADR secrets | หลัง M5 PASS (RISK-01 ปลด) |
| D-009 | Commit M2+M3 (Orchestrator) | หลัง D-005 PASS ครบทุกฝ่าย |

> 🎯 **ประโยคปิด:** "ทุกบรรทัดมีคนเซ็น — ไม่มี 'น่าจะผ่าน' มีแค่ PASS ที่มีหลักฐานกับ FAIL ที่มี root cause"
