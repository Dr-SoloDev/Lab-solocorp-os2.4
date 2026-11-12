# Content Phase 2 — Governed Call Graph (D1 Design)

Status: **D0 / NOT PASSED** — design proposal only. No code changes in this task. No campaign created. v5 `campaign_synth_phase1_20261107` is FROZEN — untouched by Phase 2.

Owner: @architect-songsak (Head of Architect) — pipeline design authority.
Consumers: @changful (engineering fix), @content-creator-sek (E2E run on a NEW campaign), @qa (independent checker).
Source kickoff: `central_bus/content/ceo-phase2-kickoff-20261107_20261107T043215271633Z.md` (2026-11-07).

## 0. Verified reality incorporated

- Skill id is `content-media-production`, not `content-video`. File: `axis_mcp/departments/content_skills/media-production/SKILL.md` (`id: content-media-production`, v1.0.0). Served as MCP resource `axis://content/skills/media-production` via `axis_mcp/departments/content_mcp.py:479` (`content_media_production_skill`) → `content_service.py:2688` `media_production_skill_resource()`. SOP resource at `content_service.py:2656` `sop_resource()` (`axis://content/sop`).
- The skill's "Workflow" section describes the **Concat continuous-narration** workflow (one full-length voice track, `render_campaign_with_concat` as the default for launch/story videos). The **local path** (`render_campaign_media_local`) is a **separate synthetic one-shot** workflow that renders **per-scene Piper segments by design** (`scripts/render_campaign_media_local.py` + `content_service.py:1528+`). Both statements are true; they describe different paths. Agents must not conflate them.
- Governed chain proven in Phase 1 (OpenCode): `ingest_client_generated_artifact` → `create_video_script` → `render_campaign_media_local` → `review_publish_gate` → `record_human_approval` (human only).
- Central Bus is the **data plane** (`central_bus/content/` — payload storage, campaign manifests, render outputs). The Content MCP is the **control plane** (tool contracts, validation, subprocess orchestration, publish gate, approval records). Agents must call governed MCP tools only; the Bus never renders, approves, or publishes.
- Known gap (Phase 1 pitfall): `render_campaign_media_local(campaign_id)` auto-picks the **latest** `video_script` (`content_service.py:1535-1538` — `reversed(campaign assets)` filtered to `type == "video_script"`). `create_video_script` scaffold emits a **4-scene** script (Hook/Context/Example/Close at lines 651-660) which fails the 6×15 validation in `_local_media_scenes` (`content_service.py:1463-1494`, requires `(6,15)` or `(10,10)` contiguous equal-duration scenes). Phase 1 therefore required a **re-ingest** of a 6-scene script. Section 3 fixes this.

---

## 1. Call graph (text diagram) — governed path only

```
External client / agent (Sek, Content Creator head)
  │  human brief / client-generated content (client LLM, human editing)
  │  NEVER: shell, subprocess, ffmpeg/piper/pdoom binaries, submit_to_bus faking render
  ▼
┌─ Content Creator MCP — control plane ───────────────────────────────────────────┐
│ content_mcp.py (tool contracts + resource serving)                              │
│   → content_service.py (validation, campaign manifest, orchestration)           │
│                                                                                 │
│  STEP 1 (optional, pre-production)                                              │
│    ingest_client_generated_artifact(campaign_id, artifact_type, content,         │
│      provenance)                                                    ──► stored  │
│      artifact_type ∈ CLIENT_GENERATED_ARTIFACT_TYPES (content_service.py:47)   │
│      provenance_status = client_supplied_unverified (content_service.py:1911)  │
│                                                                                 │
│  STEP 2   create_video_script(title, core_message, duration_seconds,             │
│            campaign_id, source_references) ──► 4-scene scaffold (lifecycle)     │
│  STEP 3   design_visual_prompt(theme, platform, aspect_ratio, campaign_id)      │
│  STEP 4   design_audio_experience(campaign_id, script_filename)                │
│            (rule-based cue sheet derived from the EXACT script; content-        │
│             service.py:1699 — never calls an LLM or provider)                   │
│                                                                                 │
│  STEP 5   render_campaign_media_local(campaign_id, script_filename?)            │
│            (content_service.py:1528; Phase 2 adds optional script_filename — §3)│
│              │ subprocess.run (content_service.py:1497-1525, 60-min cap)        │
│              ▼                                                                  │
│  ┌─ Local CLI — engine (NOT agent-callable) ────────────────────────────────┐  │
│  │ scripts/render_campaign_media_local.py  (stdin JSON → stdout JSON)       │  │
│  │   • scripts/local_tts_piper.py  (Piper, th_TH-tsync2-medium, per scene) │  │
│  │   • scripts/render_pdoom_scenes.mjs (Three.js/pdoom synthetic frames)    │  │
│  │   • FFmpeg/FFprobe (mix, loudnorm 2-pass −16 LUFS / −1.5 dBTP, captions,  │  │
│  │     zoompan, verify 1080×1920 + duration + SHA-256)                     │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│            │ job manifest + result record stored as campaign assets             │
│            ▼                                                                    │
│  STEP 6   review_publish_gate(campaign_id, filename) ──► gate report,           │
│            status review_required, approval_required=true, published=false     │
│  STEP 7   record_human_approval(campaign_id, version, approver_note)           │
│            HUMAN ONLY. Sets status=approved. NEVER publishes.                  │
└───────────────────────────────────────────────────────────────────────────────┘
  │ data plane only — payloads, manifests, MP4 bytes, SHA-256, ffprobe results
  ▼
Central Bus: central_bus/content/
  campaign manifests · asset payloads (*.md/*.json) · local_media/<campaign>/<job>/ (frames, voice/, *.mp4)
```

