---
name: voice-clone
description: Use when asked to make a video, voiceover, or audio with the user's own cloned AI voice — สร้างวิดีโอ, ทำเสียงพากย์, โคลนเสียง, เสียง AI ของมนุษย์, voice clone, voiceover, dub, TTS ด้วย OmniVoice บนเครื่อง local (RTX 4050) ให้เสียงที่ฟังเหมือนมนุษย์จริง
version: 1.0.0
category: content
platforms: [opencode, claude]
trigger: "สร้างวิดีโอ|พากย์|โคลนเสียง|เสียง AI|voice clone|dub"
mirror_check: L1
---

# 🎙️ Voice Clone — เสียง AI ของมนุษย์

> ใช้ OmniVoice (zero-shot TTS) สร้างเสียงพูดที่ **เหมือนมนุษย์จริง** ในเสียงที่โคลนไว้
> มนุษย์ยืนยันแล้วว่าฟัง "เหมือนเลย" — ใช้ได้ทันที ไม่ต้องอัดเสียงใหม่

## เมื่อไหร่ต้องใช้สกิลนี้

- "ทำวิดีโอด้วยเสียงนี้" / "พากย์ให้หน่อย" / "สร้างเสียงบอกว่า..."
- "โคลนเสียงใหม่" (มนุษย์เปลี่ยนไฟล์เสียงต้นแบบ)
- ต้องการทำคลิปหลายเวอร์ชันจากบทเดียวกัน (A/B test เสียงเดียวกัน = คุมตัวแปรสะอาด)

**ไม่ใช้สกิลนี้** ถ้าเป็นเสียงตัวละคร/นักแสดง/คนอื่น — ดูหัวข้อความปลอดภัยด้านล่าง

## สถานะที่ติดตั้งไว้แล้ว (ยืนยันด้วยหลักฐานจริง 2026-10-19)

| ชิ้น | ค่า |
|:--|:--|
| GPU | NVIDIA GeForce RTX 4050 Laptop, 6 GB — `torch.cuda.is_available() == True` |
| Python | 3.13 (venv แยก ไม่ชนกับ SoloCorp) |
| venv | `%LOCALAPPDATA%\Temp\opencode\omnivoice-venv` |
| torch | 2.8.0+cu128 |
| omnivoice | 0.2.1 |
| VRAM ที่ใช้จริง | **1.96 GB จาก 6 GB** (เหลือเฟือมาก) |
| ความเร็ว | `num_step=16` → RTF **0.36** (เร็วกว่าเวลาจริง ~3 เท่า) |
| เสียงต้นแบบ | `%USERPROFILE%\Desktop\OmniVoice\voice.wav` (จาก mp4 ของมนุษย์) |
| prompt cache | `%USERPROFILE%\Desktop\OmniVoice\voice_prompt.pt` |

**RTF = เวลาที่ใช้ ÷ ความยาวเสียง** — ต่ำกว่า 1 แปลว่าเร็วกว่าเวลาจริง
คลิป 60 วินาที ≈ 22 วินาทีที่ต้องรอ

## วิธีใช้

### 1. พิมพ์เสียง (กรณีปกติ 90%)

```bash
PY="$LOCALAPPDATA/Temp/opencode/omnivoice-venv/Scripts/python.exe"
cd .opencode/skills/voice-clone
"$PY" clone.py "ข้อความที่ให้พูด" --out clip01.wav
```

ตัวเลือก:

