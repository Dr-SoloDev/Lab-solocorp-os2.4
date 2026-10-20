# 🔄 Handoff — สนามแรก (Creator Kit) · 2026-10-21

> เขียนเมื่อ context ใกล้เต็ม · อ่านไฟล์นี้ก่อนเริ่ม session ใหม่
> ดูรายละเอียดเชิงลึก: `decisions/ADR-022` (Creator Kit) · `ADR-023` (X program) · `ADR-025` (gate+series) · `ADR-026` (cadence)

---

## ✅ เสร็จแล้ว (commit แล้วทั้งหมด)

| อะไร | ที่ไหน |
|:--|:--|
| **โพสต์แรกขึ้นจริง** | `x.com/AChaisirum/status/2112593940096709038` · 270 ตัว · ผ่าน gate 8/8 |
| Web capability (อ่านเว็บ JS + ค้นหา) | `solocorp_skills/web.py` · `tools/carbonyl/` · ADR-019 |
| ข่าวรายแผนกทุกเช้า | `loop_runner/loops/news_daily.py` · ADR-020 |
| Rules engine ของโปรแกรม X | `solocorp_skills/programs/x_kickstart.py` · ADR-023 |
| Publish gate (ตัวกรองข้อมูล + R1-R5) | `solocorp_skills/redact.py` · ADR-025 |
| ซีรีส 5 แบบ + หมุนตามวัน | `solocorp_skills/creator.py` (`SERIES`) |
| สัญญาจังหวะ (แก้ด้วยมือ) | `bus/media/creator/cadence.md` · `solocorp_skills/cadence.py` · ADR-026 |
| โมเดล B (เตรียมคลิปให้ครีเอเตอร์ทุกเช้า) | `loop_runner/loops/creator_daily.py` |
| เครื่องมือเตรียมโพสต์ X (CDP) | `scripts/x_launch.sh` `x_type.py` `x_compose.py` `x_draft.py` |
| ทำคลิป 9:16 + เสียงไทย + ซับ | `scripts/make_clip.py` (piper + ffmpeg/libass) |

**สถานะระบบ:** คิว `0/0/0` · health 🟢 · เทสต์ 794 ผ่าน (26 fail เดิม ไม่เกี่ยว) · commits push แล้ว

---

## ✅ A เสร็จ — ซับไทย (2026-10-21)

| ไฟล์ | ผล |
|:--|:--|
| `bus/media/creator/dr-solodev/clips/Loop_Engineering_FULL_2m20s_9x16_SUB.mp4` | 720x1280 · 140.1วิ · 35.2MB ✅ |
| `bus/media/creator/dr-solodev/clips/SoloCorp_OS_Full_Evolution_108s_SUB.mp4` | 720x1280 · 88.3วิ · 25.4MB ✅ |

เครื่องมือ: `scripts/burn_subs.py` (ใหม่) — ตัดหัว markdown ออกจาก SRT ก่อน (libass อ่านไม่ได้) · MarginV=60 → ซับลงล่างพอดี 9:16
วิธีทำซ้ำ: `transcribe.py --model small --lang th --srt` → `burn_subs.py IN.mp4 --srt x.srt --out OUT.mp4`
(clips ไม่ commit — gitignore `bus/media/creator/*/clips/`)

## 🔄 กำลังทำ (ค้างไว้)

**ติดตั้ง OmniVoice (voice cloning) แบบ CPU** — ⚠️ **ติดปัญหา torchaudio**
```
/data/venvs/omnivoice   ← venv (torch CPU ✅ / omnivoice ❌)
โมเดล: ~/.cache/huggingface/hub/models--k2-fsa--OmniVoice (3.1GB, cache ครบ ✅)
log:   /tmp/opencode/omnivoice_install.log
สาเหตุ: OSError: Could not load this library: .../torchaudio/lib/_torchaudio.abi3.so
→ ต้องจับคู่เวอร์ชัน torch/torchaudio ให้ตรงกัน (ลอง torch==2.8.0 + torchaudio==2.8.0)
→ แล้วรันบน CPU: device_map="cpu", dtype=torch.float32/bfloat16
```
⚠️ **หมายเหตุ: background job ต้องใช้ `setsid` ไม่ใช่แค่ nohup** — tool ตัด process group ตอน timeout

**ข้อจำกัดของเครื่องนี้:** ไม่มี GPU · RAM 15GB (ว่าง ~9GB) · โมเดล 2.45GB → CPU ได้แต่ช้า

---

## 📋 สิ่งที่ค้างรอ Owner

### 1. ⚠️ เรื่องเสียงพูดเพี้ยน — วัดแล้ว เจอสาเหตุ
- โมเดล whisper `base` อ่านเพี้ยนหนัก แต่ `small` อ่านออกเกือบทุกประโยค
  → **เสียงไม่ได้เสียมาก** ปัญหาคือ **ออกเสียงคำอังกฤษเป็นเสียงไทย** ("prompt"→"พร้อม", "Claude Code"→"คลอด คล")