### What each layer is / is not

| Layer | Role | May do | Must NOT do |
|:------|:-----|:-------|:------------|
| External agent (Sek) | Orders work via governed tools; records decisions | Call MCP tools in the order above; capture filenames/hashes; stop and report blockers | Direct subprocess; call Piper/FFmpeg/pdoom itself; write payloads via `submit_to_bus` to fake a render; approve or publish |
| content-creator MCP | Control plane: validation, campaign manifest, ordering, orchestration, gate | Validate inputs; run `_execute_local_media_pipeline` subprocess; store job/result records; return `review_required` | Never approve on the agent's behalf; never publish; never mix local-path artifacts into Concat |
| `render_campaign_media_local.py` + Piper/pdoom/FFmpeg | Engine: deterministic local rendering | Read stdin JSON payload; write isolated `output_dir` inside `central_bus/content`; emit JSON result with SHA-256 + ffprobe + EBU R128 | Never accept agent-injected shell commands; never write outside the isolated job dir; never approve work |
| Central Bus | Data plane: durable storage, audit trail | Store bytes + manifests; serve `fetch_from_bus`; retain payloads after `remove_campaign_asset` | Never render, approve, or publish; never serve as a substitute for a tool call |

### Forbidden shortcuts (QA checks for these)

1. **Direct subprocess by agent** — Sek runs `scripts/render_campaign_media_local.py`, `piper`, `ffmpeg`, `node render_pdoom_scenes.mjs`, or any `subprocess` itself. Forbidden: the only legal subprocess invocation is from `content_service._execute_local_media_pipeline`.
2. **Direct FFmpeg/Piper/Pdoom by agent** — any agent-side `ffmpeg -i …`, Piper TTS call, or pdoom render. Forbidden; FFmpeg-skill bridge (`build_ffmpeg_job_manifest` / `build_ff_tracking_manifest`) only *stores a plan* and never executes — it is not the local executable.
3. **`submit_to_bus` faking a render** — the agent writes an MP4/manifest JSON directly to `central_bus/content/` to simulate `render_campaign_media_local`. Forbidden: render outputs must arrive via the service's `_store_assets` job/result records with `execution_status`, SHA-256, ffprobe and loudness evidence.
4. **Concat mixing** — feeding local-path MP4/frames/audio into `render_campaign_with_concat`, or feeding Concat outputs into the local path. Forbidden (skill §Route Selection + SOP §ordered workflow). Phase 2 uses the local path only; Concat tools are out of the Sek E2E run.
5. **Auto-approval / auto-publish** — Sek calls `record_human_approval` itself or treats `review_publish_gate` as approval. Forbidden: `record_human_approval` is human-only (Phase 2 does not include it at all), and the MCP never publishes.

These mirror the existing MCP instructions (`content_mcp.py:65-99`) and SOP ("`render_campaign_media_local` is a separate synthetic-only path; do not mix its artifacts or steps with the Concat workflow").

---

