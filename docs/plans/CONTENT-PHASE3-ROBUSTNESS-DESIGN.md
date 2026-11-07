# Content Phase 3 — Robustness Design (D1)

> **Status: DESIGN ONLY — NOT IMPLEMENTED, NOT PASSED.** Author: @architect-songsak (Head of Architect).
> Certification: D0 as Head per `profiles/CERTIFICATION-REGISTRY.md` ("every Department Head — still no level passed"). This document is a **D1-level design** (why / which agent / scope). Implementation MUST go via @engineering — @changful with a D2 plan attached (50–150-line agent calling real tools, with run output + exit code), per `rules/06-certification.md`. No claim of "done" without evidence. Default status until evidence attached: **NOT PASSED**.
> CEO kickoff: `central_bus/content/ceo-phase3-kickoff-20261107_20261107T045253438843Z.md` (Phase 3 = local-media ONLY; at kickoff Concat MCP was down — FUSE `Operation not permitted`, exit 127; **2026-11-07 update:** extract path succeeded + MCP handshake verified per ADR-032 amended, render still unproven). This doc does not supersede the kickoff; it locks the contracts the kickoff leaves open (fallback artifact specs, lock mechanism, per-step keys, bitrate threshold, degraded gate fields).
> Frozen campaigns — **DO NOT touch assets**: `campaign_synth_phase1_20261107` v5 (approved), `campaign_synth_phase2_20261107` v7 (review_required). Phase 3 E2E uses new `campaign_synth_phase3_20261107`. Degraded-mode proof uses a separate test campaign or test-level injection only.
> No code changes in this work. No approval, no publish, no Concat in Phase 3.

## 0. Why, who, scope

**Why:** The local renderer is monolithic and fail-fast: `scripts/render_campaign_media_local.py::render()` (L104–313) runs input validation → Piper per-scene (any fail aborts) → Three.js (any fail aborts) → `silenceremove`+`apad` per scene → concat+mix → loudnorm 2-pass → video assemble + burn ASS → ffprobe verify. The service layer (`solocorp_mcp/departments/content_service.py::render_campaign_media_local`, L1528+, `_execute_local_media_pipeline` L1497, subprocess `timeout=3600`) cleans partial MP4s, sets `execution_status=failed`, gate `blocked_render_failed`, and refuses approval after a failed render (Path A — already done, do not redo). What is missing: no opt-in degraded path, no concurrent lock (per-dir existence check only at renderer L123–124), no per-step status (overall `execution_status` only), no fallbacks, no sync report beyond `voice_segments` durations, no size/bitrate audit. Phase 3 makes the pipeline *usable in real work without breaking easily* without weakening the fail-fast default.

**Who:** @architect-songsak (this D1) → @changful (implement, D2-gated) → @content-creator-sek (E2E on new campaign via MCP) → @qa (independent checker, maker ≠ checker).

**Scope (locked by kickoff):** (1) opt-in fallbacks, default ABORT; (2) concurrent=1 file lock; (3) per-step status additive keys; (4) complete output audit incl. bitrate; (5) timestamp sync report; (6) `simple_edit` DEFERRED (§6). **Non-goals:** Concat path, word-level karaoke captions, schema_version bump, new asset types, touching frozen campaigns, any auto-approval/publish.

**Relationship to Phase 1 manifest adapter** (`docs/plans/CONTENT-MANIFEST-ADAPTER-PHASE1.md`): that adapter is a *read-only projection* over existing `schema_version: 1` job/result assets (`local_media_render_job` / `local_media_render_result`). Phase 3 instrumentation (§3) is exactly the "new instrumentation required" its §1.6/§4.2 anticipated — per-step attribution, partial `voice_reports` on failure, `failed_step`. Phase 3 does **not** replace the adapter; it makes the adapter's `post_hoc_aggregate` derivation honest for new renders. Old renders (Phase 1/2) keep `derivation: post_hoc_aggregate`.

---

## 1. Failure policy

### 1.1 Principles

1. **Default = ABORT (fail fast, no fake/degraded success).** Unchanged from today. Any step failure with fallbacks OFF ⇒ `execution_status=failed`, no MP4 left in the job dir (existing partial cleanup `content_service.py:1692–1699`), gate `blocked_render_failed`, approval refused. A fallback is never applied silently.
2. **Fallbacks are opt-in, per-step, explicit.** Two independent flags (§1.2). A degraded render is a *different artifact* from what the script promised and must be visible in every record and gate output (§1.5). It can never present as clean `gate_passed`.
3. **No fallback for `input_validation`, `ffmpeg_assembly`, `output_audit`.** Invalid input cannot be degraded into output; assembly/audit failure means no trustworthy muxed output exists. These always abort (§1.2).
4. **Every failure is logged complete:** step name, error type, message (≤1600 chars, existing truncation), no fake file path. On failure the step's `output` is `null` (§3).

### 1.2 Opt-in flags and per-step table

Flags flow: MCP tool → `render_campaign_media_local(campaign_id, script_filename=None, tts_fallback=None, visual_fallback=None)` (new optional kwargs, defaults OFF) → renderer payload keys `"tts_fallback"` / `"visual_fallback"` → recorded in `job_manifest["fallback_policy"]` (§3.3). Validation: `tts_fallback ∈ {None, "silence"}`, `visual_fallback ∈ {None, "static_card"}`; any other value ⇒ `ContentServiceError` before job storage. No other fallback values exist in Phase 3.

| Step | Default (flags OFF) | Opt-in fallback | Fallback trigger |
|:-----|:------------------|:----------------|:-----------------|
| `input_validation` | **Abort.** `ContentServiceError` before any job stored (existing: script selection + `_local_media_scenes()` L1591–1594, rights read L1596–1609). No MP4, no result asset. | *None. No fallback concept applies.* | n/a |
| `piper_tts` | **Abort** on Piper non-zero exit, missing/invalid WAV, or `voice_duration > scene_seconds` (renderer L147–159). Partial `voice_reports` preserved in steps (§3). | `tts_fallback="silence"`: replace *that scene's* WAV with a silent buffer (§1.3.1), continue with remaining scenes. Other scenes unaffected. | Piper failure for scene *i* only. |
| `synthetic_visuals` | **Abort** on Three.js non-zero exit or frame-count/file mismatch (renderer L162–167). | `visual_fallback="static_card"`: replace failed scene's frame with a static card (§1.3.2). Two sub-cases: (a) node call fails outright → cards for **all** scenes; (b) node succeeds but frame *i* missing/invalid → card for scene *i* only. | Node failure or per-frame miss. |
| `ffmpeg_assembly` | **Abort** on any FFmpeg failure: silence-pad (L169–178), concat+mix (L180–198), loudnorm 2-pass (L199–225), video assemble+ASS burn (L231–249), or mixed-audio duration ≠ expected ±0.05s (L226–229). | *None.* | n/a |
| `output_audit` | **Abort** on any audit check failure (§4). Audit failure = step failure (`failed_step=output_audit`), MP4 removed by existing partial cleanup, `gate_status=blocked_render_failed`. Never "pass with warning" — except the single *advisory* bitrate floor (§4.3), which by design does not change status. | *None.* | n/a |

