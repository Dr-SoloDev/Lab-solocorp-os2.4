# Content Growth Plan v1 — จากงานวิจัย 3 ลิงก์ สู่แบบของเรา (clean-room idea only)

> **Owner สั่ง:** ร่างแผนพัฒนา Content Growth จากงานวิจัย 3 ลิงก์ (Pixelle-Video, Jellyfish, waoowaoo) แบบไม่ก๊อป — เอาไอเดียมาออกแบบแบบเรา
> **Owner:** โปรดัค (Head of Product) · **Maker:** Product · **Checker:** Architect + QA (maker ≠ checker)
> **Version:** v1.0 · **วันที่:** 2026-11-20 · **Branch:** `feat/content-growth-phase1` (ไม่สร้าง branch ใหม่ — งานนี้คือแผน ไม่ใช่งาน implement)
> **Savepoint อ้างอิง:** `save-sek-rail-20261120` (c3b2d5d) — แผนนี้ไม่แตะ savepoint ตรง ถ้าเฟส 2–3 หลุดให้ rollback กลับจุดนี้
> **สถานะ:** แผนอนุมัติรอบ Product — ยังไม่เริ่มงานเฟส 2–3 จนกว่า RISK-01 / DRAG-01 จะปลด PARKED (ดู §5)
> **สไตล์:** ของเราเอง (SoloCorp documentary honesty) — ไม่ก๊อป ไม่ Fork ไม่ก๊อปโค้ดจากงานวิจัยใด ๆ

---

## 0. ที่มาของไอเดีย (clean-room — เอาแนวคิด ไม่เอาของ)

| งานวิจัย | ไอเดียที่หยิบมา (แนวคิดเท่านั้น) | สิ่งที่เราไม่ทำ |
|:---------|:--------------------------------|:----------------|
| **Pixelle-Video** | template (โครงสำเร็จหยิบใช้เลย) · split (แตกงานย่อยแล้วแพ็กกลับ) · progress (เห็นความคืบหน้ารายขั้น) · adapter (ชั้นแปลงให้ของนอกคุยกับของเราได้) · ingest (รับของจากข้างนอกอย่างมีประตู) | ไม่ Fork repo · ไม่ก๊อปโค้ด template/adapter/ingest ใด ๆ — เขียนของเราเองให้เข้ากับ Content MCP |
| **Jellyfish** | readiness gate (เช็กความพร้อมก่อนเริ่ม) · time-box (ล็อกกรอบเวลาแตกงาน) · confirm-before-generate (ยืนยันก่อนยิงงานที่มีต้นทุน) | ไม่ก๊อป gate logic — gate เรายังเป็น `review_publish_gate` ชุดเดิมของ Media Editor |
| **waoowaoo** | Brief freeze (บรีฟนิ่งแล้วห้ามแก้ปากเปล่า) · canvas (ผืนเดียวเห็นทุกเลน) · version refine (แก้เป็น version ใหม่ ของเก่ายังอยู่) · capability gate เบา ๆ (เช็กเบา ๆ ว่าเลนนี้ทำเรื่องนี้ได้ก่อนจ่าย) | ไม่ก๊อป canvas/version โค้ด — ใช้ Decision Log + brief version ของเสกที่มีอยู่แล้ว |

**กฎการอ้างอิง:** เอกสารทุกเฟสอ้างได้แค่ "ไอเดีย X จากงานวิจัย Y" — ห้ามแปะโค้ด ห้ามแปะลิงก์ดิบที่ต้อง login ห้ามอ้างว่าเข้ากันได้กับ license ของเขา (ของเราเขียนใหม่ทั้งหมด = ไม่มีปัญหา license ขาเข้า)

**Elastic License หมายเหตุ (จาก waoowaoo):** ถ้างานวิจัยชิ้นใดอยู่ใต้ Elastic License — **ห้าม host / ห้ามเอามารันเป็น service ของเรา** อ่านเอาไอเดียได้อย่างเดียว เรื่องนี้ Legal ยืนยันใน §3 (Legal)

---

## 1. เป้าหมาย 3 เฟส

