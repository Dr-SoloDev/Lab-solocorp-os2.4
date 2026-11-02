"""Sound department MCP adapter over local Earshot tools and the Content Bus."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .content_service import ContentServiceError, result_json
from .media_service import (
    list_earshot_sounds as _list_earshot_sounds,
    render_campaign_sfx as _render_campaign_sfx,
    review_campaign_audio as _review_campaign_audio,
)


mcp = FastMCP(
    "sound-studio",
    instructions=(
        "Sound design tools for SoloCorp campaigns. All audio stays local. "
        "Audio review calls only Earshot measure and timeline; SFX calls only sfx_list, "
        "sfx_render and measure. Reports and generated stems are recorded in the Content Central Bus "
        "with local paths and SHA-256 checksums. This server never calls Gemini, approves, or publishes."
    ),
)


def _error(exc: Exception) -> str:
    return result_json({"status": "error", "error": type(exc).__name__, "message": str(exc)})


@mcp.tool()
def sound_review_campaign_audio(
    campaign_id: str,
    audio_path: str,
    video_path: str = "",
    cue_times: list[float] | None = None,
) -> str:
    """Measure audio and review event timing with local Earshot; send the report to Content through Central Bus."""

    try:
        return result_json(_review_campaign_audio(campaign_id, audio_path, video_path, cue_times))
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError, TypeError, ValueError) as exc:
        return _error(exc)


@mcp.tool()
def sound_list_earshot_sfx(category: str = "", kind: str = "") -> str:
    """List local Earshot sound-bank IDs for matching film cues."""

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
    """Render and audit one Earshot SFX stem, then publish its manifest to Content Central Bus."""

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
    except (ContentServiceError, FileNotFoundError, OSError, UnicodeError, TypeError, ValueError) as exc:
        return _error(exc)


@mcp.tool()
def sound_department_info() -> str:
    """Report the Sound Studio adapter scope, its tools, and whether this process is current.

    Sound Studio has no department head in ``profiles/INDEX.md`` — it is an
    adapter over local Earshot tools that Content drives. This tool reports
    that honestly instead of inventing an owner, and carries the same
    ``runtime`` staleness block as the other department info tools.
    """

    from ..runtime_freshness import with_freshness

    return result_json(
        with_freshness(
            {
                "status": "ok",
                "department": "sound-studio",
                "head": None,
                "owner_note": (
                    "No department head registered; specialist audio-designer-sound (ซาวด์) "
                    "sits under Content in profiles/INDEX.md."
                ),
                "scope": "Local Earshot measure/timeline and SFX rendering; no provider calls.",
                "tools": [
                    "sound_department_info",
                    "sound_list_earshot_sfx",
                    "sound_render_campaign_sfx",
                    "sound_review_campaign_audio",
                ],
                "data_root": "central_bus/content",
            }
        )
    )


if __name__ == "__main__":
    mcp.run()
