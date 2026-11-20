# Art — Thai Ref ชุดแรก 3 ขนาด (Prompt Sheet + Direction หยิบใช้เลย)

> **Phase 1 — เสี่ยงต่ำ ไม่เรียก `generate_image` จริง (no paid call)**
> **Owner:** เสก (Head of Content) · **Maker:** Content · **Checker:** QA
> **Version:** v1.0 · **วันที่:** 2026-11-20 · **Branch:** `feat/content-growth-phase1`
> **Savepoint อ้างอิง:** `save-sek-rail-20261120` (c3b2d5d)
> **สถานะ:** prompt sheet + direction พร้อมใช้ — ยังไม่สร้างภาพจริง ภาพแรกต้องมีลายเซ็นเสก 1 บรรทัดก่อน (Rule 4 ของเสก) แล้ว Art ค่อยเรียก `generate_image`
> **สไตล์:** ของเราเอง (SoloCorp documentary honesty) — ไม่ก๊อป Pixelle

---

## 1. Visual Direction กลาง (ล็อกทั้ง 3 ขนาด — เปลี่ยนต้องออก direction ใหม่)

```markdown
## Visual Direction — THAI-REF-SET-v1 (กลาง ใช้ทั้ง 3 ขนาด)

- **Mood:** restrained, hands-on, documentary honesty — จริง อบอุ่นแบบทำงานจริง ไม่ขายฝัน
- **Palette:** base #0F172A (deep navy) · surface #F5F1E8 (warm paper-white) · accent #E4572E (burnt orange ใช้จุดเดียวต่อเฟรม)
- **Lighting:** soft directional key from upper left, gentle falloff, no hard rim, no harsh shadows
- **Texture:** matte paper with visible fibre, light grain, ผิวจริงไม่พลาสติก (แก้วมีหยดน้ำได้ ผ้าเห็นเส้นใยได้)
- **Focal point rule:** one subject per frame + generous negative space เผื่อ caption/headline ภาษาไทย
- **Thai context cue:** วัตถุ/ฉากที่คนไทยจำได้ทันที (โต๊ะไม้ แก้วชา สมุดงาน แสงเช้าหน้าต่าง) แต่ไม่ใส่ข้อความไทยในภาพ (ตัวหนังสือให้เป็นงานกราฟิกทีหลัง ไม่ใช่หน้าที่โมเดล)
- **Do not:** glossy 3D renders, stock-photo smiles, neon gradients, ลุคออฟฟิศหรูเกินจริง, ภาพผลลัพธ์เกินจริง (กราฟพุ่ง คนถือเงิน)
```

**สิ่งที่ล็อก (ห้ามเปลี่ยนรายภาพ):** mood · palette 3 สี · lighting ทิศเดียว · negative มาตรฐาน (§4)
**สิ่งที่ปรับได้รายแคมเปญ:** subject (วัตถุหลัก) · ฉากหลัง · ตำแหน่ง negative space (บน/ล่างตาม caption) · accent อยู่ตรงไหนของเฟรม

---

## 2. Negative มาตรฐาน (ใช้ทุกภาพ + ส่วนเพิ่มรายขนาด)

**Standard negative (แปะทุก prompt Sheet):**

```
no text, no watermark, no logos, no identifiable faces,
no exaggerated success claims, no stock-photo smile
```

**เพิ่มรายขนาด:**

| ขนาด | เพิ่ม negative | เหตุผล |
|:-----|:--------------|:-------|
| 9:16 vertical | `no cropped headline area, no busy top third` | เว้นที่สามบนให้ caption TikTok/Reels ไม่โดน UI บัง |
| 1:1 square | `no edge-cropped subject, no tiny details` | จอเล็ก รายละเอียดจิ๋วอ่านไม่เห็น กลายเป็น noise |
| 16:9 wide | `no centered single object only, no empty sides` | เฟรมกว้าง วัตถุเดียวตรงกลางแล้วข้างโล่ง = ดูขาด — ต้องมี context ซ้ายขวา |

- ⚠️ Prompt ยาวไม่เกิน **2,000 ตัวอักษร** (รวม negative) — เขียนให้คม ไม่ใช่ยาว
- ⚠️ Output จาก NIM เป็น **JPEG เสมอ** แม้ขอ png — รายงานตามจริง (`requested_format` vs `actual_format`)

---

## 3. Prompt Sheet 3 ขนาด (EN — พร้อมยิงเมื่อเสกอนุมัติ)

### Asset 01 — Key Visual 9:16 (TikTok / Reels / Shorts)

- **Aspect / pixels (NIM จริง):** `9:16` → 1024 × 1820 (สเปกปลายทาง 1080×1920 เป็นงาน Media Editor อัพสเกล/เรนเดอร์ — คนละชั้น ห้ามสับสน)
- **ใช้กับ:** ปกคลิป 90s/100s · key art หลักของแคมเปญ
- **Composition note:** subject อยู่กลาง-ล่าง สามบนเว้นว่างให้ headline

