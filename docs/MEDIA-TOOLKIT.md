# 🛠️ เครื่องมือผลิตสื่อ — สถานะจริง ณ 2026-10-30

## Update 2026-11-02 — Content-Owned Sound Tools

Sound Designer (ซาวด์) remains a Content Creator specialist. Earshot lookup,
SFX rendering, and audio review are now exposed through the `content-creator`
MCP; `sound-studio` is no longer registered as a separate department server.
The ordered process is script → audio cue sheet → optional SFX/voiceover →
**choose the render path first** (on this host: local-media FFmpeg CLI via
`render_campaign_media_local` is the proven primary path, Phase 1–3; Concat's
MCP handshake was verified 2026-11-07 but `render_campaign_with_concat` has
never been run on this host — no render proof, ADR-032 amended) → Earshot
review → Publish Gate → human approval. See
`docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md` for inputs and failure handling.
The chosen path's renderer runs an initial gate after rendering. Run the gate
again after Earshot
review, because storing QA creates a new campaign version before approval.

## MCP Content Local Render (2026-10-30)

- ติดตั้ง Piper Thai model ที่ `tools/piper/models/` และ wrapper
  `scripts/local_tts_piper.py`; Piper สร้าง WAV ในเครื่องโดยไม่เรียก network.
- Clone แบบ sparse: AI_Animation ที่ `workers/skills/ai_animation/`
  (revision `3d17ba3`) และ pdoom-video ที่ `tools/pdoom-video/`
  (revision `fa164b7`). ทะเบียน Phone UI, Stacked Data Cards และ Swiss Shot
  อยู่ใน `workers/skills/AI-ANIMATION-REGISTRY.md`.
- pdoom dependency check: Node `24.14.1`, npm `11.18.0`, TypeScript `7.0.2`,
  Three.js `0.186.1`, Playwright Core `1.64.1`; original song/lyrics ไม่ได้
  clone มา และ campaign ใช้ฉาก Three.js ที่สร้างใหม่ทั้งหมด.
- `render_campaign_media_local` สร้าง MP4 90 วินาทีที่
  `central_bus/content/local_media/campaign_solocorp_os_1pt5m_narrative/local-media-e15ad3f3b36b4302b31084811c2f8d0b/`;
  ffprobe ยืนยัน 1080×1920, 30 fps, H.264/AAC และ SHA-256
  `5ed410c30f9d57589e719cb3c55cb1a315d4555a9f2ee2ca3451cc272c16959e`.
- วัดเสียงหลังเข้ารหัส AAC ได้ `-16.0 LUFS` และ `-3.1 dBTP`; ใช้
  loudnorm สอง pass และแยก `audio_mix` (WAV/PCM) จาก `audio` (AAC stream ใน MP4).
  งาน render ใช้ synthetic assets ในเครื่องและรายงาน `network_used: false`.
- ผลงานและ checksum ถูกบันทึกใน Central Bus พร้อมเรียก Publish Gate;
  เวอร์ชันล่าสุด `v14` คง `review_required`, `gate_passed: false`,
  `approved_version: null` และไม่มีการเผยแพร่.
- FFmpeg-skill `2.17.1` มีในเครื่อง แต่ doctor ยังไม่ผ่าน: FFmpeg `7.0.2-static`
  ต้องรอ runtime/security verification และ build นี้ไม่มี `drawtext`.
  เรนเดอร์ได้เฉพาะ synthetic assets ที่สร้างในเครื่อง; real user media ยังถูก
  กันไว้สำหรับเส้นทาง FFmpeg Direct CLI.
- ติดตั้ง Concat `0.2.8` เป็น AppImage ที่
  `/home/drsolodev/.opencode/concat/Concat-0.2.8-x86_64.AppImage` และลงทะเบียน
  MCP `concat` ใน OpenCode/Codex แบบ headless — **บน host นี้ AppImage FUSE
  mount ไม่ได้ (Phase 4 ADR-032) จึงรันจาก path ที่ `--appimage-extract`
  (`squashfs-root/AppRun`) แทน; handshake ผ่านแล้ว 2026-11-07 แต่
  `render_campaign_with_concat` ยังไม่เคยรันบน host นี้ (ยังไม่มี render
  proof) — evidence render สำเร็จ 2026-10-30 เป็น historical proof ไม่ใช่
  current host claim**. Content MCP เปิดเครื่องมือ
  `render_campaign_with_concat` เพื่อสร้างโปรเจกต์ `concat.json`, เพิ่มสื่อ/ซับ,
  เรนเดอร์ MP4 และบันทึกผลกับ checksum ลง Central Bus.
- ติดตั้ง Earshot `0.4.0` ใน CPU-only venv; ตอนบันทึก 2026-10-30 เครื่องมือ
  เสียงแยกเป็น `sound-studio` MCP. ตั้งแต่ 2026-11-02 เครื่องมือดังกล่าวอยู่
  ภายใน `content-creator` MCP โดยตรง; reports/stems ใช้ Central Bus เดิม และ
  Content ใส่ `sound_delivery_filename` ลงใน Concat timeline.
