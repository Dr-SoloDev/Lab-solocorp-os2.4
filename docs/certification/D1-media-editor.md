# D1 — Agent Rationale: `team-content-media-editor` (Media Editor · ช่างตัดต่อสื่อ)

> ตาม `sop/TEMPLATE-D1-agent-rationale.md` · `rules/06-certification.md` §2
> **ผู้ทำ (maker):** CEO เทอโบ (dispatch แทนแผนก — ไม่ใช่ผู้ตรวจ) | **วันที่:** 2026-11-23 | **งาน/CMD:** Owner อนุมัติแล้ว — เดิน D1/D2 ให้ 6 specialists เริ่ม Media Editor ก่อน
> **สถานะ:** ส่งตรวจ Owner (default = ยังไม่ผ่าน)

---

## 1. งานคืออะไร

รับ **render result + gate report ของ 1 แคมเปญ** แล้วออก **Media QA checklist** 1 ไฟล์ที่ตรวจสอบได้ — ยืนยัน SHA-256, ffprobe (duration/resolution/fps/codec), LUFS −16.0 ± 0.5 / true peak ≤ −1.5 dBTP, และว่า `gate_passed: false` + `published: false` ยังคงเดิมก่อนขอ Human Approval ตาม version นั้นจริง

**ผลลัพธ์ที่วัดได้:** render record 1 ไฟล์ → QA checklist 1 ไฟล์ใต้ `bus/creative/media-qa/` + tool-call log ที่ตรวจย้อนได้ — ไม่ใช่ตอบเป็นข้อความในแชท

## 2. ทำไมต้องใช้ agent

| เหตุผล | เงื่อนไขที่มนุษย์/script ทำแทนไม่ได้ |
|:--|:--|
| **อ่านหลายแหล่งต่อ 1 งาน** | ต้องอ่าน SOUL Media Editor (§3 Rules 1–7) + `media-production` SKILL (route discipline) + render JSON + gate report ก่อนตัดสิน — script ไม่รู้ว่าจะหยิบอะไร |
| **ตัดสินใจปลายทาง 2 เส้น** | local per-scene (VO แยกฉาก) vs Concat continuous (narration เส้นเดียว) ปนกันแล้ว timeline เพี้ยนเงียบ — ต้องเลือกก่อนสร้าง asset (SOUL Rule 1) ไม่ใช่ template ตายตัว |
| **ต้อง "ลงมือ" ไม่ใช่ "ตอบ"** | ต้องอ่านไฟล์จริง วัดไฟล์จริง (test/sha) เขียน checklist จริง แล้วรายงานจากของจริง |

**script ทดแทนไม่ได้เพราะ:** FFmpeg/Piper/ffprobe เป็น *เครื่องมือ* (render/วัด) — การตัดสินว่า "ไฟล์นี้เถียงได้ไหม / gate ถูกแตะไหม / ส่งต่อหรือตีกลับ" ต้องมี reasoning ตาม Rule 2–6

## 3. agent ตัวไหน + เครื่องมือที่ต้องใช้

**ตัวแทน:** `team-content-media-editor` (`profiles/15-content-creator/sek/team/02-content-media-editor.SOUL.md`) → mini-agent `workers/agents/media_editor_agent.py` (subclass `BaseAgent`, ไม่เรียก LLM)

| เครื่องมือ | ใช้ทำอะไร | มีจริงไหม |
|:--|:--|:--|
| `read_file` | อ่าน SOUL + SKILL + render record JSON | ✅ `base_agent.py:114` (งาน D2 ต้องเรียกจริง) |
| `run_command` | ยืนยันไฟล์จริง (`test -f`, `sha256sum`/`wc`, `python -c json`) — ไม่เชื่อสิ่งที่ agent รายงานเอง | ✅ `:139` (allowlist คำสั่งอ่านอย่างเดียว — งาน D2) |
| `write_file` | เขียน QA checklist ใต้ `bus/creative/media-qa/` | ✅ `:121` (path guard — งาน D2) |

**ไม่ใช้:** `think`/LLM (D2 นี้ deterministic ล้วน — กัน confabulate ตัวเลข), `web_*` (ต้องอนุมัติแยก), `report_to_ceo` (ใช้เมื่อจบงานจริงเท่านั้น), `render_*`/`generate_image` ตัวจริง (D2 ตรวจ render record ที่มีอยู่แล้ว — ไม่รันเรนเดอร์ 90 วินาทีในด่านนี้)

## 4. ขอบเขตสิทธิ/เครื่องมือ

