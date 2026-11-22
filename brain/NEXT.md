# NEXT — ค้างอยู่ตรงไหน เริ่มต่อตรงไหน

> อัปเดตทุกครั้งก่อนเลิกงาน อ่านทุกครั้งตอนเริ่มงาน (`/bootstrap` แล้วเปิดไฟล์นี้)
> กฎ: สั้น ตรงจุด มี commit hash + คำสั่งรันต่อเสมอ

## สถานะล่าสุด (2026-11-22 22:07 — หลัง merge PR #30)

- งานวันนี้ขึ้น `origin/main` แล้ว: `7798c6d` (merge PR #30) ← `18d4892` ← `840cad0`
- branch ที่ใช้ทำงาน `feat/content-growth-phase1` = `18d4892` — ตามหลัง origin/main 3 commit (`7798c6d`, `093f6ea`, `7702956`) · tree สะอาด
- ⚠️ canonical checkout `/data/projects/Lab-solocorp-os2.4` = **detached HEAD `87ed75d`** (เก่ากว่า origin/main) + `brain/learnt.md` ค้าง modified → ต้องกู้ก่อนใช้เป็นที่ทำงาน (ดูขั้น "เริ่มงานครั้งหน้า")

## ⚠️ งานแรกของ session หน้า (P1 — หลักฐานไม่ตรงคำกล่าวอ้าง)

commit `18d4892` message เขียน `(QA+Architect+Legal PASS)` แต่ของจริงคือ:

- `docs/showcase/CONTENT-GROWTH-PHASE2-READINESS-CHECKLIST-v1.md` และ `...PROGRESS-RAIL-v1.md` ยังเขียน **`สถานะ: DRAFT พร้อมตรวจ — รอ … เซ็น`**
- `docs/showcase/CONTENT-GROWTH-DECISION-LOG-v1.md` มีถึง **D-005 (ส่ง Checker)** — ไม่มี **D-009** (entry ที่จองไว้สำหรับ "commit หลัง PASS ครบ")
- ⇒ ตาม `rules/06-certification.md` (maker ≠ checker · default = ยังไม่ผ่าน) **M2/M3 = ยังไม่ PASS**

เลือกทางเดียวให้จบ:

- (ก) เก็บลายเซ็น QA / Legal / Architect เป็นลายลักษณ์อักษร → เขียน D-009 → แล้วค่อยนับ PASS
- (ข) แก้ถ้อยคำในเอกสาร/บันทึกให้ตรงว่า "ส่งตรวจแล้ว ยังไม่ผ่าน"

**ห้ามอ้าง M2/M3 PASS ต่อ Owner หรือภายนอกจนปิดข้อนี้**

จุดที่ checker ควรจับ (เจอตอนบันทึก brain): rail อ้าง steps 5 ขั้นที่ `axis_mcp/departments/content_service.py` แต่ชื่อจริง `input_validation` / `piper_tts` / `synthetic_visuals` / `ffmpeg_assembly` / `output_audit` อยู่ที่ `scripts/render_campaign_media_local.py` (content_service เป็น wrapper ที่ spawn CLI) — ชื่อถูก แต่ path คลาด 1 ชั้น

## ค้าง (ลำดับ)

1. ปิดหลักฐาน M2/M3 (หัวข้อ P1 ข้างบน)
2. Architect + Legal ตรวจ `docs/prds/PRD-AXIS-DEFAULT-EXECUTIVE-v1.1.md` — acceptance ยังว่าง 3 ข้อ (flow + ADR-036..039 / bundle exception ไม่ล้าง standalone / ไฟล์ไม่ทับของเก่า)
3. Content Growth: **M4** ingest → **M5** ชิ้นจริง end-to-end (วัดรอบแก้/เวลา) → **M6** adapter + ADR paid-call + ADR secrets
4. L5 parked เดิม: history ~400 MB ใน `.git` (git filter-repo) + ยืนยันก่อน split Phase 3 ว่า dept MCP code เคยถูก push ตอน repo public ไหม (ADR-030)

## เริ่มงานครั้งหน้า (3 ขั้น)

```bash
cd /data/projects/Lab-solocorp-os2.4
git fetch origin && git checkout main && git pull --ff-only   # ต้องได้ 7798c6d ขึ้นไป (ตอนนี้ checkout ค้างที่ 87ed75d)
python3 scripts/session-bootstrap.py                          # ต้องเขียว ไม่มี PRE-FLIGHT FAIL
python3 scripts/generate-specialist-manifest.py --check        # ต้อง up-to-date
```

ถ้า 3 ข้อผ่าน = ต่อได้เลย ไม่ต้องย้อนอ่านอะไรทั้งนั้น (รายละเอียดรอบล่าสุด: `brain/session-log.md` entry 2026-11-22 22:07)
