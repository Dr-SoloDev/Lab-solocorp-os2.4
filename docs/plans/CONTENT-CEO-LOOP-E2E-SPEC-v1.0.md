# Content CEO-Loop E2E Spec v1.0 — Minimal Workflow for Integrated Vertical Slice (Phase 2)

| Field | Value |
|:--|:--|
| Status | **D0 / NOT PASSED** — spec only, no code, no campaign, no commit |
| Owner | @content-creator-sek (เสก) — workflow definition authority |
| Consumers | CEO loop (runtime D7) · @qa (checker) · @architect-songsak (contract review) |
| Parents | PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0 §7.7/§11-Ph2 · Runtime-Design D7 · Phase2 Governed Call Graph §1-5 · Runbook CONTENT-LOCAL-MEDIA-RENDER |
| Frozen | `campaign_synth_phase{1,2,3}_20261107` — ห้ามแตะ ใช้ scratch `ceo-loop-e2e-*` เท่านั้น |

## 1. Workflow เดียวที่ CEO loop ต้องเรียก (minimal, จบใน 1 session)

**Path: local synthetic only 6×15s. ไม่ใช้ Concat, ไม่ใช้ ElevenLabs/NIM, ไม่เรียก `record_human_approval` (human-only, นอก scope)**

```
brief → TaskTracker.create → ModuleHost.call_tool ×5 → task terminal
  0. preflight (registry+health+freshness) — ไม่ผ่าน = หยุด + failed + hint (FR-04)
  1. ingest_client_generated_artifact  (seed สคริปต์ 6×15 จริง — ข้าม scaffold 4-scene ที่ render ไม่ได้)
  2. design_visual_prompt              (9:16, tiktok)
  3. design_audio_experience            (ผูก script_filename เป๊ะ)
  4. render_campaign_media_local        (pin script_filename, abort/abort)
  5. review_publish_gate                (จบที่ review_required — ไม่ approve, ไม่ publish)
  6. task_update_status → completed | failed + artifact_refs / error_detail
```

เหตุผลที่ minimal แบบนี้: `create_video_script` scaffold ออก 4-scene เสมอและตก `_local_media_scenes` (ต้อง 6×15 หรือ 10×10) — ถ้าใส่ใน minimal path จะบังคับ re-ingest ทุกรอบ ไม่ deterministic ใน 1 session จึงให้ ingest สคริปต์ 6×15 ที่ถูกต้องตั้งแต่ขั้นแรก (Phase 1 pitfall, แก้ด้วย `script_filename` pinning)

Scratch campaign: `ceo-loop-e2e-<YYYYMMDD>-<hhmm>` (เช่น `ceo-loop-e2e-20261113-01`) — สร้างใหม่ทุกรัน ห้าม reuse ข้ามรันเพื่อไม่ให้ "latest wins" คลุมเครือ

## 2. Tool contract สำหรับ `ModuleHost.call_tool(module_id, tool, args)`

`module_id` = `content-creator` คงที่ทุก call (interface D2: `connect/disconnect/health/call_tool`)

| # | tool (MCP) | input (args) | output ที่ CEO loop ต้องเก็บ | timeout | fail cases (→ หยุด + task failed) |
|:--|:--|:--|:--|:-:|:--|
| 0 | `content_department_info` + `module_registry_status` (preflight, ไม่ใช่ production) | `{}` | `runtime.status==current`, `restart_required==false`, registry `enabled`+`connected` | 10s | stale generation → restart MCP แล้ว retry 1 ครั้ง · `disabled/disconnected/error` → ไป FR-04 ทันที ไม่เรียกข้อถัดไป |
| 1 | `ingest_client_generated_artifact` | `campaign_id, artifact_type="video_script", content=<6×15 markdown ตาม LOCAL_SCENE_ROW>, provenance={client:"<id>", provider:null, model:null}, source_references?` | `filename` (script_filename ที่ pin), `version` (v1), `provenance_status=client_supplied_unverified` | 30s | `artifact_type` นอก allowlist · `provenance` มี secret/มี field แปลก · content ไม่ใช่ 6×15 (ไปตกขั้น 4) — เก็บ `error` string ลง `error_detail` |
| 2 | `design_visual_prompt` | `theme, platform="tiktok", aspect_ratio="9:16", campaign_id, source_references?` | `filename` (visual_prompt) | 30s | `aspect_ratio` ไม่ใช่ `W:H` · theme/platform ว่าง |
| 3 | `design_audio_experience` | `campaign_id, script_filename=<จากข้อ 1 เป๊ะ>` | `filename` (cue sheet), `dependencies=[script_filename]` | 30s | script ไม่อยู่ใน campaign / ผิด type → `script_filename must identify a video script in this campaign` · สคริปต์เปลี่ยนหลัง cue → ต้อง regenerate cue ใหม่ |
| 4 | `render_campaign_media_local` | `campaign_id, script_filename=<จากข้อ 1>, tts_fallback="" , visual_fallback=""` (ว่าง = abort/fail-fast; ห้ามส่ง `silence`/`static_card` ใน path นี้) | `job manifest + result`: `execution_status`, `steps` 5/5, `sync_report` drift, `output_audit` (1080×1920 30fps 90s, −16.0 LUFS ±0.5, ≤−1.5 dBTP), `SHA-256`, `degraded:false` | **4200s** (60-min subprocess cap + buffer; lock `LOCK_EX\|LOCK_NB` ถือตลอด render) | shape ไม่ใช่ 6×15/10×10 → ContentServiceError ไม่ fallback · ชื่อผิด/campaign ผิด → `script_filename must identify…` ไม่สร้าง job · lock ชน → `another local render in progress…` ให้ task failed แล้ว retry รอบใหม่ (ห้าม queue) · `degraded:true` ใดๆ → ถือว่า fail ของ path นี้ (ไป §3) |
| 5 | `review_publish_gate` | `campaign_id` (หรือ `filename` ถ้าตรวจไฟล์เดี่ยว) | gate report md + `gate_passed:false`, `status=review_required`, `approval_required:true`, `published:false`, `approved_version=null` | 30s | gate ไม่ใช่ approval — ห้ามตีความเป็น pass · version ขยับหลัง gate → ต้อง gate ใหม่ก่อนอ้างผล |
| 6 | task record (app `TaskTracker`, มิใช่ MCP render) | `create`: `{dept:"content", module:"content-creator", brief, route_reason}` ก่อนข้อ 1 · `update`: `completed + artifact_refs=[filenames, manifest, mp4 ref, sha]` หรือ `failed + error_detail={code,message,hint}` | `task_id`, `status=completed/failed`, timestamps | 10s | ห้าม `completed` พร้อม `error_detail` · ห้าม `result_ref` ชี้ไฟล์นอก `central_bus/content` |