## 2. Skill role clarification — guidance vs engine, naming, narration difference

### Role split

- **Skill = guidance/checklist for the agent.** `SKILL.md` (`content-media-production`) tells the agent *what order to work in, which route to pick, what to check, when to stop*. It produces no artifacts and calls no tools. The agent **reads** it (`axis://content/skills/media-production`) before production work; the agent does not "run" it.
- **Engine = `content_service` + CLI script.** `content_service.py` owns validation, campaign manifests, the subprocess call, publish-gate logic, and approval records. `scripts/render_campaign_media_local.py` owns media rendering (Piper → pdoom frames → FFmpeg mix/captions/verify). The skill never renders; the engine never interprets narrative intent.

Consequence: if the skill and the code disagree, the **code's validated behavior wins for this campaign** and the discrepancy is a documentation defect to file (Phase 4 cleanup), not a reason for the agent to improvise an engine change.

### Correct naming (use everywhere)

- Id: **`content-media-production`** (never `content-video`).
- Resource: **`axis://content/skills/media-production`** — served by `content_media_production_skill` (`content_mcp.py:479`).
- SOP resource: `axis://content/sop` (`content_service.py:2656`). Both use the same name in docs, runbooks, and code comments.

### Per-scene (local) vs continuous (Concat) — do not "fix" either

| Property | Local path (`render_campaign_media_local`) | Concat path (`render_campaign_with_concat`) |
|:---------|:------------------------------------------|:-------------------------------------------|
| Status | Separate synthetic one-shot preview path | Default for launch/story videos needing an editable project |
| Narration model | **Per-scene segments by design**: one Piper WAV per scene (`scene-01.wav` … `scene-06.wav`), each padded/trimmed to its scene slot, concatenated in the mix (`render_campaign_media_local.py:145-160, 169-198`) | **One continuous full-length voice track** spanning the whole story, starting at 0s (SKILL.md Workflow §2, Continuity Check) |
| Scene shapes | Only 6×15s or 10×10s contiguous equal-duration scenes (`_local_media_scenes`, `content_service.py:1492`) | Script-timed captions/edits; duration chosen by the project, not hardcoded to 6×15 |
| Visuals | Three.js/pdoom synthetic frames (1 per scene, zoompan) | Generated visual tracks supplied by the agent |
| Output | `{campaign}_rendered.mp4`, 1080×1920, −16 LUFS ±0.5, ≤ −1.5 dBTP, SHA-256 + ffprobe JSON | Concat project assembly + MP4 export, `review_required` |
| Rule | Local-path artifacts must never enter Concat, and vice versa | Narration continuity is judged by the skill's Continuity Check, not by scene splits |

Agent anti-patterns this resolves:

- **Do NOT "fix" the local path to continuous narration** — its per-scene Piper segments are the feature (fast synthetic storyboard preview with per-scene retry and per-scene slot checks, e.g. "scene 3 voiceover exceeds its 15s slot" at `render_campaign_media_local.py:156-159`).
- **Do NOT "fix" the Concat path to per-scene files** — Concat exists for voice continuity and re-editability; splitting into short scene files would fail the skill's Continuity Check by definition.
- When writing a runbook, always name the path first ("Phase 2 = local path, 6×15s, per-scene Piper") before quoting skill steps, so readers do not import Concat continuity rules into the local run.

---

## 3. Script-selection governance — decision and contract

### Problem restated

`render_campaign_media_local(campaign_id)` (`content_service.py:1528`) resolves the script as "the latest `video_script` asset" (line 1535). `create_video_script` scaffold (`content_service.py:651-666`) always emits 4 rows (Hook/Context/Example/Close) regardless of `duration_seconds`, which can never satisfy `_local_media_scenes`' `(6,15)` or `(10,10)` shape check (line 1492). Phase 1 worked around this by re-ingesting a hand-written 6-scene script after the scaffold failed — silently depending on asset ordering ("latest wins" is load-bearing and invisible in the call).

### Decision: (a) backward-compatible optional `script_filename` param

Adopt option **(a)** — add an optional `script_filename` parameter to `render_campaign_media_local`. Reject option (b) (runbook-only checklist) because a checklist cannot fix the root cause: with "latest wins", any later scaffold creation (or a second Sek action) silently changes which script renders, and the agent has no way to pin its intended script. A mandatory checklist step ("re-ingest after scaffold") would institutionalize the Phase 1 hack and keep the ordering hazard. Parameter pinning removes the hazard at the interface while remaining backward-compatible.