```markdown
## Asset 01 — key art (9:16)

- **Prompt (EN):** eye-level medium shot, 50mm, single wooden work desk as focal
  point with open notebook and glass of tea, morning light from upper left
  window with gentle falloff, deep navy base with warm paper-white highlights
  and burnt orange accent on notebook cover, matte paper surface with visible
  fibre and light grain, generous empty space in top third for caption,
  documentary honesty, editorial still, low saturation
- **Negative:** no text, no watermark, no logos, no identifiable faces,
  no exaggerated success claims, no stock-photo smile,
  no cropped headline area, no busy top third
- **Model target:** NVIDIA NIM FLUX.3 Klein (paid call — รอเสกอนุมัติก่อนเรียก)
- **Aspect / pixels:** 9:16 → 1024 × 1820 · **format:** jpeg · **provider:** nvidia
- **License note:** FLUX Kommunity v1.0 non-commercial default; commercial เฉพาะ Qualifying Users (< USD 5M/ปี) — human_confirmation_required ก่อนใช้เชิงพาณิชย์
```

**บรรทัดอนุมัติตัวอย่าง (เสกเขียน 1 บรรทัด Art ถึงเรียกได้):**
```text
approved_by: เสก — อนุมัติ generate_image 1 ภาพ 9:16 (1024x1820, jpeg, nvidia) ในบรีฟ <campaign_id> 2026-11-20
```

### Asset 02 — Feed 1:1 (LinkedIn / Facebook feed / carousel ปก)

- **Aspect / pixels (NIM จริง):** `1:1` → 1024 × 1024
- **ใช้กับ:** โพสต์ feed · ปก carousel · ภาพประกอบบทความ
- **Composition note:** subject กลางเฟรมชิ้นเดียว องค์ประกอบน้อย อ่านได้ใน 1 วินาทีบนมือถือ

```markdown
## Asset 02 — feed square (1:1)

- **Prompt (EN):** top-down flat lay, 35mm, single open notebook with handwritten
  checklist and burnt orange pen on warm paper-white surface, deep navy
  background edge, soft key light from upper left with gentle falloff, matte
  paper texture with visible fibre, one focal point centered with breathing
  room on all sides, documentary honesty, editorial still, low saturation
- **Negative:** no text (no readable handwriting, no legible words), no watermark,
  no logos, no identifiable faces, no exaggerated success claims,
  no stock-photo smile, no edge-cropped subject, no tiny details
- **Model target:** NVIDIA NIM FLUX.3 Klein (paid call — รอเสกอนุมัติก่อนเรียก)
- **Aspect / pixels:** 1:1 → 1024 × 1024 · **format:** jpeg · **provider:** nvidia
- **License note:** FLUX Kommunity v1.0 non-commercial default; commercial เฉพาะ Qualifying Users (< USD 5M/ปี) — human_confirmation_required ก่อนใช้เชิงพาณิชย์
```

> หมายเหตุ: `no readable handwriting` เจาะจงกว่าปกติ เพราะ flat lay สมุดมักล่อให้โมเดลสร้างลายมือปลอม — ถ้าแคมเปญต้องการลายมือจริง ให้ใช้ภาพถ่ายจริง + `ingest_client_generated_artifact` แทน ห้ามหวังพึ่งโมเดล

### Asset 03 — Cover 16:9 (YouTube / เว็บ / LinkedIn video)

- **Aspect / pixels (NIM จริง):** `16:9` → 1820 × 1024
- **ใช้กับ:** ปกวิดีโอ · hero เว็บ · สไลด์เปิด
- **Composition note:** เล่า 2 ฝั่ง — ซ้าย subject ขวา negative space ให้ title (หรือกลับข้างตามภาษา) ห้ามวัตถุเดียวโดดกลางเฟรม

```markdown
## Asset 03 — cover wide (16:9)

- **Prompt (EN):** wide eye-level shot, 35mm, small team work table on left third
  with notebook laptop glass of tea in soft morning light from upper left,
  calm office corner with window light on right two-thirds left empty for
  title, deep navy base with warm paper-white highlights and single burnt
  orange accent, matte surfaces with visible texture and light grain,
  documentary honesty, cinematic still, low saturation, shallow depth of field
- **Negative:** no text, no watermark, no logos, no identifiable faces,
  no exaggerated success claims, no stock-photo smile,
  no centered single object only, no empty sides
  (note: "empty sides" หมายถึงโล่งแบบขาด context — ที่เว้นไว้ต้องเป็นแสง/บรรยากาศ ไม่ใช่ความว่างเปล่า)
- **Model target:** NVIDIA NIM FLUX.3 Klein (paid call — รอเสกอนุมัติก่อนเรียก)
- **Aspect / pixels:** 16:9 → 1820 × 1024 · **format:** jpeg · **provider:** nvidia
- **License note:** FLUX Kommunity v1.0 non-commercial default; commercial เฉพาะ Qualifying Users (< USD 5M/ปี) — human_confirmation_required ก่อนใช้เชิงพาณิชย์
```

