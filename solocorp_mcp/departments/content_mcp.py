"""Content Creator department MCP server.

The server represents the department head as the client-facing boundary.
Copywriter, Visual Creator, Video Editor, and Trend Scout are internal roles;
they are described in ``content_department_info`` but are not exposed as
independent client entry points.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .content_service import (
    ContentServiceError,
    create_content_draft as _create_content_draft,
    create_video_script as _create_video_script,
    department_info,
    design_visual_prompt as _design_visual_prompt,
    generate_voiceover as _generate_voiceover,
    result_json,
    review_publish_gate as _review_publish_gate,
    sop_resource,
)

mcp = FastMCP(
    "content-creator",
    instructions=(
        "SoloCorp Content Creator department. The head Sek receives briefs and "
        "coordinates internal specialists. Tools create drafts only; every "
        "publication requires human approval through the Publish Gate."
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
    title: str, topic: str, target_audience: str, content_type: str = "article"
) -> str:
    """Create a content draft artifact and return a compact JSON manifest."""

    try:
        return result_json(
            _create_content_draft(title, topic, target_audience, content_type)
        )
    except (ContentServiceError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def create_video_script(
    title: str, core_message: str, duration_seconds: int = 60
) -> str:
    """Create a visual-scene and voiceover script artifact."""

    try:
        return result_json(_create_video_script(title, core_message, duration_seconds))
    except (ContentServiceError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def design_visual_prompt(
    theme: str, platform: str, aspect_ratio: str = "16:9"
) -> str:
    """Create an image-generation prompt artifact with an origin checklist."""

    try:
        return result_json(_design_visual_prompt(theme, platform, aspect_ratio))
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
) -> str:
    """Create an explicitly approved ElevenLabs audio draft artifact."""

    try:
        return result_json(
            _generate_voiceover(
                title, text, voice_id, approved, model_id, language_code
            )
        )
    except (ContentServiceError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def review_publish_gate(filename: str) -> str:
    """Review an artifact and create a human-approval gate report."""

    try:
        return result_json(_review_publish_gate(filename))
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.resource("solocorp://content/sop")
def content_sop() -> str:
    """Return the Content Creator SOP and brand voice guidance."""

    return sop_resource()


if __name__ == "__main__":
    mcp.run()
