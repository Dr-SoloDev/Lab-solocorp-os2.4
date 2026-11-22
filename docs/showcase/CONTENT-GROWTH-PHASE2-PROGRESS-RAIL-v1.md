# 📊 Progress Rail — เห็นความคืบหน้ารายขั้น (Phase 2 งาน 2.1)

> **Phase 2 — เสี่ยงต่ำ ไม่แตะ paid call · ไม่แก้ gate · ไม่แก้ renderer**
> **Owner:** Media Editor (เลนรวม — เจ้าของ render+gate) · **Maker:** Content (Media Editor) · **Checker:** QA + Architect (maker ≠ checker)
> **Version:** v1.1 (scope ลดตาม Path A — ไม่แตะ code/task schema) · **วันที่:** 2026-11-22 (v1.0: 2026-11-20) · **Branch:** `feat/content-growth-phase1` (เขียนไฟล์อย่างเดียว ไม่ commit)
> **Savepoint อ้างอิง:** `save-sek-rail-20261120` (c3b2d5d)
> **แผนแม่:** `docs/showcase/CONTENT-GROWTH-PLAN-v1.md` §1 งาน 2.1 + §3 M3
> **สถานะ:** DRAFT พร้อมตรวจ — รอ QA + Architect เซ็น Checker ก่อนนับเป็น M3 PASS
> **สไตล์:** ของเราเอง — เอา `steps` 5 ขั้นที่มีอยู่แล้วใน `render_campaign_media_local` มารายงานให้เสกเห็น (ไอเดีย progress จาก Pixelle + time-box จาก Jellyfish — เขียนใหม่ ไม่ก๊อปโค้ดใคร)

---

## 1. หลักการประโยคเดียว

> **เสกรู้ว่างานผ่านขั้นไหนมาบ้างโดยไม่ต้องถามเลน — อ่าน `steps` 5 ขั้น + timestamp จากไฟล์ `local_media_render_result` หลัง render จบ (`task_get_status` ดูสถานะรวมเท่านั้น)**

เอกสารนี้ **ไม่สร้างระบบ tracking ใหม่** ไม่แก้ renderer ไม่แก้ gate ไม่แก้ task schema — แค่กำหนดว่า Media Editor ต้องรายงาน `steps` 5 ขั้นที่มีอยู่แล้วอย่างไร (post-render pointer — v1.1 scope ลด: เห็นหลังจบเท่านั้น) + เสกต้องอ่านอย่างไร + time-box ผูกกับแต่ละขั้นอย่างไร (ตรวจแบบ post-hoc หลังจบ — ดูโน้ต ADR-xxx ท้าย §3)

---

## 2. Steps 5 ขั้น (ของเดิมใน renderer — เอกสารนี้แค่ล็อกรูปแบบรายงาน)

| # | Step (ชื่อจริงใน `render_campaign_media_local`) | เกิดอะไรขึ้น | หลักฐานที่ต้องเห็น | ถ้าค้างแปลว่าอะไร |
|:-:|:-----------------------------------------------|:------------|:-------------------|:------------------|
| 1 | `input_validation` | ตรวจ layout 6×15s/90s หรือ 10×10s/100s · hyphen ASCII · `VO: "` · route tag 1 tag/ฉาก | pass/fail + เหตุผลที่ fail (เช่น "scene count 5 ≠ 6") | สคริปต์ผิดตั้งแต่ต้น — ตีกลับ Film ทันที ไม่ไปขั้น 2 |
| 2 | `piper_tts` | สร้างเสียงไทย Piper `th_TH-tsync2-medium` ต่อฉาก (non-commercial, draft ภายใน) | ไฟล์เสียงต่อฉาก + ระยะเวลาต่อฉาก | Piper ล้ม = หยุดทันที รายงาน error ดิบ (Rule 6 Media Editor) ห้าม fallback เอง |
| 3 | `synthetic_visuals` | สร้างเฟรม Three.js สังเคราะห์ต่อฉาก (ไม่ใช่ภาพนอก ไม่ใช่ paid call) | เฟรมต่อฉาก + resolution/fps | เฟรมล้ม = หยุดทันที (ห้ามเอาภาพนอกมาเสียบแทนโดยไม่มีคำสั่งเสก) |
| 4 | `ffmpeg_assembly` | ประกอบภาพ+เสียง+ซับเป็น MP4 (H.264/AAC 48kHz) + two-pass loudnorm −16.0 LUFS | MP4 path + duration/resolution/fps | ประกอบล้ม = หยุดทันที (ห้ามรันซ้อน — No Concurrent Renders) |
| 5 | `output_audit` | วัดไฟล์จริง: SHA-256 (64 hex) + ffprobe + ebur128 (LUFS/true peak) + bitrate | SHA-256 + ffprobe + LUFS/true peak ที่วัดจากไฟล์จริง | วัดหลุดกรอบ = แก้ที่ต้นทางแล้วเรนเดอร์ใหม่ ห้ามรายงานว่า "ใกล้พอ" |

