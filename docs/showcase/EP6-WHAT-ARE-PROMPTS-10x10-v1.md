# EP.6 WHAT ARE PROMPTS? — Storyboard 10x10 v1 (100s)

> **Provenance / ที่มาของไฟล์นี้ (อ่านก่อนใช้):**
> - ไฟล์นี้คือ **storyboard ระบบเรา** ที่แพ็กจาก **สคริปต้นฉบับในแชท (Owner-approved verbatim)** ลง **layout 10 x 10s = 100s** — **ไม่ใช่ master Meta**
> - Master / character ref รูปแนบในแชท ยังเป็น **client_supplied_unverified อยู่นอกระบบ** — ไม่ก๊อปเข้า repo, ไม่อ้าง license, ไม่ใช้ render
> - บท EN / on-screen / action ในไฟล์นี้ **คัดจากแชทคำต่อคำ ห้ามแต่งเพิ่ม** — Clip5 แตกเป็น S5a Bad + S5b Good ตามคำสั่ง Owner เท่านั้น
> - **สถานะ:** draft storyboard สำหรับตรวจบท — **ห้าม render ห้าม commit** (validate เบาๆ เท่านั้น)

> **Meta:** Owner: เสก (Head of Content) · Series: What is AI? EP.6 · Version: v1.0 · วันที่: 2026-11-21
> **Branch:** `feat/content-growth-phase1` · **Layout:** 10 scenes x 10s = 100s · **Render path:** ยังไม่ล็อก (ไฟล์นี้คือบท+บอร์ดเท่านั้น)
> **Global style (จากแชท):** Modern Creative Loft · character ref รูปแนบ — หน้าเดิม แว่นดำ เสื้อยืดดำ · medium shot · pop-up บนกลาง + ซับล่างสุด · เสียงชัด ไม่มี BGM

---

## 1. Source mapping — จาก 9 คลิปในแชท → 10 ซีน 100s

| คลิปแชท | ซีนในไฟล์นี้ | เวลา | วิธีแพ็ก |
|:--------|:-------------|:-----|:---------|
| Clip1 Hook | S1 | 0-10s | ตรง 1:1 |
| Clip2 Intro | S2 | 10-20s | ตรง 1:1 |
| Clip3 นิยาม | S3 | 20-30s | ตรง 1:1 |
| Clip4 กฎเหล็ก | S4 | 30-40s | ตรง 1:1 |
| Clip5 Bad vs Good | S5 (S5a Bad) | 40-50s | **แยกครึ่งแรก → เต็ม 10s** ตามคำสั่ง Owner |
| Clip5 Bad vs Good | S6 (S5b Good) | 50-60s | **แยกครึ่งหลัง → เต็ม 10s** ตามคำสั่ง Owner |
| Clip6 สูตร 3 ส่วน | S7 | 60-70s | ตรง 1:1 (เลื่อนเวลามา 60-70s เพราะ S5 แตก) |
| Clip7 ทำไมต่าง | S8 | 70-80s | ตรง 1:1 |
| Clip8 Recap | S9 | 80-90s | ตรง 1:1 |
| Clip9 Outro | S10 | 90-100s | ตรง 1:1 |

> หมายเหตุเวลา: คำสั่งเดิมใน Clip5 เขียนว่า "5a Bad (0-10s ครึ่งแรก) / 5b Good (10-20s ครึ่งหลัง)" หมายถึงครึ่งแรก/หลัง **ภายใน Clip5** — พอแพ็กเป็น 10x10 แล้วคือ S5 = 40-50s, S6 = 50-60s ต่อเนื่องไม่มี gap

---

## 2. Global visual bible (ใช้ทุกซีน — ห้ามเปลี่ยนกลางเรื่อง)

- **Location:** Modern Creative Loft (ล็อกเดียวทั้ง 100s)
- **Character:** ref รูปแนบในแชท — หน้าเดิม แว่นดำ เสื้อยืดดำ (character consistency)
- **Framing LIPSYNC:** medium shot พูดกล้อง (S1-S4, S7-S10)
- **Framing CINEMATIC:** split-screen เทียบ Bad vs Good (S5, S6)
- **Graphics:** pop-up บนกลาง (on-screen ตามตาราง) + ซับล่างสุด (จากบท EN)
- **Audio:** เสียงชัด ไม่มี BGM
- **Language:** บทพูด EN ทั้ง 10 ซีน (ตามแชท)

---

## 3. Scene table — 10 ซีน 0-10 ... 90-100

> Time separator ใช้ hyphen ASCII `-` เท่านั้น · คอลัมน์ Voiceover ขึ้นต้น `VO: "..."` (local per-scene) · 1 ซีน = 1 tag เท่านั้น

