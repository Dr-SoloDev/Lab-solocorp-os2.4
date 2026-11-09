# Content Video Pipeline — Phase 1 Manifest Adapter (Design, D1-level)

> **Status: DESIGN ONLY — NOT IMPLEMENTED, NOT PASSED.** Author: @architect-songsak (Head of Architect).
> Certification: D0 as Head per `profiles/CERTIFICATION-REGISTRY.md` line 13 ("ทุก Department Head + Specialist ที่เหลือ — ยังไม่ผ่านด่านใด"). This document is a D1-level design (why / which agent / scope). Implementation MUST go via specialists holding a D2 plan (50–150-line agent calling real tools, with run output + exit code) attached to the work order, per `rules/06-certification.md`. No claim of "done" without evidence. Default status until evidence attached: **NOT PASSED**.
> CEO decision: `central_bus/content/ceo-phase1-decision-20261107_20261107T030931814535Z.md`. This doc does not supersede it; it specifies the adapter contract the CEO decision requires.

## 0. Non-negotiable constraints (verified in repo)

1. **Adapter, not replacement.** Existing `schema_version: 1` job/result assets (`local_media_render_job`, `local_media_render_result`) stored via `_store_assets()` in `axis_mcp/departments/content_service.py:1566-1672` are the source of truth. `review_publish_gate` / `_review_campaign` (`content_service.py:2068, 2335`) reads the **campaign manifest** (`campaign["assets"]`, `_save_campaign`/`_load_campaign`). The proposed schema (`provenance/status/pipeline.steps[5]/assets.final_video/publish_gate` R1–R5) is a **read-only projection** built from existing records. It never replaces those asset types and never mutates the campaign manifest.
2. **Provenance stays `client_supplied_unverified`.** Set only in `ingest_client_generated_artifact` (`content_service.py:1867`, `metadata.provenance_status` at 1902). The adapter copies it verbatim; it never upgrades, "verifies", or re-labels it.
3. **Local synthetic-only ≠ Concat.** Local path: `render_campaign_media_local` (`content_service.py:1528`) → `_execute_local_media_pipeline` (`:1497`, subprocess to `scripts/render_campaign_media_local.py::render()` at `:104`, stdin JSON payload, 3600s timeout). Concat path: `render_campaign_with_concat` / `concat_render_result` asset type, consumed by `_review_campaign` media_workflow (`:2114-2203`). The adapter must not mix them: no Concat fields, no `sound_delivery_filename`, no Earshot `sound_review_report` linkage.
4. **Rights gate.** Piper `th_TH-tsync2-medium` is in `tools/piper/model-rights.json`; `content_service.py:1546-1559` maps `commercial_use=false` → `noncommercial_only_human_confirmation_required`. `human_confirmation_required` propagates end-to-end. Adapter copies, never clears.
5. **Synthetic-only gate pending.** Job manifest `execution.runtime_gate = "synthetic_inputs_only_pending_independent_ffmpeg_verification"` (`:1579`). `ffmpeg-skill doctor ok:false` (per CEO decision). Adapter must surface this, not hide it.
6. **Layout lock.** Renderer accepts ONLY `(6,15)` or `(10,10)` (`scripts/render_campaign_media_local.py:114-115`, mirrored in `_local_media_scenes` `content_service.py:1492-1493`). A 30s single-scene script fails validation today. Phase 1 scope: fresh synthetic campaign in a supported layout, 6×15s recommended.

---

## 1. Field-by-field mapping: proposed `pipeline.steps[*]` ← existing job/result fields

Proposed adapter root (derived, never stored in campaign assets — see §2):

```json
{
  "adapter_version": 1,
  "campaign_id": "<canonical_id>",
  "job_id": "<job_id>",
  "provenance": {...},
  "status": "<overall>",
  "gate_status": "<...>",
  "current_step": "<step_id | null>",
  "pipeline": { "steps": [ /* 5 entries, fixed order */ ] },
  "assets": { "final_video": <object | null> },
  "publish_gate": { "status": "review_required", "gate_passed": false, "checks": [...R1-R5 + campaign checks...], "media_workflow": {...} }
}
```