Interaction: `tts_fallback` and `visual_fallback` are independent; either or both may be on. If both are on and both fire, `fallback_scenes` is the sorted union. Fallback in one step does **not** relax any other step's checks — e.g. a silence-fallback render still runs the full loudnorm 2-pass, full video assembly, and the full §4 audit including LUFS/TP. (Silence drags integrated loudness; loudnorm re-normalises the mix, so LUFS may still pass — the audit must *measure*, not assume. If it fails, the render fails even though a fallback was used.)

### 1.3 Exact fallback artifact specs

#### 1.3.1 Silent WAV (`tts_fallback="silence"`)

One file per failed scene, in the existing job `voice/` dir, named `scene-{NN:02d}-silent.wav` (1-indexed, zero-padded — same convention as `scene-{NN:02d}.wav` L146 and `scene-{NN:02d}-padded.wav` L171). It is an *intermediate*, never a campaign asset.

| Property | Value | Why |
|:---------|:------|:----|
| Format | WAV, PCM signed 16-bit little-endian (`pcm_s16le`) | Matches the padded-voice format the downstream filter expects (L175: `-ar 48000 -ac 2 -c:a pcm_s16le`). |
| Sample rate / channels | **48000 Hz, stereo (2 ch)** | Same as padded voices and `audio-mix.wav`. A silent buffer at the final format makes the downstream `silenceremove`+`apad`+`atrim` pass (L172–176) idempotent and avoids a resample stage that could shift timing. |
| Duration | **Exactly `scene_seconds`** (15.0s for 6×15, 10.0s for 10×10) = `scene_seconds × 48000` frames per channel | Fills the scene slot exactly; `apad`/`atrim` then leave it untouched. Total render duration is preserved. |
| Content | Digital silence (all samples 0), RMS = 0 (−∞ dBFS), no DC offset, no dither | Unambiguous "no voice" signal; QA can verify with `wave` module (frames count + `max(abs(samples)) == 0`). |
| Generation | FFmpeg `anullsrc` (or Python `wave` module writing zero frames) — implementer's choice, but output must satisfy the table above. No network, no model. | Deterministic, no new failure surface. |
| Downstream note | The existing `silenceremove` filter on an all-silence input must be verified by @changful's D2 run: `apad=pad_dur={scene_seconds},atrim=duration={scene_seconds}` guarantees `padded_duration == scene_seconds` regardless of what `silenceremove` trims. If the D2 run shows a problem, the fallback file bypasses `silenceremove` (flagged in `voice_segments` entry) — it must never produce a padded file ≠ slot duration. | Prevents the fallback from introducing a *new* timing bug. |
| Sync-report entry | `voice_duration_seconds = scene_seconds`, `fallback_used = true`, `fallback_kind = "silence"` (§5) | The sync report must show the silence explicitly, not pretend Piper ran. |

The original failed WAV (if any partial file exists) must not be consumed downstream; only the silent buffer enters `voices[]`.

#### 1.3.2 Static card (`visual_fallback="static_card"`)

One PNG per failed scene, in the existing job `frames/` dir, named to match the frame-slot convention the renderer expects (`frames[]` resolved paths, L165–167) — i.e. the fallback PNG occupies the failed scene's slot in `frames[]` so L234–249 (looped input → `zoompan` → concat → ASS burn) runs unchanged.

| Property | Value | Why |
|:---------|:------|:----|
| Format / size | PNG, **exactly 1080×1920** | The `-loop 1 -t {scene_seconds}` input + `zoompan ... :s=1080x1920` (L236–240) expects a full-frame image; 1080×1920 input makes zoompan a no-op scale and guarantees the audit's 1080×1920 check passes for the right reason. |
| Generation | FFmpeg `color` source, single frame: `color=c=0x111111:s=1080x1920:r=1:d=1` (dark grey) → PNG. **Plain colour only — no `drawtext`, no font dependency.** | Deterministic offline generation. A font-dependent path would introduce a new failure mode (missing font ⇒ fallback fails ⇒ abort) in the very code meant to *prevent* aborts. Dark grey (not pure black) is distinguishable from a letterboxed/black scene and from a missing-frame artefact. |
| Caption text | **None baked into the PNG.** Scene captions are preserved via the existing ASS burn (L231–243, `subtitles=...:force_style=...Alignment=2,MarginV=260`) which runs over the card exactly as over a Three.js frame. | Captions remain scene-level ASS (§5); baking text into the card would duplicate the caption and risk font/render failures. The card is a visual placeholder, not a caption carrier. |
| Verification | Implementer verifies PNG dimensions (1080×1920) before inserting into `frames[]`; a wrong-size card is a `synthetic_visuals` failure, not a silent pass. | Prevents a malformed fallback from corrupting assembly. |
| Sync-report entry | `fallback_used = true`, `fallback_kind = "static_card"` for that scene (§5) | Same visibility rule as §1.3.1. |

**Whole-visuals sub-case (a):** the Three.js call is a single node invocation for all scenes (L162). If it fails and `visual_fallback="static_card"`, generate cards for **all** scenes and continue; `fallback_scenes = [1..scene_count]`, step status `degraded`. There is no per-scene retry of the node call in Phase 3.

### 1.4 Manifest / result recording of fallbacks

Fallback facts are recorded in the *result* record (authoritative) and summarised in the *job* manifest's plan (§3.3). Exact additive keys (all present, defaults when no fallback fired):

- `result_record["steps"]["piper_tts"]["fallback_used"]` / `["synthetic_visuals"]["fallback_used"]`: `bool`.
- `result_record["steps"][...]["fallback_scenes"]`: `list[int]`, 1-indexed, sorted ascending, `[]` when unused (schema-stable; never omit the key).
- `result_record["fallback_used"]`: `bool` — OR across both steps.
- `result_record["fallback_scenes"]`: `list[int]` — sorted union across steps.
- `result_record["degraded"]`: `bool` — identical to `fallback_used` in Phase 3 (kept as a separate key so gate semantics (§1.5) read one flag; if a future phase adds non-fallback degradation, `degraded` can diverge without renaming).
- `result_record["render"]["fallback_used"]`, `["render"]["fallback_scenes"]`, `["render"]["degraded"]`: same values copied inside the renderer dict, so the renderer dict is self-describing without the service wrapper.
- Per-scene: `render["voice_segments"][i]` gains `fallback_used: bool` + `fallback_kind: "silence"|null` (existing Piper entries get `false`/`null`); `render["sync_report"][i]` gains the same (§5). Existing `voice_segments` keys are unchanged.
- Step `message` on a fallback: e.g. `"Piper scene 3 failed (<error type>); silent buffer substituted (tts_fallback=silence)"` — names the original error, never hides it. The original error type/message is preserved in the step's `error` field even on the degraded (non-failed) path.