### Phase 1 — DONE ✅ (เสี่ยงต่ำ ไม่แตะ paid call · ไม่แก้ gate)

| งาน | ไฟล์ | สาระ |
|:----|:-----|:-----|
| Film flex-script | `docs/showcase/CONTENT-GROWTH-PHASE1-FILM-FLEX-SCRIPT-v1.md` | แตกดราฟต์ยืดหยุ่น 3 หน่วย (ย่อหน้า/บรรทัด/ประโยค) → แพ็กลงล็อกตาย 6×15s=90s หรือ 10×10s=100s · gate เดิมทุกข้อ |
| Art Thai-ref 3 ขนาด | `docs/showcase/CONTENT-GROWTH-PHASE1-ART-THAI-REF-v1.md` | THAI-REF-SET-v1 (mood/palette/lighting ล็อก) + prompt sheet 9:16 / 1:1 / 16:9 — ยังไม่เรียก `generate_image` จริง |

- **Commit:** `a7fc1ad` · **Gate:** ไม่แตะ · **Paid call:** 0 ครั้ง · **Checker:** QA (ผ่านแล้ว)
- **สิ่งที่ Phase 1 พิสูจน์:** ทีมเขียน workflow doc เสริมได้โดยไม่แก้ SOUL ไม่แก้ gate — แพทเทิร์นนี้ใช้ซ้ำทุกเฟส

### Phase 2 — Progress + Ingest (งานจริง 1 ชิ้นผ่าน gate)

**โจทย์:** ทำให้ "งานเดินแล้วเห็น" (progress) และ "รับของนอกได้อย่างปลอดภัย" (ingest) — ปลด RISK-01 ด้วยชิ้นงานจริง ไม่ใช่เอกสารสวย

| # | งาน | ไอเดียต้นทาง | สาระแบบเรา |
|:-:|:----|:-------------|:-----------|
| 2.1 | **Progress rail — เห็นความคืบหน้ารายขั้น** | Pixelle (progress) + Jellyfish (time-box) | Media Editor รายงาน `steps` 5 ขั้น + timestamp ต่อขั้น (แบบเดียวกับ `render_campaign_media_local` มีอยู่แล้ว) — เสกดู `task_get_status` (สถานะรวม) แล้วเปิดไฟล์ result ดู `steps` รายขั้นหลังจบ ไม่ต้องถามเลน · ทุกเลนมี time-box ในบรีฟ (เช่น Film ส่ง storyboard ภายใน X วัน — ตัวเลขเสกกำหนดรายแคมเปญ) |
| 2.2 | **Readiness gate — เช็กก่อนเริ่ม ไม่ใช่เช็กตอนพัง** | Jellyfish (readiness gate) + waoowaoo (capability gate เบา ๆ) | ก่อนเสกจ่ายงานขนาน (Workflow §5.3) เพิ่มเช็กลิสต์ 1 ใบ: บรีฟครบ 5 อย่างไหม (goal/platform/audience/key message+CTA/deadline) · route ล็อกหรือยัง (local/concat) · visual_dependency ตั้งหรือยัง · เลนที่จ่ายมี capability ตรงงานไหม (เช่น งาน LIPSYNC ห้ามจ่ายเลนที่ไม่มี lip-sync config) — ไม่ครบ = ไม่จ่าย (Rule 1 เดิม แค่ทำเป็นใบเช็กให้ตรวจซ้ำได้) |
| 2.3 | **Ingest ประตูรับของนอก** | Pixelle (ingest) | รับ asset ลูกค้า/ภายนอกผ่านประตูด่านเดียว: ติดป้าย `client_supplied_unverified` + `human_confirmation_required` ทุกชิ้น (Art ทำอยู่แล้ว — ขยายเป็นกฎทุกเลน) · ไฟล์เปิดไม่ได้ = "ยังไม่ตรวจ" ไม่ใช่ "ผ่าน" · งาน Phase 2 ชิ้นแรกต้องมี ingest อย่างน้อย 1 ชิ้น (เช่น ภาพลูกค้า หรือ export ตัวเลขจาก Ink) เพื่อพิสูจน์ว่าประตูใช้ได้จริง |
| 2.4 | **ชิ้นงานจริง 1 ชิ้นผ่าน gate** | — (เงื่อนไขปลด RISK-01) | รัน end-to-end 1 แคมเปญ: brief → ขนาน → render local → `review_publish_gate` → Human Approval → Ink Next-Brief — วัดรอบแก้ + เวลารวม (§4) · ไม่ผ่าน = ไม่ขยับไป Phase 3 |