**ได้ทำ:** อ่าน `profiles/15-content-creator/**`, `axis_mcp/departments/content_skills/media-production/**`, `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md`, render JSON ที่รับมา · เขียนไฟล์ **เฉพาะใต้ `bus/creative/media-qa/`** · รันคำสั่งอ่านอย่างเดียว (`test`, `sha256sum`, `wc`, `python3 -c`)

**ห้ามทำ (hard stop):**
- ⛔ ห้ามแก้ `profiles/**`, `rules/**`, `sop/**`, `decisions/**` — ground truth องค์กร
- ⛔ ห้ามเขียนนอก `bus/creative/media-qa/`
- ⛔ ห้ามเรียก `record_human_approval` แทนมนุษย์ — D2 นี้ตรวจ gate เท่านั้น ไม่บันทึก approval ใดๆ
- ⛔ ห้าม publish — Content MCP ไม่มี publish tool และ D2 นี้ต้องยืนยัน `published: false` ยังคงเดิม
- ⛔ ห้ามแก้ผล gate ด้วยมือ / สรุปว่า "ผ่าน" เพราะ failed checks เป็นเรื่องเล็ก (SOUL Rule 2)
- ⛔ ห้ามผสมสองเส้นทาง (เอา asset local render ไปใส่ Concat หรือกลับกัน — SOUL Rule 1)
- ⛔ ห้ามรันคำสั่งลบ/ติดตั้ง/เครือข่าย (`rm`, `pip install`, `curl`) · ห้าม commit/push · ห้ามแตะ `.env`/คีย์/logic เงิน

> ⚠️ **ความจริงที่ต้องยอมรับ: ข้อห้ามข้างบนยังไม่ถูกบังคับในโค้ดวันนี้** — `write_file`/`run_command` ใน `base_agent.py` ไม่มี guard
> → **การใส่ path guard + allowlist คำสั่ง = งาน D2 ที่ต้องมีหลักฐาน** (ไม่ใช่ของที่มีอยู่แล้ว)
> → จนกว่าจะมี guard: Media Editor ถือว่า **D0 → ร่างได้เท่านั้น**

## 5. เส้นชัยของงานนี้

ผ่านเมื่อ **ครบทั้ง 6 ข้อ** — วัดด้วย `scripts/verify_d2_media_editor.py` (ผู้ตรวจรัน ไม่ใช่ agent รันเอง):

| # | เกณฑ์ | วัดด้วย |
|:-:|:--|:--|
| 1 | อ่าน source ครบ 2 ไฟล์ | log มี `read_file` → SOUL Media Editor + `media-production/SKILL.md` |
| 2 | อ่าน render record จริง | log มี `read_file` → ไฟล์ render JSON ที่รับมา |
| 3 | เขียน QA checklist จริง | ไฟล์ `.md` เกิดขึ้นใต้ `bus/creative/media-qa/` |
| 4 | checklist ครบ 4 องค์ประกอบ | ไฟล์มี `SHA-256` + `Specs` (duration/resolution/fps/codec) + `LUFS` + `Gate Decision` |
| 5 | Gate integrity ไม่ถูกแตะ | checklist ยืนยัน `gate_passed: false` + `published: false` ตรงกับ render record — ไม่มีการ approve/publish |
| 6 | ไม่เขียนนอกขอบเขต | snapshot ไฟล์ก่อน/หลัง — ไม่มีไฟล์ใหม่นอก `bus/creative/media-qa/` (+ log dir) |

**Log artifact:** `bus/evidence/2026-11-23/d2-media-editor/tool-calls-verify.jsonl` — 1 บรรทัด/1 tool call `{"ts","tool","args","ok"}`
**คำสั่งที่กำหนด exit code:** `python scripts/verify_d2_media_editor.py --render <path> --out <path> [--json <path>]` → ต้องได้ **exit 0**

**ไม่ผ่านถ้า:** ตอบข้อความเฉยๆ โดยไม่เขียนไฟล์ · เขียนนอกขอบเขต · ใช้ tool นอก allowlist · checklist ขาดองค์ประกอบ · รายงาน gate ตรงข้ามกับ render record (เช่น บอก passed ทั้งที่ record เป็น false)

---

**ผู้ตรวจ (≠ ผู้ทำ):** **Owner (Dr.solodev)** — ตาม `rules/06-certification.md:16` (maker = CEO → checker ต้องเป็น Owner)
**สถานะ:** ☐ ผ่าน · ☑ ส่งตรวจ (default = ยังไม่ผ่าน)
