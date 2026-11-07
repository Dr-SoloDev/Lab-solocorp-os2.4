# Content Local Media Render

## Scope

`render_campaign_media_local(campaign_id, script_filename=None, tts_fallback=None, visual_fallback=None)`
renders the latest (or, when `script_filename` is given, the pinned) supported
storyboard from generated inputs only: six 15-second scenes (90 seconds) or
ten 10-second episodes (100 seconds). It creates Thai Piper voice segments,
original procedural Three.js scene frames, scene-level ASS captions, a locally
synthesized audio bed, and an H.264/AAC MP4. It records a local CLI job/result
in the campaign manifest and calls the existing Publish Gate. Audio uses
two-pass EBU R128 normalization and measurement of the encoded MP4 stream.

The MP4 and intermediate media are written beneath
`central_bus/content/local_media/<campaign-key>/<job-id>/`. The Bus manifest
stores only JSON metadata and checksums; media binaries are not sent through
the 2 MiB text payload store.

## Prerequisites — MCP must be current before rendering

- **Check `runtime.restart_required` first.** MCP servers load code once at
  startup; "connected" ≠ "current". Confirm the running `content-creator`
  generation is newer than `solocorp_mcp/departments/content_service.py` /
  `content_mcp.py` via `*_department_info()` (`runtime.status == "current"`,
  `restart_required == false`). A stale generation renders from old code and
  cannot be trusted as Phase 3 evidence.
- **Restart stale generations:** `scripts/restart-mcp.sh` (dry-run report by
  default — safe; add `--yes` to kill, `--yes --stale-only` to kill only
  stale). The host respawns a fresh generation on the next tool call.
- **Catalog-drop warning:** `restart-mcp.sh --yes` kills the in-session SoloCorp
  MCP catalog (observed Phase 2: MCP disconnected, catalog lost SoloCorp
  servers in the CEO session). Reopen/reconnect the SoloCorp MCP servers in
  your client before the next render, or use the runbook's documented direct
  service call below as a fallback (same
  `content_service.render_campaign_media_local`) — never treat a dropped
  catalog as a successful restart.

## Installed Engines

- Piper CLI: `/data/venvs/tts/bin/piper`; model files live in
  `tools/piper/models/` and are ignored by Git.
- Piper voice: `th_TH-tsync2-medium`, 22.05 kHz. Its model card states
  CC BY-NC-SA 3.0, non-commercial. Treat resulting audio as an internal draft;
  do not use it in a commercial/public release without a separately cleared
  voice/model.
- AI Animation: sparse checkout at `workers/skills/ai_animation/`, revision
  `3d17ba3`. Phone UI, stacked data cards, and Swiss Shot template references
  are registered in `workers/skills/AI-ANIMATION-REGISTRY.md`. The upstream
  README says “MIT — for educational use only”; campaign rendering uses none
  of its upstream artwork or templates.
- pdoom-video: sparse checkout at `tools/pdoom-video/`, revision `fa164b7`.
  Node.js 24.14.1, npm 11.18.0, TypeScript 7.0.2, Three.js 0.186.1, and
  Playwright Core 1.64.1 are installed under `app/`. The original song, lyrics,
  and audio-analysis assets are excluded; SoloCorp frames are original code.
- FFmpeg/ffprobe: local FFmpeg CLI is used directly. The `ffmpeg-skill` 2.17.1
  package is installed, but its doctor currently returns `ok: false`: the
  selected 7.0.2-static build is older than the first release listed for
  CVE-2026-8461 and lacks `drawtext`. Only internally generated synthetic
  images/audio may be processed until an independent runtime verification
  clears the real-media gate.
