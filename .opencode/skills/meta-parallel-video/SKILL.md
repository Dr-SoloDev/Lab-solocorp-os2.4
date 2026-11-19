# Skill: meta-parallel-video — สั่ง Meta AI เจน 6 คลิปขนานในแชทเดียว

> บทเรียนคืน 14 พ.ย. 2026 กับ Owner: เจนทีละคลิปต่อกันในแชทเดียว ทั้งช้า ทั้งบริบทพัง หน้าเพี้ยน งง มั่ว (context collapse) — สั่งขนาน 6 subagents ทีเดียวจบ เร็วกว่า 5-6 เท่า หน้าตัวละครนิ่งกว่า

## เมื่อไหร่ต้องใช้สกิลนี้

- ต้องการคลิปเล่านิทาน/คอนเทนต์ยาว 1 นาที จาก Meta AI (ฟิกคลิปละ 10 วิ)
- มีสคริปต์ยาวแล้วอยากแตกเป็น 6x10s แล้วเจนพร้อมกัน
- Sek จะใช้ซ้ำๆ สำหรับงานสื่อ (teaser, นิทาน, เปิดตัว)

**ห้ามใช้** ถ้าต้องการคลิปยาวเกิน 10 วิในช็อตเดียว (Meta ทำไม่ได้) หรือต้องการแปะเสียง WAV นอกเข้าไป (Meta รับ sync เสียงนอกไม่ได้ — ต้องมาประกอบเองด้วย ffmpeg ฝั่งเรา)

## สถานะที่พิสูจน์แล้ว (2026-11-14)

| ชิ้น | ค่า |
|:--|:--|
| Host | solocorp-main, browse 0.0.16, relay connected |
| Meta AI | https://www.meta.ai, login ค้างใน Chrome จริงของ Owner |
| งานจริง | นิทานกระต่ายโบโบ้ + เต่าเตาะแตะ 1 นาที |
| สคริปต์ | `central_bus/content/axis-tale-rabbit-turtle/scripts-6x10s.md` (6 ซีน) |
| เสียงยาว | `tale-th-1min.wav` 85.18s Piper `th_TH-tsync2-medium` (internal draft, non-commercial) |
| แชทขนานสำเร็จ | `meta.ai/prompt/a73dc9e5-b9e1-4b4d-b220-0e655565b072` — ได้ `vidCount: 6` (mp4 fbcdn x6) |
| แชทเดี่ยวก่อนหน้า | `.../cc814f12...` (คลิป 10 วิเสียงไทยเดี่ยว), `.../2b114356...` (storybook 10 วิ), `.../12b19234...` (เล่าเรื่อง AXIS), `.../b2b70948...` (โลโก้ 3 แบบ), `.../fa0eb76c...` (ถามความสามารถ) |

## ทำไมต้องขนาน (อย่าเจนทีละคลิป)

| เจนทีละคลิป (sequential) | สั่งขนาน 6 ตัว (parallel) |
|:--|:--|
| ช้า x6 (รอตัวละ ~50-90 วิ) | รอรอบเดียวได้ 6 ตัว |
| บริบทพัง — แชทยาว ตัวละคร drift หน้าเพี้ยน | แต่ละ subagent ดึง reference frame ของตัวเอง หน้าคงที่กว่า |
| สั่งแก้ทีหลังงงว่าหมายถึงคลิปไหน | แยก Clip1-6 ชัดเจน ต่อกันง่าย |

สั่งผิดแบบ sequential คือพิมพ์ว่า *"Start with clip 1 now, then continue 2-6 in order"* — Meta จะต่อคิวให้เพื่อรักษาความต่อเนื่อง อย่าใช้ถ้าต้องการขนาน

## วิธีใช้ (copy-paste ได้เลย)

### 1. แตกสคริปต์ 1 นาที → 6x10s (หัวใจของสูตรขนาน — Owner เน้น)