### Backward compatibility argument (Codex)

`script_filename` is **optional, defaulting to current behavior**. Every existing call `render_campaign_media_local(campaign_id)` — including Codex clients that only pass `campaign_id` — behaves exactly as today (latest `video_script` wins). No schema break: campaign manifest shape unchanged; the new param is additive on the MCP tool and the service function. Old clients never send it and are unaffected; new clients gain determinism. This is the same additive-optional pattern already used elsewhere in the tool (`review_publish_gate` already accepts optional `filename` alongside `campaign_id`).

### Exact contract (for @changful to implement, D2 scope)

Service: `render_campaign_media_local(campaign_id: str, script_filename: str | None = None) -> dict`
MCP tool: `render_campaign_media_local(campaign_id: str, script_filename: str = "") -> str` (empty string ≡ absent, matching the existing `campaign_id or None` pattern at `content_mcp.py:399-405`).

Resolution rules, in order:

1. **If `script_filename` is provided (non-empty after strip):** it MUST identify an asset already in this campaign's manifest with `type == "video_script"` (reuse the exact lookup shape from `_campaign_script` / `design_audio_experience`, `content_service.py:741-759`). If not found or wrong type → raise `ContentServiceError` (`"script_filename must identify a video script in this campaign"`). No fallback to latest. The script content is then parsed by the existing `_local_media_scenes` (shape check unchanged).
2. **If absent/empty:** current behavior is preserved byte-for-byte — pick the latest `video_script` asset in `reversed(campaign assets)` (`content_service.py:1535`); if none → `ContentServiceError("campaign has no video script to render")`.
3. **Job manifest:** record the actually-used script explicitly as today (`script_filename`, `script_version` at `content_service.py:1573-1574`) so provenance/audit shows which script rendered, whichever resolution path was taken.
4. **No other behavior changes:** same isolated `output_dir` under `central_bus/content/local_media/<campaign>/<job>`, same 60-minute subprocess cap, same failure cleanup (partial MP4 deleted), same `review_required` return shape, same `published: False`.
5. **Docs accompanying the change:** tool docstring states the default ("omit to render the latest video script (legacy behavior)"); runbook updates the Sek E2E to pass the pinned filename returned by the re-ingest/`create_video_script` call.

### Test cases (acceptance for the fix)

| # | Input | Expected |
|:--|:------|:---------|
| T1 | `render_campaign_media_local(campaign_id)` with exactly one valid 6-scene script (legacy) | Renders that script; manifest records its filename/version. **Unchanged from today.** (Regression guard for Codex.) |
| T2 | `render_campaign_media_local(campaign_id, script_filename="<6-scene file>")` where campaign also has a newer 4-scene scaffold | Renders the **pinned 6-scene** script; no error. (The Phase 1 pitfall, fixed.) |
| T3 | `script_filename="<4-scene scaffold>"` | `ContentServiceError` from `_local_media_scenes` shape check (6×15 / 10×10 only); campaign stays `review_required`/`failed` with partial MP4 removed. No fallback to another script. |
| T4 | `script_filename="<nonexistent>"` or names a `visual_prompt`/non-script asset | `ContentServiceError("script_filename must identify a video script in this campaign")`; no job manifest created. |
| T5 | `script_filename=""` (empty string, omitted path) | Treated as absent → resolves as T1. (Codex clients sending `""` keep working.) |
| T6 | Campaign with no `video_script` at all, param absent | `ContentServiceError("campaign has no video script to render")` (existing error, preserved). |
| T7 | Two sequential ingests (6-scene, then 4-scene scaffold); call with param naming the 6-scene file | Renders the 6-scene file even though it is not "latest". Proves pinning beats ordering. |

Sequential rendering also verifies the frozenset: T2/T7 must never touch `campaign_synth_phase1_20261107` — run all cases on a scratch campaign id.

---

## 4. Provenance contract per step

Rules (derived from `content_service.py:320-351` `_validated_provenance`, `1876-1915` ingest, `1546-1559` Piper rights, `2547+` approval):