- Concat 0.2.8: installed at
  `/home/drsolodev/.opencode/concat/Concat-0.2.8-x86_64.AppImage` and registered
  as `concat --mcp headless` in OpenCode and Codex. **Host caveat
  (2026-11-07):** the AppImage cannot FUSE-mount here (`fusermount3 Operation
  not permitted`, exit 127), so the MCP now runs from the `--appimage-extract`
  tree (`/home/drsolodev/.opencode/concat/squashfs-root/AppRun`, ADR-032
  amendment) — handshake verified 2026-11-07, but `render_campaign_with_concat`
  has never been run on this host (no render proof); local-media render
  (`render_campaign_media_local`) is this host's proven path; fallback if the
  handshake dies = disable (`enabled: true → false` in `opencode.json`).
  `content-creator` calls
  `render_campaign_with_concat`, which creates a native project folder with
  `concat.json`, imports generated media, adds captions, exports H.264 MP4, and
  stores the result manifest/checksum in Central Bus. Project inputs are scoped
  to `central_bus/content/`.
- Earshot 0.4.0: installed in the CPU-only venv at
  `/home/drsolodev/.opencode/earshot/venv-cpu`; the Content MCP sets offline
  mode and exposes audio review, SFX lookup, and SFX rendering as internal
  Sound Designer capabilities. Reports and WAV stems use the Content Central
  Bus store. `sound_delivery_filename` attaches those stems to a Concat
  timeline. The Content MCP never approves or publishes automatically.

> **Concat status (2026-11-07): enabled + handshake verified; render NOT yet
> proven on this host.** History: the AppImage failed to mount (FUSE
> `Operation not permitted`, exit 127; verified Phase 3 kickoff/completion),
> but per ADR-032 **as amended 2026-11-07** the `--appimage-extract` path
> succeeded (`squashfs-root` 362M at `/home/drsolodev/.opencode/concat/`,
> `AppRun` = concat 0.2.8), `concat` MCP is `enabled` in `opencode.json`, and
> the MCP handshake was verified on 2026-11-07 (tools respond;
> `project_list()` → `[]`). **`render_campaign_with_concat` has never been run
> on this host — no render proof exists.** Do not claim Concat rendering works
> here; local-media renders do not need Concat. If the handshake fails, the
> fallback is Option 1 disable (ADR-032). The Concat evidence below
> (2026-10-30) is historical.

## Run

From the repository root:

```bash
source .venv/bin/activate && export PYTHONPATH=.
python - <<'PY'
from solocorp_mcp.departments.content_service import render_campaign_media_local
import json
print(json.dumps(render_campaign_media_local("campaign_solocorp_os_1pt5m_narrative"), ensure_ascii=False, indent=2))
PY
```

Codex and other connected clients can call the same operation through the
`content-creator` MCP tool `render_campaign_media_local`. Optional args:
`render_campaign_media_local(campaign_id, script_filename="<exact file>",
tts_fallback="silence", visual_fallback="static_card")` — fallbacks are opt-in
(default `abort` = fail fast); see Phase 3 Features below.

## Script selection (`script_filename`)

- Omitted (`campaign_id` only): the renderer selects the **latest**
  `video_script` asset in the campaign (existing default behavior).
- Provided (`script_filename="<exact filename>"`): the renderer selects that
  exact asset. It must exist in the same campaign, be type `video_script`,
  and parse to six 15-second scenes or ten 10-second episodes. A bad name,
  a wrong-type asset, or a script from another campaign fails before any
  pipeline run — no render, no MP4.
- **Mandatory checklist:** `create_video_script` creates a 4-scene scaffold
  that fails layout validation. Before rendering, either re-ingest the real
  6-scene/10-scene script so it becomes latest, or pass its ingested
  `script_filename` explicitly.
- Local rendering is **per-scene** (scene-level captions/voice segments).
  Concat (`render_campaign_with_concat`) is **continuous** (one full-length
  narration track). Never feed local-render artifacts into Concat.

The operation refuses unsupported timing layouts, refuses overwrites, and
validates the final MP4 with ffprobe. Its result distinguishes
`audio_mix` (PCM WAV path and checksum) from `audio` (AAC stream embedded in the
MP4). It labels Piper model rights as `human_confirmation_required`; the
Publish Gate remains `review_required` and publishing remains blocked.
Captions are scene-timed from the supplied script, not word-aligned karaoke
captions. The synth bed is a local placeholder, not licensed music.

## Phase 3 Features (2026-11-07)