Each step entry: `{ id, status: completed|failed|degraded|skipped|not_started, started_at, finished_at, detail, source_fields: [...] }`. Where `started_at/finished_at` are not in existing records, the adapter emits `null` and marks the step `derivation: "post_hoc"` (see "Derivable?" column) — it must never fabricate timestamps.

### 1.1 `input_validation`

| Adapter field | Existing source | Derivable? |
|---|---|---|
| `status` | `job_manifest.script_filename` + latest `video_script` campaign asset exists (checked at `content_service.py:1535-1540`); `_local_media_scenes()` (`:1463`) success ⇔ layout ∈ {(6,15),(10,10)}, contiguous timing, every scene has description + voiceover | **Derivable post-hoc, partial.** Success of validation is implied if a `local_media_render_job` asset exists (job is only stored after scenes parse). But the *reason* for a validation failure is lost: `_local_media_scenes` raises `ContentServiceError` **before** any job/result asset is stored, so a validation failure produces no bus record to map from. |
| `detail.scene_count / scene_seconds / duration_seconds` | `job_manifest.scene_count`, `job_manifest.scene_seconds`, `job_manifest.duration_seconds` (`:1582-1584`) | **Derivable.** |
| `detail.script_filename / script_version` | `job_manifest.script_filename`, `job_manifest.script_version` (`:1573-1574`) | **Derivable.** |
| `started_at / finished_at` | — | **NOT derivable. Needs new instrumentation** (see §1.6). Adapter emits `null`. |
| `error_code / error` | Nothing stored on pre-job failure | **NOT derivable. Needs instrumentation:** catch in `render_campaign_media_local` around `_local_media_scenes()` and record a `local_media_render_result` with `execution_status: failed` + `failed_step: "input_validation"` *or* change contract to raise with machine-readable code. Until then, adapter can only report validation as `completed` (job exists) or `unknown` (no job → no record). |

### 1.2 `piper_tts`

| Adapter field | Existing source | Derivable? |
|---|---|---|
| `provider` | `job_manifest.tts_provider = "piper-local"` (`:1571`) | **Derivable.** |
| `voice_model_license` | `job_manifest.voice_model_license` (`:1585`) + `render.voice_model_license` (`scripts/...:273`) | **Derivable.** |
| `rights_status` | `job_manifest.voice_model_rights_status` (`:1586`), `render.media_rights_status = "human_confirmation_required"` (`scripts/...:272`) | **Derivable. Must stay `human_confirmation_required`.** |
| `per-scene segments` | `render.voice_segments` = `voice_reports` from `scripts/local_tts_piper.py` stdout per scene (`scripts/...:144-160, 312`) | **Derivable when `execution_status == completed`.** On pipeline failure mid-TTS, the subprocess raises (`raise RuntimeError` via `main()` → stderr JSON, exit 1, `scripts/...:316-324`); `content_service.py:1640-1652` stores only `{error, message}` — **partial voice_segments are lost. Needs instrumentation** to capture partial `voice_reports` on failure. |
| `per-scene duration vs slot check` | Inside renderer: `voice_duration > scene_seconds` → `RuntimeError` (`scripts/...:156-159`) | **Derivable as pass/fail only** (completed ⇒ passed). No per-scene record of the check on failure. |
| `status` | `result_record.execution_status` (`:1634`/`1647`) | **Derivable as aggregate only.** Step-level attribution ("TTS failed" vs "visuals failed") is **NOT derivable** from a monolithic failure `message` string. **Needs instrumentation** (§1.6). |

### 1.3 `synthetic_visuals`