- **Gate:** ไม่แก้ gate เดิม — เพิ่มแค่ readiness checklist *ก่อนจ่ายงาน* (คนละชั้นกับ publish gate)
- **Paid call:** อนุญาตเฉพาะที่มี `approved_by` ลายเซ็นเสก 1 บรรทัด (Rule 4 เดิม — Phase 2 ยังไม่มี ADR paid-call ใหม่)

### Phase 3 — Media-Adapter + ADR paid-call/secrets (ขยายโดยไม่พัง)

**โจทย์:** เชื่อมของนอก/เครื่องมือใหม่ผ่านชั้นแปลง (adapter) ที่เราเขียนเอง + ล็อกกฎเงินและความลับเป็น ADR

| # | งาน | ไอเดียต้นทาง | สาระแบบเรา |
|:-:|:----|:-------------|:-----------|
| 3.1 | **Media-adapter — ชั้นแปลงของเราเอง** | Pixelle (adapter/template) | Adapter ทุกตัวเขียนใหม่ใน `content_service` (หรือโมดูลใหม่ที่ Architect รีวิว): รับ input นอก → แปลงเป็น layout ที่ renderer รับ (6×15 / 10×10 เท่านั้น) → ไม่ตรง = ปฏิเสธที่ `input_validation` เหมือนเดิม · template หมายถึงโครงบรีฟ/prompt สำเร็จของเรา (ต่อยอด THAI-REF-SET-v1 + flex-script) ไม่ใช่ template ของใคร |
| 3.2 | **ADR paid-call** | Jellyfish (confirm-before-generate) | เขียน ADR ล็อกกฎ paid call ระดับองค์กร: หนึ่งคำสั่งหนึ่งภาพ · ห้าม variant เผื่อเลือก · provider ล้ม = รายงาน error ดิบ + รอคำสั่ง ห้าม retry เอง · ทุก call อ้าง `approved_by` ใน Decision Log ได้ (ยกระดับ Rule 4 ของเสก → ADR) |
| 3.3 | **ADR secrets** | — (กฎเหล็ก §6) | เขียน ADR ล็อกกฎความลับ: ห้าม secrets/tokens/credentials/`.env` ใน repo ทุกกรณี · paid provider key อยู่ที่ host + env เท่านั้น · ไฟล์ bus runtime (`*.db-shm/*.db-wal`/log) เป็น local-only ห้าม commit — อ้าง `rules/04-safety.md` + `LEGAL-SCOPE-v1.md` |
| 3.4 | **Version refine เป็นระบบ** | waoowaoo (version refine + canvas) | บรีฟ version ใหม่ = ไฟล์/Decision Log entry ใหม่ ของเก่าอยู่ครบ (ไม่แก้ทับ) · approval ผูก version เดิม (Rule 6: asset เปลี่ยน = gate + approve ใหม่) · canvas = Master Brief ใบเดียวที่เห็น 6 เลนในผืนเดียว (ของเสกมีอยู่แล้ว — Phase 3 แค่ทำเทมเพลตให้ก๊อปง่าย) |

- **Gate:** publish gate เดิมยังไม่เปลี่ยน — ถ้าจะเปลี่ยนต้องออก ADR แยก + QA รีวิว + มนุษย์อนุมัติ
- **Concat:** `render_campaign_with_concat` ยังไม่มี render proof บน host นี้ (ADR-032) — Phase 3 ห้ามวางแผนพึ่ง Concat จนกว่าจะมีหลักฐานเรนเดอร์จริง

---

## 2. ทีมรับผิดชอบรายข้อ (ใครทำอะไร — ตาม SOUL ไม่ตั้งใหม่)

