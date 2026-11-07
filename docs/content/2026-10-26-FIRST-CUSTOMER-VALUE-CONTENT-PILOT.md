# First Content Customer-Value Pilot — Run Record

Date: 2026-10-26
Status: review required; draft only; no customer validation

## Owner Sequencing Decision — 2026-10-29

The Owner has deferred all external audience and customer validation until the Content Creator system-readiness gate is met and independently reproduced. This changes the order of future work; it does not change the results recorded for this 2026-10-26 run. The existing audience-feedback CTA is draft history and must not be used to collect validation now. See `docs/plans/CONTENT-CUSTOMER-VALUE-PILOT.md` for the new sequence.

## Question

Can SoloCorp OS create a credible, reviewable short-form content package around a real solo-builder problem, while being explicit about what is not yet proven?

This run tests production feasibility and creative clarity. It does not test customer adoption, willingness to pay, comparative product quality, or repeat use.

## Campaign

- Campaign ID: `customer-value-proof-2026-10-26`
- Latest version: `v6`
- Latest lifecycle: `review_required`; approval required; no approval record exists.
- Format: 38-second Thai vertical-video draft.
- Hook: “คนเดียวจะสร้างซอฟต์แวร์ที่คนใช้จริงได้ไหม?”
- CTA: ask solo developers which repetitive task costs them the most time and what evidence they would need before trying SoloCorp OS.
- Creative constraint: the clip says customer value and competitiveness remain unproven; it does not present a finished product UI or finished render.

## Artifacts

- Script v1: scaffold — `central_bus/content/campaign-customer-value-proof-2026-10-26-script-บทแรกของการพ-ส-จ_20261026T111252054102Z.md`.
- Script v2: originally recorded as `human_edited`, but this was authored by an AI agent; no human edit occurred. Preserve as history and treat the lifecycle label as inaccurate.
- Script v5: `llm_generated`, supersedes the mislabeled v2 copy — `central_bus/content/campaign-customer-value-proof-2026-10-26-llm-script-v2-provenanc_20261026T111656364131Z.md`.
- Visual prompt v3: scaffold — `central_bus/content/campaign-customer-value-proof-2026-10-26-visual-solo-builder-tes_20261026T111507278512Z.md`.
- Audio cue v4: scaffold for an earlier script version; retained as history, not current.
- Audio cue v6: scaffold, depends on script v5 — `central_bus/content/campaign-customer-value-proof-2026-10-26-audio-cue-campaign-cust_20261026T111656727257Z.md`.
- Latest campaign manifest — `central_bus/content/campaign-customer-value-proof-2026-10-26-manifest_20261026T111656895672Z.json`.
- Latest Publish Gate report — `central_bus/content/campaign-customer-value-proof-2026-10-26-publish-gate-v6_20261026T111656859209Z.md`.

## Gate Result

The latest campaign review returned `review_required`, `gate_passed: false`, and `publish_action: blocked_until_human_approval`.

- Passed: primary script, visual prompt, audio cue linked to the current script, source references supplied, and R1-R5 checks.
- Still requires human review: independent source verification, media rights confirmation, and redaction review.
- Human approval and publication did not occur.

## Execution Evidence

- Artifact timestamps span 11:12:52–11:16:56 UTC. This is a storage timestamp window, not measured end-to-end production time.
- Human editing minutes, total elapsed labor, and revision effort were not instrumented.
- No external provider API, ElevenLabs request, user media, render, or publication was used in this run. External provider spend for this run: $0; token and local compute costs were not measured.
- The Content Creator Head agent prepared the draft. The five specialist roles are in the official roster, but no separate specialist execution or review was recorded; the MCP exposes them only internally, not as individual client entry points.
- The FFmpeg diagnostic at `bus/evidence/2026-10-26/ffmpeg-skill-diagnostic.json` reports FFmpeg 7.0.2-static, a missing `drawtext` filter, and an unresolved security-version warning. No media was processed; rendering remains blocked pending independent patch verification or a safe runtime update.

> **Superseded (Phase 1–3, 2026-11-07):** synthetic-only render ทำงานได้จริง — locally rendered MP4s ที่ `central_bus/content/local_media/` ผ่าน ffprobe (Phase 1–3 frozen campaigns, SHA-verified); real user media ยัง blocked จน runtime ได้รับการ independent verification. ข้อความ "rendering remains blocked" ข้างบนเป็นประวัติ ณ 2026-10-26 (FIX F6, CEO-ordered 2026-11-07) — ดู `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md`

## What This Run Establishes

It establishes that the current Content campaign flow can store a versioned script, visual prompt, audio cue, and a human-gated review report. It does not establish that the content workflow is faster than a manual baseline, that solo builders want the product, or that the output is competitive with leading tools.

## Next Evidence Needed

1. Resolve LLM availability and complete the documented D3 evaluation without infrastructure-blocked cases.
2. Verify campaign claims, redaction, source handling, rights, and human Publish Gate behavior for internal readiness.
3. Clear the FFmpeg runtime gate if rendering is in scope; otherwise, keep rendering explicitly out of scope and label outputs as drafts.

> **Superseded (Phase 1–3, 2026-11-07):** synthetic-only render ทำงานได้จริง — locally rendered MP4s ที่ `central_bus/content/local_media/` ผ่าน ffprobe; real user media ยัง blocked จน runtime ได้รับการ independent verification (FIX F6, CEO-ordered 2026-11-07 — ประวัติ ณ 2026-10-26)
4. Complete independent reproduction of the system-readiness result.
5. Only after readiness is recorded, run target-audience reviews, a comparable manual baseline, and real-task tests for repeat use, referral, or payment. These are final-phase validation, not current prerequisites for engineering work.