| Adapter field | Existing source | Derivable? |
|---|---|---|
| `provider` | `job_manifest.visual_provider = "three.js-pdoom-local"` (`:1572`); `render.visual_engine = "Three.js via pdoom-video dependencies"` (`scripts/...:270`) | **Derivable.** |
| `frames` | `render.frames` (resolved paths, `scripts/...:165-167, 311`) | **Derivable when completed.** |
| `frame count == scene count` check | `scripts/...:166-167` | **Derivable as pass/fail only.** |
| `scene_count` | `render.scene_count` (`scripts/...:282`) | **Derivable.** |
| `status` | `result_record.execution_status` | **Aggregate only — same limitation as §1.2. Step attribution needs instrumentation.** |

### 1.4 `ffmpeg_assembly`

| Adapter field | Existing source | Derivable? |
|---|---|---|
| `provider` | `job_manifest.provider = "ffmpeg-cli"` (`:1570`); `result_record.provider` (`:1633`); `render.execution_mode = "local_ffmpeg_cli"` (`scripts/...:269`) | **Derivable.** |
| `audio_target` | `render.audio_target = {standard: EBU_R128, lufs: -16.0, true_peak_dbtp: -1.5, normalizer: loudnorm two-pass}` (`scripts/...:278`); `render.silence_removal` (`:277`) | **Derivable.** |
| `audio_mix / audio` | `render.audio_mix {path, bytes, sha256, codec pcm_s16le, sample_rate, channels}` (`:295-302`), `render.audio` (`:303-310`) | **Derivable when completed.** |
| `video` | `render.video {path, bytes, sha256, codec, width, height, frame_rate}` (`:286-294`) | **Derivable when completed.** |
| `subtitles` | `render.caption_timing = "scene-level from supplied script; no word-level alignment"` (`:280`); `captions.ass` written by `_write_subtitles` (`:55-70`) | **Derivable as claim only.** No subtitle file hash is returned — if the adapter needs `captions.ass` provenance, **needs instrumentation** (return its sha256). |
| `status` | `result_record.execution_status` | **Aggregate only — needs instrumentation for step attribution.** |

### 1.5 `output_audit` (ffprobe + EBU R128 + SHA-256)

| Adapter field | Existing source | Derivable? |
|---|---|---|
| `ffprobe verification` | `scripts/...:251-260` — runs `ffprobe`, asserts 1080×1920, duration ±0.5s, both streams present | **Derivable as pass/fail** (completed ⇒ passed). Raw probe JSON is **not** stored. |
| `loudness measurement` | `render.audio_measurement {integrated_lufs, true_peak_dbtp}` from `_measure_ebur128` (`:86-101`); gate: `abs(lufs+16.0) ≤ 0.5`, `true_peak ≤ -1.5` (`:261-265`) | **Derivable.** |
| `video sha256` | `render.video.sha256` via `_sha256` (`:78-83`) and validated 64-hex at `content_service.py:1626-1627` | **Derivable.** |
| `independent re-probe` | — | **NOT derivable. Needs new instrumentation:** an independent checker (QA, not the maker — §5) re-running `ffprobe` + EBU R128 measurement + SHA-256 against the file on disk and recording its own evidence. This is the "pending independent verification" the job manifest already flags (`runtime_gate`). The adapter must label the renderer-embedded audit as `self_reported` and reserve `verified` for the independent checker. |

### 1.6 New instrumentation required (owned by @engineering — @changful, not by this adapter)

The renderer `scripts/render_campaign_media_local.py::render()` is monolithic: one `try` in `main()` (`:316-324`), one aggregate `status: completed` return (`:267-313`). To make `pipeline.steps[*].status` honest, the following must be added (D2-gated, §5):