### 1.5 Gate semantics for a degraded render (exact fields)

A degraded render **exists** (MP4 on disk, audit passed) but is **not a clean pass**. The design reuses the existing failed-render pattern (`local_render_failed` forces `gate_passed=False`, `approved_for_version=False`, `publish_action=blocked_render_failed` at `content_service.py:2388–2396, 2467–2475`) with a *distinct* degraded branch, so the three states (clean / degraded / failed) are never conflated:

| Surface | Clean render | Degraded render (`fallback_used=true`) | Failed render |
|:--------|:------------|:---------------------------------------|:--------------|
| `execution_status` | `completed` | **`completed`** (unchanged — `_latest_local_render_failed` treats only `failed` as failed, L2145; inventing `completed_degraded` would break that and every existing reader) | `failed` |
| `result_record["degraded"]` | `false` | `true` | `false` (no render) |
| `_review_campaign` new check | — | `{check: "local render degraded (fallback_used)", ok: false, detail: "fallback_scenes=[...]; human approval must explicitly acknowledge degraded render"}` appended to `checks` | existing failed branch (unchanged) |
| `review["gate_passed"]` | computed normally (`all(checks ok)`) | **`false`** — forced, exactly like `local_render_failed` (L2389–2391). The degraded check's `ok:false` already makes `all(...)` false; the explicit force is belt-and-braces so a future check-list refactor cannot accidentally pass a degraded render | `false` (existing) |
| `review["status"]` / tool `status` | `review_required` (existing) | **`review_required`** (kickoff requirement: degraded = review_required, not blocked, not approved) | `failed` (existing Path A) |
| `review["publish_action"]` | `blocked_until_human_approval` (existing) | **`blocked_degraded_render`** (new, distinct from `blocked_render_failed` and `blocked_until_human_approval`) | `blocked_render_failed` (existing) |
| `review["degraded"]` | `false` | **`true`** | `false` |
| `review["fallback_used"]` / `review["fallback_scenes"]` | `false` / `[]` | `true` / `[…]` (copied from latest completed result record) | `false` / `[]` |
| `review["overrides_degraded"]` | `false` | `false` before approval; `true` after an acknowledging approval (§1.5.1) | `false` |
| `gate_passed` after approval | preserved (existing: approval never flips it) | **still `false`** — approval records the override, it does not rewrite history | n/a (approval refused) |

**How the gate finds the degraded flag (implementer contract):** `_review_campaign` reads the latest `local_media_render_result` asset (same iteration as `_latest_local_render_failed`, L2129–2149) and, when its `execution_status == "completed"`, reads `degraded` / `fallback_used` / `fallback_scenes` from the stored record (asset metadata first, JSON body as fallback — mirror the existing `status is None` pattern at L2134–2144). It must **not** infer degradation from the tool's top-level `status` string. The gate report markdown (`report_lines`, L2404+) gains a line: `- **Degraded:** yes — fallback_scenes=[...]; gate_passed is false and approval requires explicit degraded acknowledgement.` when degraded.

#### 1.5.1 Human override — exact field and refusal rule

`record_human_approval` gains one new optional parameter (additive, backward-compatible):

```
record_human_approval(campaign_id, version, approver_note, acknowledge_degraded=False)
```

- **Refusal rule:** if the latest local render for the campaign is degraded and `acknowledge_degraded is not True`, raise `ContentServiceError("degraded local render requires explicit degraded acknowledgement: pass acknowledge_degraded=true to approve this exact version")`. This sits alongside the existing failed-render refusal (L2633–2636) and the Concat-readiness refusal (L2627–2632). A degraded render is *approvable* (unlike a failed render) — but only with the explicit flag. The `approver_note` alone is **not** sufficient (free-text notes cannot be machine-checked and would let a copy-pasted note silently approve degradation).
- **Approval record (exact fields):** the stored approval JSON (L2666–2676 pattern) gains:
  - `"overrides_degraded": true` — the exact field name. Present as `true` only when the approver passed `acknowledge_degraded=true` on a degraded render; `false` otherwise (clean approval). Mirrors the existing `overrides_failed_checks` naming so reviewers read one convention.
  - `"degraded_fallback_scenes": [...]` — copied from the review, so the approval artifact is self-contained evidence of *which* scenes were degraded.
  - Existing fields unchanged: `gate_passed` preserved from review (`false` for degraded — **never faked to `true`**), `overrides_failed_checks` unchanged.
- **Return value:** gains `"overrides_degraded": bool` and `"degraded": bool` (mirroring `gate_passed` / `overrides_failed_checks` at L2692–2705). `status` becomes `approved` (existing semantics: human approved, not published), `published` stays `false`.
- **Idempotency:** the existing already-approved early return (L2637–2659) must also return `overrides_degraded` from the stored record, not recompute it.
- **Decision line:** after approval, `_review_campaign`'s decision for a degraded+approved campaign reads `approved; human approval for vN overrides degraded render (fallback_scenes=[...]); not published.` — must name the degradation, never a bare "approved".

**Invariant (all rows):** no code path in Phase 3 sets `gate_passed=true` for a degraded render, and no path sets `review["status"]=approved` for a degraded render without a stored approval record containing `overrides_degraded=true`.

---

## 2. Concurrent=1 lock design

### 2.1 Where and mechanism

- **Layer:** `content_service` only (`solocorp_mcp/departments/content_service.py`, `render_campaign_media_local`). The CLI subprocess does not lock (it is short-lived and must not outlive the service lock; if the service dies, the lock must die with it — §2.3). No lock in the MCP wrapper (`content_mcp.py`) — one enforcement point.
- **Acquisition point:** after cheap, side-effect-free validation (script selection, `_local_media_scenes()`, rights read — L1540–1609) and **before** `job_id` generation / job-manifest storage (L1611). Rationale: a concurrently-rejected call must leave **no** `local_media_render_job` asset claiming `in_progress`, no output directory, no MP4 — the same "no partial output" guarantee as a failed render. Validation errors still raise before the lock (a bad script never contends for the lock).
- **Mechanism:** `fcntl.flock` (POSIX), following the established `_campaign_lock` idiom (L230–263) but **non-blocking** and **global** (not per-campaign):
  - Lock file: `central_bus/content/.local_render.lock` (dotfile in the same `BUS_ROOT / DEPARTMENT` directory as the existing `.{campaign_key}.lock` files — precedent that lock files live there and are not bus assets).
  - Open with `"a+b"` (create if absent, never truncate/delete), then `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)`.
  - On `BlockingIOError` / `OSError` with `errno` in `{EACCES, EAGAIN, EWOULDBLOCK}`: raise `ContentServiceError("another local render in progress" + holder info if available)` — **immediately, no sleep, no retry loop, no queue**. This is the user-visible contract: second render while one runs ⇒ clear error in milliseconds, not a 3600s timeout hang.
  - Holder info (advisory): after acquiring, the holder truncates and writes one JSON line into the lock file — `{pid, campaign_id, job_id, started_at}` — and flushes. On contention, the loser best-effort reads that line and appends it to the error: `another local render in progress: holder campaign_id=... job_id=... pid=... started_at=...`. If the line is missing/unparseable (e.g. holder crashed before writing, or an older holder that wrote nothing), the error is the bare `another local render in progress` — the advisory content must never affect lock correctness (§2.3). The lock file is **never unlinked** by anyone (unlinking breaks flock for holders with an open fd to the now-unlinked inode).
  - **Scope:** the lock is held from acquisition through job storage, the entire subprocess (3600s timeout included), result storage, `_review_campaign`, and return construction — i.e. the whole remainder of `render_campaign_media_local`, via a `with` context manager so every exit path (success, `ContentServiceError`, timeout, unexpected exception) releases it. Concat renders (`render_campaign_with_concat`) are **not** covered (separate subsystem, out of Phase 3 scope).
  - **Windows fallback:** mirror `_campaign_lock`'s `msvcrt` branch but non-blocking: single `LK_NBLCK` attempt; on `EACCES/EAGAIN/EDEADLK` raise the same `another local render in progress` error — no `time.sleep(0.05)` polling loop (that loop is blocking by design for campaign locks; the render lock must fail fast). If neither `fcntl` nor `msvcrt` is available: raise `ContentServiceError("cross-process local render locking is unsupported on this platform")` (mirror L255).
