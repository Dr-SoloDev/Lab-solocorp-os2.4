# Content Creator MCP — Internal System Audit

> **วันที่:** 2026-11-01 · **ผู้ตรวจ:** MCP Builder (🔌) · **สถานะ:** AUDIT ONLY — ยังไม่แก้โค้ด
> **ขอบเขต:** `solocorp_mcp/departments/content_mcp.py`, `content_service.py`, `media_service.py`,
> `content_helpers.py`, `sound_mcp.py`, `bus_mcp.py`, `bus_store.py`, `mcp_stdio.py`
> + ข้อมูลจริงใน `central_bus/content/` + `solocorp_skills/redact.py` (Publish Gate)
> **สถานะสรุป:** ⚠️ **NOT PASSED** — gate หลัก (Publish Gate) มีช่องโหว่ D2 ที่ยืนยันด้วย probe แล้ว
> **ตรวจซ้ำรอบสอง:** รัน probe ใหม่ทั้งหมดใน process/bus root ใหม่ ที่ `2026-11-01T13:32Z`
> → ผลและข้อแก้ไขอยู่ที่ **§11** (มี 2 ข้อที่รอบแรกเขียนผิดและถูกแก้แล้ว)
> **ผู้ตรวจซ้ำ:** ยังต้องมีคนที่สอง (คนละ agent/คนละเครื่อง) รันตาม §8 ก่อนปิด finding (maker ≠ checker)

---

## 1. บทสรุปผู้บริหาร

ระบบทำงานได้จริงและ defensive หลายชั้น (path guard, atomic write, flock, pinned ffmpeg contract)
แต่มีปัญหาสองระดับที่ต่างกัน:

1. **ความถูกต้องของ gate (P0)** — Publish Gate ที่ doc อ้างว่า "ตรวจ redaction + R1–R5"
   ในทางปฏิบัติ **ทิ้งผลตรวจ legal (L1–L3)** และถือว่า secret/PII ที่ถูก mask เป็น "ผ่าน"
   → เนื้อหาที่มีอีเมลลูกค้าหรือ API key ยังถูกบันทึกใน bus และรายงานว่า `PASS — redaction`
2. **โครงสร้างการเก็บข้อมูล (P1)** — ไม่มี index, ชื่อไฟล์คือ index; ทุก tool call สแกนและอ่าน
   manifest ทั้งหมด และ artifact 613 MB / 898 ไฟล์ถูก track ใน git

ผลลัพธ์: **ห้ามใช้ `gate_passed` เป็นสัญญาณอนุมัติ** จนกว่าจะแก้ F1 และห้ามเพิ่ม campaign
จำนวนมากบน storage แบบปัจจุบันก่อนแก้ F2

---

## 2. แผนที่ระบบ (ตามโค้ดจริง)

```text
OpenCode V2 / Codex / Perch Desktop
   │
   ├── content-creator   solocorp_mcp/departments/content_mcp.py   (16 tools + 1 resource)
   │        ├── content_service.py   2,350 บรรทัด  domain logic ทั้งหมด
   │        ├── media_service.py       925 บรรทัด  Concat MCP + Earshot MCP (stdio)
   │        └── content_helpers.py     319 บรรทัด  series 10 ตอน (ยังไม่มี tool)
   │
   ├── sound-studio      departments/sound_mcp.py (3 tools) → media_service.py
   └── central-bus       bus_mcp.py (3 tools)
              │
              └── bus_store.py (220)  ← shared, protocol-neutral
                       └── central_bus/content/   (ไม่มี DB, ไม่มี index)
```

### 2.1 Tool inventory — content-creator (16)

| กลุ่ม | Tools | หมายเหตุ |
|:--|:--|:--|
| info / gate | `content_department_info`, `review_publish_gate` | gate ไม่มีผลผูกพันทางกฎหมาย (ดู §5) |
| scaffold | `create_content_draft`, `create_video_script`, `design_visual_prompt` | เขียน template ไม่เรียก LLM |
| audio | `generate_voiceover` (ElevenLabs, **เสียเครดิตจริง**), `design_audio_experience`, `generate_voice_lipsync_prompt` | `approved=true` เป็น boolean ที่ agent ตั้งเอง |
| media plan | `build_ffmpeg_job_manifest`, `record_ffmpeg_job_result`, `build_ff_tracking_manifest` | เก็บ plan เท่านั้น ไม่ execute |
| media exec | `render_campaign_media_local`, `render_campaign_with_concat` | blocking, ถึง 60 นาที |
| governance | `ingest_client_generated_artifact`, `save_human_edited_artifact`, `record_human_approval` | approval ไม่ authenticate ตัวบุคคล |

Resource: `solocorp://content/sop` (`sop_resource()`, ตัดที่ 14,000 ตัวอักษร)

### 2.2 ขนาดโค้ด / ภาระที่วัดได้