| เวลา | Scene / Visual | Voiceover / On-screen / Action / Tag |
|:-----|:---------------|:-------------------------------------|
| 0-10s | S1 Hook — [TAG: LIPSYNC] Modern Creative Loft, medium shot พูดกล้อง, pop-up บนกลาง | VO: "AI is a genius, but it cannot read your mind. To get great results, you need one skill: Prompting." / On-screen: "AI CANNOT READ YOUR MIND" / Action: hook พูดกล้องตรง / Tag: LIPSYNC |
| 10-20s | S2 Intro — [TAG: LIPSYNC] Modern Creative Loft, medium shot พูดกล้อง, pop-up บนกลาง | VO: "Welcome back to AXIS. I'm Dr. Solodev. This is What is AI? EP.6. Today: What are Prompts?" / On-screen: "WHAT ARE PROMPTS? \| EP.6" / Action: intro ทักทายพูดกล้อง / Tag: LIPSYNC |
| 20-30s | S3 Definition — [TAG: LIPSYNC] Modern Creative Loft, medium shot + open hand gestures, pop-up บนกลาง | VO: "A Prompt is simply the instruction you give to AI. It can be a question, a command, or an example." / On-screen: "Prompt = Your Instruction to AI" / Action: open hand gestures / Tag: LIPSYNC |
| 30-40s | S4 Golden rule — [TAG: LIPSYNC] Modern Creative Loft, medium shot, เปรียบเทียบสองมือ, pop-up บนกลาง | VO: "Think of it like talking to a smart assistant. Vague instructions give vague answers. Clear prompts give magic." / On-screen: "Clear Prompt = Better Output" / Action: compare both hands / Tag: LIPSYNC |
| 40-50s | S5a Bad example — [TAG: CINEMATIC] Split-screen ฝั่ง Bad, Modern Creative Loft, pop-up บนกลาง "Bad", ซับล่างสุด | VO: "Bad prompt: Write an email." / On-screen: "Be Specific with Details" (ครึ่ง Bad — จอแสดงคำว่า Bad / vague) / Action: ยกมือข้างหนึ่งนับตัวอย่างที่ 1 (Bad) สีหม่น / Tag: CINEMATIC split-screen |
| 50-60s | S5b Good example — [TAG: CINEMATIC] Split-screen ฝั่ง Good, Modern Creative Loft, pop-up บนกลาง "Good", ซับล่างสุด | VO: "Good prompt: Write a polite 3-sentence email to reschedule a client meeting." / On-screen: "Be Specific with Details" (ครึ่ง Good — จอแสดงประโยค Good เต็ม) / Action: ยกอีกมือนับตัวอย่างที่ 2 (Good) สีสว่าง / Tag: CINEMATIC split-screen |
| 60-70s | S7 Formula 3 parts — [TAG: LIPSYNC] Modern Creative Loft, medium shot, ชู 3 นิ้ว, pop-up บนกลาง | VO: "Here is a simple formula. Give AI a Role, explain the Task, and set the Format you want." / On-screen: "Role + Task + Format" / Action: count 3 fingers / Tag: LIPSYNC |
| 70-80s | S8 Why different — [TAG: LIPSYNC] Modern Creative Loft, medium shot, ชี้กล้องแบบเป็นกันเอง, pop-up บนกลาง | VO: "Two people can use the exact same AI, and get totally different results-all because of how they prompt." / On-screen: "Same AI, Different Prompts" / Action: point camera friendly / Tag: LIPSYNC |
| 80-90s | S9 Recap — [TAG: LIPSYNC] Modern Creative Loft, close-up medium shot ช้าๆ ชัดๆ, pop-up บนกลาง | VO: "Let's recap. A prompt is how you guide AI. Be clear, give context, and tell it exactly what you need." / On-screen: "Clarity + Context = Great Prompt" / Action: close-up medium shot slow clear / Tag: LIPSYNC |
| 90-100s | S10 Outro — [TAG: LIPSYNC] Modern Creative Loft, medium shot ยิ้มโบกมือเล็กน้อย, pop-up บนกลาง | VO: "Do you use a secret prompt trick? Share it below! Next episode, EP.7: What is a Token? See you there. This is AXIS." / On-screen: "NEXT EP.7: WHAT IS A TOKEN?" / Action: smile wave slightly / Tag: LIPSYNC |

**Tag summary (ปรับตามจริง — จาก 9 คลิป → 10 ซีน):**
- เดิม 9 คลิป = LIPSYNC 7 (S1-4,6,8,9 นับแบบ 9 คลิป) + CINEMATIC 2 (Clip5 แตกในคลิปเดียว)
- **จริง 10x10 = LIPSYNC 8 (S1-S4, S7-S10) + CINEMATIC 2 (S5, S6 split-screen)** — Clip5 แยกเป็น 2 ซีนเต็ม 10s ละซีน เลยเพิ่ม LIPSYNC ไม่ได้ แต่ CINEMATIC ได้ 2 ซีนเต็ม (S5 Bad + S6 Good)

---

## 4. Visual dependency

