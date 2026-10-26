# D1 — FFmpeg Job Bridge for the First Content Pilot

Author: CEO session draft
Date: 2026-10-26
Task: record FFmpeg job manifests and real execution results in the existing Content campaign flow
Status: D1 passed independent review; D2 runner passed independent rerun

## 1. Work

Extend the existing Content Creator MCP with a versioned media-job manifest and a separate result recorder for responses returned by the installed `ffmpeg-skill` MCP. This is an enabling task for `customer-value-proof-2026-10-26`; it should let the first campaign record either a real preview result or a real execution failure. The Content MCP must not run FFmpeg itself or claim an unobserved render succeeded.

## 2. Why an agent

The integration crosses MCP tool schemas, campaign storage, path validation, artifact provenance, and publish governance. A specialist whose profile covers Python/TypeScript MCP interface design and tool testing is a closer fit than a general full-stack implementer. This bridge only establishes a trustworthy production record; the video pilot separately measures time, editing effort, quality, cost, and audience response. Neither passing the bridge tests nor producing one internal clip proves customer demand.

## 3. Agent and tools

- Proposed specialist: `team-mcp-builder` (`profiles/16-neteng/neet/team/04-mcp-builder.SOUL.md`), dispatched through the NetEng head.
- The registry currently marks this specialist D0. Its first assignment is only a 50-150 line D2 mini-agent that performs a real stdio MCP initialize and tools/list call against the installed `ffmpeg-skill` server, validates required tool names/schema, makes one safe read-only `tools/call` to the `check` tool with a deliberately nonexistent fixture and asserts the expected validation response, records command/output/exit code, and supports an independent rerun.
- Use a newly created private temporary directory under `/tmp` for the fixture path. Never create the fixture file. Immediately before `tools/call`, assert that the path does not exist and is not a symlink; abort if either assertion fails. This avoids probing an existing file in shared `/tmp`.
- Preserve the author run and independent rerun in separate evidence files; the runner must not overwrite prior evidence. The missing-path call must not process media or write output.
- Bridge implementation may start only after the D2 mini-agent passes independent verification. The earlier handshake evidence did not satisfy this specialist's D2.
- Toolchain: Python 3.12 from `.venv`, the repository's existing `content_mcp.py` and `content_service.py`, and the locally installed FFmpeg MCP contract. Do not register a new or unverified Concat server.

## 4. Boundaries

- Keep the current Central Bus storage contract, campaign identity, versioning, and publish gate.
- Store only compact job manifests and result records; keep media binaries out of the 2 MiB payload store.
- The client invokes FFmpeg MCP tools. The Content MCP records the submitted real response and never shells out or fabricates execution status.
- Validate campaign IDs, allowed operations, arguments, and local asset paths against the verified FFmpeg MCP schema.
- Use synthetic media only while the local FFmpeg 7.0.2-static build's security patch status is unresolved and `drawtext` is unavailable. Do not process user media until the runtime is independently verified safe.
- Do not call ElevenLabs or other paid/external APIs, publish, or alter `opencode.json` wholesale.
- Do not treat the current pilot's AI-generated v5 script as human-edited. Keep lifecycle state and execution state separate.

## 5. Definition of success

1. The assigned specialist's D2 mini-agent passes the criteria in section 3 with an independent rerun and reproducible evidence.
2. A valid synthetic-media job plan becomes a versioned asset in the same campaign; unsafe paths and unsupported operations are rejected.
3. A real success or failure response from the standalone FFmpeg MCP is recorded accurately, without implying an unobserved render.
4. Publish approval remains human-gated and separate from execution status.
5. After the runtime gate is cleared, the first campaign can produce a preview or record a transparent failure, with actual time, revisions, and costs captured for comparison against a manual baseline.

## Source and review

- Customer-value protocol: `docs/plans/CONTENT-CUSTOMER-VALUE-PILOT.md`.
- First run and current blockers: `docs/content/2026-10-26-FIRST-CUSTOMER-VALUE-CONTENT-PILOT.md`.
- Current campaign state: v6 `review_required`; rendered locally with the FFmpeg CLI from synthetic media, not rendered through FFmpeg MCP, not approved or published, and not customer-validated. Latest gate recheck: `central_bus/content/campaign-campaign_proof_ch1_power_of_one-publish-gate-v6_20261026T140732113447Z.md`.
- First independent D1 review returned the earlier draft for agent-fit and customer-value linkage. The independent reviewer confirmed this revision addresses both points.
- Independent reviewer `review_ffmpeg_d1` passed this revision after the unique private temporary directory and immediate absent-path/non-symlink checks were added.
- D2 author run: `bus/evidence/2026-10-26/ffmpeg-skill-mcp-builder-d2-authored.json`; independent rerun: `bus/evidence/2026-10-26/ffmpeg-skill-mcp-builder-d2-independent.json`. Both exited 0, used separate evidence files, verified the 9 required tool schemas, and called the read-only `check` tool against an absent private fixture. This certifies the D2 runner only; it does not validate video rendering or the planned Content MCP bridge.