> หลัก: Head ไม่ออกแบบแทน specialist · specialist ไม่คุยข้ามแผนกตรง ๆ (ผ่าน Central Bus) · Maker ≠ Checker ทุกงาน

### ฝั่ง Content (ทีมเสก — 6 เลน)

| เลน | รับผิดชอบในแผนนี้ | Phase |
|:----|:-------------------|:------|
| **เสก (Head)** — brief/orchestrate | ออก Master Brief ใบเดียว + Brief freeze (บรีฟจ่ายแล้ว = frozen input รอบนั้น เปลี่ยน = ออก v ใหม่) · จ่ายขนาน 6 เลน · BLOCKED จบใน 1 รอบ · ลายเซ็น paid call 1 บรรทัด · รวมรายงานถึง CEO | ทุกเฟส — เจ้าของ Phase 2 งาน 2.2 (readiness checklist) |
| **Film (scriptwriter)** — storyboard + cue | เจ้าของ flex-script Phase 1 แล้ว · Phase 2: ใส่ time-box ต่อฉากใน storyboard + ระบุ route (local/concat) ก่อนเขียนฉากสุดท้าย · ไม่เรียก paid call ไม่เรนเดอร์เอง | P1 done → P2 (2.1 time-box) |
| **Kawee (copywriter)** — copy deck + claims | Copy Deck + Claims Table ทุกแคมเปญ · claim ไม่มี source = ตัดออกหรือติดป้าย `claims_pending_human_verification` ตั้งแต่ในบรีฟ · ไม่เดาตัวเลข | P2 (งาน 2.4 ชิ้นจริงต้องมี claims table) |
| **Art (visual designer)** — direction + prompt | เจ้าของ THAI-REF-SET-v1 แล้ว · Phase 2: ขยาย provenance/license ทุก asset · `generate_image` ต่อเมื่อมี `approved_by` เท่านั้น · หนึ่งคำสั่งหนึ่งภาพ ห้าม retry เอง | P1 done → P2 (2.3 ingest ฝั่งภาพ) |
| **Sound (audio designer)** — soundscape + cue | Soundscape + audio cue sheet + Earshot SFX · cue สร้างจากสคริปต์ตัวจริงหลังนิ่งเท่านั้น (สคริปต์เปลี่ยน = cue ใหม่) · ไม่เรียก render เอง | P2 (งาน 2.4 ชิ้นจริงต้องมี cue) |
| **Media Editor (ช่างตัดต่อ)** — รวม+เรนเดอร์+gate | เลนรวมตั้งแต่ route selection · รัน render (local เท่านั้นจนกว่า Concat จะมี proof) · ตรวจ LUFS −16.0 / SHA-256 / ffprobe · รัน `review_publish_gate` (ห้ามแก้ผล) · บันทึก `record_human_approval` ตาม version จริง · เจ้าของ progress `steps` 5 ขั้น (งาน 2.1) | ทุกเฟส — เจ้าของ Phase 2 งาน 2.1 + 2.4 |
| **Ink (analyst)** — strategy + ปิดวงจร | แปะ baseline/metric/review window ตั้งแต่บรีฟ · observed vs inferred แยกชัด · ไม่มีข้อมูล = `no data` + Data Gap Report (ไม่เดา) · ออก Next-Brief Input ทุกแคมเปญ — ไม่มี Next-Brief = งานค้าง "รอปิดวงจร" | P2 (2.3 ingest ฝั่งข้อมูล + 2.4 Next-Brief) |

### ข้ามแผนก (Head-to-Head)