| รายการ | ค่า |
|:--|--:|
| `content_service.py` | 2,350 บรรทัด (ไฟล์เดี่ยวใหญ่สุดใน `solocorp_mcp/`) |
| รวม `solocorp_mcp/` | 5,336 บรรทัด |
| `central_bus/content/` ระดับ root | 363 ไฟล์ (ณ วันตรวจ), 898 ไฟล์ track ใน git |
| ไฟล์ `.lock` ที่ถูก track | 12 |
| ขนาด content | 613 MB (`local_media/` 595 MB) |
| ขนาด `.git` | 402 MB |
| manifest snapshot ทั้งหมด | 161 ไฟล์ |
| snapshot ต่อ campaign สูงสุด | 40 (`solocorp-origin-10x10s`) |
| latency `_load_campaign` (median) | 1.56 ms @ 1 campaign · 19.96 ms @ 25 · **77.2 ms @ 100** (probe D) |

---

## 3. Data model — "ชื่อไฟล์คือ index"

ไม่มีฐานข้อมูล ไม่มีดัชนี campaign หนึ่งตัว = **ชุด snapshot JSON ที่ append ต่อทุกครั้งที่เขียน**

```text
central_bus/content/
  campaign-<key>-manifest_<UTC ts>.json          snapshot ต่อ 1 ครั้งที่เขียน (append-only)
  campaign-<key>-<type>-<slug>_<ts>.<ext>        artifact payload
  campaign-<key>-publish-gate-v<N>_<ts>.md       รายงาน gate
  campaign-<key>-approval-v<N>_<ts>.json         บันทึกอนุมัติ
  .<key>.lock                                     flock (ถูก track ใน git)
  local_media/<key>/<job_id>/                     วิดีโอ/เสียงที่ render แล้ว
  concat_projects/<key>/<job_id>/                 Concat project (concat.json)
  concat_renders/<key>/<job_id>/                  MP4 ที่ export
  sound/<key>/<job_id>/                           Earshot report + stem
```

### 3.1 manifest schema (จากข้อมูลจริง)

```json
{
  "schema_version": 1,
  "campaign_id": "campaign_mcp_pilot_llm_04",
  "campaign_key": "campaign-mcp-pilot-llm-04",
  "version_number": 4, "version": "v4", "revision": 6,
  "status": "approved",
  "created_at": "...", "updated_at": "...",
  "source_references": ["..."],
  "assets": [{ "filename": "...", "path": "...", "type": "video_script",
               "version": "v4", "status": "scaffold",
               "source_references": [], "source_reference_status": "user_supplied_unverified",
               "media_rights_status": "human_confirmation_required",
               "dependencies": [], "created_at": "..." }],
  "review": { "status": "review_required", "version": "v4", "gate_passed": false,
              "checks": [...], "report": {...} },
  "approved_version": "v4",
  "approval_records": [{ "version": "v4", "recorded_by": "human MCP caller; identity is not independently authenticated", "overrides_failed_checks": [...] }]
}
```

**Lifecycle:** `scaffold → client_generated → llm_generated → human_edited → review_required → approved`

### 3.2 การเข้าถึงข้อมูล — `_load_campaign()` (`content_service.py:266-285`)

```python
for item in list_department_bus(DEPARTMENT)["files"]:   # iterdir + stat ทั้งโฟลเดอร์
    if filename.startswith(f"campaign-{key}-manifest_") and filename.endswith(".json"):
        raw = fetch_from_bus(DEPARTMENT, filename)["content"]   # เปิด+parse ทุกไฟล์
return max(snapshots, key=lambda i: (int(i["revision"]), i["updated_at"]))
```

ทุก tool call ที่แตะ campaign เรียกฟังก์ชันนี้ (บางเส้นเรียกซ้ำ 2–3 ครั้ง) → ต้นทุนโตตามจำนวน
campaign × จำนวน snapshot ทั้งระบบ ไม่ใช่ตามขนาด campaign ที่สนใจ

---

## 4. Workflow จริง 8 เส้น

| # | เส้นทาง | โค้ดหลัก | จุดที่ต้องระวัง |
|:--|:--|:--|:--|
| W1 | scaffold: `create_content_draft` / `create_video_script` / `design_visual_prompt` | `_store_assets` `content_service.py:406-524` | เขียน template + brand context, `lifecycle_state=scaffold` |
| W2 | client สร้างเนื้อหาเอง → `ingest_client_generated_artifact` | `content_service.py:1867-1906` | provenance เป็น self-reported, มี secret scan ใน provenance |
| W3 | `review_publish_gate` → `_review_campaign` | `content_service.py:2069-2212` | gate ครอบ **ทุก asset ตลอดกาล** ไม่ใช่เฉพาะ version ปัจจุบัน |
| W4 | `record_human_approval` | `content_service.py:2256-2324` | ต้อง version ตรง + ต้องมี review ของ version นั้น; override รายการที่ไม่ผ่าน |
| W5 | `save_human_edited_artifact` | `content_service.py:1814-1864` | สร้าง version ใหม่ + `supersedes` (ของเก่าไม่ถูกลบ) |
| W6 | `render_campaign_media_local` | `content_service.py:1497-1687` | subprocess ถึง 3,600 s: Piper TTS → three.js pdoom → ffmpeg |
| W7 | `render_campaign_with_concat` | `media_service.py:347-635` | stdio Concat: `project_create` → `media_import` → `clip_add` → `captions_add` → `export_start`/`export_wait` → ffprobe + sha256 |
| W8 | `sound-studio` → Earshot | `media_service.py:722-925` | `measure`/`timeline`/`sfx_render` → `sound_delivery` JSON → W7 ใช้ต่อผ่าน `sound_delivery_filename` |

