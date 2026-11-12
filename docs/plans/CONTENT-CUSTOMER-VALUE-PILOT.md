# Content Creator Customer-Value Pilot

Status: engineering phase; customer validation deferred to the final phase
Original plan date: 2026-10-26
Owner sequencing decision: 2026-10-29

> **Superseded (Phase 1–3, 2026-11-07):** synthetic-only render ทำงานได้จริง — locally rendered MP4s ที่ `central_bus/content/local_media/` ผ่าน ffprobe; real user media ยัง blocked จน runtime ได้รับการ independent verification. แผนเดิม (lines 37, 80, 97: "clear the FFmpeg runtime gate", "local preview cut after the gate is cleared", "production rendering has not been validated") เป็นประวัติ ณ 2026-10-26 — FIX F6 (CEO-ordered 2026-11-07). ดู `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md`

## Purpose

Make the Content Creator system work end to end before asking customers or target users to evaluate it. Defer audience interviews, demand research, willingness-to-pay questions, and adoption tests until the system-readiness gate below is met. This is a sequencing decision, not a decision to drop validation permanently.

The current work tests whether the system can reliably turn a brief into a traceable, reviewable content package. It does not test whether customers want the product.

## Initial assumptions

- Intended audience: Thai-speaking independent developers and solo founders. Keep this as an unvalidated hypothesis until the final validation phase.
- Format: one 30-45 second vertical video in Thai for short-form platforms.
- Topic: showing how a small builder can turn a clear brief into a structured, reviewable content package.
- Voice provider: no ElevenLabs call or paid generation during this pilot unless the Owner explicitly authorizes it.
- Publication: no automatic publishing; the human publish gate remains required.

## Hypothesis

For this narrowly defined task, the Content Creator workflow can produce an audience-relevant video package at a lower production cost or with less human editing time while preserving factual accuracy and acceptable creative quality.

This is a testable hypothesis, not a claim that the product has already achieved customer value or can outperform every leading editing product.

Hold this hypothesis for Phase 3. Phases 1-2 test whether the system works, not whether the market wants it.

## Evidence sequence

### Phase 1 — System readiness (current)

- Complete the supported workflow from brief intake through content generation, artifact storage, manifest/version tracking, and Publish Gate review.
- Verify the workflow in supported MCP clients, including recoverable errors when the LLM or another dependency is unavailable.
- Meet the documented D3 certification criteria and complete independent reproduction before calling the workflow operational.
- Verify path safety, redaction, source handling, and human approval behavior.
- If video rendering is in scope, independently clear the FFmpeg runtime and render path. Otherwise, document rendering as out of scope and label output as a script/package draft.
- Use synthetic or internal briefs only. Do not recruit target users, run surveys, ask willingness-to-pay questions, or collect customer-demand signals in this phase.

### Phase 2 — Internal operational proof

- Repeat representative workflows and record completed runs, failures, recovery, elapsed time, revisions, and actual provider and compute costs.
- Keep evidence tied to run logs and artifacts. Separate infrastructure failures from agent behavior in D3 results.
- Do not use internal results to claim customer value, demand, or superiority over other products.

### Phase 3 — Customer validation (final phase; deferred)

Start only after the system-readiness gate is documented and independently reproduced:

- Ask 3-5 target-audience reviewers what they understood, whether the task is relevant, and what they would change. Treat the small sample as formative, not representative market research.
- Compare the SoloCorp workflow with a manual baseline using the same brief and evaluation rubric; disclose differences in scope and tools.
- Test a real user task and look for repeat use, referral, or payment evidence before making a customer-value claim.
- If the Owner publishes an approved asset, track retention, completion, shares, saves, and substantive comments. Views or likes alone do not prove product value.

## System-readiness gate

Customer validation stays deferred until all applicable conditions are documented:

1. The core workflow completes end to end in a supported client on repeat runs.
2. LLM and dependency failures are handled without fabricated output, and D3 meets its documented pass criteria.
3. An independent checker reproduces the required result under the certification runbook.
4. Artifact lineage, path boundaries, redaction, source checks, and human Publish Gate behavior work as specified.
5. Video rendering is independently cleared if included in scope; otherwise, the limitation is explicit and no finished render is promised.

Passing this gate means the system is ready for external validation. It does not mean customer demand or willingness to pay has been proven.

## First-run protocol

- Produce one 30-45 second Thai vertical draft for solo developers/builders: script, scene direction, visual prompt, audio cues, and publish-gate report, all linked to one campaign.
- Run the same internal or synthetic brief repeatedly through the system and verify the expected artifacts, boundaries, and Publish Gate behavior.
- Record start/finish timestamps, tool failures, recovery, revisions, and actual provider and compute spend for each run.
- Do not contact target-audience reviewers or ask whether they would use or pay for the product during this phase; defer those questions to Phase 3.
- Use the internal acceptance criteria and D3 checks for readiness. Defer audience scores and reviewer notes to Phase 3.
- If the local render gate is not cleared, label the deliverable as a script/package draft and do not imply a finished video exists.

## Pilot deliverables

1. A source-grounded video script and storyboard.
2. Visual and audio cue sheets linked to the same campaign.
3. A local preview cut after the FFmpeg runtime gate is cleared.
4. A publish-gate report with no approval implied.
5. A short internal evidence record containing actual time, cost, revisions, failures, and recovery behavior.

## Measurement

- Record elapsed time from brief to reviewable draft.
- Record human editing minutes, revision rounds, tool failures, and direct external cost.
- During the engineering phase, measure technical completion, failures, recovery, latency, revisions, and actual cost using internal or synthetic runs.
- If the Owner publishes an approved asset after readiness, add platform retention, completion, shares, saves, and substantive comments. Do not treat views or likes alone as proof of product value.
- Defer audience scores and the manual baseline to Phase 3 after readiness is recorded.

## Guardrails and current readiness

- Keep claims tied to repository evidence or mark them unverified.
- Keep the artifact in review-required status until a human approves the exact campaign version.
- Do not use user media until the local FFmpeg build is updated or its patch status is independently verified.
- The diagnostic shows FFmpeg 7.0.2-static, a missing drawtext filter, and no Concat CLI. Core editing tools are exposed over stdio MCP, but production rendering has not been validated. See bus/evidence/2026-10-26/ffmpeg-skill-diagnostic.json.
- Do not claim customer validation from internal runs, a single clip, views, or likes. External feedback is deferred to Phase 3.

## Next decision

Resolve the current system-readiness blockers first, including LLM availability for D3 and the FFmpeg scope decision. Do not schedule external feedback or willingness-to-pay research until the readiness gate is met and independently reproduced. Run customer validation only in Phase 3.