**กฎรายงาน (Media Editor ทำทุกเรนเดอร์ — v1.1 post-render เท่านั้น):**
1. รายงาน `steps` ในไฟล์ `local_media_render_result` เป็น dict `{step_name: {status, started_at, finished_at, error}}` — timestamp ทุกขั้น (ISO 8601 + timezone) — อ่านหลังจบเท่านั้น
2. ขั้นที่ไม่ได้รันเพราะล้มก่อน = `pending` (ไม่ใช่ "น่าจะผ่าน") · ขั้นที่ล้ม = `failed` + error ดิบ + หยุดขั้นถัดไป (ดูจากไฟล์หลังจบ)
3. `task_update_status(task_id, status, result_ref, error_detail)` รายงานสถานะรวมเท่านั้น (overall status) — `steps` รายละเอียดรายขั้นอ่านจากไฟล์ `local_media_render_result` (`result_ref` ชี้ไฟล์) **หลังจบ**เท่านั้น · v1.1 ไม่รายงานกลางทาง (true mid-flight ต้องรอ ADR-xxx task steps schema รอบ M5/M6)
4. ห้ามรันเรนเดอร์ซ้อน (lock เดิม — รันที่ 2 ชน = fail fast ทันที ไม่ queue เงียบ)

---

## 3. เสกอ่านอย่างไร (ไม่ถามเลน — อ่านไฟล์ `local_media_render_result` หลังจบ + `task_get_status` ดูสถานะรวมเท่านั้น)

```
เสกเช็กหลังจบ (Workflow §5.4 ของเสก — v1.1 scope ลด: ไม่เช็กกลางทาง):
  1. task_list(dept="content") → หา task_id ของ Media Editor (เลนรวม)
  2. task_get_status(task_id) → ดูสถานะรวมเท่านั้น (running/completed/failed) + เอา result_ref (path ไฟล์ local_media_render_result)
  3. เปิดไฟล์ local_media_render_result → อ่าน steps dict + timestamp 5 ขั้น
  4. เทียบ time-box (§4) แบบ post-hoc → เกินกรอบ = บันทึก root cause + เสกตัดสิน A/B/C ก่อนเรนเดอร์รอบถัดไป (Rule 5)
```

**ตัวอย่างสิ่งที่เสกเห็น (copy-paste จากไฟล์ local_media_render_result หลังจบ — ไม่ใช่ task_get_status กลางทาง):**

```json
{
  "task_id": "media-editor-campaign_growth_m2_demo_90s-render-v1",
  "status": "completed",
  "result_ref": "central_bus/content/local_media/campaign_growth_m2_demo_90s-render-v1.json",
  "steps": {
    "input_validation":   { "status": "completed", "started_at": "2026-11-20T10:00:00+07:00", "finished_at": "2026-11-20T10:00:12+07:00", "error": null },
    "piper_tts":           { "status": "completed", "started_at": "2026-11-20T10:00:12+07:00", "finished_at": "2026-11-20T10:02:40+07:00", "error": null },
    "synthetic_visuals":   { "status": "completed", "started_at": "2026-11-20T10:02:40+07:00", "finished_at": "2026-11-20T10:05:10+07:00", "error": null },
    "ffmpeg_assembly":     { "status": "completed", "started_at": "2026-11-20T10:05:10+07:00", "finished_at": "2026-11-20T10:08:30+07:00", "error": null },
    "output_audit":        { "status": "completed", "started_at": "2026-11-20T10:08:30+07:00", "finished_at": "2026-11-20T10:09:05+07:00", "error": null }
  }
}
```