---

## 5. Findings

> ระดับ: **P0** = ความถูกต้อง/ความปลอดภัย · **P1** = ทำให้ระบบไม่เสถียรหรือ agent ใช้ผิด ·
> **P2** = หนี้ทางเทคนิคที่ยังไม่เจ็บ

### P0-1 · Publish Gate ทิ้งผลตรวจ legal และถือ secret ที่ถูก mask ว่า "ผ่าน"

**กลไกที่ผิด 3 จุดต่อกัน**

1. `solocorp_skills/redact.py:188` — `res.ok = not res.needs_approval`
   โดย `needs_approval` = `bool(flagged or banned)` → **`blocked` (SECRET/PII/PATH/INT_HOST) ไม่ทำให้ ok=False**
   ข้อความถูกแทนด้วย `[REDACTED:<label>]` ในหน่วยความจำเท่านั้น (`redact.py:157-170`)
2. `content_service.py:2145-2153` — ดึง checks จาก `publish_gate` เฉพาะที่ `rule.startswith("R")`
   → **L1 (ไม่มี D2 หลุด), L2, L3 ถูกทิ้งทั้งหมด**
3. `content_service.py:2139-2143` — check `redaction` ใช้ `redaction.ok` ซึ่งเป็น True ตามข้อ 1

**ผลที่วัดได้ (probe A, §11 — รันซ้ำใน bus root ใหม่แล้ว)**

```text
artifact มี: dr.solodev@example.com  และ  sk-abcdefghijklmnopqrstuvwx
report:     PASS — redaction: ไม่พบรายการค้างตรวจ
ไฟล์ใน bus:  has sk- key: True   has email: True
```

**ผลกระทบ:** เนื้อหาที่มีข้อมูลส่วนบุคคลหรือ credential ถูกเก็บลง bus ตามปกติ และรายงาน gate
เขียนว่า PASS — ผู้ตรวจมนุษย์ที่อ่านเฉพาะบรรทัด `redaction` จะปล่อยผ่าน
**ข้อควรระวังเพิ่ม:** artifact ที่เก็บไว้ยังเป็นข้อความต้นฉบับ (ไม่ถูก redact จริง) จึงต้องถือว่า
`central_bus/content/` เป็นที่เก็บข้อมูลอ่อนไหว (ดู P1-1 เรื่อง git)

**เกณฑ์ปิด finding:** มี regression test ที่ (ก) ingest ข้อความที่มี EMAIL/SECRET →
gate ต้อง `ok=False` และ (ข) report ต้องมีบรรทัด L1/L2/L3 ปรากฏ

---

### P0-2 · `gate_passed` เป็น `False` ตลอดกาล — approval override ทุกครั้งโดยโครงสร้าง

| check | โค้ด | ทำไมไม่มีทางผ่าน |
|:--|:--|:--|
| `claims: source verification` | `content_service.py:2127-2131` | hardcode `ok=False` |
| `media rights` | `content_service.py:2132-2138` | ต้องมี `media_rights_status == "confirmed"` แต่ **ไม่มีโค้ดไหนตั้งค่านี้เลย** (grep ทั้ง repo เจอแต่ `human_confirmation_required`: `content_service.py:487,1605,1668`, `media_service.py:115,708`, `scripts/render_campaign_media_local.py:272`) |

**ผลกระทบ:** `gate_passed` เป็นค่าคงที่ False → `approval_records[].overrides_failed_checks`
มี 2 รายการเสมอ → ตัวเลข "gate ผ่าน/ไม่ผ่าน" ใช้ตัดสินใจอะไรไม่ได้ และผู้อ่าน audit เข้าใจผิดว่า
gate ทำงาน ทางเดียวที่ระบบยังปลอดภัยคือมนุษย์ต้องอ่าน report เอง

**วัดจริง (probe B, §11):** campaign ที่เนื้อหาสะอาด (redaction PASS, R1–R5 ผ่านครบ) ยังได้
`gate_passed=False` และ failed checks = `['claims: source verification', 'media rights']` เท่านั้น
+ สแกนโค้ดทั้ง `solocorp_mcp/` และ `scripts/render_campaign_media_local.py` ไม่พบจุดใดที่เขียน
`media_rights_status = "confirmed"` (0 จุด)