- **Interaction with `_campaign_lock`:** orthogonal locks (per-campaign vs global render). Lock ordering is fixed to avoid deadlock: render lock is acquired *before* the campaign lock is ever taken inside `_store_assets`/approval paths within this function, and no code path acquires the render lock while holding a campaign lock. @changful's D2 must state the ordering explicitly.

### 2.2 Stale lock handling — confirmed

`flock` locks are associated with the **open file description**, not with the file path or a PID. The kernel releases the lock when the last fd referencing it is closed — including on process death (`SIGKILL`, crash, OOM, MCP server restart). Therefore:

- **No stale-lock cleanup exists or is needed.** If the holder process dies mid-render (90s into a 3600s subprocess), the lock is free the moment the service process exits; the next render acquires it immediately. The leftover lock *file* contains stale advisory JSON, but the *lock* is gone — the next holder overwrites the advisory line after acquiring. QA must prove this (kill −9 the holder, next acquire succeeds with no manual file removal) — §7.
- This is strictly stronger than the current per-dir existence check (renderer L123–124), which *does* leave stale state (an output dir from a crashed run blocks that exact `job_id` path — harmless because `job_id` is a fresh UUID, but it is not a lock at all).
- Caveat to record: the lock protects against *process* contention on one host/filesystem. It does not protect against two hosts sharing `central_bus/content` over NFS (flock semantics over NFS are implementation-defined) — out of scope for the local-first single-host deployment; the lock file path is on the local bus root.

### 2.3 Test strategy (summary; full matrix §7)

1. **Unit (same process, two fds):** open two fds to the lock file; first `LOCK_EX|LOCK_NB` succeeds, second raises `EAGAIN` — proves non-blocking rejection without threads. Release first; second now succeeds.
2. **Integration (threaded):** mock the pipeline to block (event-controlled), start render #1 in a thread, assert render #2 raises `another local render in progress` in well under the subprocess timeout, and leaves no job/result asset and no output dir (§7, T-CONC-*).
3. **Release paths:** lock is free after success, after step failure, after subprocess `TimeoutExpired`, and after an unexpected exception (all four must be tested — a leaked lock on the exception path would wedge every future render).
4. **Process death:** spawn a holder subprocess that acquires and sleeps, `kill -9` it, assert a fresh acquire succeeds with no file deletion.
5. **Advisory content:** holder writes JSON; loser error contains `job_id`/`campaign_id`; corrupt the advisory line and assert the loser still gets the correct *rejection* (content ignored for correctness).

---

## 3. Per-step status contract

### 3.1 Exact additive keys

Step names (fixed, in pipeline order): `input_validation`, `piper_tts`, `synthetic_visuals`, `ffmpeg_assembly`, `output_audit`. Stored as a **dict keyed by step name** (not a list) — the Phase 1 manifest adapter's `pipeline.steps` list is a read-only projection that can iterate this dict in the fixed order.

Each step entry has **exactly** these keys (no omissions, no extras in Phase 3):

| Key | Type | Meaning |
|:----|:-----|:--------|
| `status` | `str` | `completed` \| `degraded` \| `failed` \| `skipped` \| `not_started`. `degraded` = step succeeded via fallback (§1). `skipped` = pipeline aborted at an earlier step in this run. `not_started` = only in the job-manifest plan snapshot (§3.3) before execution begins. |
| `started_at` | `str \| null` | ISO-8601 UTC with offset (`datetime.now(timezone.utc).isoformat()`), recorded by whoever runs the step (renderer for its 4 steps, service for `input_validation`). `null` if never started — **never fabricated**. |
| `finished_at` | `str \| null` | Same format; `null` if still running or never finished. |
| `output` | `object \| null` | Step-specific summary (§3.2 table). `null` on `failed`/`skipped`/`not_started` — a failed step never claims an output file. |
| `fallback_used` | `bool` | `false` except `piper_tts`/`synthetic_visuals` when a fallback fired. Always present (schema-stable). |
| `fallback_scenes` | `list[int]` | 1-indexed scene numbers, sorted; `[]` when unused. Always present. |
| `error` | `str \| null` | Exception type name (e.g. `"RuntimeError"`, `"ContentServiceError"`) or `null`. Set on `failed`; **also set on `degraded`** (the original error that triggered the fallback — degradation must not erase its cause). |
| `message` | `str \| null` | Human message, truncated to 1600 chars (existing convention, `content_service.py:1707`). `null` on clean `completed`. |

**Top-level additive keys in `result_record`** (in addition to the existing `schema_version`, `job_id`, `campaign_id`, `provider`, `execution_status`, `error`, `message`, `lifecycle_state`, `approval_effect`):

- `steps`: the dict above (authoritative).
- `failed_step`: `str | null` — first step with `status=failed`, else `null`.
- `degraded`: `bool`; `fallback_used`: `bool`; `fallback_scenes`: `list[int]` (sorted union) — §1.4.
- `sync_report`: `list` — copy of `render["sync_report"]` (§5), `[]` on failure before any scene completed.
- `output_audit`: `object | null` — copy of `steps["output_audit"]["output"]` when present, else `null`. Gives the gate/manifest adapter one stable read point without digging through `steps`.

The same `steps` / `failed_step` / `degraded` / `fallback_used` / `fallback_scenes` / `sync_report` / `output_audit` keys are added to the **renderer result dict** (`render(...)` return, L267–313) so the CLI output is self-describing. `render["steps"]` contains the 4 renderer-owned steps; the service merges in its `input_validation` step (see §3.2). `voice_segments` is unchanged except the additive per-entry fallback keys (§1.4).