> เสกอ่านแล้วรู้ทันที: "งานจบแล้ว เห็น steps 5/5 ครบ + timestamp — ไม่ต้องถามเลน (v1.1: เห็นหลังจบเท่านั้น)"
>
> **โน้ต ADR-xxx (task steps schema — รอบ M5/M6):** true mid-flight rail (เห็น `running/pending` กลางทางผ่าน `task_get_status`) ต้องมี ADR-xxx ออกแบบ task steps schema ก่อน (เก็บ steps กลางทางที่ไหน + ใครเขียน/ใครอ่าน + ไม่ชน lock) — รอบ M5/M6 ค่อยทำ ไม่ทำใน v1.1

---

## 4. Time-box ต่อขั้น (กัน DRAG-01 — งานเดินแล้วเห็นว่าช้าตรงไหน)

> ตัวเลขเสกกำหนดรายแคมเปญ — ตารางนี้คือค่าเริ่มต้นสำหรับ 6×15s=90s local render (อ้างอิง Phase 1–3 ที่ผ่าน: render จบในหลักนาที ไม่ใช่หลักชั่วโมง) — v1.1 เทียบแบบ post-hoc หลังจบจาก timestamp ในไฟล์ result (ไม่ใช่ interrupt กลางทาง)

| Step | Time-box เริ่มต้น (90s local) | เกินแล้วเสกทำอะไร |
|:-----|:-----------------------------|:------------------|
| `input_validation` | ≤5 นาที (ตรวจสคริปต์อย่างเดียว) | เกิน = สคริปต์ผิดซ้ำซาก → เสกตัดสิน B (ตัดฉากที่ผิดออก) หรือ C (ขอสคริปต์ใหม่จาก Film) ใน 1 รอบ |
| `piper_tts` | ≤15 นาที (6 ฉาก) | เกิน = Piper ช้าหรือล้ม → หยุด รายงาน error ดิบ เสกตัดสิน (ห้าม fallback silence เอง) |
| `synthetic_visuals` | ≤20 นาที (6 ฉาก Three.js) | เกิน = เฟรมติด → หยุด เสกตัดสิน (ห้ามเอาภาพนอกมาเสียบ) |
| `ffmpeg_assembly` | ≤15 นาที (ประกอบ + loudnorm 2 pass) | เกิน = ทรัพยากรชน (อาจมี render ซ้อน) → หยุด ตรวจ lock เสกตัดสิน retry หรือรอ |
| `output_audit` | ≤5 นาที (ffprobe + ebur128 + SHA-256) | เกิน = ไฟล์ใหญ่ผิดปกติ → หยุด ตรวจไฟล์ก่อนรายงานเสร็จ |
| **รวม render** | **≤60 นาที** (ไม่รวมรอคิว lock) | เกิน 2 รอบติด = **stop Loop + escalate** (savepoint rollback — ดู §6) |

**กฎ:** time-box อยู่ใน Master Brief ตั้งแต่ต้น (readiness checklist ข้อ 15–16) — เอกสารนี้แค่แตกย่อยลงรายขั้นให้เสกเห็นว่าช้าตรงไหน

---

## 5. รายงาน Sek Brief Status (Media Editor ส่งถึงเสก — เสกกระจายต่อถึง CEO)

```text
📋 Sek Brief Status — campaign_growth_m2_demo_90s (Brief v1)
────────────────────
Goal:      education → CTA บันทึก checklist ไว้ใช้กับบรีฟหน้า
Lanes:     Kawee completed · Film completed · Art completed · Sound completed · Ink completed · Media Editor completed (steps 5/5 ครบ — ดูไฟล์ result หลังจบ)
Route:     local per-scene 6×15s
Gate:      review_required · gate_passed false · approved_version null
BLOCKED:   ไม่มี
Next:      รวมที่ Media Editor → render → gate → Human Approval 7 จุด → Ink Next-Brief
────────────────────
```

---

## 6. Stop conditions (ผิดข้อเดียว = หยุด Loop ทันที — ไม่วนต่อ)