**เกณฑ์ปิด finding:** ระบุให้ชัดว่าข้อใด "มนุษย์ต้องยืนยันเสมอ" (ไม่นับเป็น fail) และข้อใด
"ผ่านได้จริง" พร้อม tool ที่ทำให้ผ่านได้ (เช่น `confirm_media_rights`) แล้วทดสอบทั้งเส้นทางผ่านและไม่ผ่าน

---

### P1-1 · `central_bus/content/` ถูก track ใน git — 613 MB

| ตัวชี้วัด | ค่า |
|:--|--:|
| ไฟล์ content ที่ track | 898 |
| ขนาดรวมที่ track | 613 MB |
| `.git` | 402 MB |
| `.gitignore` ที่เกี่ยวข้อง | บรรทัด 25: `central_bus/content/voiceover-*` เท่านั้น |

รวมถึงไฟล์ `central_bus/content/.campaign_*.lock` ที่ถูก commit และ artifact ที่มี PII (P0-1)
**ผลกระทบ:** clone บวม, merge conflict บน artifact, ลบ campaign ออกจากระบบไม่ได้เพราะติด history,
และความเสี่ยงข้อมูลส่วนบุคคลใน history ที่ลบยาก
**เกณฑ์ปิด finding:** untrack (ไม่ rewrite history โดยไม่ขออนุมัติ), เพิ่ม ignore pattern,
ย้าย fixture ที่ test ต้องใช้ไป `tests/fixtures/content/`, ระบุที่เก็บ artifact จริงใน runbook

---

### P1-2 · `_load_campaign` เป็น O(ทุก manifest ทั้งระบบ) ต่อ tool call

`content_service.py:266-285` เปิดและ parse ทุก `campaign-*-manifest_*.json`
- ปัจจุบัน 161 manifests; campaign เดียวมีได้ถึง 40 snapshot
- `_store_assets` → `_load_campaign` + `_save_campaign`; `_review_campaign` → `_load_campaign` อีก
- `render_campaign_with_concat` → `_load_campaign` แล้ว `_review_campaign` → `_load_campaign` ซ้ำ

**ผลกระทบ:** latency โตเชิงเส้นกับจำนวน campaign สะสม; บน storage ที่โตขึ้นจะทำให้ tool timeout
(โดยเฉพาะเมื่อ MCP timeout ตั้งไว้ 1,800,000 ms ใน `opencode.json`)

**วัดจริง (probe D, median 7 รอบ):** 1 campaign → **1.56 ms** · 25 → **19.96 ms** · 100 → **77.2 ms**
≈ 0.77 ms ต่อ campaign ต่อการเรียกหนึ่งครั้ง และ `_store_assets`/`_review_campaign` เรียกซ้ำ 1–2 ครั้ง
ต่อ tool call เดียว

**เกณฑ์ปิด finding:** มี pointer file `campaign-<key>-current.json` (หรือ subdir ต่อ campaign)
ที่อ่านได้ใน O(1) + benchmark ก่อน/หลังด้วยจำนวน campaign คงที่

---

### P1-3 · Error semantics ไม่ตรง spec ของ MCP — agent แยกไม่ออกว่าสำเร็จหรือพัง

**แก้ถ้อยคำจากรอบแรก:** รอบแรกเขียนว่า "ไม่ตั้ง `isError`" ซึ่งไม่ถูกต้อง — field นี้มีอยู่จริง
(protocol serialize เสมอ) แต่ค่าที่วัดได้คือ **`False` ทั้งเส้นสำเร็จและเส้น error** จึงยังไม่มีสัญญาณ
ให้ agent แยกได้ (หลักฐาน: §11 probe E)

- `content_mcp.py:59-60` — ทุก tool คืน `str` ที่มี `{"status":"error"}`; ผลจริงบนสาย:
  `isError = False`, `structuredContent = {"result": "{\"status\": \"error\", ...}"}`
  → JSON ถูกห่อเป็น **string ซ้อนอีกชั้น** และ `outputSchema` ของทุก tool เป็น `string`
  แปลว่า "structured output" ที่มีอยู่ไม่ใช่ structured จริง
- `render_campaign_media_local` คืน `status: "review_required"` **แม้ render ล้มเหลว**
  (`content_service.py:1684`); `render_campaign_with_concat` ก็เช่นกัน (`media_service.py:631`)
  ความจริงอยู่ใน `execution_status`/`error` ซึ่ง agent มักไม่อ่าน

**ผลกระทบ:** agent รายงานผู้ใช้ว่า "สร้างเสร็จ รออนุมัติ" ทั้งที่ไม่มีไฟล์วิดีโอ — เป็นความล้มเหลว
แบบเงียบที่แพงที่สุดในระบบ agent
**เกณฑ์ปิด finding:** error คืน `isError: true` (หรือ raise ให้ FastMCP แปลง) และ result ที่ล้มเหลว
ต้องมี `status: "failed"` ที่ top level + test ยืนยันทั้งสองเส้น