1. **Phase markers.** Wrap each phase (TTS loop `:145-160`, Three.js scene render `:162-167`, silence-pad + mix `:169-229`, subtitle+video assembly `:231-249`, audit `:251-265`) in try/except that records `{phase, status, started_at, finished_at, error_type, error_message}` into a `steps` array in the returned dict. On failure the renderer should still return (or print) the partial `steps` + partial artifacts (e.g. `voice_reports` collected so far) so `content_service.py:1640-1652` can persist them in `result_record` instead of only `{error, message}`.
2. **Pre-job validation record.** In `render_campaign_media_local`, catch `_local_media_scenes` failure and persist a failed `local_media_render_result` (or at minimum return `{execution_status: failed, failed_step: input_validation}` in the tool response) so `input_validation` failures are mappable.
3. **Caption/audio-mix hashes.** Return `sha256` for `captions.ass` and keep `audio_mix.sha256` (already present) so the adapter's `assets.final_video` audit block is complete.
4. **No schema change to `schema_version: 1` job/result beyond additive keys.** Additive `steps`/`partial` keys inside `result_record.render` are backward-compatible (existing readers ignore unknown keys; `tests/test_content_mcp.py:654` only asserts known keys). Do **not** bump `schema_version` to 2 — that would be the breaking replacement the CEO decision forbids.

Until (1)–(3) land, the adapter reports steps 2–4 as `status: completed|failed` derived from the aggregate `execution_status`, with `derivation: "post_hoc_aggregate"` and `started_at/finished_at: null`. It must never claim per-step timing or per-step failure attribution it cannot prove.

---

## 2. Where adapter output lives (without breaking `review_publish_gate` / tests)

**Rule: the adapter output is NOT a campaign asset.** It must not be appended to `campaign["assets"]` via `_store_assets()`.

Why: `_review_campaign` (`content_service.py:2075-2082`) iterates **every** `.md/.txt/.json` campaign asset, joins all text into `all_text` (redaction input) and `primary_text` (publish-gate R1–R5 input via `publish_gate(primary_text, ...)` at `:2089`). A JSON adapter asset containing words like "guarantee"/"100%" in step details, or any `PRIMARY_CONTENT_ARTIFACT_TYPES` collision, would pollute redaction and R1–R5. It would also change `assets` length/version semantics that `tests/test_content_mcp.py` asserts (e.g. removal tests `:738-759`, gate tests `:187-322`).

**Chosen placement:**

- Adapter output is produced by a **pure read function** (new, e.g. `build_manifest_adapter(campaign_id, job_id) -> dict` in `content_service.py` or a small `content_adapter.py` module) that reads: latest `local_media_render_job` + `local_media_render_result` assets + `_review_campaign`-equivalent gate output (see §3) and returns a dict. It performs **no writes** to the campaign manifest and takes no campaign lock beyond a read.
- If a persisted copy is needed for audit, it is written via `submit_to_bus(DEPARTMENT, task_id, json_str, "json")` **directly** (the same pattern `_review_campaign` uses for the publish-gate report at `:2303-2304` — `submit_to_bus`, not `_store_assets`), with:
  - `task_id = _asset_task_id(canonical_id, "manifest-adapter", job_id)` (reuses the existing helper, unique per job),
  - filename lands under `central_bus/content/` as a standalone artifact,
  - **no entry** in `campaign["assets"]`, **no** `campaign["version"]` bump, **no** `campaign["status"]` change.
- The existing asset types `local_media_render_job` / `local_media_render_result` and the campaign manifest stay byte-for-byte the records `review_publish_gate` consumes. `tests/test_content_mcp.py` expectations (`:654-702`: job `execution_status == "in_progress"`, result `completed`, `media_rights_status == "human_confirmation_required"`, `campaign["approved_version"] is None`) are untouched by the adapter.
- **Return-shape compatibility:** `render_campaign_media_local`'s return dict (`:1674-1687`) keeps its current keys. The adapter may be exposed as an *additional* key (e.g. `"manifest_adapter": {...}`) or a separate tool, but must not rename/remove `job_manifest`, `result_record`, `publish_gate`, `status`. Existing callers and tests assert `result["status"] == "review_required"` on the completed path (`:689`) — §3 preserves that on success and changes it only on failure.