- **VD-01 Character ref:** รูปแนบในแชท (client_supplied_unverified, อยู่นอกระบบ) — หน้าเดิม แว่นดำ เสื้อยืดดำ ทุกซีน LIPSYNC medium shot
- **VD-02 Set:** Modern Creative Loft ล็อกเดียวทั้ง 100s — ห้ามเปลี่ยน set กลางเรื่อง (S1-S10 ต่อเนื่อง)
- **VD-03 Graphics:** pop-up บนกลาง (ข้อความ on-screen ตามตาราง §3) + ซับล่างสุด (ตรง VO EN) — ฟอนต์/ตำแหน่งเดียวทั้งเรื่อง
- **VD-04 S5/S6 split-screen:** S5 = ฝั่ง Bad (โทนหม่น, ข้อความสั้น "Write an email") / S6 = ฝั่ง Good (โทนสว่าง, ประโยค Good เต็ม) — ต้องเห็นความต่างใน 1 วินาทีแรกของแต่ละซีน
- **VD-05 S7 fingers:** ชู 3 นิ้วนับ Role / Task / Format ตรงจังหวะ VO (3 จังหวะใน 10s)
- **VD-06 S8 eye-line:** มองกล้องตรง ชี้กล้องแบบ friendly (ไม่ใช่ aggressive point)
- **VD-07 S9 pacing:** close-up medium shot ช้าลงกว่าซีนอื่น เน้นจำ (recap)
- **VD-08 S10 exit:** ยิ้ม + โบกมือเล็กน้อย + on-screen "NEXT EP.7: WHAT IS A TOKEN?" ค้างจนจบ 100s
- **VD-09 Audio:** เสียงพูดชัด ไม่มี BGM — ห้ามใส่ดนตรีทับ VO เด็ดขาด

---

## 5. Lip-sync note

- **LIPSYNC 8 ซีน (S1-S4, S7-S10):** พูดกล้อง medium shot (S9 close-up medium) — ปากต้องตรง VO EN ทุกซีน
- **CINEMATIC 2 ซีน (S5, S6):** split-screen ตัวอย่าง Bad/Good — ไม่บังคับ lip-sync เต็มปาก (เน้นกราฟิก on-screen + VO Dennis ชัด) ถ้าจะ render local per-scene ให้ใช้ VO แยกแถว ถ้า concat ให้ใช้ cue ต่อแถว + narration ก้อนเดียว (ห้ามผสม route กลางเรื่อง)
- **VO timing heuristic (10s/ซีน):** EN ~35-45 syllables/10s โดยประมาณ — บทในตาราง §3 เป็น verbatim จากแชท ถ้า renderer รายงาน drift เกิน ±50 ms ให้ตัด/ขยายที่ action/visual ก่อน ห้ามแก้บทเองโดยไม่ผ่าน Owner (บทนี้ Owner ล็อก verbatim)
- **S5/S6 VO สั้น:** S5 "Bad prompt: Write an email." สั้นกว่า 10s โดยธรรมชาติ — ให้ค้างภาพ split-screen + on-screen "Be Specific with Details" จนครบ 10s ห้ามยืดคำ/ซ้ำประโยคถ่วงเวลา
- **S10 VO ยาว:** ประโยค Outro ยาวสุด — ถ้าเกิน 10s ให้เร่งจังหวะภาพ (ไม่ใช่ตัดบท) แล้ววัด drift จริงที่ renderer

---

## 6. Light validation (เบาๆ — ไม่ render)

```
[ ] จำนวนซีน = 10 (S1-S10) — ครบ
[ ] ผลรวมเวลา = 100s — 0-10 ... 90-100 ต่อเนื่อง ไม่มี gap/ทับ
[ ] ตัวคั่นเวลา hyphen ASCII `-` ทั้ง 10 แถว
[ ] บท EN ครบ 10 ซีน verbatim จากแชท (S5/S6 แยกตามคำสั่ง ไม่แต่งเพิ่ม)
[ ] on-screen ครบ 10 ซีน (S5/S6 ใช้ "Be Specific with Details" ทั้งคู่ แยก Bad/Good ด้วยภาพ)
[ ] action ครบ 10 ซีน
[ ] tag ซีนละ 1 tag — LIPSYNC 8 + CINEMATIC 2 (ปรับจาก 7+2 ของ 9 คลิป เพราะ Clip5 แตก)
[ ] visual_dependency ครบ (VD-01 - VD-09)
[ ] lip-sync note ครบ (8 พูดกล้อง + 2 split-screen)
[ ] หัวไฟล์ระบุชัด: storyboard ระบบเรา (10x10) ไม่ใช่ master Meta (client_supplied_unverified นอกระบบ)
[ ] ไม่ render ไม่ commit (ไฟล์ draft ใน working tree เท่านั้น)
```

---

## 7. Next steps (ไม่ทำในรอบนี้)

1. Owner/QA ตรวจบท verbatim + on-screen ในไฟล์นี้
2. ล็อก render path (local per-scene vs concat continuous) ก่อนทำ cue/voice — รอบนี้ยังไม่ล็อก
3. Handoff ให้ Media Editor ทำ cue + visual prompt EN 5 องค์ประกอบ (หลังบทนิ่ง)
4. Render + gate + human approval แยกอีกงาน — ไม่รวมในไฟล์นี้

> 🎯 **ประโยคปิด:** "บทเดิมจากแชท 100% — Clip5 แตกเป็น Bad/Good 2 ซีนเต็ม ที่เหลือพูดกล้องเหมือนเดิม"