- **คลิปไม่มีซับไทย** → คนดูไม่เข้าใจ → ต้องใส่ซับ
- ✅ **แก้ได้เลยด้วยของที่มีอยู่**: `scripts/transcribe.py --model small --lang th --srt` → เบิร์นด้วย `scripts/make_clip.py`

### 2. 🎯 คลิปที่มีอยู่ — นับโบนัสได้กี่ตัว
ตรวจ `/home/drsolodev/Videos` (18 ไฟล์) ด้วย `scripts/audit_clips.py`:
```
ผ่านขนาด+เวลา (9:16, <180วิ) : 10
ไม่ซ้ำจริง (md5)            : 8      ← ขาดอีก 7
```
| ไฟล์ | สถานะ |
|:--|:--|
| `Loop_Engineering_FULL_2m20s_9x16.mp4` | ✅ ครีเอเตอร์ on camera, ไม่มีลายน้ำ, 140วิ |
| `SoloCorp_OS_Full_Evolution_108s.mp4` | ✅ ครีเอเตอร์ on camera, 88วิ |
| `master_2_20_horizontal.mp4` | ✅ 704x1248, 140วิ — เนื้อหา**ต่าง**จาก Loop_Engineering (เทียบเฟรมแล้ว) |
| `image_20261010_*.mp4` ×5 | ⚠️ 10.2วิ — ภาพอนิเมชัน → **ต้องตัดสินใจว่านับไหม** (AI-made?) |
| `Inside_the_Ultimate_Junk_Shop_POS_System.mp4` | ❌ มีลายน้ำ **"© Canmore Animation"** → ไม่นับ |

### 3. 🔀 ทางแยกเรื่อง voice cloning กับโบนัส (ต้องตัดสิน)
Terms §4(a): *"The Qualifying Video must be **yours**"* → **คลิป AI/เสียง clone = ไม่นับ**
| ทาง | นับโบนัส? | ใช้ทำอะไรได้ |
|:--|:--:|:--|
| ครีเอเตอร์ถ่าย+พูดเอง → เราใส่ซับ/ตัด/ตรวจ | ✅ | 15 คลิป (ต้องถ่ายเพิ่ม 7) |
| AI ทำคลิป + เสียง clone | ❌ | สร้างตัวตน/ทดลอง/คอนเทนต์อื่น (ต้อง label AI) |

**ข้อเสนอ:** ทำ **2 อย่างขนานกัน**
- **ทางโบนัส** = ใส่ซับไทยให้คลิปที่ถ่ายเอง (ใช้ของที่มี) → ได้ 8 คลิปทันที ขาดอีก 7
- **ทาง voice cloning** = ทำเป็น capability ของ SoloCorp ให้ลูกศิษย์ + ครีเอเตอร์ (ตามที่ Owner สั่ง "ใช้ SoloCorp OS เหมือนกัน CEO ทำหน้าที่")

---

## ▶️ ขั้นถัดไป (เลือก 1 อย่าง)

| # | ทำอะไร | ใช้เวลา |
|:--|:--|:--|
| **A** | เบิร์นซับไทยให้ `Loop_Engineering` + `SoloCorp_OS` (transcribe small → SRT → libass) | 15 นาที |
| **B** | ทดสอบ OmniVoice clone เสียงจริง (ต้อง ref audio 3-10 วิ + ข้อความ) | 30 นาที |
| **C** | ตัดสินใจเรื่อง `image_2026*` (ภาพอนิเมชัน) นับโบนัสไหม | 5 นาที |
| **D** | เขียน skill `voice-clone` + เอกสาร เหมือนของอื่น | 30 นาที |

**คำแนะนำ: A → B** (ทำของที่ได้ผลกับโบนัสก่อน แล้วค่อยเปิด capability ใหม่)

---

## ⚠️ บันทึกไว้เพื่อไม่ลืม
- X ของ Owner **ยังไม่มี Premium** → ลิมิต 280 ตัวอักษร (ต้องมี Premium อยู่ดีสำหรับโปรแกรม X Kickstart ด้วย)
- วันที่ 30 ต.ค. 23:59 PT = 31 ต.ค. 12:59 ไทย = **deadline enroll รอบแรก**
- โปรแกรม X บังคับ **Premium + Stripe + ID verification** (คนนอกสหรัฐฯ) + บัญชี active ≥3 เดือน
- `skills/REGISTRY.md` ต้องเพิ่ม skill ใหม่ทุกครั้งที่สร้าง
- auto-commit loop จะ commit/push ให้เองทุก ~30 นาที (ระวัง: commit message มักผิด)