**`assets.final_video` mapping:**

| Adapter field | Source |
|---|---|
| `assets.final_video.path` | `render.video.path` (`scripts/...:287`) — absolute path under `central_bus/content/local_media/<campaign_key>/<job_id>/` |
| `assets.final_video.sha256` | `render.video.sha256` (`:289`) |
| `assets.final_video.bytes / codec / width / height / frame_rate` | `render.video.*` (`:288-294`) |
| `assets.final_video.audio_measurement` | `render.audio_measurement` (`:279`) |
| `assets.final_video` (whole) | `null` whenever `execution_status != "completed"` — see §4 |

---

## 3. Status semantics

### 3.1 Vocabulary

| Adapter field | Values | Meaning |
|---|---|---|
| `status` (overall) | `completed` · `failed` · `blocked` | `completed`: all 5 steps completed + audit passed. `failed`: renderer raised (any step). `blocked`: render completed but a gate cannot pass (e.g. rights unconfirmed) — note this is *not* a render failure. |
| `gate_status` | `review_required` · `blocked_render_failed` · `blocked_rights` · `blocked_audit` | `review_required` is only reachable from `completed`. Failed render → `blocked_render_failed`. Completed render with `human_confirmation_required` rights → still `review_required` (human decides), never `passed`. |
| `current_step` | `input_validation` · `piper_tts` · `synthetic_visuals` · `ffmpeg_assembly` · `output_audit` · `null` | First non-completed step; `null` when `status == completed`. With post-hoc derivation (§1.6 caveat) this equals the instrumented `failed_step` once instrumentation lands, otherwise `null` + `derivation: post_hoc_aggregate` on failure. |
| `publish_gate.status` | `review_required` | Mirrors `_review_campaign` (`:2306, 2323`). The gate never auto-passes and never auto-approves: `approval_required: True`, `publish_action: blocked_until_human_approval` (`:2325, 2331`). |
| `publish_gate.gate_passed` | `bool` | Copy of `_review_campaign`'s `all(item["ok"] for item in checks)` (`:2272`). For local-only campaigns it is expected `False` (media-rights + source-verification checks at `:2226-2237` fail by design until a human confirms). Adapter must not soften this. |
| `publish_gate.checks` (R1–R5) | verbatim from `gate.checks` where `rule` starts with `R` (`:2263-2271`) | Embedded **verbatim**, never recomputed. |
| `publish_gate.media_workflow` | verbatim from `_review_campaign` (`:2118-2203`) | For local renders this describes the **Concat** workflow (`mode: concat`, `status: not_started` when no `concat_render_result` exists). The adapter must label it as such and add its local-render summary **alongside** (new key, e.g. `local_render`), never overwrite `media_workflow`. |

### 3.2 The bug and the fix (owned by @engineering — @changful)

**Bug (verified):** `render_campaign_media_local` returns `"status": "review_required"` unconditionally at `content_service.py:1684`, even when `execution_status == "failed"` (`:1641`). A failed render therefore *claims* review status for a video that does not exist.

**Adapter contract (the adapter itself cannot fix the tool — it can only stop propagating the lie):**

- The adapter computes its own `status`/`gate_status` from `execution_status`, **never** from the tool's top-level `status`:
  - `execution_status == "failed"` → adapter `status: "failed"`, `gate_status: "blocked_render_failed"`, `current_step: <failed_step or null>`, `assets.final_video: null`, `publish_gate` still present (text gate ran) but `gate_status` forces the overall verdict to blocked.
  - `execution_status == "completed"` → adapter `status: "completed"`, `gate_status: "review_required"` (pending human approval/rights).
