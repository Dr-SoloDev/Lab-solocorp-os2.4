# ✅ Readiness Checklist — เช็กก่อนจ่าย ไม่ใช่เช็กตอนพัง (Phase 2 งาน 2.2)

> **Phase 2 — เสี่ยงต่ำ ไม่แตะ paid call · ไม่แก้ gate**
> **Owner:** เสก (Head of Content) · **Maker:** Content (เสก — Master Brief owner) · **Checker:** QA + Legal (maker ≠ checker)
> **Version:** v1.1 (scope ลดตาม Path A — ไม่แตะ code/task schema) · **วันที่:** 2026-11-22 (v1.0: 2026-11-20) · **Branch:** `feat/content-growth-phase1` (เขียนไฟล์อย่างเดียว ไม่ commit)
> **Savepoint อ้างอิง:** `save-sek-rail-20261120` (c3b2d5d)
> **แผนแม่:** `docs/showcase/CONTENT-GROWTH-PLAN-v1.md` §1 งาน 2.2 + §3 M2
> **สถานะ:** DRAFT พร้อมตรวจ — รอ QA + Legal เซ็น Checker ก่อนนับเป็น M2 PASS
> **Scope v1.1 (ลดตาม Architect FAIL แบบมีเงื่อนไข):** 17 ข้อคงเดิม — ข้อความที่อ้าง task tracking กลางทางเปลี่ยนเป็น post-render pointer ทั้งหมด (อ่าน `steps` 5 ขั้นจากไฟล์ `local_media_render_result` หลัง render จบเท่านั้น · `task_get_status` ดูสถานะรวมเท่านั้น) — true mid-flight tracking ต้องรอ ADR-xxx (task steps schema) รอบ M5/M6
> **สไตล์:** ของเราเอง — ต่อยอด Rule 1/3/4 ของเสก + ประตู ingest ของ Art/Ink (ไอเดีย readiness gate จาก Jellyfish + capability gate เบา ๆ จาก waoowaoo — เขียนใหม่ทั้งหมด ไม่ก๊อปโค้ดใคร)

---

## 1. หลักการประโยคเดียว

> **บรีฟไม่ครบ 5 อย่าง = ไม่จ่าย — ใบนี้คือหลักฐานว่าถามครบแล้ว ไม่ใช่ความจำว่าเคยถาม**

ใบนี้อยู่ **คนละชั้น** กับ `review_publish_gate` ของ Media Editor: ใบนี้กันงานครึ่งใบตั้งแต่ก่อนจ่าย (pre-dispatch) ส่วน publish gate กันงานผิดก่อนเผยแพร่ (pre-publish) — ใบนี้ผ่านไม่ได้แปลว่า gate จะผ่าน และ gate ผ่านไม่ได้แปลว่าใบนี้เคยครบ

---

## 2. ใบเช็ก (ก๊อปไปใช้กับทุกบรีฟ — 1 ใบต่อ 1 brief_version)