- ทดลองครบวงจรกับ `campaign_solocorp_content_creator_60s` เมื่อ 2026-10-30:
  MP4 H.264/AAC 1080×1920, 30 fps, 60.5667 วินาที; ใช้ซับไทยที่ฝังในภาพ
  ต้นฉบับและไม่เพิ่ม SRT ซ้ำ พร้อม SFX `whoosh_fast/tight`. Earshot วัด final
  mix ได้ `-16.0 LUFS`, `-2.3 dBTP`, clipped samples `0`; checksum และหลักฐาน
  อยู่ใน runbook ด้านล่าง.
- การรันจริงยืนยันการทำงานของ adapter/engine แต่ยังไม่ใช่ D3/D4 อิสระ;
  manifest คง runtime gate สำหรับ independent verification และ Publish Gate
  v16 คง `review_required`, `gate_passed: false`, `approved_version: null`
  จนกว่าจะมีการอนุมัติจากมนุษย์.
- Piper `th_TH-tsync2-medium` ระบุ CC BY-NC-SA 3.0 (non-commercial); เสียงที่
  สร้างจึงเป็น draft ที่ต้องยืนยันสิทธิ์ ห้ามเผยแพร่เชิงพาณิชย์โดยใช้โมเดลนี้.
- ผล render, ข้อจำกัดด้านสิทธิ์ และสถานะ certification บันทึกไว้ใน
  `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md` และ D1 draft.

รายละเอียดการใช้และข้อจำกัดอยู่ที่
`docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md`.

## ff-tracking Story Plans

- `build_ff_tracking_manifest(campaign_id, scene_definitions, camera_params)` stores a
  validated JSON plan beside the campaign's latest video script. It does not run
  Rust, FFmpeg, approve the campaign, or publish.
- `scene_definitions` accepts 1–120 entries with `scene_id`, `text`, and optional
  `episode_id` (`EPnn`), `kind` (`Cursor`, `Typing`, `Collapse`, `Done`), `palette`
  (`Paper`, `Thermal`, `Mono`, `Phosphor`, `Amber`, `Navy`, `Neon`), per-scene
  `camera`, `hero: [x, y]`, and `size`. `camera_params` supplies shared defaults;
  camera keys are `tilt_x`, `tilt_y`, `roll`, `zoom_start`, `zoom_end`, `pan_x`,
  `pan_y`, `blur`, and `shake`. Text must be at most 80 printable ASCII characters.
- `create_10s_series(..., with_ff_tracking=True)` adds one 20-shot plan per selected
  Origin episode. `ff_tracking_episode_count` accepts 1–3 and defaults to three;
  each plan describes 20 × 15 frames at 30 fps (10 seconds). The default series
  remains unchanged when the flag is off.
- Scene text is restricted to printable ASCII for the bundled JetBrains Mono font.
  Copy is a scripted workflow visualization, not a model's private chain of thought.
  Origin claims remain client supplied and independently unverified.
- The checked upstream renderer defines `SCENE_LIST` at compile time in
  `hud/src/lib.rs`, with 12 scenes × 15 frames at 30 fps, and outputs 1920×1080.
  Its stock `tools/render.sh` does not read the JSON plan. Therefore each manifest
  has `render_ready: false`; a local materializer adapter and runtime verification
  are still required. These plans do not produce 10-second or portrait MP4s by
  themselves and do not replace the FFmpeg workflow.

> ตรวจแล้ว**ทดสอบจริงทุกชิ้น** ไม่ใช่อ่านชื่อไฟล์

## สรุป: **ทำคลิปแนวตั้งพร้อมเสียงไทย+ซับไตเติล ได้จริงแล้ว**

```
สคริปต์ (4 ท่อน) → เสียงพูดไทย (piper) → ซับไตเติล (ffmpeg+libass) → คลิป 9:16 → ตรวจเงื่อนไขโปรแกรม
```

**หลักฐาน:** สคริปต์ตัวอย่าง → mp4 **1080x1920, 31.0 วิ, เสียง+ซับไทยครบ, ผ่านทั้ง 2 เงื่อนไขโปรแกรม**

---

## 📦 เครื่องมือที่มี (พร้อมใช้)

