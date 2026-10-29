"""Content Creator department MCP server.

The server represents the department head as the client-facing boundary. The
five named production specialists are listed in ``profiles/INDEX.md`` and are
not exposed as separate client entry points.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .content_service import (
    ContentServiceError,
    build_ffmpeg_job_manifest as _build_ffmpeg_job_manifest,
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
    review_publish_gate as _review_publish_gate,
    save_human_edited_artifact as _save_human_edited_artifact,
    sop_resource,
)

mcp = FastMCP(
    "content-creator",
    instructions=(
        "SoloCorp Content Creator department. The head Sek receives briefs and "
        "coordinates the five internal specialists. Draft and prompt tools "
        "store artifacts without publishing. Client-generated artifacts retain "
        "client-supplied, unauthenticated provenance; this route never calls an LLM. "
        "Audio cue and lip-sync tools never "
        "call providers. Paid ElevenLabs voiceover requires approved=true. "
        "FFmpeg job tools store a validated plan and the identified MCP call result; "
        "they never execute FFmpeg or approve work. The local runtime gate remains required. "
        "Every publication requires recorded human approval for the current "
        "campaign version."
    ),
)


def _error(exc: Exception) -> str:
    return result_json({"status": "error", "error": type(exc).__name__, "message": str(exc)})


@mcp.tool()
def content_department_info() -> str:
    """Return the head, internal specialists, scope, and data root."""

    return result_json(department_info())


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


if __name__ == "__main__":
    mcp.run()