```markdown
## Readiness Check — <campaign_id> Brief v<N> (วันที่: YYYY-MM-DD)

### A. บรีฟครบ 5 อย่างไหม (Rule 1 ของเสก — ขาดข้อเดียว = ไม่จ่าย)
- [ ] 1. goal (awareness | engagement | conversion | education — เลือก 1)
- [ ] 2. platform (primary + secondary — เช่น LinkedIn primary / X secondary)
- [ ] 3. audience (ใคร + รู้อะไรอยู่แล้ว — 1 บรรทัด)
- [ ] 4. key message + CTA (core message 1 ประโยค + primary CTA → goal + secondary CTA ≤1)
- [ ] 5. deadline (draft / final / publish — 3 วันครบ)
- [ ] 5b. claims guard: ตัวเลข/คำรับรองทุกข้อมี source หรือติดป้าย claims_pending_human_verification แล้ว
- [ ] 5c. license guard: Piper non-commercial / FLUX Kommunity / client asset = client_supplied_unverified + human_confirmation_required ครบ

### B. Route ล็อกหรือยัง (Rule 3 — ผิดเส้นทาง = รื้อทั้งเรื่อง)
- [ ] 6. route: {local per-scene 6×15s | local per-scene 10×10s | concat continuous} — ล็อก 1 อย่าง ห้าม "เดี๋ยวค่อยเลือก"
- [ ] 7. route เหตุผล 1 บรรทัด (เช่น "ต้องการ storyboard ตรวจได้ทันที → local" — บันทึกใน handoff log)

### C. Visual dependency ตั้งหรือยัง (กัน Kawee ล็อกคำที่อ้างภาพที่ยังไม่มี)
- [ ] 8. visual_dependency: {true | false} ระบุชัด
- [ ] 9. ถ้า true → ระบุจุดที่ต้องรอ Art (เช่น "รอตำแหน่ง headline บนปกก่อนล็อกคำ") — Kawee เขียนโครงไว้ก่อนได้ ห้ามล็อกคำที่อ้างภาพ
- [ ] 10. ถ้า false → Kawee ลุยได้เลย ไม่ต้องรอภาพ

### D. Capability gate เบา ๆ — เลนที่จ่ายมีของตรงงานไหม (กันจ่ายงานที่เลนทำไม่ได้)
- [ ] 11. งานมี LIPSYNC_AVATAR ไหม → ถ้ามี: Film มี lip-sync config จาก generate_voice_lipsync_prompt แนบ handoff หรือยัง (ไม่มี = ไม่จ่ายเลนนั้น)
- [ ] 12. งานมี PRODUCT_I2V ไหม → ถ้ามี: Art ยืนยันวัตถุ/โลโก้ reference ครบหรือยัง (ไม่มี = ไม่จ่ายเลนนั้น)
- [ ] 13. งานมี SFX/mix ไหม → ถ้ามี: Sound ยืนยัน Earshot SFX ID + sound_delivery_filename plan หรือยัง
- [ ] 14. งานมี ingest นอกไหม → ถ้ามี: ระบุ asset + ป้าย client_supplied_unverified + human_confirmation_required ครบทุกชิ้น (Art/Ink เจ้าของประตู — §1 งาน 2.3)

### E. Time-box ต่อเลน (กัน DRAG-01 — deadline ไหล)
- [ ] 15. ทุกเลนมีกรอบเวลาในบรีฟ (Kawee / Film / Art / Sound / Media Editor / Ink — เสกกำหนดรายแคมเปญ เช่น Film storyboard ภายใน X วัน)
- [ ] 16. เกินกรอบ = เสกตัดสิน A/B/C ใน 1 รอบ (ยืนยัน / ตัดออก / ขอข้อมูลเพิ่ม) ไม่ปล่อยไหล — อ้าง Rule 5 ของเสก

### F. Brief freeze (กันแก้ปากเปล่ากลางทาง)
- [ ] 17. บรีฟที่จ่าย = frozen input รอบนั้น — เปลี่ยน goal/key message = ออกบรีฟ v ใหม่ (ของเก่าอยู่ครบ) ไม่แก้ทับ

### ผลตัดสิน (เสกเซ็น)
- [ ] ✅ READY — ครบ 17 ข้อ → จ่ายขนาน 6 เลนได้ (task_create ทีละเลน — task_get_status ดูสถานะรวมเท่านั้น · steps รายขั้นดูจากไฟล์ local_media_render_result หลังจบ ไม่ใช่กลางทาง)
- [ ] ⛔ NOT READY — ตกข้อ {หมายเลข} → ไม่จ่ายเลนที่เกี่ยว → ออก BLOCKED 1 รอบ (A/B/C) → บันทึก Decision Log
```

**กฎใช้ใบนี้:**
1. 1 บรีฟ 1 ใบ — บรีฟ v2 = ใบใหม่ (ไม่แก้ใบเก่า)
2. ไม่ครบ = ไม่จ่ายเลนที่เกี่ยวเท่านั้น (เลนที่ไม่เกี่ยวล็อกแล้วจ่ายได้ — เช่น Ink baseline รอได้แต่ Media Editor route selection จ่ายก่อนได้ถ้าข้อ 6–7 ครบ)
3. ผลทุกใบลง Decision Log (`docs/showcase/CONTENT-GROWTH-DECISION-LOG-v1.md`) — ใครตัดสิน เมื่อไร ตกข้อไหน เลือก A/B/C อะไร