> สคริปต์ย่อยต้องชัดระดับที่หยิบแยกแผ่นเดียวไปให้ subagent ตัวไหนก็ทำได้โดยไม่อ่านแผ่นอื่น — Meta จะเอาสคริปต์ย่อยนั้นส่งให้ subagent ตัวละสคริปต์ ทำขนานกัน

แต่ละซีนต้องมีครบ 5 ช่องนี้เสมอ (ขาดช่องไหน = เพี้ยน):

```text
[Clip N/6 | 10s | 16:9]
Visual EN: <ตัวละครชื่อเฉพาะ + ฉาก + แอคชันเดียว + กล้อง + สไตล์ storybook pastel>
  ตัวอย่างดี: "Cute fluffy rabbit Bobo sleeping under big banyan tree, kind turtle Tor-tae walking behind, Thai forest morning, storybook pastel style, slow pan"
  ตัวอย่างห่วย: "กระต่ายกับเต่าแข่งกัน" (กว้างเกิน subagent เดาเอง → 6 ตัวออกมา 6 สไตล์)
Narration TH: <ประโยคไทยเดียว ~15-20 คำ ≈ 10 วิ>
  ตัวอย่างดี: "โบโบ้คิดว่าชนะแน่ จึงแวะนอนพักใต้ต้นไม้ใหญ่ แล้วเผลอหลับไป"
Style lock: storybook pastel, soft morning light, 16:9 (เขียนซ้ำทุกคลิป — อย่าคิดว่ามันจำจากคลิป 1)
Character lock: Bobo = fluffy rabbit / Tor-tae = kind slow turtle (ชื่อ+คาแรกเตอร์ซ้ำทุกคลิป)
```

กฎ 3 ข้อจากประสบการณ์ตรง Owner:
1. **หนึ่งคลิป = หนึ่งแอคชัน** (วิ่ง / หลับ / เดิน / เชียร์ — อย่ายัด 2 แอคชันใน 10 วิ)
2. **ชื่อเฉพาะซ้ำทุกแผ่น** (Bobo / Tor-tae — ห้ามเรียก "กระต่าย" ลอยๆ บางแผ่น)
3. **สไตล์+สัดส่วนซ้ำทุกแผ่น** (pastel + 16:9 ทุกคลิป — ไม่งั้น 6 ตัวออกมาคนละโทน)

```text
Visual EN: <storybook pastel style, 16:9 หรือ 9:16, ตัวละคร + ฉาก + กล้อง>
Narration TH: <ประโยคไทยสั้น ~15-20 คำ ≈ 10 วิ>
```

ตัวอย่าง 6 ซีนนิทานกระต่าย (ดูไฟล์จริงที่ `scripts-6x10s.md`):
1. เปิดป่า / 2. ท้าแข่ง / 3. พุ่งนำ / 4. แวะหลับ / 5. เต่าเดิน + เพื่อนเชียร์ / 6. เส้นชัย + คติ

### 2. เปิด Meta AI ผ่าน browse

```js
await page.goto("https://www.meta.ai/", {waitUntil: "domcontentloaded"});
// รอ snapshot ขึ้น textbox "composer-input" แล้วค่อยพิมพ์
```

### 3. Prompt สั่งขนาน (ห้ามเติม "ทีละคลิป")

**EN (วางทั้งก้อน):**
```text
I have a 1-minute story split into six 10-second scripts. Please send each script to your subagents to generate all 6 clips in parallel at the same time: [1/6 Visual: ... / Narration Thai: ...] [2/6 ...] ... [6/6 ...] Fire all 6 generations together.
```

**TH (สั่งย้ำหลัง EN):**
```text
ส่งงาน 6 คลิปนี้ให้ subagent ของคุณรับไปทำต่อเลย แบ่งกันตัวละคลิปพร้อมกัน 6 ตัว: Clip1 intro / Clip2 challenge / Clip3 dash / Clip4 sleep / Clip5 walk / Clip6 finish เริ่มเลย
```