- **Required fix in the tool** (engineering scope, D2-gated): at `content_service.py:1684`, return `status = "review_required" if execution_status == "completed" else "failed"`, and set `approval_required = (execution_status == "completed")`. Existing test `test_local_media_render_records_cli_and_keeps_publish_gate` (`tests/test_content_mcp.py:689`) asserts `review_required` only on the mocked-completed path, so this fix does not break it. A new failure-injection test must assert: failed render → `status != "review_required"`, no MP4 file on disk, `assets.final_video is null`.
- **Campaign-level nuance:** `_review_campaign` always sets `campaign["status"] = "review_required"` (`:2317`) once the text gate runs — even after a failed render. That is pre-existing campaign semantics (the *text* is under review) and out of scope for the adapter. The adapter distinguishes `campaign_status` (from the manifest) from `render_status` (from `execution_status`) and from `gate_status` (the video-specific verdict). It must surface all three so nobody mistakes campaign review for a renderable video.

### 3.3 Transition table

| Event | `status` | `gate_status` | `current_step` | `assets.final_video` |
|---|---|---|---|---|
| Job stored, renderer running | `in_progress` (pass-through from `job_manifest.execution.status`) | `not_started` | `input_validation` | `null` |
| Renderer returns completed, audit gates pass (`scripts/...:259-265`) | `completed` | `review_required` | `null` | `{path, sha256, ...}` |
| Renderer raises at any step | `failed` | `blocked_render_failed` | first failed step (instrumented) or `null` (post-hoc) | `null` |
| Completed but `output_audit` loudness/probe gate would fail (renderer raises at `:262-265`) | `failed` (audit is a step) | `blocked_audit` | `output_audit` | `null` |
| Completed, gate checks fail (rights/source-verification) | `completed` | `review_required` (`gate_passed: false`) | `null` | `{...}` — video exists but is **not publishable** |

`gate_passed: true` is unreachable in Phase 1 for local renders (rights check `:2231-2237` fails until human confirmation). Any adapter output showing `gate_passed: true` for a local render without `record_human_approval` evidence is a bug.

---

## 4. Fallback spec — Silence / StaticCard / Failed

### 4.1 Phase 1 rule (locked): NO substitution fallbacks

**On any step failure the result is `Failed` and no MP4 is produced.** There is no Silence fallback and no StaticCard fallback in Phase 1. Rationale: a substituted silent track or static card is a *different artifact* from what the script promised; silently producing one would be fabrication (the exact failure mode `rules/06-certification.md` guards against). The CEO Phase 1 success criterion is explicit: "failed render produces NO mp4 and NO review_required claim."

Concretely:

- **No fake MP4.** On failure, `result_record` has no `render.video` (`content_service.py:1642-1652`), the adapter sets `assets.final_video: null`, and no file named `*_rendered.mp4` may exist for that `job_id` (the renderer writes it only at `scripts/...:233, 249` after all phases succeed; partial `voice/*.wav` / `frames/*` / `audio-premix.wav` may remain on disk for debugging but are not deliverables and are never referenced by the adapter).
  - Note on tests: `test_local_media_render_records_cli_and_keeps_publish_gate`'s `fake_pipeline` writes `b"synthetic mp4 placeholder"` (`tests/test_content_mcp.py:670`) — that is a **test double for the completed path**, not a production fallback. Production code must contain no placeholder-byte path.
- **No partial-credit downgrade.** A 5-of-6-scene TTS success is still `failed`. The adapter does not emit a `degraded` video.

### 4.2 Per-step fallback table (normative for any future opt-in)

| Step | `Silence` fallback | `StaticCard` fallback | Phase 1 behavior |
|---|---|---|---|
| `input_validation` | n/a | n/a | **Failed.** Abort before job storage (existing behavior). No fallback concept applies — invalid input cannot be "degraded" into output. |
| `piper_tts` | Replace failed scene's WAV with silence of `scene_seconds`, mark step `degraded`, continue | Replace scene's visual with static card + silence | **Failed (no substitution).** Future design (not Phase 1): requires explicit `fallback_policy: "silence"` on the job manifest, per-scene `fallback_used: true` flags surfaced in the adapter and in `voice_segments`, forced `gate_status: blocked_fallback_used` (never `review_required`), and loudness audit re-run (silent scenes drag LUFS). |
| `synthetic_visuals` | n/a (audio-only) | Static 1080×1920 card for failed scene, mark step `degraded` | **Failed.** Future: same explicit-policy + `blocked_fallback_used` requirements; adapter must list affected scene indexes. |
| `ffmpeg_assembly` | n/a | n/a | **Failed.** No fallback — assembly failure means no muxed output exists. |
| `output_audit` | n/a | n/a | **Failed** (audit failure = step failure, §3.3). Never "pass with warning." |