---

### P1-4 · ไม่มี read model — agent มองไม่เห็นสถานะ campaign

ไม่มี `list_campaigns` / `get_campaign_status` / `get_campaign_manifest`
ทางเดียวที่ agent ใช้ได้คือ `central-bus.list_department_bus("content")` ซึ่งคืน **363 ไฟล์ดิบ**
ที่ระดับ root (ไม่รวม subdir) ไม่บอกว่าอะไรคือ campaign ล่าสุด version ไหน status อะไร

**ผลกระทบ:** agent ต้องเดา filename จาก pattern หรือให้มนุษย์บอก — ผิดหลัก "agent เลือก tool ถูกเองได้"
**เกณฑ์ปิด finding:** มี tool อ่าน 2 ตัว (list + status) ที่คืน campaign-level summary และไม่คืน payload

---

### P2 · หนี้ทางเทคนิค (ยังไม่เจ็บ แต่จะเจ็บ)

| # | เรื่อง | หลักฐาน |
|:--|:--|:--|
| P2-1 | `supersedes` ไม่ตัด scope ของ gate — แก้จนสะอาดแล้ว gate ยังติดของเก่า | `content_service.py:2076-2088` รวมข้อความ **ทุก** asset; probe C (§11) ยืนยัน: v2 ที่แก้สะอาดแล้วยัง fail `redaction` |
| P2-2 | `approved=true` ของ `generate_voiceover` เป็น boolean ที่ agent ตั้งเอง → เผาเครดิต ElevenLabs ได้โดยไม่มีมนุษย์ | `content_service.py:1920-1923` |
| P2-3 | ลบ/แทน asset ไม่ได้ → campaign ที่มี artifact เสียต้องเปิดใหม่ทั้งชุด | plan doc §112 ระบุไว้แล้ว ยังไม่แก้ |
| P2-4 | `create_10s_series` (30 artifacts) ทำงานได้แต่ไม่มี MCP tool | `content_helpers.py:198` |
| P2-5 | lifecycle label ปน: render result ถูกติด `client_generated` | `media_service.py:113` |
| P2-6 | render ยาว block stdio process เดียว → tool อื่นของ server ค้างตาม | `content_service.py:1497-1525` (timeout 3600) |
| P2-7 | caption regex แข็ง `\d{1,5}s` — สคริปต์ที่ใช้ทศนิยม parse ไม่เจอ | `media_service.py:28-30` |
| P2-8 | `review_publish_gate(campaign_id, filename)` มี back-compat สลับพารามิเตอร์ | `content_service.py:2223-2225` |
| P2-9 | doc drift: plan doc §"เกณฑ์ผ่าน" ระบุ "Publish Gate ตรวจ redaction + R1–R5" ซึ่งไม่จริงตาม P0-1 | `docs/plans/MCP-DEPARTMENT-SERVERS-CONTENT-PILOT.md:65` |

---

## 6. จุดที่ทำได้ดี — ห้ามแก้โดยไม่จำเป็น

1. **Path guard 3 ชั้น** — `is_relative_to` + เดินเช็ค symlink + reject `..` (`bus_store.py:45-60`,
   `content_service.py:811-851`, `media_service.py:37-67`)
2. **Atomic write** — `NamedTemporaryFile` + `fsync` + `replace()` ในไดเรกทอรีเดียวกัน (`bus_store.py:104-111`)
3. **Cross-process lock ต่อ campaign** — `fcntl`/`msvcrt` fallback (`content_service.py:230-263`)
4. **ffmpeg contract ปักหมุด** — whitelist args ของ ffmpeg-skill 2.17.1, ไม่รับ raw argv, ห้าม `overwrite`
   (`content_service.py:129-192, 854-970`)
5. **Provenance พูดตรง** — `client_supplied_unverified` ไม่แอบอ้าง (`content_service.py:320-351, 1900-1903`)
6. **Secret scan ใน provenance** — ปฏิเสธค่าที่ดูเป็น credential (`content_service.py:330-349`)
7. **ff-tracking validation ละเอียด** — canvas fit, camera bounds, ASCII-only, redaction ต่อ scene

---

## 7. Roadmap ที่เสนอ (ยังไม่เริ่ม)