| ตัวเลือก | ค่าเริ่มต้น | ความหมาย |
|:--|:--|:--|
| `--out` | `clone_result.wav` | ชื่อไฟล์ผลลัพธ์ (วางใน `Desktop\OmniVoice\`) |
| `--steps` | `16` | `16` เร็ว / `32` คุณภาพละเอียดขึ้น |
| `--speed` | `1.0` | `<1.0` = ช้าลง (ใช้ตอนพูดเร็วเกิน), `>1.0` = เร็วขึ้น |

### 2. เปลี่ยนเสียงต้นแบบ (ใช้เมื่อมนุษย์อัดเสียงใหม่)

```bash
"$PY" clone.py --setup "C:/Users/Lenovo/Desktop/วิดีโอใหม่.mp4"
```

รองรับ mp4 / mp3 / m4a / wav — ffmpeg ดึงเสียงออกให้เอง (mono 24 kHz)
**ลบ prompt เดิมอัตโนมัติ** เพราะเสียงต้นแบบเปลี่ยน

## ⚠️ ความเสี่ยงที่ต้องบอกมนุษย์

**venv อยู่ใน `Temp/`** — Windows ล้างได้ ถ้าหาย skill จะพัง
ตรวจสอบ: `test -x "$PY"` ถ้าไม่มี ให้ติดตั้งใหม่ (ดูหัวข้อ "ซ่อมเมื่อพัง")

## ซ่อมเมื่อพัง

```bash
py -3.13 -m venv "$LOCALAPPDATA/Temp/opencode/omnivoice-venv"
"$PY" -m pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 \
  --extra-index-url https://download.pytorch.org/whl/cu128
"$PY" -m pip install omnivoice
```

## ข้อควรรู้เรื่องคุณภาพ

1. **ความเร็วของคำพูด** — ถ้าฟังแล้วเร็วเกินจริง ให้ลด `speed` เป็น `0.9`
2. **เสียงต้นแบบต้องเป็นภาษาเดียวกับที่จะพูด** — คนละภาษา = สำเนียงกลาง ไม่ใช่เสียงมนุษย์
3. **อัดต้นแบบ = พูดธรรมชาติ ไม่ใช่พูดเก่ง** — AI เรียนแบบก๊อป ถ้าต้นแบบพูดแข็ง ผลก็แข็ง
4. **ห้ามสลับภาษาในข้อความ** — "10,000 บาท" ให้พิมพ์เป็นคำ หรือใช้ `normalize_text` (ต้องลง `omnivoice[tn]`)
5. **prompt cache** — ครั้งแรกช้า (~12 วิ) ครั้งต่อไปเร็ว (~3 วิ) เพราะไม่ต้อง encode ใหม่

## 🔴 ความปลอดภัย — ห้ามข้าม

**โคลนได้เฉพาะเสียงของมนุษย์ (Owner) เท่านั้น**

ห้าม: นักแสดง / นักข่าว / คนดัง / เพื่อน / เสียงใครที่ไม่ได้ยินยอม
เหตุผล: OmniVoice มี disclaimer ห้าม voice impersonation / fraud / scam โดยตรง
การปลอดเป็นคนอื่น = ผิดกฎหมาย + ทำลายช่องที่สร้างมา

ถ้ามนุษย์สั่งให้โคลนเสียงคนอื่น → ปฏิเสธ อธิบายเหตุผล ไม่ต้องรอคำอนุมัติ

## เอาต่อกับคลิป

OmniVoice ให้ **ไฟล์เสียงเปล่า** ไม่ได้ให้ภาพ ถ้าต้องการวิดีโอ:

1. สร้างเสียงด้วยสกิลนี้ → ได้ `.wav`
2. ffmpeg รวมภาพ: `ffmpeg -i video.mp4 -i voice.wav -c:v copy -c:a aac -shortest out.mp4`
3. หรือถ้ามีภาพนิ่ง: `ffmpeg -loop 1 -i still.jpg -i voice.wav -c:v libx264 -shortest out.mp4`

## ตำแหน่งไฟล์ทั้งหมด

| Path | คืออะไร |
|:--|:--|
| `.opencode/skills/voice-clone/clone.py` | สคริปต์หลัก (git-tracked) |
| `.opencode/skills/voice-clone/SKILL.md` | ไฟล์นี้ |
| `Desktop\OmniVoice\voice.wav` | เสียงต้นแบบ (7.5 วิ จาก mp4 มนุษย์) |
| `Desktop\OmniVoice\voice_prompt.pt` | prompt cache |
| `Desktop\OmniVoice\*.wav` | ผลลัพธ์ที่สร้าง |
| `Desktop\OmniVoice\โคลนเสียง.bat` | ปุ่มลัดสำหรับมนุษย์ |
| `%LOCALAPPDATA%\Temp\opencode\omnivoice-venv` | Python environment (เปราะ — ดูหัวข้อความเตือน) |

## หลักฐานการทำงานล่าสุด

```
ข้อความ  : ทดสอบสคริปต์ในสกิล ถ้าคุณฟังออกว่าเป็นเสียงเดิม ก็ถือว่าสกิลทำงาน
ใช้เวลา : 2.93 วินาที
ความยาว : 8.20 วินาที  (RTF 0.36)
ผลลัพธ์ : C:\Users\Lenovo\Desktop\OmniVoice\skill_test.wav
CLONE_OK                                    exit=0
```

มนุษย์ฟังแล้วยืนยัน **"เหมือนเลย"** เมื่อ 2026-10-19

## เรียกชื่อมนุษย์

ใช้ **"HUMAN"** หรือ **"มนุษย์"** เท่านั้น
ห้าม "เอ็ง" / "หนู" / "ตัวเอง" (บันทึกใน `brain/learnt.md` 2026-10-19)
