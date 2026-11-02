"""Content Creator department MCP server.

The server represents the department head as the client-facing boundary. The
five named production specialists are listed in ``profiles/INDEX.md`` and are
not exposed as separate client entry points.
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..auth import verify_scope

def _check_scope(required: str):
    """Check auth scope inside a tool function.
    Raises PermissionError if scope insufficient, which FastMCP converts to isError response.
    """
    key = os.environ.get("SOLOCORP_API_KEY")
    if not verify_scope(required, key):
        raise PermissionError(
            f"Requires scope '{required}' — set SOLOCORP_API_KEY with scope >= '{required}'\n"
            f"(current key: {'not set' if key is None else 'insufficient scope'})"
        )

from .content_service import (
    ContentServiceError,
    build_ffmpeg_job_manifest as _build_ffmpeg_job_manifest,
    build_ff_tracking_manifest as _build_ff_tracking_manifest,
    create_content_draft as _create_content_draft,
    create_video_script as _create_video_script,
    department_info,
    design_audio_experience as _design_audio_experience,
    design_visual_prompt as _design_visual_prompt,
    generate_voice_lipsync_prompt as _generate_voice_lipsync_prompt,
    generate_voiceover as _generate_voiceover,
    ingest_client_generated_artifact as _ingest_client_generated_artifact,
    record_ffmpeg_job_result as _record_ffmpeg_job_result,
    record_human_approval as _record_human_approval,
    result_json,
    render_campaign_media_local as _render_campaign_media_local,
    review_publish_gate as _review_publish_gate,
    save_human_edited_artifact as _save_human_edited_artifact,
    sop_resource,
)
from .media_service import render_campaign_with_concat as _render_campaign_with_concat
from ..module_registry import ModuleRegistry
from ..task_tracking import TaskTracker

_module_registry = ModuleRegistry()
_task_tracker = TaskTracker()

mcp = FastMCP(
    "content-creator",
    instructions=(
        "SoloCorp Content Creator department. The head Sek receives briefs and "
        "coordinates the five internal specialists. Draft and prompt tools "
        "store artifacts without publishing. Client-generated artifacts retain "
        "client-supplied, unauthenticated provenance; this route never calls an LLM. "
        "Audio cue and lip-sync tools never "
        "call providers. Paid ElevenLabs voiceover requires approved=true. "
        "FFmpeg job tools store a validated plan and the identified MCP call result. "
        "build_ff_tracking_manifest stores a validated visual plan only; the stock upstream renderer "
        "does not consume JSON manifests, and this tool never runs Rust or FFmpeg. "
        "render_campaign_media_local is a separate local CLI path limited to generated "
        "synthetic assets; it records local CLI provenance, never an MCP result, and never approves work. "
        "render_campaign_with_concat uses the local Concat MCP engine for project assembly and MP4 export; "
        "it writes media under central_bus/content, records hashes and ffprobe validation, and keeps review required. "
        "Real user media remains blocked until independent runtime verification. "
        "Every publication requires recorded human approval for the current "
        "campaign version."
    ),
)


def _error(exc: Exception) -> str:
    return result_json({"status": "error", "error": type(exc).__name__, "message": str(exc)})


@mcp.tool()
def content_department_info() -> str:
    """Return the head, internal specialists, scope, and data root."""

    from ..runtime_freshness import with_freshness

    return result_json(with_freshness(department_info()))


@mcp.tool()
def create_content_draft(
    title: str,
    topic: str,
    target_audience: str,
    content_type: str = "article",
    campaign_id: str = "",
    source_references: list[str] | None = None,
) -> str:
    """Create a content draft artifact and return a compact JSON manifest."""

    try:
        return result_json(
            _create_content_draft(
                title,
                topic,
                target_audience,
                content_type,
                campaign_id or None,
                source_references,
            )
        )
    except (ContentServiceError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def create_video_script(
    title: str,
    core_message: str,
    duration_seconds: int = 60,
    campaign_id: str = "",
    source_references: list[str] | None = None,
) -> str:
    """Create a visual-scene and voiceover script artifact."""

    try:
        return result_json(
            _create_video_script(
                title,
                core_message,
                duration_seconds,
                campaign_id or None,
                source_references,
            )
        )
    except (ContentServiceError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def design_visual_prompt(
    theme: str,
    platform: str,
    aspect_ratio: str = "16:9",
    campaign_id: str = "",
    source_references: list[str] | None = None,
) -> str:
    """Create an image-generation prompt artifact with an origin checklist."""

    try:
        return result_json(
            _design_visual_prompt(
                theme,
                platform,
                aspect_ratio,
                campaign_id or None,
                source_references,
            )
        )
    except (ContentServiceError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def generate_voiceover(
    title: str,
    text: str,
    voice_id: str,
    approved: bool = False,
    model_id: str = "eleven_v4",
    language_code: str = "th",
    campaign_id: str = "",
) -> str:
    """Create an explicitly approved ElevenLabs audio draft artifact."""

    try:
        return result_json(
            _generate_voiceover(
                title,
                text,
                voice_id,
                approved,
                model_id,
                language_code,
                campaign_id or None,
            )
        )
    except (ContentServiceError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def design_audio_experience(campaign_id: str, script_filename: str) -> str:
    """Create an audio cue sheet from a stored campaign video script."""

    try:
        return result_json(_design_audio_experience(campaign_id, script_filename))
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def generate_voice_lipsync_prompt(
    campaign_id: str, script_filename: str, voice_profile: str
) -> str:
    """Create a voice/lip-sync config without calling external providers."""

    try:
        return result_json(
            _generate_voice_lipsync_prompt(campaign_id, script_filename, voice_profile)
        )
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def review_publish_gate(campaign_id: str = "", filename: str = "") -> str:
    """Review a campaign or legacy single artifact without approving it."""

    try:
        return result_json(
            _review_publish_gate(filename or None, campaign_id or None)
        )
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def record_human_approval(
    campaign_id: str, version: str, approver_note: str
) -> str:
    """Record human approval for the exact reviewed campaign version."""

    try:
        return result_json(
            _record_human_approval(campaign_id, version, approver_note)
        )
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def save_human_edited_artifact(
    campaign_id: str,
    source_filename: str,
    edited_content: str,
    edit_note: str,
) -> str:
    """Store a reviewed human edit as a new versioned artifact."""

    try:
        return result_json(
            _save_human_edited_artifact(
                campaign_id, source_filename, edited_content, edit_note
            )
        )
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def ingest_client_generated_artifact(
    campaign_id: str,
    artifact_type: str,
    content: str,
    provenance: dict[str, str],
    source_references: list[str] | None = None,
) -> str:
    """Store content made by the client with self-reported provenance."""

    try:
        return result_json(
            _ingest_client_generated_artifact(
                campaign_id,
                artifact_type,
                content,
                provenance,
                source_references,
            )
        )
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def build_ffmpeg_job_manifest(
    campaign_id: str,
    script_filename: str,
    audio_cue_filename: str,
    operations: list[dict[str, Any]],
) -> str:
    """Store a validated ffmpeg-skill 2.17.1 call plan without executing it."""

    try:
        return result_json(
            _build_ffmpeg_job_manifest(
                campaign_id, script_filename, audio_cue_filename, operations
            )
        )
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError, TypeError) as exc:
        return _error(exc)


@mcp.tool()
def build_ff_tracking_manifest(
    campaign_id: str,
    scene_definitions: list[dict[str, Any]],
    camera_params: dict[str, Any] | None = None,
) -> str:
    """Store a validated ff-tracking scene plan; do not execute the renderer."""

    try:
        return result_json(
            _build_ff_tracking_manifest(campaign_id, scene_definitions, camera_params)
        )
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError, TypeError) as exc:
        return _error(exc)


@mcp.tool()
def render_campaign_media_local(campaign_id: str) -> str:
    """Render the latest 90-second synthetic storyboard locally; keep human approval required."""

    try:
        return result_json(_render_campaign_media_local(campaign_id))
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError, TypeError) as exc:
        return _error(exc)


@mcp.tool()
def render_campaign_with_concat(
    campaign_id: str,
    timeline_media: list[dict[str, Any]],
    captions: list[dict[str, Any]] | None = None,
    sound_delivery_filename: str = "",
    concat_project_path: str = "",
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    crf: int = 20,
) -> str:
    """Create or copy a Concat project, add generated assets and script-timed captions, then export an MP4."""

    try:
        return result_json(
            _render_campaign_with_concat(
                campaign_id,
                timeline_media,
                captions,
                sound_delivery_filename,
                concat_project_path,
                width,
                height,
                fps,
                crf,
            )
        )
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError, TypeError, ValueError) as exc:
        return _error(exc)


@mcp.tool()
def record_ffmpeg_job_result(
    campaign_id: str,
    job_id: str,
    job_version: str,
    operation_index: int,
    execution_result: dict[str, Any],
) -> str:
    """Store an actual ffmpeg-skill MCP response; this never approves or publishes."""

    try:
        return result_json(
            _record_ffmpeg_job_result(
                campaign_id, job_id, job_version, operation_index, execution_result
            )
        )
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError, TypeError) as exc:
        return _error(exc)


@mcp.resource("solocorp://content/sop")
def content_sop() -> str:
    """Return the Content Creator SOP and brand voice guidance."""

    return sop_resource()


@mcp.tool()
def module_registry_status() -> str:
    """Return module registry status for all SoloCorp department MCPs."""
    _check_scope("team")
    try:
        from ..runtime_freshness import with_freshness

        return result_json(with_freshness(_module_registry.status()))
    except Exception as exc:
        return _error(exc)



@mcp.tool()
def task_create(
    dept: str,
    module: str,
    brief: str,
    task_type: str = "content",
) -> str:
    """Create a new task record and return its task_id."""
    try:
        return result_json(_task_tracker.create(dept, module, brief, task_type))
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def task_get_status(task_id: str) -> str:
    """Return the current status record for a task."""
    try:
        record = _task_tracker.get(task_id)
        if record is None:
            return result_json({"status": "error", "error": "task_not_found", "message": f"task {task_id} not found"})
        return result_json(record)
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def task_list(dept: str = "") -> str:
    """List all tasks, optionally filtered by department."""
    try:
        records = _task_tracker.list_tasks(dept or None)
        return result_json({"count": len(records), "tasks": records})
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def task_update_status(
    task_id: str,
    status: str,
    result_ref: str = "",
    error_detail: str = "",
) -> str:
    """Update task status and optional result/error detail."""
    try:
        record = _task_tracker.update_status(
            task_id,
            status,
            result_ref or None,
            error_detail or None,
        )
        if record is None:
            return result_json({"status": "error", "error": "task_not_found", "message": f"task {task_id} not found"})
        return result_json(record)
    except Exception as exc:
        return _error(exc)





if __name__ == "__main__":
    mcp.run()