- **Per-step status (`steps`, 5/5 on success):** `input_validation`,
  `piper_tts`, `synthetic_visuals`, `ffmpeg_assembly`, `output_audit` — each
  records `status` (`running` → `completed`/`failed`), `started_at`,
  `finished_at`, `error`, `message`, `output`, and any
  `fallback_scenes`/`fallback_used`. The service returns `steps` and stores
  them in the result record; a failed run persists `steps` via the exception
  (renderer stderr JSON), so partial progress is visible — not just overall
  `execution_status`.
- **Fallback opt-in + degraded visibility:** `tts_fallback="silence"`
  substitutes a silent buffer per failed Piper scene;
  `visual_fallback="static_card"` substitutes a solid 1080×1920 card per
  failed Three.js scene. Default is `abort` (fail fast, unchanged behavior);
  any other value raises `ContentServiceError` before any job is stored.
  Any fallback use sets `degraded: true` with
  `fallbacks: {tts, visual}` in the result, and the Publish Gate adds the
  failing check `media: local render used fallback (degraded)` — a degraded
  render is never presented as a clean pass; a human must explicitly
  acknowledge it before approval.
- **Concurrent lock:** non-blocking exclusive file lock
  (`.local_render.lock`, `fcntl.LOCK_EX | LOCK_NB` in
  `content_service._local_render_lock`), acquired before any job asset or
  output directory is created and held for the whole render (subprocess +
  gate included). A second caller fails immediately with
  `another local render in progress; wait for it to finish and retry` —
  no queue, no partial output. Concat renders are not covered (separate
  subsystem).
- **Sync report (`sync_report`, per scene):** `voice_duration_sec`,
  `padded_duration_sec`, `drift_ms`, `start_sec`/`end_sec` — proves each
  scene's voice fits its 10/15-second slot (Phase 3 evidence: drift
  `0.0 ms` × 6).
- **Audit bitrate (`output_audit` + `video`):** file existence, size bytes,
  duration, width/height, `bitrate_bps`, integrated LUFS and true peak are
  measured from the encoded MP4 (Phase 3 evidence: `bitrate_bps: 252607`,
  `size_bytes: 2841836`, `-16.0 LUFS`, `-3.0 dBTP`).

## Latest Render Evidence

- Job: `local-media-e15ad3f3b36b4302b31084811c2f8d0b`.
- Output: `central_bus/content/local_media/campaign_solocorp_os_1pt5m_narrative/local-media-e15ad3f3b36b4302b31084811c2f8d0b/campaign_solocorp_os_1pt5m_narrative_rendered.mp4`.
- ffprobe: 90 seconds, 1080×1920, 30 fps, H.264 video, AAC stereo at 48 kHz.
- Measured final audio: `-16.0 LUFS`, `-3.1 dBTP`; configured ceiling is `-1.5 dBTP`.
- Video SHA-256: `5ed410c30f9d57589e719cb3c55cb1a315d4555a9f2ee2ca3451cc272c16959e`.
- Result asset: `campaign-campaign_solocorp_os_1pt5m_narrative-local-media-result_20261029T222334921317Z.json`.
- Post-Gate manifest: `campaign-campaign_solocorp_os_1pt5m_narrative-manifest_20261029T222335213328Z.json`, version `v14`.
- Campaign Publish Gate: `review_required`, `gate_passed: false`; no human approval or publishing was recorded.

## Ordered Content Audio Workflow

> **Concat workflow status (2026-11-07):** MCP handshake verified but the
> render has never been run on this host (see Concat status note above) — do
> not treat `render_campaign_with_concat` as proven here. Use the local-only
> path for renders in the meantime; if the handshake fails, fall back to
> ADR-032 Option 1 (disable).

Use this path for a campaign that needs a custom sound mix. All tools are owned
by `content-creator`; Sound is an internal specialist, not a separate module.

1. Finalize the campaign with `create_video_script`.
2. Create a cue sheet for that exact script with `design_audio_experience`.
   If the script changes, regenerate the cue sheet before continuing.
