---
name: "@axis/content-creator/meta-ai"
version: 1.0.0
category: content-creator
platforms: [opencode]
trigger: "/meta-gen"
mirror_check: L2
---

# 🎬 Meta AI ผ่านเบราว์เซอร์ — Browser Workflow Skill

> ถอดจากประสบการณ์จริงวันที่ 2026-11-18: สร้างซีรีส์คลิปตัวละครด้วย Meta AI (meta.ai) ผ่าน browse relay — ตั้งแต่เปิด tab ยัน concat รวมคลิป

## Purpose

เมื่อต้องสร้างภาพ/วิดีโอตัวละครด้วย Meta AI ผ่านเบราว์เซอร์จริง (ไม่มี API) → ใช้ workflow นี้ตั้งแต่เชื่อมต่อ, ล็อกตัวละคร, สั่ง gen แบบ parallel, โหลดผล, ตัดต่อ จนได้คลิปพร้อมใช้

## Inputs

| Field | Required | Description |
|:------|:--------:|:------------|
| `brief_md` | Yes | ไฟล์ .md ทั้งก้อน: ตัวละคร + LOCK BLOCK + ฉากทั้งหมด (ห้ามส่งทีละฉาก) |
| `ref_images` | Yes | รูป ref ตัวละคร (A-1→A-4 + B-Day/Night) — ต้องแนบทุกครั้ง |
| `scene_count` | Yes | จำนวนคลิป (เช่น 18 คลิป → split 9 กลุ่ม×2) |
| `mode` | No | `image` (ล็อกตัวละคร) หรือ `video` (คลิป 10วิ), default = `video` |

## Steps

### 1. เชื่อมต่อเบราว์เซอร์

```bash
# browse relay (SoloCorp host)
ws://127.0.0.1:19988
browser: chrome-solocorp-main
```

- เปิด lent tab จากเบราว์เซอร์จริงของผู้ใช้ (user กดปุ่ม lent ใน toolbar)
- `tabs list` → จด **tab id ตัวเลข** ของ lent tab ไว้ใช้ทุกคำสั่ง
- สัญญาณพร้อม: เจอ debugging banner **"Agents · 1"** ใน snapshot
- ถ้า body ว่าง / snapshot ไม่มี content → **ต้อง login meta.ai ก่อน** (เปิด tab ให้ user login เอง ห้ามข้าม)

### 2. คำสั่ง browse CLI ที่ใช้

| คำสั่ง | ใช้ทำอะไร |
|:-------|:----------|
| `navigate <url> --tab <id>` | ไป meta.ai (image/video tab) |
| `snapshot --tab <id>` | อ่าน state หน้า + หา ref/selector |
| `fill <ref> <text>` | วางพร้อมท์ยาวพรวดเดียว (prompt ภาพ/วิดีโอ) |
| `type <ref> <text>` | เคาะทีละตัวเหมือนคนพิมพ์ (ใช้กับช่องแชทสั้น) |
| `click <ref>` | กดปุ่ม gen / แนบไฟล์ / เล่นวิดีโอ |
| `upload <selector> <path>` | อัปโหลดรูป ref |
| `eval <js>` | ดึง video src / DOM ที่ snapshot มองไม่เห็น |
| `screenshot` | ยืนยันภาพ gen เสร็จก่อนโหลด |

> **fill vs type — เลือกให้ถูก:**
> - `fill` = วางพรวดเดียว → พร้อมท์ยาว (prompt ภาพ/วิดีโอ + LOCK BLOCK)
> - `type` = เคาะทีละตัวเหมือนคนพิมพ์ → ช่องแชทสั้น (Meta อาจดัก paste event)

### 3. Upload รูป ref (กฎ file roots + ownership)

```bash
cp <รูปต้นฉบับ> /tmp/<ชื่อ>.jpg && chmod 600 /tmp/<ชื่อ>.jpg
# selector: input[type=file]
```

- browse server มี **file roots** — อ่านได้เฉพาะ path ที่ allow (`/tmp` ปลอดภัยสุด)
- ไฟล์ต้อง **owned + readable** (chmod 600 หลังก๊อป ไม่งั้น upload ล้ม)
- selector อัปโหลด: `input[type=file]`