---

## 4. วิธีหยิบใช้ (Direction — อ่าน 2 นาทีแล้วสั่งงานได้)

```
เสกออก Master Brief → ระบุว่าใช้ Thai-ref ชุดไหน:
  ├─ ใช้ดิบ (default): อ้าง "THAI-REF-SET-v1 Asset 01/02/03" ทั้งก้อน — Art ไม่ต้องเขียน direction ใหม่
  │   └─ Art ทำ: design_visual_prompt ด้วย prompt ข้างบน → รอ approved_by 1 บรรทัด → generate_image
  ├─ ปรับ subject: เปลี่ยนแค่วัตถุหลัก/ฉากหลัง แต่ mood/palette/lighting/negative มาตรฐานคงเดิม
  │   └─ Art ทำ: แก้บรรทัด subject ใน prompt + บันทึกว่าแก้อะไรใน Image Call Record
  └─ ฉีก direction: mood/palette ใหม่ทั้งชุด → ไม่ใช่ ref ชุดนี้แล้ว ต้องเขียน Visual Direction Sheet ใหม่ทั้งใบ

Media Editor รับต่อ:
  ├─ ตรวจ: pixels ตรงตาราง NIM ไหม (9:16=1024×1820 / 1:1=1024×1024 / 16:9=1820×1024) · format jpeg จริงไหม
  ├─ Visual QA ด้วยตา 6 ข้อ (text ปลอม / watermark / logo / ใบหน้า / claim เกินจริง / ตรง direction)
  └─ เปิดไฟล์ตรวจไม่ได้ = "ยังไม่ตรวจ" ไม่ใช่ "ผ่าน" (Rule 6 ของ Art)
```

**ห้าม (ย้ำเพราะเป็น paid call):** หนึ่งคำสั่งหนึ่งภาพ · ห้ามสร้าง variant เผื่อเลือก · ภาพแรกไม่สวย = paid call ใหม่ต้องมีคำสั่งใหม่ · provider ล้ม = รายงาน error ดิบ + prompt ที่ใช้ แล้วรอคำสั่ง ห้าม retry เอง

---

## 5. Provenance & License (แปะทุก asset — ไม่มีข้อยกเว้น)

```json
{
  "ref_set": "THAI-REF-SET-v1",
  "assets": ["9:16 key art", "1:1 feed", "16:9 cover"],
  "model": "NVIDIA NIM FLUX.3 Klein",
  "provider_default": "nvidia",
  "license_note": "FLUX Kommunity v1.0 non-commercial default; commercial use only for Qualifying Users (< USD 5M annual revenue) — human_confirmation_required",
  "generated_with_paid_call": false,
  "phase1_status": "prompt sheet + direction only — no image generated yet"
}
```

- Asset ลูกค้าส่งมา = `client_supplied_unverified` + `human_confirmation_required` (ไม่เกี่ยวกับ ref ชุดนี้ แต่ Art ต้องรายงานตามจริงถ้ามีปนมา)
- `resolution` (`1K`/`2K`/`4K`) เป็นค่าที่ tool รับ แต่ขนาดจริงบนเส้น NIM มาจากตาราง aspect เท่านั้น — **ห้ามรายงานว่าได้ 4K** ถ้าไฟล์ไม่ใช่ 4K จริง

---

## 6. อ้างอิง (ของเดิมทั้งหมด)

| แหล่ง | ใช้เรื่อง |
|:------|:----------|
| `profiles/15-content-creator/sek/team/03-visual-designer-art.SOUL.md` | Rule 1–7, Prompt 5 องค์ประกอบ, ตาราง aspect NIM, Visual QA, Image Call Record — เอกสารนี้คือ ref พร้อมใช้ ไม่แก้ต้นฉบับ |
| `profiles/15-content-creator/SOUL.md` (เสก) | Rule 4 (paid call ลายเซ็น 1 บรรทัด), Visual direction pointer ใน Master Brief |
| `docs/MEDIA-TOOLKIT.md` | สถานะเครื่องมือ + ข้อจำกัดสิทธิ์ Piper/FLUX |
| `axis_mcp/departments/content_service.py` | ตาราง `NVIDIA_ASPECT_TO_WIDTH_HEIGHT`, เพดาน 2,000 ตัวอักษร, license note NIM |

> 🎯 **ประโยคปิด:** "สามขนาด หนึ่ง mood — หยิบไปสั่งได้เลย ภาพแรกยังต้องมีลายเซ็นเสกก่อนเสมอ"