3. For SFX, query `sound_list_earshot_sfx` as needed, then call
   `sound_render_campaign_sfx`. Keep the returned `sound_delivery_filename`.
   Voiceover is optional and separate; only call paid ElevenLabs generation
   after explicit approval.
4. Call `render_campaign_with_concat` with generated `timeline_media`,
   optional timed captions, and the SFX delivery filename when present. An
   existing Concat project can be resumed with `concat_project_path` and must
   contain `concat.json`. Paths must remain under `central_bus/content/`.
5. Call `sound_review_campaign_audio` on the final mix/video and inspect its
   stored loudness and timeline report. If it needs changes, revise inputs and
   render again; do not continue to approval with a failed or missing review.
6. After audio review, run `review_publish_gate` for the final campaign version.
   The Concat render runs an initial gate automatically; storing the Earshot
   review creates a newer campaign version, so run the gate again after QA.
   Resolve failed checks before requesting approval.
7. After a person reviews the exact version, call `record_human_approval` with
   that version. Any later asset change requires another gate review and
   approval. This workflow records approval; it does not publish.

If an audio stage fails, stop the dependent stages and report the returned
error. Omit SFX only when the brief accepts a no-SFX mix; never silently fall
back to a different sound path. The synthetic-only `render_campaign_media_local`
path is separate and must not be mixed with the Concat workflow.

## Content Creator 60s Concat Evidence — 2026-10-30

- Campaign: `campaign_solocorp_content_creator_60s`; reused the existing
  ElevenLabs v2 voice mix and six-scene picture asset; no voice credits were
  consumed during this render.
- Concat: version `0.2.8`, headless MCP; project:
  `central_bus/content/concat_projects/campaign_solocorp_content_creator_60s/concat-48c2555fc08c4859997eda6ebb1985b5/campaign_solocorp_content_creato-bb1985b5/concat.json`.
- Earshot SFX: `whoosh_fast/tight`, placed at 10.0s, 0.55s duration, timeline
  volume 0.25; clean SFX check, `-24.2 LUFS`, `-9.0 dBTP`, no clipped samples.
  Stem: `central_bus/content/sound/campaign_solocorp_content_creator_60s/sound-sfx-57c2e654757a49ab8ded066c429b644b/sfx.wav`.
- MP4:
  `central_bus/content/concat_renders/campaign_solocorp_content_creator_60s/concat-48c2555fc08c4859997eda6ebb1985b5/campaign_solocorp_content_creato-bb1985b5.mp4`;
  ffprobe: 60.5667s, 1080×1920, 30 fps, H.264 video/AAC stereo 48kHz.
  The source picture already contains Thai captions, so the final project adds
  zero extra caption overlays. SHA-256:
  `5febea15988dee00ec473c3fc62cc4bd4314bc552a9b368c333cf9918788645b`.
- Earshot final review: `-16.0 LUFS`, `-2.3 dBTP`, LRA 15.1 LU, zero clipped
  samples; review report:
  `central_bus/content/campaign-campaign_solocorp_content_creator_60s-sound_review_repo_20261030T065022262645Z.json`.
  Its automated section labels describe the middle mix as “funk music, vocal
  chop”; treat these as model hints and have a person confirm the sound matches
  the proposed restrained/warm cue direction and has cleared music rights.
- Render result:
  `central_bus/content/campaign-campaign_solocorp_content_creator_60s-concat_render_res_20261030T064928760663Z.json`.
  Final Gate: manifest `v16`, report
  `campaign-campaign_solocorp_content_creator_60s-publish-gate-v16_20261030T065039654406Z.md`,
  `review_required`, `gate_passed: false`, `approved_version: null`.
- This is an operational end-to-end run, not independent D3/D4 certification.
  Runtime gate remains pending independent Concat verification; no approval or
  publishing was recorded.

## Origin 10×10 Render Evidence