| ฝ่าย | รับผิดชอบในแผนนี้ |
|:----|:-------------------|
| **Architect (พี่ทรงศักดิ์)** — adapter/task/matrix | รีวิว design ของ media-adapter (Phase 3 งาน 3.1) ก่อน implement · ดู task tracking (`task_create/list/get_status`) ให้รองรับ progress rail · ดู routing matrix (local vs concat + capability gate) ไม่ให้ route ผิด · ร่วมตรวจ (Checker) กับ QA |
| **Legal (ตุลย์)** — license | ยืนยัน license ขาเข้าทุกครั้ง (checklist 4 ข้อใน `LEGAL-SCOPE-v1.md`) · ยืนยัน Elastic License ห้าม host (ถ้าเจอ) · ร่วมร่าง ADR secrets (Phase 3 งาน 3.3) · ตรวจ FLUX Kommunity / Piper non-commercial note ทุก asset |
| **QA (QA-ทีม)** — gate | Checker ทุกงาน Phase 2–3 (maker ≠ checker) · gate เดิมไม่เปลี่ยนโดยไม่มีรีวิว QA · ออก QA PASS/FAIL เป็นลายลักษณ์อักษรต่อชิ้นงาน (วัด §4) · ตรวจ validate 20/20 (วัด §4) |
| **Orchestrator (พี่วุฒิ)** — pipeline/commit | ประสาน pipeline ข้ามแผนก (Content ↔ Architect ↔ Legal ↔ QA) · คุม commit/pipeline ตาม SOP — **แผนนี้เขียนไฟล์อย่างเดียว ไม่ commit** (commit เป็นงาน Orchestrator หลังทุกฝ่ายตรวจ) |

---

## 3. Milestones + วิธีวัด (ตัวเลข ไม่ใช่ความรู้สึก)

| Milestone | เงื่อนไขผ่าน (ต้องครบทุกข้อ) | วิธีวัด |
|:----------|:-----------------------------|:--------|
| **M1 — Phase 1 ปิด** ✅ | flex-script + thai-ref ครบ · gate ไม่แตะ · paid call 0 ครั้ง · commit a7fc1ad | ไฟล์ 2 ใบอยู่บน branch · QA ตรวจแล้ว |
| **M2 — Readiness checklist ใช้ได้** | เสกมีใบเช็ก 1 ใบ (§1 งาน 2.2) · ใช้กับบรีฟจริง ≥1 ใบ · ไม่ครบ = ไม่จ่าย (มีหลักฐาน 1 เคสที่ checklist จับได้ หรือยืนยันว่าบรีฟนั้นครบตั้งแต่แรก) | ใบเช็ก + Decision Log entry |
| **M3 — Progress rail เห็นจริง** | ชิ้นงาน 1 ชิ้นมี `steps` 5 ขั้น + timestamp ครบทุกระยะ · เสกดูสถานะได้โดยไม่ถามเลน | log `steps` + รายงาน Sek Brief Status |
| **M4 — Ingest รับของนอกได้** | asset นอก ≥1 ชิ้นผ่านประตู (ป้าย `client_supplied_unverified` + `human_confirmation_required` ครบ) · ไฟล์เปิดไม่ได้ (ถ้ามี) ถูกบันทึก "ยังไม่ตรวจ" ไม่ใช่ "ผ่าน" | handoff payload + provenance manifest |
| **M5 — ชิ้นงานจริงผ่าน gate (ปลด RISK-01)** | 1 แคมเปญ end-to-end: render → gate → Human Approval (version ตรง + SHA-256 ตรง) → Ink Next-Brief · **รอบแก้ ≤2** · เวลารวมอยู่ใน time-box ที่บรีฟล็อก | ดู §4 (รอบแก้/เวลา/งบ) + approval record + Next-Brief Input |
| **M6 — Adapter ตัวแรก + 2 ADR (ปิด Phase 3)** | media-adapter 1 ตัวผ่านรีวิว Architect · ADR paid-call + ADR secrets อนุมัติแล้ว · validate 20/20 · QA PASS (maker ≠ checker) | ADR 2 ฉบับ + รีวิว Architect + ผล validate + QA report |

### เกณฑ์วัดกลาง (ใช้ทุก milestone ที่เกี่ยวข้อง)