### 3.2 Who reports what — renderer vs service

**Renderer CLI (`scripts/render_campaign_media_local.py`) is the authority for its 4 steps.** It wraps each phase in try/except recording `started_at`/`finished_at`/`error`/`message` into the steps dict as it goes:

| Step | Renderer phase (current lines) | `output` on success |
|:-----|:-------------------------------|:--------------------|
| `piper_tts` | Per-scene Piper loop (L145–160) + silence-pad loop (L169–178) | `{voice_count, voice_segments: [...], sync_report: [...]}` — `voice_segments` is the existing list (with additive fallback keys); `sync_report` is §5. |
| `synthetic_visuals` | Three.js call + frame check (L162–167) | `{frame_count, frames: [...]}` (existing `frames` paths). |
| `ffmpeg_assembly` | Pad (L169–178) through video assemble (L231–249) | `{video_path, audio_mix_path, captions_path, captions_sha256}` — `captions_sha256` is new (Phase 1 adapter §1.6 item 3 anticipated it; compute with existing `_sha256`, L78–83). |
| `output_audit` | ffprobe + EBU R128 (L251–265) + §4 checks | The full audit object (§4.4). |

**Failure reporting (the load-bearing change):** today `main()` (L316–324) prints only `{status, error, message}` to stderr and exits 1, so partial progress (e.g. 4 of 6 Piper scenes) is lost when the service truncates stderr into `message` (L1516–1518). Phase 3: the CLI's except handler prints the same JSON **plus** `steps` (partial — completed steps filled, failed step filled, remaining `skipped`), `failed_step`, `degraded`, `fallback_used`, `fallback_scenes`, `sync_report` (partial), and exits 1. Unknown-key-tolerant consumers are unaffected (backward compatible).

**Service (`content_service.py`) aggregates, never recomputes:**