---

## 3. หลักฐานใช้กับบรีฟจริง ≥1 ใบ (เงื่อนไข M2 — วัดได้ ไม่ใช่ความรู้สึก)

### เคส 1 — บรีฟจริงผ่านตั้งแต่แรก (PASS)

> **Campaign:** `campaign_growth_m2_demo_90s` Brief v1 · **วันที่ตรวจ:** 2026-11-20 · **ผู้ตรวจ:** เสก (Maker)

```markdown
## Readiness Check — campaign_growth_m2_demo_90s Brief v1 (2026-11-20)

### A. บรีฟครบ 5 อย่าง
- [x] 1. goal: education → CTA "บันทึก checklist ไว้ใช้กับบรีฟหน้า"
- [x] 2. platform: LinkedIn primary / X secondary (feed 1:1 + cover 16:9 จาก THAI-REF-SET-v1)
- [x] 3. audience: ทีม SoloCorp + ผู้ติดตามสาย dev ที่รู้ว่า Content MCP มี gate แล้ว
- [x] 4. key message + CTA: "บรีฟใบเดียวทำให้ทีม 6 เลนวิ่งพร้อมกันได้" + primary CTA "ก๊อปใบเช็กนี้ไปใช้" / secondary "อ่าน Phase 1 flex-script"
- [x] 5. deadline: draft 2026-11-21 · final 2026-11-22 · publish โดยมนุษย์หลัง approval (ไม่กำหนด publish auto)
- [x] 5b. claims guard: ไม่มีตัวเลข % ใด ๆ — ไม่ต้องติดป้าย (Kawee ยืนยันไม่มี claim ลอย)
- [x] 5c. license guard: ใช้ THAI-REF-SET-v1 prompt sheet เท่านั้น (ยังไม่เรียก generate_image) · Piper non-commercial (draft ภายใน) · ไม่มี client asset รอบนี้

### B. Route
- [x] 6. route: local per-scene 6×15s = 90s (ล็อก)
- [x] 7. เหตุผล: "ต้องการ storyboard ตรวจได้ทันที + Concat ยังไม่มี render proof บน host นี้ (ADR-032) → local เท่านั้น"

### C. Visual dependency
- [x] 8. visual_dependency: false (copy ไม่รอภาพ — ใช้ THAI-REF-SET-v1 ดิบ)
- [x] 9–10. N/A (false → Kawee ลุยได้เลย)

### D. Capability
- [x] 11. LIPSYNC_AVATAR: ไม่มีในบรีฟนี้ (ทุกฉาก CINEMATIC_STORY / ACTION_DYNAMIC) → ไม่ต้องมี lip-sync config
- [x] 12. PRODUCT_I2V: ไม่มี (ไม่มีวัตถุ/โลโก้ที่ต้องรักษาทรง) → ไม่ต้องมี reference เพิ่ม
- [x] 13. SFX/mix: มี (Sound ทำ cue + Earshot SFX ประกอบ — Sound ยืนยันมี SFX ID plan)
- [x] 14. ingest นอก: ไม่มีรอบนี้ (M4 จะมี ingest จริง — รอบนี้ N/A แต่ประตูพร้อมแล้ว)

### E. Time-box
- [x] 15. Kawee 1 วัน / Film 2 วัน (รวม storyboard + cue) / Art 1 วัน (prompt sheet จาก ref ดิบ) / Sound 1 วัน / Media Editor 2 วัน (render local + gate) / Ink 1 วัน (baseline + metric) — รวม ≤7 วันอยู่ในกรอบบรีฟ
- [x] 16. เกินกรอบ = เสกตัดสิน A/B/C ใน 1 รอบ (Rule 5)

### F. Freeze
- [x] 17. บรีฟ v1 = frozen — เปลี่ยน goal = ออก v2

**ผล: ✅ READY — ครบ 17/17 → จ่ายขนานได้**
```

### เคส 2 — ใบเช็กจับได้ 1 จุด (หลักฐานว่าใบนี้กันงานครึ่งใบได้จริง)