- **รอบแก้ ≤2:** จำนวนรอบแก้บรีฟ/บทก่อน render ผ่าน — เกิน 2 = milestone นั้นไม่ผ่าน ต้องบันทึก root cause
- **เวลา/งบ:** เวลารวมตั้งแต่บรีฟถึง approval เทียบ time-box ในบรีฟ · งบ = paid call ทุกครั้งต้องมี `approved_by` อ้างได้ (0 unapproved calls)
- **validate 20/20:** รัน validation ครบ 20 ข้อผ่าน 20 ข้อ (สคริปต์/adjunct ตามที่ QA กำหนด — แผนนี้ไม่นิยามเอง ให้ QA เป็นเจ้าของ)
- **QA PASS แบบ maker ≠ checker:** ผู้ตรวจต้องคนละคนกับผู้ทำ — รายงาน "เสร็จ" ไม่มีหลักฐาน = ไม่ผ่าน (กฎ `rules/06-certification.md`)
- **gate false → approval ตาม version:** ก่อนมนุษย์เซ็นต้อง `gate_passed: false · published: false · approved_version: null` · approval อ้าง version + SHA-256 ที่ตรวจจริงเท่านั้น · asset เปลี่ยน = version ใหม่ = gate + approve ใหม่
- **Next-Brief 100%:** ทุกแคมเปญมี Next-Brief Input จาก Ink — ไม่มีงานค้าง "รอปิดวงจร" เกิน 7 วัน (metric ของเสก Rule 7)

---

## 4. (ย้ายไป §5 — รวมความเสี่ยงไว้ที่เดียว กันลืมซ้ำ)

---

## 5. ความเสี่ยง RISK-01 / DRAG-01 + วิธีปลด + savepoint rollback

> แหล่ง: `docs/showcase/RISK-REGISTER-PHASE23-DRAG-v1.md` (PARKED — Owner decision 2026-11-20)

### RISK-01: เฟส 2–3 ช้า → ทีมติดแค่เอกสารสวยไม่มีงานออก

- **Impact:** โตไม่จริง (ตัวเลขไม่ขยับ มีแต่เอกสาร)
- **วิธีปลด (4 ชั้น — ทำครบถึงปลด):**
  1. **Readiness gate (Jellyfish):** ไม่จ่ายงานจนกว่าใบเช็ก §1 งาน 2.2 จะครบ — กันงานครึ่งใบที่ลากยาว
  2. **Time-box (Jellyfish):** ทุกเลนมีกรอบเวลาในบรีฟ — เกินกรอบ = เสกตัดสิน A/B/C ใน 1 รอบ ไม่ปล่อยไหล
  3. **Brief freeze (waoowaoo):** บรีฟจ่ายแล้ว = frozen — เปลี่ยน goal = ออกบรีฟ v ใหม่ (version refine ของเก่าอยู่ครบ) ไม่แก้ปากเปล่า
  4. **Refine-retain:** ทุกรอบแก้เก็บของเก่าไว้ — ตรวจย้อนได้ว่ารอบไหนพังเพราะอะไร (root cause ทุกรอบที่เกิน)
- **เงื่อนไขปลด PARKED:** M5 ผ่าน (ชิ้นงานจริง 1 ชิ้นผ่าน gate — วัดรอบแก้/เวลาได้เป็นตัวเลข)

### DRAG-01: สคริปต์ยืดหยุ่นเกิน ไม่มีคนคุมเวลา → Film ตัดนานขึ้น

- **Impact:** deadline ไหลทั้งก้อน
- **วิธีปลด (ของเดิม + วิจัยใหม่):**
  1. เสกคุมบรีฟใบเดียวตาม Rule 1 (บรีฟเดียวเท่านั้น ไม่มีบรีฟซ้อน) — *ของเดิม*
  2. ล็อกเวลารวม 90/100s (6×15s หรือ 10×10s — เกินไม่ได้) — *ของเดิม + flex-script Phase 1 รองรับแล้ว*
  3. BLOCKED จบใน 1 รอบ — *ของเดิม*
  4. **เพิ่มจากวิจัย:** time-box ต่อเลนในบรีฟ (Jellyfish) + readiness checklist ก่อนจ่าย (Jellyfish) + Brief freeze กันแก้กลางทาง (waoowaoo)