| เฟส | งาน | เกณฑ์ผ่าน |
|:--|:--|:--|
| **F1 Truth** | คืน L1–L3, `blocked` ต้อง fail, `media_rights_status` เปลี่ยนเป็น `confirmed` ได้ผ่าน tool, `isError`/`status: failed`, regression test จาก probe P0-1/P0-2 | test ใหม่ ≥4 ตัวผ่าน; report มี L1–L3; gate ที่สะอาดจริงได้ `gate_passed=true` |
| **F2 Speed & Hygiene** | pointer file O(1), subdir ต่อ campaign, untrack `central_bus/content`, prune snapshot, fixture แยก | benchmark ก่อน/หลัง; `git ls-files central_bus/content` เหลือเฉพาะ fixture |
| **F3 Capability** | `list_campaigns`, `get_campaign_status`, `create_10s_series`, `supersede_asset`/`delete_asset`, `export_publish_package` | agent ทำงานครบ loop โดยไม่ต้องรู้ filename |
| **F4 Governance** | asset-scoped gate, approval ที่ผูกกับมนุษย์จริง (elicitation), async job start/poll สำหรับ render ยาว | ไม่มี tool ใดที่ agent อนุมัติ/จ่ายเงินได้เอง |

**ลำดับที่แนะนำ:** F1 → F2 → F3 → F4 (F1 ถูกและเร็วที่สุด และปลดล็อกความน่าเชื่อถือของทั้งระบบ)

---

## 8. วิธีตรวจซ้ำ (reproduce)

### 8.1 test suite ที่เกี่ยวข้อง (ผ่าน 44 ตัว ณ วันที่ตรวจ)

```bash
source .venv/bin/activate && export PYTHONPATH=.
python -m pytest tests/test_content_mcp.py tests/test_media_services.py \
                 tests/test_bus_mcp.py tests/test_mcp_stdio.py --tb=short -q --no-header
```

### 8.2 probe P0-1 (gate มองไม่เห็น D2)

```bash
source .venv/bin/activate && export PYTHONPATH=.
SOLOCORP_BUS_ROOT=/tmp/opencode/bus-probe2 python - <<'PY'
import shutil; from pathlib import Path
root = Path("/tmp/opencode/bus-probe2")
if root.exists(): shutil.rmtree(root)
root.mkdir(parents=True)
from solocorp_mcp.departments import content_service as cs
from solocorp_mcp import bus_store
cid = "leak-probe"
text = ("# บทความทดสอบ\n\n## Hook\n\nเราลองแล้วพัง 2 ชั่วโมง ต้นทุนคือเวลา\n\n"
        "## Body\n\nหลักฐาน: tests/test_content_mcp.py และ git 78d915f\n"
        "ติดต่อผู้ดูแลได้ที่ dr.solodev@example.com และคีย์ sk-abcdefghijklmnopqrstuvwx\n\n"
        "## ยังไม่ได้ทำ\n\nยังไม่ได้ทดสอบบน production\n\nคุณเจอปัญหาแบบเดียวกันไหม?\n")
a = cs.ingest_client_generated_artifact(cid, "article", text, {"client": "probe"},
                                        ["tests/test_content_mcp.py"])
cs.design_visual_prompt("probe theme", "linkedin", "16:9", cid, ["tests/test_content_mcp.py"])
r = cs.review_publish_gate(campaign_id=cid)
print("gate_passed:", r["gate_passed"])
print("failed:", [c["check"] for c in r["checks"] if not c["ok"]])
stored = bus_store.fetch_from_bus("content", a["filename"])["content"]
print("has sk- key:", "sk-abcdefghijklmnopqrstuvwx" in stored)
print("has email:", "dr.solodev@example.com" in stored)
PY
```

ผลที่ควรเห็นถ้ายังไม่แก้: `redaction` = PASS และ `has sk- key: True`

### 8.3 ตรวจขนาด storage

```bash
git ls-files central_bus/content | wc -l          # 898
git ls-files -z central_bus/content | xargs -0 du -ch | tail -1   # ~613M
du -sh .git                                       # ~402M
ls central_bus/content/campaign-*-manifest_*.json | wc -l         # 161
```

---

## 9. ข้อจำกัดของ audit นี้ (ยังไม่ได้ตรวจ)

- ไม่ได้รัน full suite (`tests/` + `central_bus/tests/`) — รันเฉพาะ 4 ไฟล์ที่เกี่ยวข้อง (44 ตัว ผ่าน)
- ไม่ได้ทดสอบ concurrency จริง (สอง process เขียน campaign เดียวกันพร้อมกัน)
- ~~ไม่ได้ทำ load test กับจำนวน campaign มาก~~ → **ปิดแล้ว** ด้วย probe D (§11) ที่ 100 campaigns
- ไม่ได้ตรวจ E2E ผ่าน Codex/OpenCode ในรอบนี้
- ไม่ได้ตรวจ internals ของ Concat AppImage / Earshot — ถือเป็นกล่องดำที่ยิงผ่าน MCP stdio
- ยังไม่ได้ยืนยันว่า `record_human_approval` ถูกเรียกโดยมนุษย์จริงหรือ agent ในประวัติที่ผ่านมา
- **การตรวจซ้ำใน §11 เป็นการรันซ้ำโดย agent เดียวกันบนเครื่องเดียวกัน** → พิสูจน์ได้ว่า
  "reproducible" แต่ **ไม่ใช่ independent verification** ตาม `rules/06-certification.md`