| # | สัญญาณ | แอ็กชัน |
|:-:|:--------|:--------|
| 1 | gate ถูกแก้โดยไม่มี ADR | หยุด Loop → `git stash -u` → กลับ `save-sek-rail-20261120` → รายงาน CEO/Owner (rollback ไม่ต้องขอ Owner — ย้อนกลับได้ใน 1 session) |
| 2 | paid call ไม่มี `approved_by` | หยุด Loop → บันทึก Decision Log → รายงาน CEO (0 unapproved calls — เกิน 0 = ไม่ผ่าน) |
| 3 | secrets/tokens/credentials/`.env` หลุดเข้า repo | หยุด Loop → rotate ที่ต้นทางก่อน → รายงาน CEO/Owner (`secret-history-scan.sh` ต้องผ่านก่อนตรวจรับทุกครั้ง) |
| 4 | deadline ไหลเกิน time-box 2 รอบติด | หยุด Loop → เสกออก root cause (รอบไหนพังเพราะอะไร) → รายงาน CEO/Owner + rollback ถ้าหลุดทั้งก้อน |

**ตรวจรอบนี้ (M2/M3 DRAFT):** gate ไม่แตะ (diff ว่าง — ดู Decision Log D-001) · paid call 0 ครั้ง · `secret-history-scan.sh --current` ต้องผ่านก่อนส่ง Checker · deadline รอบนี้ไม่มี (งานเอกสาร — time-box เริ่มนับรอบ 2.4 ชิ้นจริง)

---

## 7. Maker ≠ Checker + วิธีตรวจรับ

| บทบาท | ใคร | ทำอะไร |
|:------|:----|:-------|
| Maker | Media Editor (เลนรวม) | เขียนเอกสารนี้ + ล็อกรูปแบบ steps/timestamp/time-box ข้างบน |
| Checker QA | QA-ทีม | ตรวจว่า steps 5 ชื่อตรง `render_campaign_media_local` จริง / ไม่แก้ renderer / timestamp ครบ / time-box วัดได้ — ออก QA PASS/FAIL |
| Checker Architect | พี่ทรงศักดิ์ | ตรวจว่า v1.1 ไม่แก้ task tracking (`task_create/list/get_status`) — ใช้ของเดิมดูสถานะรวมเท่านั้น + steps อ่านจากไฟล์ result หลังจบ · ถ้าจะทำ mid-flight จริงต้องมี ADR-xxx (task steps schema) + รีวิวก่อน |
| Orchestrator | พี่วุฒิ | ประสาน + คุม commit (ไฟล์อย่างเดียว ไม่ commit จนกว่าตรวจครบ) |

**เส้นชัย M3 (v1.1 scope ลด):** ชิ้นงาน 1 ชิ้นมี `steps` 5 ขั้น + timestamp ครบ — **เห็นหลังจบจากไฟล์ `local_media_render_result`** (รูปแบบ §2–§3) + เสกดูสถานะรวมผ่าน `task_get_status` + อ่าน steps จากไฟล์โดยไม่ถามเลน (§5) + QA PASS + Architect PASS — รอบนี้ DRAFT พร้อมตรวจ (render จริงเกิดรอบ 2.4/M4–M5) · true mid-flight rail ต้องรอ ADR-xxx (task steps schema) รอบ M5/M6

---

## 8. อ้างอิง (ของเดิมทั้งหมด)

| แหล่ง | ใช้เรื่อง |
|:------|:----------|
| `profiles/15-content-creator/sek/team/02-content-media-editor.SOUL.md` §3 Rule 4/6 + §5.2 | steps 5 ขั้น + No Concurrent Renders + stop-on-error — เอกสารนี้คือรูปแบบรายงานของของเดิม |
| `profiles/15-content-creator/SOUL.md` (เสก §5.4 + Rule 5) | เสกอ่าน task_get_status + BLOCKED 1 รอบ |
| `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md` | prerequisite + steps + fallback + evidence ที่ renderer ให้จริง |
| `docs/showcase/CONTENT-GROWTH-PLAN-v1.md` §1 งาน 2.1 + §3 M3 + §5 | นิยามงาน + เงื่อนไขผ่าน + stop conditions |
| `axis_mcp/departments/content_service.py` (`render_campaign_media_local`) | ชื่อ steps 5 ขั้นตัวจริง — ห้ามสะกดผิด ห้ามเพิ่มขั้นที่ 6 โดยไม่มี ADR |

> 🎯 **ประโยคปิด:** "5 ขั้นมีอยู่แล้ว — เอกสารนี้แค่ทำให้เสกเห็นโดยไม่ต้องถาม แล้วรู้ว่าช้าตรงไหน (v1.1: เห็นหลังจบจากไฟล์ result — mid-flight จริงรอ ADR-xxx รอบ M5/M6)"