### 4. ขั้นล็อกตัวละคร (โหมด image — ทำก่อนวิดีโอเสมอ)

1. Gen ทีละภาพ: **A-1 → A-2 → A-3 → A-4** (CR หน้าตรง/ซ้าย/ขวา/ยิ้ม) **+ B-Day + B-Night** (full-body)
2. แนบ **LOCK BLOCK** ทุกครั้ง + แนบรูป ref ทุกครั้งที่ gen
3. ภาพไหนหน้าเพี้ยน → **สร้างใหม่ภาพนั้นทันที** ห้ามปล่อยผ่าน (ดริฟต์จะลามไปวิดีโอ)

### 5. กฎเหล็กคลิป 10 วิ (โหมด video)

- พร้อมท์ **ภาษาอังกฤษ** + บทพูด **ภาษาไทย** ( dialogue คงไทยไว้ใน prompt)
- ทุก prompt วิดีโอต้องลงท้าย **IRON TAIL** (กันหัวเราะท้าย + กันท่าหลุด):
  ```
  No laughing/no chuckle/no smile widening + same sitting position seamless cuts
  ```
- ความยาว 10 วิ / แนวตั้ง **720x1280** (เช็กด้วย ffprobe หลังโหลด)

### 6. ส่งงานให้ sub-agent Meta (กันหน้าดริฟต์)

- แนบ **md ทั้งไฟล์** ให้ sub-agent + สั่ง **split parallel**
  - ตัวอย่าง: 18 คลิป → **9 กลุ่ม × 2 คลิป** รันพร้อมกัน
- ⛔ **ห้ามส่งทีละฉาก** — gen ทีละฉาก = หน้าดริฟต์ทีละนิดจนตอนท้ายจำไม่ได้

### 7. โหลดผล + ตัดต่อ

```bash
# 1. eval ดึง video src จาก DOM
# 2. curl โหลดไฟล์
curl -sL "<video-src>" -o clip01.mp4
# 3. ffprobe เช็ก 10วิ / 720x1280
ffprobe -v error -show_entries format=duration -show_entries stream=width,height clip01.mp4
# 4. ตัดหางหัวเราะ (ถ้ามี)
ffmpeg -y -i clip01.mp4 -t 8 -c copy clip01_cut.mp4
# 5. concat รวมทุกคลิป
ffmpeg -f concat -safe 0 -i list.txt -c copy final.mp4
```

## Output

```
🎬 Meta AI — {campaign}: {n}/{n} คลิป
   Character lock: ✅ A-1→A-4 + B-Day/Night
   Spec: 10s / 720x1280 / IRON TAIL ✅
   Final: {final.mp4} ({duration}s รวม)
   Status: 🟢 พร้อมส่ง gate / 🟡 มีคลิปต้อง gen ใหม่ ({list})
```

## Integration

- Browse relay: `ws://127.0.0.1:19988` → `chrome-solocorp-main` (lent tab)
- Render/ตัดต่อ: FFmpeg CLI local (`ffmpeg -t` + `concat`)
- Queue: `skill.content.invoke` → meta-ai session → clips → concat

## Dependencies

- browse MCP server (relay + lent tab จากเบราว์เซอร์จริงของผู้ใช้)
- FFmpeg CLI (ffprobe + `-t` trim + concat)
- Meta AI account (user login เองใน lent tab)

## ปัญหาที่เจอจริง + วิธีแก้ (2026-11-18)

| # | ปัญหา | วิธีแก้ |
|:-:|:------|:--------|
| 1 | **หัวเราะท้ายทุกคลิป** (~2 วิสุดท้าย) | IRON TAIL ทุก prompt + ตัดหางด้วย `ffmpeg -t` |
| 2 | **หน้าดริฟต์** เมื่อส่งทีละฉาก | แนบ md ทั้งก้อน + split parallel (9×2), แนบ ref ทุกครั้ง |
| 3 | upload ล้ม (file roots) | ก๊อปมา `/tmp` + `chmod 600`, selector `input[type=file]` |
| 4 | snapshot body ว่าง | **ต้อง login** — เปิด tab ให้ user login meta.ai ก่อนเริ่มงาน |
| 5 | ภาพล็อกหน้าเพี้ยน | สร้างใหม่ภาพนั้นทันที ห้ามปล่อยผ่าน |