| ความสามารถ | เครื่องมือ | สถานะ | พิสูจน์แล้ว |
|:--|:--|:--|:--|
| **คิดไอเดีย + สคริปต์ (ไทย)** | `workers/llm_provider.py` | ✅ | 4 ท่อน → JSON ไอเดีย + hook |
| **เสียงพูดไทย** | `piper` + `tltk` | ✅ | 5.2s WAV @22kHz (ติดตั้งใหม่วันนี้) |
| **ถอดเสียง → ซับ** | `scripts/transcribe.py` (faster-whisper) | ✅ | ทำงานจริง |
| **ประกอบคลิป 9:16** | `ffmpeg` + `libass` | ✅ | 3 คลิป → 1080x1920 จริง |
| **ซับไตเติลเบิร์น** | `scripts/make_clip.py` | ✅ | เห็นภาพจริง — ไทยครบ ล่างจอ |
| **ตรวจเงื่อนไขโปรแกรม** | `solocorp_skills/programs/x_kickstart.py` | ✅ | ffprobe → 9:16 + <180 วิ |
| **สคริปต์แบบมีช่วงเวลา** | `workers/media_pipeline.py script` | ✅ | 10 วิ/ท่อน + validate |
| **ปกวิดีโอ** | `workers/media_pipeline.py cover` | ✅ | SVG |
| **อ่านเว็บที่ต้อง render JS** | `tools/carbonyl/web-read` | ✅ | 47.5MB, ไม่มี display |
| **ค้นหาเว็บ** | `solocorp_skills/web.py` | ✅ | DuckDuckGo ผ่าน Chromium |
| **ข่าวรายแผนก** | `loop_runner/loops/news_daily.py` | ✅ | 15 แหล่ง → facts + inbox |
| **เตรียมคลิปให้ครีเอเตอร์ (โมเดล B)** | `loop_runner/loops/creator_daily.py` | ✅ | 3 ไอเดีย → 15 ไฟล์ |

**ฟอนต์ไทยที่มี:** Noto Sans Thai · Noto Looped Thai · Garuda · Loma · Kinnari · Laksaman · Norasi

---

## 🔧 สิ่งที่ติดตั้งเพิ่มวันนี้ (ทำซ้ำได้)

```bash
scripts/setup_tts.sh     # venv + piper + tltk + โมเดลเสียงไทย 63MB
```

| สิ่งที่ต้องแก้ | เหตุผล |
|:--|:--|
| `edge-tts` (7.2.8) | **ใช้ไม่ได้** — endpoint ตอบ 403 ทุกภาษา (ไม่ใช่แค่ไทย) |
| `piper` + `tltk` | ใช้ได้ ✅ local ไม่ใช้ key ไม่ต้องเน็ตตอนรัน |
| `tltk` ต้อง `--no-deps` | ไม่งั้นจะ build scikit-learn เก่าจาก source (ช้ามาก/พัง) |

---

## 🧱 สายผลิตแบบเต็ม

```
bus/media/creator/<slug>/<วัน>/
  ├─ xxx.script.md      ← 4 ท่อน + เวลา (จาก creator-kit)
  ├─ xxx.shots.md       ← shot list
  ├─ xxx.caption.md     ← แคปชัน + แฮชแท็ก
  ├─ xxx.origin.md      ← ตลิ่งที่มา (ต้นทางของภาพ/เพลง/ฟอนต์)
  ├─ xxx.checklist.md   ← checklist โปรแกรม + สถานะโควตา
  └─ xxx.mp4            ← คลิป 9:16 พร้อมเสียง+ซับ ← scripts/make_clip.py
```

```bash
python scripts/make_clip.py --script <xxx.script.md> --out <xxx.mp4>
# → แล้วตรวจเงื่อนไขโปรแกรมให้อัตโนมัติ
```

---

## ⚠️ ข้อจำกัดสำคัญ (ต้องรู้ก่อนใช้กับโปรแกรม X)

Terms §4(a) ของ X Video Kickstart Bonus:
> *"The Qualifying Video must be **yours**"* · *"not mass-produced solely to manufacture qualifying posts"*

→ **คลิปที่เสียงสังเคราะห์ = ไม่นับ** ต้องเป็นครีเอเตอร์พูดเอง/ถ่ายเอง
→ เครื่องมือชุดนี้ใช้ได้กับ:
- **ครีเอเตอร์ถ่ายเอง** + เราช่วยคิด/เขียนสคริปต์/ตัดคลิป/ซับไตเติล → ✅ นับได้
- **คลิป AI ล้วน** → ❌ ไม่นับ (ใช้กับงานอื่น/สาธารณะ/การทดลองได้)
- **TTS เป็นเสียงพากยากรณ์/นักเล่าเรื่อง** → ต้องดูว่าโปรแกรมนับไหม (ความเสี่ยง — ควรเช็คกับครีเอเตอร์)

---

## ❌ สิ่งที่ยังไม่มี

| ขาด | หมายเหตุ |
|:--|:--|
| **AI สร้างภาพ/วิดีโอ** | ไม่มี — ไม่จำเป็นกับโปรแกรม X (ครีเอเตอร์ถ่ายเอง) |
| **ตรวจลายน้ำอัตโนมัติ** | ยังต้องให้คนดู |
| **โพสต์เป็น draft อัตโนมัติ** | เสี่ยง Terms §4(a) — แนะนำให้คนกดเอง |
| **TTS หลายเสียง / เสียงต้นฉบับ** | piper ไทยมี 1 เสียง (tsync2) — คุณภาพปานกลาง |
