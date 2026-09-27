---
name: "@solocorp/content/script-design"
version: 0.1.0
category: content
platforms: [opencode, claude]
trigger: "ขอสคริปวิดีโอ / ตรวจสคริป / เตรียมสคริปส่งเจน"
mirror_check: L1
---

# 🎬 Script Design — ทักษะออกแบบสคริปวิดีโอ SoloCorp

> กลั่นจาก Forum 005 + เคาะ 3 ฝ่าย (Notebook / โรงงาน EP.4 / Owner) 2026-09-28

## Purpose
เมื่อต้องเขียน ตรวจ หรือเตรียมสคริปวิดีโอ (แบ่งท่อน 10 วิ) สำหรับส่งเจน — ให้ออกมาเวลาตรง พูดทัน ตรวจย้อนได้ พร้อม gate

## Segment Schema v2 (6 ฟิลด์ — ขาดไม่ได้)
```
[ท่อน i/MM:SS-MM:SS] พูด: (≤32 คำ ภาษาพูด) + | ฉาก: (ท่าทาง) +
| กราฟิก: (popup text) + | SFX: (เสียง) + | ภาพ: (visual) + [ไฟล์อ้างอิง]
```

## Iron Rules
1. **32 คำ/10 วิ** — เกิน = พูดไม่ทัน = เผาเครดิต (validator จับ)
2. **เลขเวลาต่อเนื่อง** — ผลรวมต้องเท่าความยาวที่สั่ง
3. **Pilot-first** — เจน 1 ท่อน Owner เคาะแล้วค่อย batch
4. **ตัด citation ลอย** `[1]` ก่อนส่งเจน (ขยะจาก Notebook)
5. **เลของค์กรใช้ fact-table เท่านั้น** — `bus/media/fact-table.md` (ห้ามจำเลขเอง)
6. **2 โหมด** — `static` (ฉากเดียว ถูก/ไว) / `cinematic` (หลายฉาก แพง ต้องมี character ref)

## Validation (รันก่อนส่ง gate ทุกครั้ง)
```bash
python3 -m workers.media_pipeline validate --path <scripts.md> [--seg 10]
```
ต้องได้ `✅ ผ่าน` (นับท่อนครบ + เวลาตรง + ไม่เกินลิมิตคำ + citation ถูกตัด)

## Gate Checklist (Owner เคาะ)
- [ ] Validator ✅
- [ ] ทุก claim มี source (fact-table หรือ [ไฟล์])
- [ ] Hook เปิด + cliffhanger ปิด
- [ ] Pilot 1 ท่อนผ่านตา Owner แล้ว

## Golden Reference
- 🥇 `bus/media/clawforge/scripts.md` — 11 ท่อน 108s static (**APPROVED by Owner 2026-09-28**, +titles+cover)
- `bus/media/ep4/scripts.md` — 18 ท่อน 3 นาที cinematic (candidate, รอ Owner gate)
- Notebook 11 ท่อน (1.8 นาที static) — ตัวอย่างโหมด static + schema ครบ

## Integration
- Factory: `python3 -m workers.media_pipeline script --mode static|cinematic --count K`
- Render: `concat --preset master|reels` (1920×1080 / 1080×1920 + loudnorm)
- Transcribe: `scripts/transcribe.py` (ตรวจคลิปที่เจนแล้ว)