- **เงื่อนไขปลด PARKED:** M2 + M3 ผ่าน (checklist ใช้กับบรีฟจริงแล้ว + progress เห็นรายขั้น) — แล้วค่อยเปิดงาน 2.4 (ชิ้นจริง)

### Savepoint rollback

- **จุดกลับ:** `save-sek-rail-20261120` (c3b2d5d) — Sek v0.2.0 + 6 specialists Active + Phase 1 ครบ
- **เมื่อไรต้องกลับ:** เฟส 2–3 หลุด (gate ถูกแก้โดยไม่มี ADR / paid call ไม่มี approved_by / secrets หลุดเข้า repo / deadline ไหลเกิน time-box 2 รอบติด)
- **วิธีกลับ:** `git stash -u` งานค้าง → `git checkout save-sek-rail-20261120` (หรือ reset branch กลับ c3b2d5d) → เสกออกบรีฟใหม่จากจุดที่นิ่ง — ไม่แก้ history ที่ push แล้ว
- **กฎ:** rollback ไม่ต้องขอ Owner (ย้อนกลับได้ใน 1 session = CEO/Product ตัดสินเอง ตาม Decision Gate)

---

## 6. กฎเหล็ก 5 ข้อ (ผิดข้อเดียว = งานนั้นไม่ผ่าน ไม่ว่าผลจะสวยแค่ไหน)

1. **ไม่ Fork ไม่ก๊อปโค้ด — clean-room idea only:** เอาแนวคิดจากงานวิจัยได้ (template/split/progress/adapter/ingest · readiness/time-box/confirm · freeze/canvas/refine/capability) — ห้าม Fork repo ห้ามก๊อปโค้ด ห้ามแปะโค้ดเขาลงไฟล์เรา · adapter/template ทุกตัวเขียนใหม่เข้ากับ Content MCP
2. **Local-first:** render/test/validate รันบน host เราก่อนเสมอ (Piper + FFmpeg CLI) · Concat ใช้ได้ต่อเมื่อมี render proof บน host นี้ (ปัจจุบันยังไม่มี — ADR-032) · ห้ามพึ่ง service นอกที่ไม่มีใน runbook
3. **No paid call โดยไม่มี `approved_by`:** `generate_image` ทุกครั้งต้องมีลายเซ็นเสก 1 บรรทัดใน Decision Log ก่อนเรียก · หนึ่งคำสั่งหนึ่งภาพ · provider ล้ม = รายงาน error ดิบ + รอคำสั่ง ห้าม retry เอง
4. **No secrets ใน repo:** ห้าม secrets/tokens/credentials/`.env` ทุกกรณี · key อยู่ host + env เท่านั้น · bus runtime files (db-shm/wal/log) เป็น local-only ห้าม commit · ตรวจด้วย `secret-history-scan.sh` ก่อนส่งตรวจ
5. **Maker ≠ Checker + หลักฐานก่อนคำว่าเสร็จ:** ผู้ทำห้ามตรวจรับงานตัวเอง · รายงาน "เสร็จ" ไม่มีหลักฐาน = ไม่ผ่าน · gate/approval ผูก version · ทุกแคมเปญปิดด้วย Next-Brief

---

## 7. ลำดับถัดไป (หลังแผนนี้)

```
1. แผนนี้ → Architect + QA ตรวจ (Checker) → Owner เห็นชอบ
2. ปลด DRAG-01: เสกออก readiness checklist (M2) + Media Editor เปิด progress steps (M3)
3. ปลด RISK-01: รันชิ้นงานจริง 1 ชิ้น end-to-end (M4+M5) — วัดรอบแก้/เวลาเป็นตัวเลข
4. เปิด Phase 3: adapter ตัวแรก + ADR paid-call + ADR secrets (M6)
5. ทุกขั้น: เขียนไฟล์อย่างเดียว ไม่ commit — commit เป็นงาน Orchestrator หลังตรวจครบ
```

> 🎯 **ประโยคปิด:** "วิจัยสามลิงก์ให้ไอเดีย — แต่ของที่ส่งต้องเป็นของเรา เขียนใหม่ วัดได้ มีคนตรวจ และกลับจุดเดิมได้เสมอ"