- Job: `local-media-75418cc936ee498a8e1f9b9a35cc68ef`.
- Script: `campaign-solocorp-origin-10x10s-client-generated-video_script-93_20261029T231301234823Z.md`, version `v35`; audio cue sheet is linked to this script.
- Output: `central_bus/content/local_media/solocorp-origin-10x10s/local-media-75418cc936ee498a8e1f9b9a35cc68ef/solocorp-origin-10x10s_rendered.mp4`.
- ffprobe: 100 seconds, 1080×1920, 30 fps, H.264 video, AAC stereo at 48 kHz.
- Measured final audio: `-16.0 LUFS`, `-3.7 dBTP`; configured ceiling is `-1.5 dBTP`.
- Video SHA-256: `a0cffc5aec6fcdf16ea06aea97f867e5cdb753e04d11e57074c0f1b8c9795c3e`.
- Job/result assets: `campaign-solocorp-origin-10x10s-local-media-job-local-media-7541_20261029T231314118957Z.json` and `campaign-solocorp-origin-10x10s-local-media-result-local-media-7_20261029T231529864292Z.json`.
- Publish Gate report: `campaign-solocorp-origin-10x10s-publish-gate-v38_20261029T231530150888Z.md`; R1–R5 passed, but independent source verification, media rights, and redaction remain `review_required`.
- No human approval or publishing was recorded. Piper `th_TH-tsync2-medium` is non-commercial; this render is for internal review only.

## Phase 3 Render Evidence — 2026-11-07 (MCP, clean `abort`/`abort`)

- Campaign: `campaign_synth_phase3_20261107` (Product synthetic, 6×15s, frozen
  — do not touch assets). Job:
  `local-media-78141119480f4b918c065b17cdf05639`, via MCP (`runtime current`,
  `requested_by: content-creator MCP tool call`, clean `tts_fallback=abort` /
  `visual_fallback=abort`).
- Output:
  `central_bus/content/local_media/campaign_synth_phase3_20261107/local-media-78141119480f4b918c065b17cdf05639/campaign_synth_phase3_20261107_rendered.mp4`;
  ffprobe: 90s, 1080×1920, 30 fps, H.264/AAC stereo 48 kHz.
  Measured final audio: `-16.0 LUFS`, `-3.0 dBTP` (QA ebur128 re-measure);
  `size_bytes: 2841836`, `bitrate_bps: 252607`.
- Video SHA-256:
  `192ba6c5e0b0c74dcd02f262df5f8771e399a8573b220e75e267531f48a7cc32`.
- Steps 5/5 `completed` with timestamps
  (`input_validation`, `piper_tts`, `synthetic_visuals`, `ffmpeg_assembly`,
  `output_audit`); `degraded: false` (`fallbacks.tts/visual.used: false`);
  `sync_report` drift `0.0 ms` × 6; `output_audit` passed (file, duration,
  resolution, bitrate, LUFS/TP).
- Result asset:
  `campaign-campaign_synth_phase3_20261107-local-media-result-local_20261107T050758104106Z.json`.
  Publish Gate `v7`: `review_required`, `gate_passed: false`,
  `approved_version: null`, `published: false` (PASS visual/cue/R5;
  FAIL source/media/R1/R2/R3). No human approval or publishing was recorded.
- Provenance `client_supplied_unverified`, provider/model null; Piper
  CC-BY-NC-SA non-commercial. Frozen Phase 1/2 SHAs unchanged. This is an
  operational E2E run, not independent D3/D4 certification.

## Verification

```bash
source .venv/bin/activate && export PYTHONPATH=.
python -m pytest tests/test_content_mcp.py tests/test_mcp_stdio.py --tb=short --no-header -q --no-cov
```

Latest targeted verification: 65 tests passed on 2026-11-07 (docs-only Phase
4 update; earlier the same day the baseline was 64 — `tests/test_content_mcp.py`
gained 1 test from concurrent working-tree changes; re-run `python -m pytest
tests/test_content_mcp.py tests/test_mcp_stdio.py --tb=short --no-header -q
--no-cov`). This is not independent D1 review, D3 evaluation, or D4
reproduction.

The local renderer's FFmpeg execution is not an FFmpeg-skill MCP result and
must never be sent to `record_ffmpeg_job_result`. Its manifest records
`provider: ffmpeg-cli` and `execution_mode: local_ffmpeg_cli` explicitly.
