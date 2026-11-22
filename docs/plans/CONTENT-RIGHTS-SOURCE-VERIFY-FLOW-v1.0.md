# CONTENT Rights + Source Verify Flow — v1.0 (Round-2: gate72 2→0)

**วันที่:** 2026-11-23
**สาขา:** `feat/gate72-2to0-r2`
**ฐาน:** `origin/main` @ `60d35c5` (PR #41 merged — gate72 v7 `review_required` 10 PASS / 2 REVIEW)
**ขอบเขต:** ออกแบบ flow ใหม่บน campaign ใหม่ ไม่แตะ `campaign_synth_phase1_20261107` v5 (frozen SHA `ef3b282c…`) และไม่แตะ `campaign_synth_gate72_20261123` v7/v8 artifacts
**หลัก:** ห้าม publish จนกว่า Piper/provenance พร้อม — flow นี้ทำได้แค่ `gate_passed: true` + `published: false`, ไม่ใช่ publish

## 1. ปัญหาที่รอบ 1 ทิ้งไว้ (2 REVIEW)

| # | check | สาเหตุที่ hardcoded |
|:-:|:------|:---------------------|
| 1 | `claims: source verification` | `_review_campaign` คืน `False` ตายตัว — ไม่มี auto-check, ไม่มี human flag |
| 2 | `media rights` | `all(asset.confirmed)` แต่ไม่มี API เปลี่ยนสถานะ — default `human_confirmation_required` เลยไม่มีวันผ่าน |

รอบ 1 พิสูจน์ว่า copy เพียงอย่างเดียวไปไม่ถึงเขียว รอบ 2 จึงออกแบบ **flow** ไม่ใช่แค่ copy

## 2. Rights-confirm flow

```
ingest/design (human_confirmation_required, rights_origin=undecided)
  │
  ├─ synthetic_internal ──► confirm_media_rights(origin=synthetic_internal)
  │     │ eligible: video_script, visual_prompt, audio_cue_sheet,
  │     │ voice_lipsync_config, local_media_render_*, draft/article/…/transcript
  │     │ reject: voiceover_audio (ElevenLabs ภายนอก)
  │     ▼
  │   media_rights_status=confirmed
  │   rights_origin=synthetic_internal
  │   rights_proof="auto: synthetic internal pipeline only (…); non-commercial-only (Piper CC-BY-NC-SA-3.0)"
  │   rights_confirmed_by=system:auto-internal_synthetic
  │
  └─ external / mixed ──► confirm_media_rights(origin, license_proof*, confirmed_by*)
        * license_proof 1–500 chars (SPDX / license URL / consent record)
        * confirmed_by human id 1–80 chars
        ▼
      media_rights_status=confirmed + proof + human + timestamp
```

- ทุกครั้งที่ confirm **bump version + reset review/approval** (gate input เปลี่ยน)
- Gate: `_summarize_rights_status` — ผ่านเมื่อทุก asset `confirmed`; detail บอกว่า auto กี่ชิ้น / human กี่ชิ้น + ไฟล์ค้าง (สูงสุด 3 ชื่อ)
- Legacy (gate72 v7): ไม่มี `rights_origin` → ยัง `human_confirmation_required` → ยัง REVIEW — backward compat โดยเจตนา

## 3. Source-verify flow

```
source_references: [decisions/ADR-032-….md, https://…]
  │
  ▼ auto-check _auto_verify_source_references(refs, all_text)
  │  url       → valid URL? + ปรากฏ verbatim ใน text? (URL+quote match)
  │  repo_path → อยู่ใน repo? (ห้าม .. / absolute) + is_file? + ถูกอ้างถึงใน text?
  │  citation   → ปรากฏ verbatim ใน text?
  │
  ▼ human flag confirm_source_verification(verified_by*, note)
  │  * required, pinned to exact campaign.version (ไม่ bump version,
  │    แต่ _save_campaign bump revision; flag เก่าข้าม version ใช้ไม่ได้)
  │
  ▼ gate "claims: source verification"
    source_ok = auto_all_pass AND human_flag_pinned_to_current_version
```

- ลำดับที่ถูก: **confirm media rights ก่อน (bump version) → confirm source flag ทีหลัง (pin version ล่าสุด) → review**
- Gate detail 3 สถานะ: `ยังไม่มีแหล่งอ้างอิง` / `auto-check ไม่ผ่าน n/m` / `auto ผ่านแต่ยังไม่มี human flag` / `auto ผ่าน + human confirm โดย X`
- Report เพิ่ม `## Source auto-check` + `## Media rights` (per-file) เพื่อ audit
- `review.review` เพิ่ม `source_auto_checks[]` + `source_verification` — evidence ตรวจซ้ำได้

## 4. API (MCP tools)

| tool | params | ผล |
|:-----|:-------|:---|
| `confirm_media_rights` | `campaign_id, filename, rights_origin, license_proof?, confirmed_by?` | asset confirmed + version bump + review/approval reset, `published:false` |
| `confirm_source_verification` | `campaign_id, verified_by, note?` | flag pinned to current version, `published:false`, next_step=review |

ทั้งสองไม่ publish, ไม่ approve — publish ยังต้อง `record_human_approval(exact version)` แยกต่างหาก (และรอบนี้ **ไม่เรียก** เพราะ Piper/provenance ยังไม่พร้อม)

## 5. Non-goals / guardrails

- ไม่แตะ phase1 v5 + gate72 artifacts (verify ด้วย `git status` clean สำหรับ paths เหล่านั้น)
- ไม่ auto-confirm `voiceover_audio` ภายนอกเป็น synthetic เด็ดขาด
- ไม่ทำ degraded→pass: fallback render ยัง fail gate เหมือนเดิม
- ไม่ publish: `published` ต้อง `false` ทุก response จนกว่า Piper rights + provenance จะพร้อมในรอบถัดไป

## 6. วิธีตรวจซ้ำ (reproduce)

```bash
source .venv/bin/activate && export PYTHONPATH=.
python -m pytest tests/test_content_mcp.py -q --no-cov -k "rights or source_verify"
# คาด: 4 passed (synthetic auto, external guard, source two-factor, missing-ref reject)
```

Evidence run (real bus, campaign ใหม่): ดู `bus/evidence/2026-11-23/gate72-2to0-r2.json`
