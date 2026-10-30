# Content FFmpeg Job Bridge

## Scope

The Content Creator MCP stores a versioned plan for the installed `ffmpeg-skill` MCP and records a response returned by that server. It does not launch FFmpeg, copy media, call a cloud provider, approve a campaign, or publish content.

This contract remains specific to the FFmpeg-skill MCP bridge. The separate
`render_campaign_media_local` tool uses a local CLI pipeline for generated
synthetic assets only and records `provider: ffmpeg-cli`; its setup, runtime
gate, and output contract are documented in
`docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md`. Never submit its local CLI result
to `record_ffmpeg_job_result` as though it came from MCP.

The accepted argument subset is pinned to the `tools/list` response for `ffmpeg-skill` 2.17.1. The author and independent D2 evidence are:

- `bus/evidence/2026-10-26/ffmpeg-skill-mcp-builder-d2-authored.json`
- `bus/evidence/2026-10-26/ffmpeg-skill-mcp-builder-d2-independent.json`

## Tool Order And Contract

1. Call `build_ffmpeg_job_manifest` with the campaign's current script, its latest audio cue sheet, and 1-12 ordered operations.
2. After the runtime gate is cleared, the client calls each listed tool on the standalone `ffmpeg-skill` MCP with the exact manifest arguments.
3. Pass each unmodified MCP result to `record_ffmpeg_job_result` with the manifest's `campaign_id`, `job_id`, `campaign_version` as `job_version`, and the operation's zero-based index.

The manifest uses bridge `schema_version: 1`, provider contract `2.17.1`, lifecycle `scaffold`, execution `not_started`, and runtime gate `blocked_pending_independent_runtime_verification`. Results are bounded to 64 KiB and text/structured content; media payloads are rejected. A result is `reported_completed` only for `structuredContent.status == "completed"` and `exit_code == 0`; `isError`, failed status, or non-zero exit code is `reported_failure`; other shapes remain `unclassified`. Recording a result appends a campaign version but never approves or publishes it.

## Create A Job Manifest

Call `build_ffmpeg_job_manifest` with the current campaign video script, the latest audio cue sheet for that script, and ordered MCP calls:

```json
{
  "campaign_id": "campaign-id",
  "script_filename": "stored-script.md",
  "audio_cue_filename": "stored-audio-cue.md",
  "operations": [
    {
      "tool": "cut",
      "arguments": {
        "input": "/absolute/path/to/repo/central_bus/content/input.mp4",
        "output": "/absolute/path/to/repo/central_bus/content/preview.mp4",
        "start": "0",
        "duration": "10",
        "fast": true
      }
    }
  ]
}
```

Paths must be absolute and resolve inside the configured `central_bus/content/` directory. Inputs must be regular files or outputs from an earlier operation. Output files must not exist; overwrite is rejected. Symlinks, `argv`, `plan`, unknown tools, unknown arguments, and invalid types are rejected. Supported tools are `probe`, `check`, `cut`, `silence`, `loudness`, `fit`, `caption`, and `look`; each accepts only the field subset described by its 2.17.1 schema in the service implementation.

The response returns `job_id`, the manifest filename, and the campaign version that owns this job. The stored manifest starts at lifecycle `scaffold`, execution `not_started`, and `automatic_execution: false`.

Do not call the FFmpeg server with this plan while the local FFmpeg runtime gate is unresolved. In particular, do not send user media. The Content MCP does not enforce a remote server's runtime status; the operator must clear the runtime gate independently before executing any media operation.

## Record An MCP Result

After a planned operation has actually been called through the standalone `ffmpeg-skill` MCP, pass the returned `CallToolResult` without rewriting it to `record_ffmpeg_job_result`. Supply the exact `campaign_id`, `job_id`, and job version from the manifest response, plus the zero-based `operation_index` whose response is being recorded.

The result must contain text content or structured content. Image/resource blocks and media payloads are rejected. The complete bounded response is saved with its operation index and the tool name from the manifest. The bridge reports `reported_completed` only for `structuredContent.status == "completed"` with `exit_code == 0`; it reports failures from `isError`, `status == "failed"`, or a non-zero exit code. Ambiguous responses remain `unclassified`.

Recording a result appends a new campaign version and leaves its lifecycle at `scaffold`. It clears any prior review/approval state for the new version. Execution status never implies campaign approval, publication, or customer validation.

## Verification

Run the focused regression suite from the repository root:

```bash
source .venv/bin/activate && export PYTHONPATH=.
python -m pytest tests/test_content_mcp.py --tb=short --no-header -q --no-cov
```

The latest test-run evidence is stored in `bus/evidence/2026-10-26/ffmpeg-bridge-focused-tests.json`. Tests use an isolated temporary Central Bus and synthetic bytes only as path fixtures; they do not invoke FFmpeg or process media.

## Current Result And Blocker

No real bridge result has been recorded yet. The only actual FFmpeg MCP response is the D2 `check` failure for an intentionally missing `/tmp/.../input.mp4`; that path is outside `central_bus/content/` and cannot match a valid in-bus job manifest. Do not rewrite or attach that response to another operation. D2 proves MCP initialize, schema discovery, and missing-input error handling only; no media was processed. A future bridge round trip needs a new manifest and a real response whose arguments exactly match its operation, after the runtime safety gate is independently cleared.
