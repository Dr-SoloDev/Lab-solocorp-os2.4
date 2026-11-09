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
    build_ff_tracking_manifest as _build_ff_tracking_manifest,
    create_content_draft as _create_content_draft,
    create_video_script as _create_video_script,
    department_info,
    design_audio_experience as _design_audio_experience,
    design_visual_prompt as _design_visual_prompt,
    generate_voice_lipsync_prompt as _generate_voice_lipsync_prompt,
    generate_voiceover as _generate_voiceover,
    generate_image as _generate_image,
    ingest_client_generated_artifact as _ingest_client_generated_artifact,
    media_production_skill_resource as _media_production_skill_resource,
    record_ffmpeg_job_result as _record_ffmpeg_job_result,
    record_human_approval as _record_human_approval,
    remove_campaign_asset as _remove_campaign_asset,
    result_json,
    render_campaign_media_local as _render_campaign_media_local,
    review_publish_gate as _review_publish_gate,
    save_human_edited_artifact as _save_human_edited_artifact,
    sop_resource,
)
from .media_service import (
    list_earshot_sounds as _list_earshot_sounds,
    render_campaign_sfx as _render_campaign_sfx,
    render_campaign_with_concat as _render_campaign_with_concat,
    review_campaign_audio as _review_campaign_audio,
)
from ..module_registry import ModuleRegistry
from ..task_tracking import TaskTracker

_module_registry: ModuleRegistry | None = None
_task_tracker = TaskTracker()


def _registry() -> ModuleRegistry:
    """Create the registry on first use, seeded with this department only.

    Importing this module must not touch the filesystem: a standalone
    department MCP that a host merely lists must not create a registry file,
    and when it does need one it declares only the module it owns
    (PRD:155, FR-07; CMD-006 §4.1). The old module-scope construction wrote all
    five modules on import.
    """

    global _module_registry
    if _module_registry is None:
        _module_registry = ModuleRegistry(seed_module_ids=("content-creator",))
    return _module_registry


mcp = FastMCP(
    "content-creator",
    instructions=(
        "SoloCorp Content Creator department. The head Sek receives briefs and "
        "coordinates the five internal specialists. Draft and prompt tools "
        "store artifacts without publishing. Client-generated artifacts retain "
        "client-supplied, unauthenticated provenance; this route never calls an LLM. "
        "Audio cue and lip-sync tools never "
        "call providers. A direct user request to create an ElevenLabs voiceover "
        "authorizes the requested credit use; do not ask for a separate approval "
        "or generate unrequested variants. "
        "Sound Designer is an internal Content specialist; Earshot tools are exposed "
        "through this Content MCP, not as a separate department. For the Concat audio "
        "workflow follow this order: create/finalize the video script, create its audio "
        "cue sheet, optionally list and render SFX (keep sound_delivery_filename), "
        "render with Concat, review the final audio/video with Earshot, run the publish "
        "gate, then record human approval for the exact current version. Stop on an "
        "error; never silently skip a requested sound stage or publish automatically. "
        "The synthetic-only local-media renderer is a separate path and must not be "
        "mixed with the Concat workflow. "
        "FFmpeg job tools store a validated plan and the identified MCP call result. "
        "build_ff_tracking_manifest stores a validated visual plan only; the stock upstream renderer "
        "does not consume JSON manifests, and this tool never runs Rust or FFmpeg. "
        "render_campaign_media_local is a separate local CLI path limited to generated "
        "synthetic assets; it records local CLI provenance, never an MCP result, and never approves work. "
        "render_campaign_with_concat uses the local Concat MCP engine for project assembly and MP4 export; "
        "it writes media under central_bus/content, records hashes and ffprobe validation, and keeps review required. "
        "Real user media remains blocked until independent runtime verification. "
        "Every publication requires recorded human approval for the current "
        "campaign version. For video narration, read the internal resource "
        "axis://content/skills/media-production: use one continuous full-length "
        "voice track, choose Concat or local-media rendering before generating assets, "
        "and never mix the two workflows. generate_image makes one paid image call "
        "(NVIDIA NIM FLUX.3 Klein by default, legacy OpenRouter via provider=openrouter) "
        "and stores the image under central_bus/content for human review; it never "
        "publishes. NIM output is always JPEG (a requested png is saved as .jpg)."
    ),
)