| Step | Provenance recorded | Provider / model | Rights / human gate |
|:-----|:-------------------|:-----------------|:--------------------|
| `ingest_client_generated_artifact` | `provenance = {client, provider, model}` — `provider`/`model` default `null` unless the client actually supplies them (`_validated_provenance`, line 336-338); stored `provenance_status = client_supplied_unverified` (line 1911). Secrets in any field are rejected (line 346-349). | `provider: null`, `model: null` unless client-supplied; the MCP **never calls an LLM** on this route (`client_supplied_unverified` everywhere, incl. publish gate at line 2368). | `lifecycle_state = client_generated`; counts as unverified at the gate until a human confirms. |
| `create_video_script` / `design_visual_prompt` | `source_references` if any; `lifecycle_state = scaffold`. | No provider called; template-generated. | Scaffold until human edits via `save_human_edited_artifact` (`llm_generated`/`human_edited` transitions). |
| `design_audio_experience` | Derived from the **exact** script file named (cue sheet is a function of that script). | No provider; rule-based (line 1699). | Regenerate whenever the script changes. |
| `render_campaign_media_local` | Job + result records: `provider: ffmpeg-cli`, `tts_provider: piper-local`, `visual_provider: three.js-pdoom-local`; `local_only: true`, `network_used: false`, `synthetic_inputs_only: true`; SHA-256 + ffprobe + EBU R128 measurements. | `tts_provider: piper-local` — **never "ElevenLabs"** on this path; Piper model `th_TH-tsync2-medium` + license from `tools/piper/model-rights.json` (line 1546). No cloud TTS in Phase 2. | `media_rights_status = human_confirmation_required` / `voice_model_rights_status = noncommercial_only_human_confirmation_required` (line 1555-1559; Thai model CC BY-NC-SA 3.0, internal/non-commercial). Publication blocked until human rights review. |
| `review_publish_gate` | Gate report persisted to bus; `gate_passed` boolean; checks for secrets/redaction/rights. | n/a | Status remains `review_required`; `approval_required: true`; `published: false`. A report is **not** an approval. |
| `record_human_approval` | `approver_note` + exact `version` (e.g. `v3`); approval record stored; `status = approved` only if `version == current version` (lines 2564-2566). | n/a | **Human only.** Any later asset change bumps the version and resets review/approval; a new review + approval is required. Never publishes. |

Phase 2 E2E outcome: campaign ends at **`review_required`** (Step 6). Step 7 is out of scope for Sek entirely; `approved_pending_separate_publish_step` may occur only if a human later approves — not in this phase.

---

## 5. What Phase 2 does NOT include

- **Generic durations** — only 6×15s and 10×10s local shapes (`_local_media_scenes` line 1492). Arbitrary `duration_seconds` (e.g. 60s) still templates a 4-scene scaffold that cannot render locally.
- **Concurrent jobs** — no parallel campaign rendering, no queueing/backpressure design; one job per call, isolated output dir per job.
- **Failure fallbacks** — no silent fallback to another script, engine, or path on failure (stop + report, per skill Stop Conditions); Phase 3 designs fallback policy.
- **Doc cleanup** — reconciling skill text vs code behavior (e.g. Concat-leaning Workflow prose vs local-path prose) and fixing stale references (`content-video` remnants) is Phase 4.
- **Publishing** — no publish tool, no upload, no `record_human_approval` by the agent. Publication requires a separate human approval step after Phase 2's `review_required` gate.

---

## D1 acceptance (for QA)

1. This document exists at `docs/plans/CONTENT-PHASE2-GOVERNED-CALL-GRAPH.md` with sections 1–5.
2. Call graph names all 7 tools in order and marks all 5 forbidden shortcuts.
3. Skill id spelled `content-media-production` everywhere; resource path correct; per-scene vs continuous stated explicitly.
4. §3 picks option (a), gives the exact param contract plus 7 test cases, and argues Codex backward compat.
5. §4 provenance table includes `client_supplied_unverified`, `provider/model: null`-unless-real, and Piper `human_confirmation_required`.
6. §5 exclusions present; document states **D0 / NOT PASSED**; **no code changed** (verify `git status` clean for `axis_mcp/`, `scripts/`, `central_bus/`); v5 `campaign_synth_phase1_20261107` untouched (no bus writes for that campaign id since 2026-11-07 kickoff except reads).

D1 verdict: **NOT PASSED** until @qa confirms items 1–6. D2 (the `@changful` fix) and D3 (Sek E2E) require this D1 to be accepted first.