---

## 10. อ้างอิง

- `docs/plans/MCP-DEPARTMENT-SERVERS-CONTENT-PILOT.md` — แผนและ verification record เดิม
- `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md`, `CONTENT-FFMPEG-JOB-BRIDGE.md`
- `solocorp_skills/redact.py` — แหล่ง Publish Gate (R1–R5 + L1–L3)
- `rules/06-certification.md` — เหตุผลที่ finding ต้องมีหลักฐานและผู้ตรวจซ้ำ

---

## 11. Fresh verification record — 2026-11-01T13:32Z

### 11.1 สภาพแวดล้อมและวิธีแยก

| รายการ | ค่า |
|:--|:--|
| Python | 3.12.3 (CPython) |
| Platform | Linux 7.0.0-38-generic x86_64 |
| git HEAD | `78d915f08589f1b1b6e1a612c261a5ce1e85c9dc` (branch `main`) |
| เวลารัน | 2026-11-01T13:32:17Z |
| Isolation | ทุก probe ใช้ `SOLOCORP_BUS_ROOT` ของตัวเองใต้ `/tmp/opencode/audit-verify/<probe>` + ล้าง `sys.modules` ของ `solocorp_mcp` ก่อน import ใหม่ |
| ผลกระทบต่อข้อมูลจริง | **ไม่มี** — ไม่มีการเขียนลง `central_bus/content` ของ repo |
| Script | `/tmp/opencode/audit_verify.py` (probe A–F) + `/tmp/opencode/audit_verify_out.txt` (output ดิบ) |

> หมายเหตุความซื่อสัตย์: "fresh" ในที่นี้ = process ใหม่ + bus root ใหม่ + import ใหม่
> **ไม่ใช่** เครื่องใหม่หรือ agent คนใหม่ จึงยังไม่นับเป็น independent verification

### 11.2 Probe A — P0-1 (gate vs secret/PII)

```text
gate_passed                       : False
failed_checks                     : ['claims: source verification', 'media rights']
redaction_check_ok                : True
redaction_check_detail            : ไม่พบรายการค้างตรวจ
report_redaction_line             : - PASS — redaction: ไม่พบรายการค้างตรวจ
report_has_L1_L3_lines            : []
stored_artifact_has_secret        : True
stored_artifact_has_email         : True

--- report excerpt ---
## Checks
- PASS — dependencies: primary content: พบ draft/script
- PASS — dependencies: visual prompt: พบ visual prompt
- PASS — dependencies: audio cue sheet: audio cue อ้างถึงสคริปต์ล่าสุด
- PASS — claims: source references supplied: พบ 1 รายการ
- REVIEW — claims: source verification: ระบบยังไม่ได้ตรวจสอบแหล่งอ้างอิงโดยอิสระ; ต้องให้มนุษย์ยืนยัน
- REVIEW — media rights: ต้องยืนยันลิขสิทธิ์ภาพ/เพลง/เสียงก่อนเผยแพร่
- PASS — redaction: ไม่พบรายการค้างตรวจ
- PASS — R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน: 2 รายการ: tests/test_content_mcp.py, git 78d915f
- PASS — R2 แสดงความล้มเหลวและต้นทุน/เหตุผล: มีรอยแผล
- PASS — R3 มีบรรทัด 'ยังไม่ได้/ยังไม่รู้' (calibration): ยังไม่ได้
- PASS — R4 ไม่เทียบ/ไม่วัดคนอื่น ไม่มีคำสั่ง: สะอาด
- PASS — R5 ปิดด้วยคำถามเปิด 1 ข้อ: มีคำถาม
```

**สรุป:** P0-1 **CONFIRMED** — ข้อความมีทั้งอีเมลและ API key, รายงานเขียน `PASS — redaction`,
ไม่มีบรรทัด L1–L3 เลย, และไฟล์ที่เก็บใน bus ยังมีข้อมูลจริงครบ

### 11.3 Probe B — P0-2 (gate_passed เป็น False โดยโครงสร้าง)

```text
gate_passed                       : False
failed_checks                     : ['claims: source verification', 'media rights']
redaction_check_ok                : True
code_paths_setting_confirmed      : NONE
```

**สรุป:** P0-2 **CONFIRMED** — campaign ที่สะอาด (redaction PASS + R1–R5 ผ่านครบ) ยังได้
`gate_passed=False` จาก 2 check ที่ผ่านไม่ได้เชิงโครงสร้าง และการสแกนโค้ดหา
`media_rights_status = "confirmed"` ได้ **0 จุด**

### 11.4 Probe C — P2-1 (superseded asset ยังอยู่ใน scope ของ gate)