def _error(exc: Exception) -> str:
    return result_json(
        {"status": "error", "error": type(exc).__name__, "message": str(exc)}
    )


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
    model_id: str = "eleven_v4",
    language_code: str = "th",
    campaign_id: str = "",
) -> str:
    """Create the specifically requested ElevenLabs audio draft artifact."""

    try:
        return result_json(
            _generate_voiceover(
                title,
                text,
                voice_id,
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
def sound_list_earshot_sfx(category: str = "", kind: str = "") -> str:
    """List local Earshot sound-bank IDs for Content campaign sound design."""

    try:
        return result_json(_list_earshot_sounds(category, kind))
    except (ContentServiceError, OSError, TypeError, ValueError) as exc:
        return _error(exc)


@mcp.tool()
def sound_render_campaign_sfx(
    campaign_id: str,
    sound: str,
    start_seconds: float = 0,
    duration_seconds: float | None = None,
    apex_seconds: float | None = None,
    pitch: str = "",
    peak_db: float = -1.0,
    volume: float = 1.0,
) -> str:
    """Render and audit one local Earshot SFX stem for a Content campaign."""

    try:
        return result_json(
            _render_campaign_sfx(
                campaign_id,
                sound,
                start_seconds,
                duration_seconds,
                apex_seconds,
                pitch,
                peak_db,
                volume,
            )
        )
    except (
        ContentServiceError,
        FileNotFoundError,
        OSError,
        UnicodeError,
        TypeError,
        ValueError,
    ) as exc:
        return _error(exc)


@mcp.tool()
def sound_review_campaign_audio(
    campaign_id: str,
    audio_path: str,
    video_path: str = "",
    cue_times: list[float] | None = None,
) -> str:
    """Measure final campaign audio and cue timing with local Earshot."""

    try:
        return result_json(
            _review_campaign_audio(campaign_id, audio_path, video_path, cue_times)
        )
    except (
        ContentServiceError,
        FileNotFoundError,
        OSError,
        UnicodeError,
        TypeError,
        ValueError,
    ) as exc:
        return _error(exc)


@mcp.tool()
def generate_image(
    prompt: str,
    aspect_ratio: str = "16:9",
    resolution: str = "4K",
    format: str = "jpeg",
    reference_image_path: str | None = None,
    output_filename: str | None = None,
    provider: str = "nvidia",
) -> str:
    """Generate one image; store it, never publish.

    provider="nvidia" (default) calls NVIDIA NIM FLUX.3 Image Klein
    ({prompt, image[], width, height, steps}, 110s timeout, single attempt).
    Output is always JPEG; a requested png is saved as .jpg with an
    actual_format note. provider="openrouter" keeps the legacy
    chat-completions flow (paid single request ~USD 0.008, 90s timeout).
    Both providers: no retries so costs never double. Saves the image under
    central_bus/content with a SHA-256 hash and a provenance manifest
    (license_note records FLUX Kommunity v1.0 non-commercial terms for the
    NIM path). The result stays gated (gate_passed false, human review
    required); this MCP does not publish or approve.
    """

    try:
        return result_json(
            _generate_image(
                prompt,
                aspect_ratio,
                resolution,
                format,
                reference_image_path or None,
                output_filename or None,
                provider,
            )
        )
    except (
        ContentServiceError,
        FileNotFoundError,
        OSError,
        UnicodeError,
        TypeError,
        ValueError,
    ) as exc:
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
        return result_json(_review_publish_gate(filename or None, campaign_id or None))
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def record_human_approval(campaign_id: str, version: str, approver_note: str) -> str:
    """Record human approval for the exact reviewed campaign version."""

    try:
        return result_json(_record_human_approval(campaign_id, version, approver_note))
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
    except (
        ContentServiceError,
        FileNotFoundError,
        OSError,
        UnicodeError,
        TypeError,
    ) as exc:
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
    except (
        ContentServiceError,
        FileNotFoundError,
        OSError,
        UnicodeError,
        TypeError,
    ) as exc:
        return _error(exc)


@mcp.tool()
def render_campaign_media_local(
    campaign_id: str,
    script_filename: str = "",
    tts_fallback: str = "",
    visual_fallback: str = "",
) -> str:
    """Render the latest 90-second synthetic storyboard locally; keep human approval required.

    Omit ``script_filename`` to render the latest campaign video script
    (existing default). Pass it to render that exact ``video_script`` asset
    instead — use this when a newer scaffold script would otherwise be
    picked. The script must belong to this campaign and use six 15-second
    scenes or ten 10-second episodes.

    ``tts_fallback`` / ``visual_fallback`` are opt-in and default to abort
    (fail fast): pass ``tts_fallback="silence"`` to substitute a silent
    buffer per failed Piper scene, or ``visual_fallback="static_card"`` to
    substitute a solid 1080x1920 card per failed Three.js scene. Fallback
    renders complete as degraded and stay visibly flagged in the publish
    gate — never as a clean pass.
    """

    try:
        return result_json(
            _render_campaign_media_local(
                campaign_id,
                script_filename or None,
                tts_fallback or None,
                visual_fallback or None,
            )
        )
    except (
        ContentServiceError,
        FileNotFoundError,
        OSError,
        UnicodeError,
        TypeError,
    ) as exc:
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
    except (
        ContentServiceError,
        FileNotFoundError,
        OSError,
        UnicodeError,
        TypeError,
        ValueError,
    ) as exc:
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
    except (
        ContentServiceError,
        FileNotFoundError,
        OSError,
        UnicodeError,
        TypeError,
    ) as exc:
        return _error(exc)


@mcp.tool()
def remove_campaign_asset(campaign_id: str, filename: str, reason: str = "") -> str:
    """Remove one asset from a campaign manifest so later publish-gate reviews
    only see remaining assets. Payload stays on the bus for audit; the campaign
    version bumps and any prior review/approval is reset."""

    try:
        return result_json(_remove_campaign_asset(campaign_id, filename, reason))
    except (ContentServiceError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.resource("axis://content/sop")
def content_sop() -> str:
    """Return the Content Creator SOP and brand voice guidance."""

    return sop_resource()


@mcp.resource("axis://content/skills/media-production")
def content_media_production_skill() -> str:
    """Return the internal Content Creator media production skill."""

    return _media_production_skill_resource()


@mcp.tool()
def module_registry_status() -> str:
    """Return module registry status for the modules this config declares.

    Public by design: read-only, local, and free of secrets, so a standalone
    department MCP answers it without SOLOCORP_API_KEY (CMD-006 §4.2).
    """

    try:
        from ..runtime_freshness import with_freshness

        return result_json(with_freshness(_registry().status()))
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
        if dept != "content" or module != "content-creator":
            return result_json(
                {
                    "status": "error",
                    "error": "task_scope_violation",
                    "message": "Content MCP tasks must use dept='content' and module='content-creator'.",
                }
            )
        return result_json(_task_tracker.create(dept, module, brief, task_type))
    except Exception as exc:
        return _error(exc)


def _is_content_task(record: dict[str, Any] | None) -> bool:
    return bool(
        record
        and record.get("dept") == "content"
        and record.get("module") == "content-creator"
    )


def _task_not_found(task_id: str) -> str:
    return result_json(
        {
            "status": "error",
            "error": "task_not_found",
            "message": f"task {task_id} not found",
        }
    )


@mcp.tool()
def task_get_status(task_id: str) -> str:
    """Return the current status record for a task."""
    try:
        record = _task_tracker.get(task_id)
        if not _is_content_task(record):
            return _task_not_found(task_id)
        return result_json(record)
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def task_list(dept: str = "") -> str:
    """List Content Creator tasks only."""
    try:
        if dept not in {"", "content"}:
            return result_json(
                {
                    "status": "error",
                    "error": "task_scope_violation",
                    "message": "Content MCP can list only dept='content' tasks.",
                }
            )
        records = _task_tracker.list_tasks("content")
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
        if not _is_content_task(_task_tracker.get(task_id)):
            return _task_not_found(task_id)
        record = _task_tracker.update_status(
            task_id,
            status,
            result_ref or None,
            error_detail or None,
        )
        if record is None:
            return result_json(
                {
                    "status": "error",
                    "error": "task_not_found",
                    "message": f"task {task_id} not found",
                }
            )
        return result_json(record)
    except Exception as exc:
        return _error(exc)


if __name__ == "__main__":
    mcp.run()