> **Campaign เดียวกัน รอบซ้อม:** สมมติบรีฟ v0 (ดราฟต์ก่อนแก้) ที่ลืมข้อ 8 — เสกตีกลับก่อนจ่าย Kawee

```markdown
## Readiness Check — campaign_growth_m2_demo_90s Brief v0-draft (ซ้อม — 2026-11-20)

- [ ] 8. visual_dependency: ไม่ระบุ (ตกข้อนี้ข้อเดียว)
**ผล: ⛔ NOT READY — ตกข้อ 8 → ไม่จ่าย Kawee (เลนอื่นที่ครบจ่ายได้)**
**BLOCKED 1 รอบ:** เสกเลือก A) ยืนยัน — ระบุ visual_dependency: false ใน v1 ภายในรอบเดียว → ปิด BLOCKED (closed_in_one_round: true)
**บันทึก:** Decision Log D-004 (ดูไฟล์ Decision Log)
```

> เคส 2 คือสิ่งที่ M2 ต้องการ: **มีหลักฐาน 1 เคสที่ checklist จับได้** (หรือยืนยันว่าบรีฟครบตั้งแต่แรก — เรามีทั้งสองแบบ: เคส 1 ครบตั้งแต่แรก + เคส 2 จับข้อ 8 ได้ในรอบซ้อม)

---

## 4. Maker ≠ Checker + วิธีตรวจรับ

| บทบาท | ใคร | ทำอะไร |
|:------|:----|:-------|
| Maker | เสก (Head of Content) | ออกใบนี้ + ตรวจ 2 เคสข้างบน + บันทึก Decision Log |
| Checker QA | QA-ทีม | ตรวจว่าใบนี้ไม่แก้ gate / 17 ข้ออ้าง Rule 1/3/4/5 ของเสกจริง / 2 เคสมีหลักฐานตรวจซ้ำได้ — ออก QA PASS/FAIL เป็นลายลักษณ์อักษร |
| Checker Legal | ตุลย์ | ตรวจข้อ 5c + 14 (license guard + ingest ป้ายครบ) + ยืนยันไม่มี paid call ไม่มี secrets ในไฟล์ — อ้าง LEGAL-SCOPE-v1 + rules/04-safety.md |
| Orchestrator | พี่วุฒิ | ประสาน + คุม commit (ไฟล์อย่างเดียว ไม่ commit จนกว่าตรวจครบ) |

**เส้นชัย M2 (v1.1 scope ลด):** ใบนี้ 1 ใบ (17 ข้อคงเดิม) + ใช้กับบรีฟจริง ≥1 ใบ (มี 2 เคสข้างบน) + Decision Log entry + QA PASS + Legal PASS (license/secrets) — steps รายขั้นอ่านจากไฟล์ result หลังจบเท่านั้น ไม่ใช่ task tracking กลางทาง

---

## 5. อ้างอิง (ของเดิมทั้งหมด)

| แหล่ง | ใช้เรื่อง |
|:------|:----------|
| `profiles/15-content-creator/SOUL.md` (เสก Rule 1/3/4/5) | โครง 17 ข้อทั้งหมด — ใบนี้คือ Rule 1 ที่ทำเป็นใบเช็กตรวจซ้ำได้ |
| `docs/showcase/CONTENT-GROWTH-PLAN-v1.md` §1 งาน 2.2 + §3 M2 | นิยามงาน + เงื่อนไขผ่าน |
| `docs/showcase/CONTENT-GROWTH-PHASE1-FILM-FLEX-SCRIPT-v1.md` §5 | checklist ก่อน handoff ของ Film (ใบนี้อยู่ก่อนหน้านั้น 1 ชั้น) |
| `docs/showcase/LEGAL-SCOPE-v1.md` + `rules/04-safety.md` | ข้อ 5c/14 — license + secrets |
| `decisions/ADR-032-concat-host-2026-11-07.md` | ข้อ 6–7 — ทำไมรอบนี้ล็อก local เท่านั้น |

> 🎯 **ประโยคปิด:** "ใบเดียว 17 ข้อ — ครบถึงจ่าย ไม่ครบไม่จ่าย แล้วมีหลักฐานว่าเคยจับได้จริง"