ถ้า Meta ตอบว่าจะทำ sequential (เช่น *"setting up sequential generation"*) ให้กด Stop แล้วส่งประโยค TH ข้างบนซ้ำ — รอบที่สำเร็จขึ้นว่า *"Running 6 subagents / Dispatching six clip tasks / Spawning six clip agents"*

### 4. รอ + ตรวจ

- รอ 60-120 วิ แล้วอ่าน `document.body.innerText` + นับ `document.querySelectorAll('video').length` ต้องได้ 6
- แต่ละคลิปต้องยาว 10 วิ มี Thai voiceover ตาม narration ที่สั่ง
- ถ้าได้ไม่ครบ 6 ให้สั่งต่อเฉพาะคลิปที่ขาด (เช่น *"Clip4 sleep subagent ทำต่อ"*)

### 5. ประกอบร่างฝั่งเรา (Meta ประกอบเสียงนอกให้ไม่ได้)

```bash
# ตรวจคลิปที่โหลดมา + เสียง Piper ยาว
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 clip1.mp4
# ต่อ 6 คลิป → 60s แล้ววางเสียงยาวทับ (ตัวอย่าง ต้องปรับให้ตรงงานจริง)
ffmpeg -y -i clip1.mp4 -i clip2.mp4 -i clip3.mp4 -i clip4.mp4 -i clip5.mp4 -i clip6.mp4 \
  -filter_complex "[0:v][1:v][2:v][3:v][4:v][5:v]concat=n=6:v=1:a=0[v]" -map "[v]" story-60s-video-only.mp4
ffmpeg -y -i story-60s-video-only.mp4 -i tale-th-1min.wav -c:v copy -c:a aac -shortest story-60s-final.mp4
```

## ข้อจำกัดที่ต้องจำ (Meta บอกเอง)

- ความยาวฟิก **10 วิ/คลิป** ขอ 5/30/60 วิไม่ได้ — อยากยาวต้องต่อกันเองข้างนอก
- ไม่มีปุ่มเลือก 720p/4K — ได้ MP4 ระดับโซเชียล (Reels/TikTok) ไม่ใช่มาสเตอร์โรงหนัง
- สัดส่วนสั่งได้ 9:16 / 16:9 / 1:1 ถ้าไม่สั่งมันเลือกเอง
- Prompt ไทยได้ แต่อังกฤษคุมกล้องแม่นกว่า — บทพูดให้ระบุ `พูดภาษาไทย` เสมอ
- เอาไฟล์ MP4/WAV ของเราไปให้ตัด/ซิงก์ไม่ได้ — ต้องประกอบเอง
- ใช้เชิงพาณิชย์ได้แต่ต้องเช็กเอง ห้ามอ้างหน้าคนจริงมารับรองสินค้า

## ความปลอดภัย + กฎหมาย (จาก @legal-tulya 2026-11-14)

- ผลงานล็อตนี้ตีตรา `DRAFT-unverified-external-AI` — ห้ามเอาโลโก้/คลิป AI เพียวๆ ไปจดทะเบียน
- ห้ามใส่ความลับองค์กร / ข้อมูลลูกค้า / API key ลง prompt Meta
- ใช้ session login ค้างของ Owner ได้เฉพาะแบบ attended (มีคนเฝ้า) + allowlist แค่ `meta.ai` + ห้ามเก็บ token ลง log/bus
- ไฟล์ output + Terms วันที่เช็ก + prompt + SHA ต้องเก็บเป็น provenance ก่อนเข้า `central_bus/content`

## ตำแหน่งไฟล์

| Path | คืออะไร |
|:--|:--|
| `.opencode/skills/meta-parallel-video/SKILL.md` | ไฟล์นี้ (วิธีสั่งขนาน) |
| `central_bus/content/axis-tale-rabbit-turtle/scripts-6x10s.md` | สคริปต์ 6x10s ต้นแบบ |
| `central_bus/content/axis-tale-rabbit-turtle/tale-th-1min.txt` | บทเต็มภาษาไทย |
| `central_bus/content/axis-tale-rabbit-turtle/tale-th-1min.wav` | เสียง Piper 85.18s (draft) |