```text
v1_failed_checks                  : ['claims: source verification', 'media rights', 'redaction', 'R1 มีหลักฐานตรวจสอบได้อย่างน้อย 1 อัน']
human_edit_version                : v3
human_edit_supersedes             : True
v2_failed_checks                  : ['claims: source verification', 'media rights', 'redaction']
redaction_still_failing_in_v2     : True
```

**สรุป:** P2-1 **CONFIRMED** — แก้เนื้อหาให้สะอาดแล้ว (ลบ `ลูกค้า: ACME Corporation` ออก)
gate ยังฟ้อง `redaction` เพราะยังรวมข้อความของ asset เวอร์ชันเก่า

### 11.5 Probe D — P1-2 (ต้นทุน `_load_campaign`)

```text
   1 campaigns -> _load_campaign median 1.56 ms
  25 campaigns -> _load_campaign median 19.96 ms
 100 campaigns -> _load_campaign median 77.2 ms
files_in_content_root             : 300
```

**สรุป:** P1-2 **CONFIRMED** — โตเชิงเส้น ≈ 0.77 ms/campaign/ครั้ง (median 7 รอบ ต่อระดับ)

### 11.6 Probe E — P1-3 (error semantics บนสาย MCP จริง)

```text
result_keys                       : ['content', 'isError', 'structuredContent']
has_isError_key                   : True
payload_status                    : error
payload_error                     : ContentServiceError
tool_count                        : 16

ERROR PATH   isError = False | structuredContent = {'result': '{"error": "ContentServiceError", "message": "title is required", "status": "error"}'}
SUCCESS PATH isError = False
tool count = 16
has outputSchema: 16/16 (schema เป็น string)
```

**สรุป:** P1-3 **CONFIRMED แต่ต้องแก้ถ้อยคำ** — `isError` มีอยู่จริงและเป็น `False` ทั้งเส้นสำเร็จ
และเส้น error; `structuredContent` เป็น JSON string ที่ถูกห่อใน `{"result": ...}` อีกชั้น;
`outputSchema` ทั้ง 16 tool เป็น `string` → agent ไม่มีสัญญาณแยก success/failure จาก protocol

### 11.7 Probe F — P1-1 (storage ใน git)

```text
tracked_files                     : 898
tracked_lock_files                : 12
content_dir_size                  : 614M
git_dir_size                      : 402M
manifest_snapshots                : 161
```

**สรุป:** P1-1 **CONFIRMED** (เพิ่มหลักฐานใหม่: `.lock` ถูก track 12 ไฟล์)

### 11.8 Test suite ที่เกี่ยวข้อง (รันสด)

```bash
python -m pytest tests/test_content_mcp.py tests/test_media_services.py \
                 tests/test_bus_mcp.py tests/test_mcp_stdio.py \
                 --tb=short -q --no-header -p no:cacheprovider
# 44 passed in 10.22s
```

### 11.9 สรุปสถานะ finding หลังตรวจซ้ำ

| Finding | สถานะ | หลักฐาน |
|:--|:--|:--|
| P0-1 gate มองไม่เห็น D2 | **CONFIRMED** | probe A |
| P0-2 `gate_passed` เป็น False ตลอดกาล | **CONFIRMED** | probe B + สแกนโค้ด 0 จุด |
| P1-1 bus content ใน git | **CONFIRMED** | probe F |
| P1-2 `_load_campaign` O(n) | **CONFIRMED (วัดได้)** | probe D |
| P1-3 error semantics | **CONFIRMED (แก้ถ้อยคำ)** | probe E |
| P1-4 ไม่มี read model | **CONFIRMED (code-level)** | `tools/list` 16 ตัว ไม่มี tool อ่าน campaign |
| P2-1 superseded ยังอยู่ใน gate | **CONFIRMED** | probe C |
| P2-2 … P2-9 | **CODE-LEVEL ONLY** | ยังไม่มี runtime probe (ต้องมี tool/hardware จริง) |

### 11.10 ข้อแก้ไขจากรอบแรก (self-correction)

1. **จำนวน tool:** รอบแรกเขียน 15 → ที่จริง **16** (`tools/list` ยืนยัน: เพิ่ม `record_ffmpeg_job_result`
   ที่นับตกไป) แก้แล้วใน §2 และ §2.1
2. **P1-3 ถ้อยคำ:** รอบแรกเขียนว่า "ไม่ตั้ง `isError`" → ที่จริง field มีและเป็น `False`
   แก้เป็น "`isError=False` ทั้งสองเส้น" พร้อมหลักฐาน `structuredContent` ที่ห่อ string ซ้อน
3. **บทเรียนวิธีตรวจ:** probe E รอบแรกพิมพ์แค่ว่ามี key `isError` หรือไม่ ทำให้อ่านผลผิดทิศ
   → ต้องพิมพ์ **ค่าจริง** ไม่ใช่แค่การมีอยู่ของ key (บันทึกไว้เป็นแนวปฏิบัติของ audit รอบถัดไป)