**Invariant (all rows, all phases):** a fallback, if ever enabled, can never produce `gate_status: review_required`. Degraded output is blocked from human review until a human explicitly accepts the degraded artifact — and that acceptance is recorded via `record_human_approval`, never by the pipeline.

---

## 5. D-certification status & execution routing

- **@architect-songsak: D0** (Head, per `profiles/CERTIFICATION-REGISTRY.md:13`). This document is therefore a **D1-level design** ("why / which-agent / scope"), not an implementation. It contains no code, changes no schema, and passes no gate. Nothing in it may be cited as evidence of a passed D-level.
- **Implementation routing (per CEO decision owners):**
  - @engineering — @changful: fix failed-status semantics (§3.2), add per-step instrumentation (§1.6), `output_audit` independent ffprobe checks, `concurrent=1` + timeout guard. **Requires a D2 plan attached** (50–150-line mini-agent exercising the real tool path, with run output + exit code) before execution work, per registry rule 1.
  - @content-creator-sek: synthetic test campaign + script in supported layout (6×15s). Note: sek holds D1+D2 (registry `:11`); D3 eval is still pending, so high-risk/complex execution remains gated.
  - @qa: independent checker (maker ≠ checker, `rules/06-certification.md`) — targeted tests incl. failure-injection (failed render ⇒ no MP4, no `review_required`), ffprobe/SHA-256/−16 LUFS evidence, re-probe of `assets.final_video` against disk.
- **Phase 1 success (from CEO decision, unchanged):** 1 new local MP4 (ffprobe-verified, SHA-256, ~−16 LUFS, 1080×1920) + Publish Gate `review_required` + human approval NOT recorded + failed render produces NO mp4 and NO `review_required` claim. Status until evidence attached: **NOT PASSED**.
  > **Follow-up (2026-11-07):** the "human approval NOT recorded" criterion above reflects the CEO-decision wording at gate time; since then phase 1 v5 **has** a recorded human approval (`central_bus/content/campaign-campaign_synth_phase1_20261107-approval-v5_20261107T031906146707Z.json`, `gate_passed: false` + 7 overrides, does not publish) while phase 2/3 remain `approved_version: null` — see README §Approval status. D-level status here (NOT PASSED, D3 pending) is unchanged.

---

## 6. What a checker will verify (acceptance checklist, not results)

1. Adapter output for a completed local render shows `pipeline.steps` in the fixed order `input_validation → piper_tts → synthetic_visuals → ffmpeg_assembly → output_audit`, each `status: completed`, `assets.final_video.sha256` matches `render.video.sha256`, `publish_gate.checks` contains R1–R5 verbatim, `provenance` (if the script came from `ingest_client_generated_artifact`) is `client_supplied_unverified`.
2. Adapter output for a **failed** render shows `status: failed`, `gate_status: blocked_render_failed`, `assets.final_video: null`, and no `*_rendered.mp4` exists under that job's output directory.
3. `central_bus/content/` contains no new campaign-manifest entries caused by the adapter; `tests/test_content_mcp.py` passes unmodified (except the new failure-injection test).
4. No adapter field claims `verified` for provenance, loudness, or rights without an independent checker artifact in `bus/evidence/`.
5. No Concat fields (`sound_delivery_filename`, Earshot review linkage) appear in any local-path adapter output.