1. Builds `input_validation` itself: `completed` with `output={scene_count, scene_seconds, duration_seconds, script_filename, script_version}` when `_local_media_scenes()` + rights read succeed (L1591–1609); the step is only persisted if a job exists — a pre-job validation failure still raises before job storage (§1.2), so no result record exists to hold it. (The Phase 1 adapter's caveat stands: pre-job failures are visible as the raised `ContentServiceError`, not as a bus record. Phase 3 does not change pre-job failure into a stored record — that would be a behaviour change beyond the kickoff scope.)
2. On subprocess success: merges renderer `steps` (4 steps) with its `input_validation` step, persists verbatim in `result_record["steps"]` and `result_record["render"]`.
3. On subprocess non-zero exit: `_execute_local_media_pipeline` (L1516–1518) must **parse the stderr JSON first** (new behaviour) to recover `steps`/`failed_step`/fallback keys, and carry them into the failed `result_record` (which today has no `render` key — Phase 3 keeps `render` absent on failure to avoid faking a video, but adds the step keys at top level). If stderr is not parseable JSON (old CLI, crash), the service falls back to post-hoc synthesis (item 4) and the raw (truncated) stderr text still becomes `message` as today.
4. **Post-hoc derivation (backward compat):** if the renderer dict has no `steps` (old CLI, or a test double like `tests/test_content_mcp.py`'s `fake_pipeline`), the service synthesises steps from `execution_status` only: all steps `completed` (if completed) or the aggregate `failed` with `failed_step=null`, `started_at`/`finished_at=null`, `output=null`, plus `derivation: "post_hoc_aggregate"` inside each synthesised step. It must never fabricate timestamps or per-step attribution it cannot prove. Existing tests that mock the pipeline must keep passing unmodified.

### 3.3 Job manifest vs result record; schema discipline

- `job_manifest` (`local_media_render_job`, stored **before** execution, L1616–1640) gains a *plan* snapshot only: `fallback_policy: {tts_fallback, visual_fallback}` (the effective flags for this job) and `steps` with all five steps `{status: "not_started", started_at: null, finished_at: null, output: null, fallback_used: false, fallback_scenes: [], error: null, message: null}`. It cannot contain final statuses (the run hasn't happened) and the job asset is immutable after storage — the **result record is authoritative**.
- **No `schema_version` bump** (stays `1`), **no new asset types** (still exactly `local_media_render_job` / `local_media_render_result`). All Phase 3 fields are additive keys; existing readers (`_review_campaign`, manifest adapter, tests asserting known keys) ignore unknown keys. The manifest adapter can now project `steps` dict → ordered list with real timestamps for new renders, and must keep the `post_hoc_aggregate` label for Phase 1/2 renders.

### 3.4 Illustrative shape (not evidence)

```json
"steps": {
  "input_validation":  {"status": "completed", "started_at": "2026-11-07T05:00:00+00:00", "finished_at": "2026-11-07T05:00:00+00:00", "output": {"scene_count": 6, "scene_seconds": 15, "duration_seconds": 90, "script_filename": "...", "script_version": "v1"}, "fallback_used": false, "fallback_scenes": [], "error": null, "message": null},
  "piper_tts":          {"status": "degraded",  "started_at": "...", "finished_at": "...", "output": {"voice_count": 6, "...": "..."}, "fallback_used": true, "fallback_scenes": [3], "error": "RuntimeError", "message": "Piper scene 3 failed (...); silent buffer substituted (tts_fallback=silence)"},
  "synthetic_visuals":  {"status": "completed", "...": "..."},
  "ffmpeg_assembly":    {"status": "completed", "...": "..."},
  "output_audit":       {"status": "completed", "output": {"file_exists": true, "size_bytes": 3073503, "duration_seconds": 90.0, "width": 1080, "height": 1920, "bitrate_total_bps": 273200, "integrated_lufs": -16.0, "true_peak_dbtp": -1.5, "...": "..."}}
}
```

---

## 4. Output audit completion

### 4.1 Current vs Phase 3

Current audit (renderer L251–265): ffprobe JSON; video+audio streams present; 1080×1920; duration ±0.5s; `_measure_ebur128` LUFS −16±0.5, TP ≤−1.5. **No** `file_exists`/`size_bytes`/bitrate check (size/sha are computed at return L286–294 but not gated). Phase 3 keeps every existing check with its exact tolerance and adds: explicit file existence + size, stream bitrates, derived bitrate consistency, codec identity, and the audit object persisted as `steps["output_audit"]["output"]` / `result_record["output_audit"]` / `render["output_audit"]`.

### 4.2 Evidence: proven bitrates of frozen Phase 1/2 renders

Measured read-only from the frozen MP4s on disk (2026-11-07, `ffprobe -show_format -show_streams`):

| Render | Size (bytes) | Duration | Total bitrate (`format.bit_rate`) | Video bitrate | Audio bitrate | Derived `size×8/duration` |
|:-------|:------------:|:--------:|:---------------------------------:|:-------------:|:-------------:|:-------------------------:|
| Phase 1 `campaign_synth_phase1_20261107` | 3,073,503 | 90.000s | **273,200 bps** | 72,270 bps | 191,942 bps | 273,200 bps ✓ |
| Phase 2 `campaign_synth_phase2_20261107` | 2,824,995 | 90.000s | **251,110 bps** | 50,071 bps | 192,052 bps | 251,111 bps ✓ |

Why so low: the encoder is fixed (`-c:v libx264 -preset veryfast -crf 20`, L246) over slow synthetic `zoompan` scenes that compress heavily, while audio is CBR `-b:a 192k` (L247) and dominates the total. Consequences:

- A total-bitrate hard floor of **≥500 kbps** (a "typical 1080×1920" guess) would **false-fail both proven renders**.
- Even ≥260 kbps false-fails Phase 2; ≥280 kbps false-fails both.
- A *video-stream* floor of ≥100 kbps false-fails both (50–72 kbps proven); ≥60 kbps false-fails Phase 2.
- A degraded static-card render (§1.3.2, solid colour) will have a video bitrate *far below* 50 kbps — any video floor false-fails the very degraded path Phase 3 exists to allow.

**Therefore an absolute bitrate threshold cannot be a hard gate in Phase 3.** The kickoff's "bitrate (new) — all checked, failure = failed render" is implemented as a *structural* hard check + an *advisory* absolute floor (§4.3), which satisfies "checked" without false-failing proven evidence. Revisit a hard floor only after an encoder change (e.g. `-b:v` floor or higher CRF target) re-baselines proven renders — that is a Phase 4 decision with new evidence, not a Phase 3 guess.

### 4.3 Threshold table (normative)

| Check | Source | Threshold | Hard / advisory |
|:------|:-------|:----------|:----------------|
| `file_exists` | `Path.is_file()` on the rendered MP4 | must be `true` | **Hard** |
| `size_bytes` | `stat().st_size` | `> 0` | **Hard** |
| Duration | `format.duration` vs expected `duration_seconds` | `abs(diff) ≤ 0.5s` (existing) | **Hard** |
| Resolution | video stream `width`/`height` | exactly `1080`×`1920` (existing) | **Hard** |
| Codecs | `codec_name` per stream | video `h264`, audio `aac` (renderer always encodes these, L246–247; asserting catches a wrong-encoder regression) | **Hard** |
| Streams present | video + audio stream found | both present (existing) | **Hard** |
| `bitrate_total_bps` | `format.bit_rate` parsed as int (`"N/A"`/missing ⇒ fail) | present, finite, `> 0` | **Hard** |
| `bitrate_video_bps` / `bitrate_audio_bps` | per-stream `bit_rate` | present, `> 0` | **Hard** |
| Derived consistency | `bitrate_derived_bps = round(size_bytes × 8 / duration_seconds)` (duration > 0 guarded) vs `bitrate_total_bps` | relative difference `≤ 10%` (catches truncated-size/probe mismatch; proven renders match to <0.001%) | **Hard** |
| LUFS | `_measure_ebur128` integrated | `abs(lufs − (−16.0)) ≤ 0.5` (existing) | **Hard** |
| True peak | `_measure_ebur128` TP | `≤ −1.5 dBTP` (existing) | **Hard** |
| **Absolute floor** | `bitrate_total_bps` vs **100,000 bps** | `passed = total ≥ 100000` | **Advisory only** — recorded as `bitrate_advisory: {threshold_bps: 100000, passed: bool, blocking: false}`; never changes step status, `execution_status`, or gate. 100 kbps is ~2.5× below the lowest proven total (251 kbps) and above any metadata-only stub, so it flags degenerate output without false-failing clean *or* degraded (static-card) renders. |

Any **hard** failure ⇒ `output_audit` step `failed`, whole render `failed`, MP4 removed by existing cleanup, `failed_step=output_audit`, `gate_status=blocked_render_failed` (manifest-adapter vocabulary). The advisory floor failing ⇒ step stays `completed`, `output.bitrate_advisory.passed=false` visible for a human/QA to see — this is the *only* "warning" in the audit, and it is explicitly non-blocking.

### 4.4 `output_audit` object shape

```json
{
  "file_exists": true,
  "path": "central_bus/content/local_media/.../campaign_..._rendered.mp4",
  "size_bytes": 3073503,
  "duration_seconds": 90.0,
  "width": 1080, "height": 1920,
  "video_codec": "h264", "audio_codec": "aac",
  "bitrate_total_bps": 273200,
  "bitrate_video_bps": 72270,
  "bitrate_audio_bps": 191942,
  "bitrate_derived_bps": 273200,
  "bitrate_advisory": {"threshold_bps": 100000, "passed": true, "blocking": false},
  "integrated_lufs": -16.0,
  "true_peak_dbtp": -1.5,
  "sha256": "…64 hex…"
}
```

`sha256` is the existing `_sha256` (L78–83), already validated 64-hex by the service (L1676–1677). All numeric fields are JSON numbers (not strings); unparseable probe values become `null` and fail the corresponding hard check — never a silent `0`.

---

## 5. Timestamp sync report

### 5.1 Per-scene fields (exact names)

`render["sync_report"]` is a list with one entry per scene, in scene order. Each entry:

| Field | Type | Derivation |
|:------|:-----|:------------|
| `scene_no` | `int` | 1-indexed (`index + 1`). |
| `start_seconds` / `end_seconds` | `int` | Copied verbatim from the validated scene timing (`scene["start_seconds"]`/`["end_seconds"]`, renderer L128–129 — contiguous by construction). |
| `slot_duration_seconds` | `int` | `scene_seconds` (15 or 10). |
| `voice_duration_seconds` | `float` (3 dp) | Piper WAV duration `getnframes()/getframerate()` (existing L154–155). For a silence fallback: `scene_seconds` (§1.3.1). |
| `trimmed_silence_seconds` | `float (3 dp) \| null` | `voice_duration_seconds − trimmed_duration_seconds`, where `trimmed_duration_seconds` is measured from a `silenceremove`-only intermediate `voice/scene-{NN:02d}-trimmed.wav`. **Requires splitting the fused filter** (L173–175) into step A (`silenceremove` only → `-trimmed.wav`) and step B (`apad`+`atrim` → `-padded.wav`) — same filter order, same output, one extra measured intermediate per scene (job-dir only, not an asset). If the implementer does not split the filter, this field **must be `null`** with `trim_measurement: "not_measured"` — never estimated or fabricated. |
| `padded_duration_seconds` | `float` (3 dp) | Padded WAV duration `getnframes()/48000` (wave module, same technique as L226–227). Must equal `slot_duration_seconds`. |
| `drift_ms` | `int` | `round((padded_duration_seconds − slot_duration_seconds) × 1000)`. By construction (`apad`+`atrim`, integer PCM frames) this is `0` for every scene — reported anyway so QA can assert it, and so a future filter change that introduces drift fails loudly. |
| `fallback_used` / `fallback_kind` | `bool` / `"silence" \| "static_card" \| null` | §1.4. `static_card` entries describe the *visual* fallback for that scene; a scene can have both (voice silence + visual card) — in that case this entry's `fallback_kind` is `"silence"` (voice dimension) and the visual fallback is visible in `steps["synthetic_visuals"]["fallback_scenes"]`. (The sync report is voice/timing-scoped; visual fallback per scene lives in §1.4 + `steps`.) |
| `caption_start_seconds` / `caption_end_seconds` | `int` | Identical to `start_seconds`/`end_seconds` — captions are scene-level (§5.2). |

**Tolerance:** `padded_duration_seconds` must be within `±0.05s` of the slot (mirrors the existing mixed-audio check L227–229); a larger deviation is an `ffmpeg_assembly` failure. `drift_ms` is reported, not gated beyond that tolerance.

### 5.2 Caption alignment statement (normative wording)

Captions are **scene-level only**. The existing renderer claim is preserved verbatim and extended — `render["caption_timing"]` stays `"scene-level from supplied script; no word-level alignment"` (L280), and every `sync_report` entry carries `caption_timing: "scene-level"`:

> Each scene's ASS caption spans the full scene slot `[start_seconds, end_seconds]`, anchored to the script's scene timing — **not** to measured voice onset, silence-trim points, or word boundaries. There is no karaoke/word-level alignment in Phase 3. A silence-fallback scene still shows its scene caption for the full slot over the silent buffer.

QA verifies: for every scene, `caption_start_seconds == start_seconds` and `caption_end_seconds == end_seconds`, and no `sync_report` entry claims word-level timing.

### 5.3 Where stored

- Primary: `render["sync_report"]` (renderer dict) → persisted in `result_record["render"]["sync_report"]`.
- Convenience copy: `result_record["sync_report"]` (same list, §3.1) and `steps["piper_tts"]["output"]["sync_report"]`.
- **Not** a campaign asset, **not** in the job manifest (plan snapshot only). The manifest adapter may project it read-only.

---

## 6. `simple_edit` — deferral rationale and Phase 4

**Deferred (locked non-goal for Phase 3).** Rationale, grounded in current reality:

1. **The renderer already does the simple-edit job for its supported shape:** native 9:16 output (1080×1920 via `zoompan`, L240), scene concatenation (video `concat` + audio `concat`/`amix`, L184–188/242), and burned ASS subtitles (L243). A generic crop/trim/burn/concat post-edit tool would duplicate assembly logic and create a *second* mux path to audit, lock, and gate.
2. **Generic edit is Concat-path work, and Concat is not yet proven here.** The Concat workflow (`render_campaign_with_concat`, `concat_render_result`, Earshot review linkage) is the designed home for post-edit operations; its MCP server was unusable at kickoff (AppImage FUSE `Operation not permitted`, exit 127) and, as of 2026-11-07, runs via `--appimage-extract` with the MCP handshake verified — but `render_campaign_with_concat` has still never been run on this host (no render proof). Building `simple_edit` now would mean building on an unproven foundation and risking the forbidden mix of local-media artifacts into the Concat workflow (`solocorp_mcp/departments/content_skills/media-production/SKILL.md`: "Do not combine artifacts from `render_campaign_media_local` with the Concat [workflow]").
3. **Phase 3's locked scope is local-media ONLY** (kickoff). `simple_edit` would expand the audit/lock/gate surface (§2–§4) to a second tool with no checker capacity allocated.

**What Phase 4 could add** (after a proven Concat render on this host — extract + handshake are done but render proof is still missing — or as a standalone FFmpeg tool — CEO decision at Phase 4 kickoff):

- A standalone `simple_edit` FFmpeg tool (input: one existing MP4 + edit spec: crop/scale-to-9:16, trim by timestamps, burn external ASS, concat list, loudnorm re-check) with the **same** contracts as this design: per-step status (§3), complete output audit (§4, including the advisory bitrate floor re-baselined with new evidence), the **shared** `central_bus/content/.local_render.lock` (one lock for all local FFmpeg work — two locks would allow CPU/IO contention the concurrent=1 rule exists to prevent), and publish-gate + Earshot linkage if it feeds the Concat workflow.
- Word-level karaoke captions (forced alignment over `voice_segments`) as a separate Phase 4+ item — it changes the §5.2 alignment statement and needs its own accuracy evidence.
- An encoder change ( `-b:v` floor) *before* any hard absolute bitrate gate — re-baseline §4.2 evidence first.

None of the Phase 4 items may reuse or mutate frozen Phase 1/2 assets.

---

## 7. Test matrix for QA (independent checker)

QA runs these against a **new** Phase 3 campaign + a separate degraded-proof test campaign. Failure injection is at **test level only** (monkeypatch / fixture / mock subprocess) — Sek must not fake failures on a real campaign. Frozen-campaign integrity is checked by hash before and after the whole Phase 3 run.

### 7.1 Failure injection per step (default OFF ⇒ abort; opt-in ⇒ degraded)

| ID | Injection | Expected (default) | Expected (opt-in) |
|:---|:----------|:-------------------|:------------------|
| T-FAIL-01 | Invalid script (bad layout / missing voiceover / bad `script_filename`) | `ContentServiceError` pre-job; no job/result asset, no output dir, no MP4 | Same — **no fallback exists** for `input_validation` (flags irrelevant) |
| T-FAIL-02 | Piper fails scene *i* (mock Piper exit 1 / rename model fixture) | `execution_status=failed`, `failed_step=piper_tts`, steps: prior scenes `completed`, scene step `failed`, later steps `skipped`; no MP4; gate `blocked_render_failed`; approval refused | `tts_fallback=silence`: `completed` + `degraded=true`, `fallback_scenes=[i]`; silent WAV exists at 48kHz stereo, exactly `scene_seconds` frames, all-zero samples; MP4 exists; §5 entry shows `voice_duration=scene_seconds`, `fallback_kind=silence` |
| T-FAIL-03 | Three.js fails (mock node exit 1) | `failed`, `failed_step=synthetic_visuals`, no MP4 | `visual_fallback=static_card`: `completed`+`degraded`, `fallback_scenes=[1..N]` (whole-visuals sub-case), static PNGs 1080×1920, MP4 exists, ASS captions still burned |
| T-FAIL-04 | Single frame missing after node success (delete one frame fixture) | `failed` (`synthetic_visuals`) | `static_card`: `fallback_scenes=[i]` only, other frames untouched |
| T-FAIL-05 | FFmpeg fails in assembly (mock ffmpeg exit 1 at mix / loudnorm / video stage) | `failed`, `failed_step=ffmpeg_assembly`, no MP4 (partial cleanup), gate `blocked_render_failed` | Same — **no fallback** (flags do not rescue assembly) |
| T-FAIL-06 | Audit failure (mock ffprobe: wrong resolution / truncated file / LUFS out of range) | `failed`, `failed_step=output_audit`, MP4 removed, `output_audit` object shows the failing field | Same — **no fallback** for audit |
| T-FAIL-07 | Bad fallback flag value (`tts_fallback="loud"`) | `ContentServiceError` pre-job, no assets | n/a |

### 7.2 Concurrent rejection

| ID | Scenario | Expected |
|:---|:---------|:---------|
| T-CONC-01 | Render #1 blocked (event-controlled mock pipeline); render #2 started | #2 raises `ContentServiceError` containing `another local render in progress` **fast** (≪ subprocess timeout, no hang); #2 leaves no job/result asset, no output dir |
| T-CONC-02 | Lock released after #1 succeeds | #3 acquires immediately |
| T-CONC-03 | Lock released after #1 fails / times out (`TimeoutExpired`) / raises unexpectedly | Next render acquires (no wedged lock on any exit path) |
| T-CONC-04 | Holder subprocess `kill -9` mid-acquire | Next acquire succeeds with **no** lock-file deletion (flock auto-release, §2.2); stale advisory JSON overwritten |
| T-CONC-05 | Advisory line corrupted / absent | Rejection still correct (holder info omitted, bare message) — correctness never depends on advisory content |

### 7.3 Degraded visibility and gate

| ID | Scenario | Expected |
|:---|:---------|:---------|
| T-GATE-01 | Degraded render (T-FAIL-02 opt-in), then `review_publish_gate` | `status=review_required`, `degraded=true`, `fallback_used=true`, `fallback_scenes=[i]`, `publish_action=blocked_degraded_render`, degraded check `ok=false`, **`gate_passed=false`** |
| T-GATE-02 | `record_human_approval` on degraded **without** `acknowledge_degraded` | Refused: `ContentServiceError` naming the degraded acknowledgement requirement; campaign not approved |
| T-GATE-03 | `record_human_approval` **with** `acknowledge_degraded=true` | `status=approved`, approval record contains `overrides_degraded=true` + `degraded_fallback_scenes=[i]`, **`gate_passed` still `false`**, `published=false`, decision line names the degradation |
| T-GATE-04 | Clean render gate (regression) | No degraded fields set (`degraded=false`, `fallback_scenes=[]`, `overrides_degraded=false`), `publish_action=blocked_until_human_approval`, byte-for-byte same gate shape as Phase 2 |
| T-GATE-05 | Failed render gate (regression, Path A) | `blocked_render_failed`, approval refused — unchanged from Phase 2 |

### 7.4 Output audit, sync report, evidence

| ID | Scenario | Expected |
|:---|:---------|:---------|
| T-AUD-01 | Clean E2E render via MCP on new campaign | `output_audit` complete (§4.4); independent QA re-probe (ffprobe + EBU R128 + SHA-256) matches renderer self-report; `bitrate_advisory.passed=true` (proven totals 251–273 kbps > 100 kbps floor) |
| T-AUD-02 | Re-probe frozen Phase 1/2 MP4s | Both pass all hard checks; advisory passes; **proves** the floor does not false-fail proven renders (§4.2) |
| T-AUD-03 | Static-card degraded render | Passes hard checks (incl. LUFS/TP measured, not assumed); video bitrate low but **no hard failure** (advisory only) |
| T-AUD-04 | Truncated MP4 fixture | Hard fail: `file_exists`/`size_bytes`/derived-consistency (§4.3) |
| T-SYNC-01 | Clean render sync report | Per-scene `start/end`, `voice_duration`, `padded == slot`, `drift_ms == 0`, `caption_start/end == scene start/end`, `caption_timing="scene-level"`; no word-level claim |
| T-SYNC-02 | Silence-fallback scene | Entry shows `voice_duration == slot`, `fallback_kind=silence`, caption still spans full slot |

### 7.5 Backward compatibility and frozen integrity

| ID | Scenario | Expected |
|:---|:---------|:---------|
| T-BC-01 | Clean render with **all flags OFF** (defaults) | MP4 ffprobe-equal to Phase 2 shape (1080×1920, expected duration ±0.5s, −16 LUFS ±0.5, TP ≤−1.5); `result_record` diff vs Phase 2 record = **additive keys only** (existing keys unchanged); `schema_version=1`, asset types unchanged; existing `tests/test_content_mcp.py` passes (mocked pipeline without `steps` handled via `post_hoc_aggregate`, §3.2) |
| T-BC-02 | Frozen campaigns | SHA-256 of every asset file under `campaign_synth_phase1_20261107` v5 and `campaign_synth_phase2_20261107` v7 identical before/after Phase 3; no new assets under their campaign keys; campaign `version`/`approved_version` unchanged |
| T-BC-03 | Scope guard | No Concat tool invoked during Phase 3 E2E; no `record_human_approval` / publish on the Phase 3 E2E campaign (kickoff success criterion); degraded-override proof (T-GATE-03) only on the separate test campaign |
| T-BC-04 | Manifest adapter projection | Adapter over a Phase 3 render shows real per-step timestamps/statuses (not `post_hoc_aggregate`); over Phase 1/2 renders still shows `post_hoc_aggregate` with `null` timestamps — never fabricated |

QA verdict is **GO / NO-GO with evidence** in `bus/evidence/` (ffprobe outputs, SHA-256 lists, test run output + exit code). Maker ≠ checker: QA does not implement the features it checks.

---

## 8. Routing and acceptance (for the checker, not results)

- **Implementation:** @engineering — @changful, D2 plan attached before any code (per `rules/06-certification.md`: 50–150-line agent really calling tools, run output + exit code). Code touchpoints (for the D2, not done here): `scripts/render_campaign_media_local.py` (steps instrumentation, fallback generation, split `silenceremove` filter, §4 audit, `captions_sha256`, failure stderr JSON), `solocorp_mcp/departments/content_service.py` (flags + validation, lock §2, service aggregation §3.2, degraded gate §1.5, `acknowledge_degraded` §1.5.1), `solocorp_mcp/departments/content_mcp.py` (optional flag pass-through, defaults OFF).
- **E2E:** @content-creator-sek on `campaign_synth_phase3_20261107` — one clean render via MCP; degraded proof on a separate test campaign or test-level injection.
- **Checklist QA must confirm (acceptance, not results):** (1) default-off failure ⇒ no MP4, `failed`, `blocked_render_failed`; (2) opt-in tts/visual fallback ⇒ `completed` + `degraded` + visible `fallback_scenes` everywhere (§1.4–1.5); (3) `gate_passed` never `true` for degraded, approval without `acknowledge_degraded` refused, with it records `overrides_degraded=true`; (4) concurrent second render rejected fast with `another local render in progress`, lock released on all paths incl. `kill -9`; (5) `steps` dict complete with real timestamps (new renders) / `post_hoc_aggregate` (old renders), `schema_version=1` unchanged; (6) §4 hard checks pass on proven renders, advisory floor non-blocking; (7) sync report `drift_ms=0`, scene-level captions; (8) frozen campaigns byte-identical, no Concat/approval/publish in Phase 3 E2E.
- **Status until that evidence exists: D0 / NOT PASSED.**

*— @architect-songsak, Head of Architect. Design only; no code changed.*
