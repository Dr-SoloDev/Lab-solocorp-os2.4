# Content Creator Customer-Value Pilot

Status: pilot brief, not customer validation
Date: 2026-10-26

## Purpose

Use one short-form video to test whether SoloCorp OS helps a solo builder produce a reviewable content asset with acceptable quality, less hands-on time, and low cost.

## Initial assumptions

- Audience: Thai-speaking independent developers and solo founders. This is inferred from the Owner's stated mission and still needs confirmation through audience feedback.
- Format: one 30-45 second vertical video in Thai for short-form platforms.
- Topic: showing how a small builder can turn a clear brief into a structured, reviewable content package.
- Voice provider: no ElevenLabs call or paid generation during this pilot unless the Owner explicitly authorizes it.
- Publication: no automatic publishing; the human publish gate remains required.

## Hypothesis

For this narrowly defined task, the Content Creator workflow can produce an audience-relevant video package at a lower production cost or with less human editing time while preserving factual accuracy and acceptable creative quality.

This is a testable hypothesis, not a claim that the product has already achieved customer value or can outperform every leading editing product.

## What this pilot can prove

Keep three evidence levels separate:

1. **Production feasibility:** Can the current Content Creator workflow produce a coherent, reviewable package? Record elapsed time, human editing time, revision rounds, tool failures, and direct cost.
2. **Audience signal:** Do 3-5 independent people from the target audience understand the message, find it relevant, and identify a real use for the workflow? This is formative feedback, not proof of market demand.
3. **Customer value:** Has a target user completed a real task with the workflow and chosen to use it again, recommend it, or pay for it? Do not claim this from an internally produced clip or views alone.

The first video should invite a concrete response from solo builders about a costly content-production task. It must not claim that SoloCorp already matches leading products or saves time until the pilot measures that outcome against a comparable manual baseline.

## First-run protocol

- Produce one 30-45 second Thai vertical draft for solo developers/builders: script, scene direction, visual prompt, audio cues, and publish-gate report, all linked to one campaign.
- Produce a comparable manual baseline from the same brief and scope. Use the same reviewer rubric for both; conceal which workflow produced each package when practical.
- Record start/finish timestamps and human editing minutes for each stage; record actual revisions, failures, and external spend. Use zero for external spend only after confirming no paid provider was called.
- Ask 3-5 target-audience reviewers the same questions: what they understood, whether the problem is relevant, what they would change, and whether they would use a workflow like this for a real task. Preserve raw notes without identifying details unless reviewers consent.
- Score clarity, relevance, credibility, pacing, and audio/video quality from 1 to 5. Report the sample size and raw distribution; do not present the average as statistically representative.
- If the local render gate is not cleared, label the deliverable as a script/package draft and do not imply a finished video exists.

## Pilot deliverables

1. A source-grounded video script and storyboard.
2. Visual and audio cue sheets linked to the same campaign.
3. A local preview cut after the FFmpeg runtime gate is cleared.
4. A publish-gate report with no approval implied.
5. A short evidence record containing actual time, cost, revisions, failures, and reviewer feedback.

## Measurement

- Record elapsed time from brief to reviewable draft.
- Record human editing minutes, revision rounds, tool failures, and direct external cost.
- Have 3-5 people from the intended audience review the draft. Ask what they understood, whether it feels credible and relevant, and what they would change.
- Score clarity, relevance, credibility, pacing, and audio/video quality from 1 to 5. Keep each reviewer's raw notes.
- If the Owner later publishes it, add platform retention, completion, shares, saves, and substantive comments. Do not treat views or likes alone as proof of product value.
- Compare against the manual baseline using the same brief and evaluation rubric; disclose any differences in scope or tools.

## Guardrails and current readiness

- Keep claims tied to repository evidence or mark them unverified.
- Keep the artifact in review-required status until a human approves the exact campaign version.
- Do not use user media until the local FFmpeg build is updated or its patch status is independently verified.
- The diagnostic shows FFmpeg 7.0.2-static, a missing drawtext filter, and no Concat CLI. Core editing tools are exposed over stdio MCP, but production rendering has not been validated. See bus/evidence/2026-10-26/ffmpeg-skill-diagnostic.json.
- Do not claim customer validation from a single internally produced clip. The first clip is a learning sample; audience feedback supplies the first external evidence.

## Next decision

Complete the first script and cue sheets as a reviewable campaign draft, then collect formative audience feedback. Clear or independently verify the FFmpeg runtime before rendering a real clip. Treat customer value as unproven until a target user completes a real workflow and shows a repeat-use, referral, or payment signal.