ห้ามเรียกใน path นี้: `render_campaign_with_concat` (continuous-voice คนละ path), `generate_voiceover` (ElevenLabs เสียเครดิต), `generate_image` (paid NIM), `build_ffmpeg_job_manifest`/`record_ffmpeg_job_result` (plan-only, ไม่ใช่ local renderer), `record_human_approval` (human-only — CEO loop ห้ามเรียกเอง), `submit_to_bus` ตรงเพื่อเสก MP4 (forbidden shortcut #3)

## 3. FR-04 — disable/disconnect ต้อง failed + hint (ห้ามเงียบ, ห้าม route ใหม่)

Preflight ก่อนข้อ 1 ทุกรัน (`health(module_id)`):
- ถ้า registry `status=disabled` หรือ state `disconnected/connecting/error` หรือ provider `unconfigured/failed` → **ห้าม `call_tool` แม้แต่ครั้งเดียว** สร้าง/อัปเดต task เป็น `failed` ทันทีพร้อม:
```json
{"code":"module_unavailable","message":"Content Creator module is disabled/disconnected (state=<state>).","hint":"เปิด Modules → enable content-creator แล้วรอ connected (health check ผ่าน) จากนั้น retry task เดิม; ดู response_time_ms/last_error ใน registry state ถ้ายัง error"}
```
- CEO log ต้องมี `route_reason` ว่าเลือก content-creator เพราะอะไร + บันทึกว่าหยุดเพราะ FR-04 ไม่ใช่เพราะสคริปต์ผิด — แยก `module_unavailable` ออกจาก `content_validation_error` และ `render_failed` ใน `error_detail.code` เสมอ

## 4. Piper / FFmpeg ใช้ได้แค่ไหน (non-commercial internal draft)

- Piper `th_TH-tsync2-medium` (CC BY-NC-SA 3.0): **internal draft เท่านั้น** — `tts_provider=piper-local`, `voice_model_rights_status=noncommercial_only_human_confirmation_required`, `human_confirmation_required` ทุก render ห้ามอ้างเป็น publish/commercial/public release ต้องผ่าน human rights review แยกก่อนเสมอ
- FFmpeg: ใช้ **local CLI direct** (`provider:ffmpeg-cli`, `execution_mode:local_ffmpeg_cli`) — bridge `build_ffmpeg_job_manifest`/`build_ff_tracking_manifest` เก็บ plan เฉยๆ ไม่ execute ห้ามส่ง local render ไป `record_ffmpeg_job_result`
- Real user media ถูก block จนกว่า independent runtime verification จะผ่าน — path นี้รับเฉพาะ synthetic inputs (`synthetic_inputs_only:true, local_only:true, network_used:false`)
- **Degraded publication ยัง NO-GO**: `tts_fallback`/`visual_fallback` ใดๆ ที่ไม่ใช่ abort แล้วเกิด fallback จริง → `degraded:true` + gate FAIL (`media: local render used fallback (degraded)`) ห้าม present เป็น clean pass ต้องมี architect D1 waiver + render ซ้ำบน throwaway campaign ต่างหาก — ใน spec นี้ถือว่า fail

## 5. DoD สำหรับ QA (ผ่านเมื่อครบทุกข้อในรันเดียว)

1. Task หนึ่ง `task_id` เดินครบข้อ 0–6 บน scratch campaign ใหม่ ไม่ reuse ไม่แตะ frozen v5/v7
2. `review_publish_gate` จบ `review_required`, `gate_passed:false`, `published:false`, `approved_version=null`; provenance `client_supplied_unverified`, provider/model null
3. MP4 ตรวจจริง: ffprobe 90s 1080×1920 30fps H.264/AAC 48kHz + SHA-256 ตรง manifest + −16.0 LUFS ±0.5 + DTP ≤ −1.5 + `steps` 5/5 + `degraded:false` + drift 0.0ms×6
4. Forbidden shortcuts = 0: ไม่มี direct subprocess/piper/ffmpeg/pdoom จาก agent, ไม่มี `submit_to_bus` เสก render, ไม่มี Concat mixing, ไม่มี `record_human_approval` จาก loop
5. Negative proof: ปิด module แล้วรันซ้ำ → task `failed` + `code=module_unavailable` + hint ตาม §3 (แนบ state ก่อน/หลัง enable)
6. หลักฐานอยู่ `central_bus/content/<campaign>/` + task record เท่านั้น รายงานเป็นลิงก์ไฟล์ ไม่ใช่ตัวเลขลอยๆ
