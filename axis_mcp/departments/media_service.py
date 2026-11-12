"""Local Concat rendering and Central Bus media handoff services."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from axis_mcp import bus_store

from . import content_service
from .mcp_stdio import MCPStdioClient, MCPStdioError


CONCAT_DEFAULT = Path.home() / ".opencode" / "concat" / "Concat-0.2.8-x86_64.AppImage"
CONCAT_MAX_MEDIA = 120
CONCAT_MAX_CAPTIONS = 1000
_VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
_CAPTION_ROW = re.compile(
    r"(?m)^\|\s*(\d{1,5})\s*[–—-]\s*(\d{1,5})s\s*\|\s*[^|]*\|\s*([^|]+?)\s*\|\s*$"
)


def _content_root() -> Path:
    return (bus_store.BUS_ROOT / "content").resolve()


def _resolve_content_path(value: Any, label: str, *, must_exist: bool = True) -> Path:
    if not isinstance(value, str) or not value.strip() or len(value) > 2_000:
        raise content_service.ContentServiceError(f"{label} must be a local Central Bus path")
    if any(ord(char) < 32 for char in value):
        raise content_service.ContentServiceError(f"{label} contains a control character")
    candidate = Path(value.strip())
    if ".." in candidate.parts:
        raise content_service.ContentServiceError(f"{label} cannot contain parent-directory segments")
    if not candidate.is_absolute():
        if candidate.parts[:1] == ("central_bus",):
            candidate = bus_store.ROOT / candidate
        elif candidate.parts[:1] == ("content",):
            candidate = bus_store.BUS_ROOT / candidate
        else:
            candidate = _content_root() / candidate
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as exc:
        raise content_service.ContentServiceError(f"{label} does not exist") from exc
    root = _content_root()
    if resolved == root or not resolved.is_relative_to(root):
        raise content_service.ContentServiceError(f"{label} must be inside central_bus/content")

    cursor = candidate
    while cursor != root and cursor != cursor.parent:
        if cursor.is_symlink():
            raise content_service.ContentServiceError(f"{label} cannot use symlinks")
        cursor = cursor.parent
    if cursor != root:
        raise content_service.ContentServiceError(f"{label} must be inside central_bus/content")
    return resolved


def _safe_task_id(campaign_key: str, kind: str, job_id: str) -> str:
    return content_service._asset_task_id(campaign_key, kind, job_id)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _earshot_result_payload(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    for marker in ("JSON (compact):", "JSON:"):
        position = value.rfind(marker)
        if position >= 0:
            try:
                return json.loads(value[position + len(marker) :].strip())
            except json.JSONDecodeError:
                break
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _store_campaign_json(
    campaign_id: str,
    artifact_type: str,
    label: str,
    payload: dict[str, Any],
    dependencies: list[str],
    *,
    expected_campaign_version: str | None = None,
) -> dict[str, Any]:
    asset = {
        "task_id": _safe_task_id(campaign_id, artifact_type, label),
        "content": json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        "extension": "json",
        "type": artifact_type,
        "lifecycle_state": "client_generated",
        "dependencies": dependencies,
        "media_rights_status": "human_confirmation_required",
        "metadata": {
            "provider": payload.get("provider"),
            "job_id": payload.get("job_id"),
            "execution_status": payload.get("execution_status"),
        },
    }
    if expected_campaign_version is not None:
        asset["expected_campaign_version"] = expected_campaign_version
    return content_service._store_assets(
        campaign_id,
        [asset],
    )[0]


def _latest_script(campaign: dict[str, Any], campaign_id: str) -> tuple[dict[str, Any], str]:
    asset = next(
        (item for item in reversed(campaign.get("assets", [])) if item.get("type") == "video_script"),
        None,
    )
    if asset is None:
        raise content_service.ContentServiceError("campaign has no video script")
    fetched = bus_store.fetch_from_bus(content_service.DEPARTMENT, asset["filename"])
    return asset, fetched["content"]


def _latest_audio_cue(campaign: dict[str, Any], script_asset: dict[str, Any]) -> dict[str, Any]:
    cue = next(
        (
            asset
            for asset in reversed(campaign.get("assets", []))
            if asset.get("type") == "audio_cue_sheet"
            and script_asset["filename"] in asset.get("dependencies", [])
        ),
        None,
    )
    if cue is None:
        raise content_service.ContentServiceError(
            "create an audio cue sheet for the latest video script before continuing"
        )
    return cue


def _script_captions(script: str) -> list[dict[str, Any]]:
    result = []
    for match in _CAPTION_ROW.finditer(script):
        start, end = int(match.group(1)), int(match.group(2))
        text = match.group(3).strip()
        if end > start and text:
            result.append({"start": start, "end": end, "text": text})
    return result


def _validate_media_items(value: Any, *, require_video: bool = True) -> list[dict[str, Any]]:
    minimum_items = 1 if require_video else 0
    if not isinstance(value, list) or not minimum_items <= len(value) <= CONCAT_MAX_MEDIA:
        raise content_service.ContentServiceError(
            f"timeline_media must contain 1-{CONCAT_MAX_MEDIA} assets"
        )
    allowed_source_kinds = {
        "generated_visual",
        "generated_audio",
        "local_synthetic",
        "earshot_sfx",
        "elevenlabs_voiceover",
    }
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise content_service.ContentServiceError(f"timeline_media[{index}] must be an object")
        allowed = {"path", "kind", "start_seconds", "source_kind", "track_id", "volume"}
        unknown = set(item) - allowed
        if unknown:
            raise content_service.ContentServiceError(
                f"timeline_media[{index}] has unsupported keys: {', '.join(sorted(unknown))}"
            )
        kind = item.get("kind")
        if kind not in {"video", "audio"}:
            raise content_service.ContentServiceError(
                f"timeline_media[{index}].kind must be video or audio"
            )
        source_kind = item.get("source_kind")
        if source_kind not in allowed_source_kinds:
            raise content_service.ContentServiceError(
                f"timeline_media[{index}].source_kind must identify a generated asset"
            )
        path = _resolve_content_path(item.get("path"), f"timeline_media[{index}].path")
        if not path.is_file() or path.stat().st_size == 0:
            raise content_service.ContentServiceError(f"timeline_media[{index}].path must be a non-empty file")
        suffix = path.suffix.lower()
        allowed_suffixes = _VIDEO_SUFFIXES if kind == "video" else _AUDIO_SUFFIXES
        if suffix not in allowed_suffixes:
            raise content_service.ContentServiceError(
                f"timeline_media[{index}].path has an unsupported {kind} extension"
            )
        start = item.get("start_seconds")
        if isinstance(start, bool) or not isinstance(start, (int, float)) or not math.isfinite(start):
            raise content_service.ContentServiceError(
                f"timeline_media[{index}].start_seconds must be finite seconds"
            )
        if not 0 <= start <= 3_600:
            raise content_service.ContentServiceError(
                f"timeline_media[{index}].start_seconds must be within one hour"
            )
        normalized_item: dict[str, Any] = {
            "path": str(path),
            "kind": kind,
            "start_seconds": float(start),
            "source_kind": source_kind,
        }
        track_id = item.get("track_id")
        if track_id is not None:
            if not isinstance(track_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", track_id):
                raise content_service.ContentServiceError(
                    f"timeline_media[{index}].track_id is invalid"
                )
            normalized_item["track_id"] = track_id
        if "volume" in item:
            volume = item["volume"]
            if isinstance(volume, bool) or not isinstance(volume, (int, float)) or not math.isfinite(volume):
                raise content_service.ContentServiceError(f"timeline_media[{index}].volume must be finite")
            if not 0 <= volume <= 2:
                raise content_service.ContentServiceError(f"timeline_media[{index}].volume must be 0-2")
            normalized_item["volume"] = float(volume)
        normalized.append(normalized_item)
    if require_video and not any(item["kind"] == "video" for item in normalized):
        raise content_service.ContentServiceError("timeline_media must include at least one video asset")
    return normalized


def _validate_captions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > CONCAT_MAX_CAPTIONS:
        raise content_service.ContentServiceError(
            f"captions must be a list of at most {CONCAT_MAX_CAPTIONS} items"
        )
    captions: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != {"start", "end", "text"}:
            raise content_service.ContentServiceError(
                f"captions[{index}] must contain start, end, and text"
            )
        start, end, text = item["start"], item["end"], item["text"]
        if (
            isinstance(start, bool)
            or not isinstance(start, (int, float))
            or not math.isfinite(start)
            or isinstance(end, bool)
            or not isinstance(end, (int, float))
            or not math.isfinite(end)
            or start < 0
            or end <= start
            or end > 3_600
        ):
            raise content_service.ContentServiceError(f"captions[{index}] has invalid timing")
        if not isinstance(text, str) or not text.strip() or len(text) > 1_000:
            raise content_service.ContentServiceError(f"captions[{index}].text must contain 1-1000 characters")
        captions.append({"start": float(start), "end": float(end), "text": text.strip()})
    return captions


def _merge_sound_delivery(
    campaign_id: str,
    delivery_filename: str,
    timeline_media: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if not delivery_filename:
        return timeline_media, None
    fetched = bus_store.fetch_from_bus(content_service.DEPARTMENT, delivery_filename)
    try:
        delivery = json.loads(fetched["content"])
    except json.JSONDecodeError as exc:
        raise content_service.ContentServiceError("sound delivery artifact is not valid JSON") from exc
    if delivery.get("campaign_id") != campaign_id or delivery.get("provider") != "earshot":
        raise content_service.ContentServiceError("sound delivery must belong to this campaign and Earshot")
    stems = delivery.get("stems")
    if not isinstance(stems, list) or not stems:
        raise content_service.ContentServiceError("sound delivery contains no audio stems")
    merged = list(timeline_media)
    for index, stem in enumerate(stems):
        if not isinstance(stem, dict):
            raise content_service.ContentServiceError(f"sound delivery stem {index} is invalid")
        merged.extend(
            _validate_media_items(
                [
                    {
                        "path": stem.get("path"),
                        "kind": "audio",
                        "start_seconds": stem.get("start_seconds", 0),
                        "source_kind": "earshot_sfx",
                        "volume": stem.get("volume", 1.0),
                    }
                ],
                require_video=False,
            )
        )
        if len(merged) > CONCAT_MAX_MEDIA:
            raise content_service.ContentServiceError(
                f"combined timeline exceeds {CONCAT_MAX_MEDIA} media assets"
            )
    return merged, {"filename": delivery_filename, "path": fetched["path"]}


def _concat_binary() -> str:
    binary = os.environ.get("CONCAT_BIN", str(CONCAT_DEFAULT))
    path = Path(binary).expanduser()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise content_service.ContentServiceError(
            "Concat executable is unavailable; set CONCAT_BIN to the installed concat AppImage"
        )
    return str(path.resolve())


def _probe_mp4(path: Path) -> dict[str, Any]:
    executable = shutil.which("ffprobe")
    if not executable:
        raise content_service.ContentServiceError("ffprobe is required to verify Concat exports")
    completed = subprocess.run(
        [
            executable,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height,avg_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        text=True,
        capture_output=True,
        timeout=45,
        check=False,
    )
    if completed.returncode != 0:
        raise content_service.ContentServiceError(
            f"ffprobe rejected the Concat export: {completed.stderr[-600:].strip()}"
        )
    try:
        probe = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise content_service.ContentServiceError("ffprobe returned invalid JSON for the Concat export") from exc
    video_streams = [
        stream for stream in probe.get("streams", [])
        if stream.get("codec_type") == "video" and stream.get("width") and stream.get("height")
    ]
    try:
        duration = float(probe.get("format", {}).get("duration", 0))
    except (TypeError, ValueError) as exc:
        raise content_service.ContentServiceError("Concat export duration is invalid") from exc
    if not video_streams or not math.isfinite(duration) or duration <= 0:
        raise content_service.ContentServiceError("Concat export has no valid video stream or duration")
    return {"duration_seconds": duration, "video_streams": video_streams}


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
) -> dict[str, Any]:
    """Build or copy a Concat project, render MP4, and record it without publishing."""

    campaign_key, canonical_id = content_service._campaign_identity(campaign_id)
    campaign = content_service._load_campaign(campaign_key)
    if campaign is None or campaign.get("campaign_id") != canonical_id:
        raise content_service.ContentServiceError(f"campaign not found: {canonical_id}")
    script_asset, script = _latest_script(campaign, canonical_id)
    cue_asset = _latest_audio_cue(campaign, script_asset)
    expected_campaign_version = campaign.get("version")
    if isinstance(width, bool) or not isinstance(width, int) or not 16 <= width <= 7680:
        raise content_service.ContentServiceError("width must be an integer between 16 and 7680")
    if isinstance(height, bool) or not isinstance(height, int) or not 16 <= height <= 7680:
        raise content_service.ContentServiceError("height must be an integer between 16 and 7680")
    if isinstance(fps, bool) or not isinstance(fps, int) or not 12 <= fps <= 60:
        raise content_service.ContentServiceError("fps must be an integer between 12 and 60")
    if isinstance(crf, bool) or not isinstance(crf, int) or not 12 <= crf <= 30:
        raise content_service.ContentServiceError("crf must be an integer between 12 and 30")

    sources = _validate_media_items(timeline_media, require_video=not bool(concat_project_path))
    sources, sound_dependency = _merge_sound_delivery(canonical_id, sound_delivery_filename, sources)
    if sound_dependency:
        delivery_asset = next(
            (
                asset
                for asset in campaign.get("assets", [])
                if asset.get("filename") == sound_dependency["filename"]
                and asset.get("type") == "sound_delivery"
            ),
            None,
        )
        required_dependencies = {script_asset["filename"], cue_asset["filename"]}
        if delivery_asset is None or not required_dependencies.issubset(
            set(delivery_asset.get("dependencies", []))
        ):
            raise content_service.ContentServiceError(
                "sound delivery must be generated from the current script and audio cue sheet"
            )
    caption_source = "caller"
    caption_rows = _validate_captions(captions) if captions is not None else _script_captions(script)
    if captions is None:
        caption_source = "video_script" if caption_rows else "none"

    content_root = _content_root()
    content_root.mkdir(parents=True, exist_ok=True)
    job_id = f"concat-{uuid4().hex}"
    project_parent = content_root / "concat_projects" / campaign_key / job_id
    output_dir = content_root / "concat_renders" / campaign_key / job_id
    project_parent.mkdir(parents=True, exist_ok=False)
    output_dir.mkdir(parents=True, exist_ok=False)
    project_name = f"{campaign_key[:32]}-{job_id[-8:]}"
    project_path = project_parent / project_name
    output_path = output_dir / f"{project_name}.mp4"
    project_copy_source: Path | None = None
    if concat_project_path:
        project_copy_source = _resolve_content_path(concat_project_path, "concat_project_path")
        if not project_copy_source.is_dir() or not (project_copy_source / "concat.json").is_file():
            raise content_service.ContentServiceError(
                "concat_project_path must be a Concat project folder containing concat.json"
            )
        for item in project_copy_source.rglob("*"):
            if item.is_symlink():
                raise content_service.ContentServiceError("Concat projects cannot contain symlinks")
        if project_path.is_relative_to(project_copy_source) or project_copy_source.is_relative_to(project_path):
            raise content_service.ContentServiceError("Concat project source and destination cannot overlap")
        shutil.copytree(project_copy_source, project_path)

    dependencies = [script_asset["filename"], cue_asset["filename"]]
    if sound_dependency:
        dependencies.append(sound_dependency["filename"])

    execution_status = "failed"
    failure_message = "Concat render did not complete"
    concat_version: Any = None
    output_probe: dict[str, Any] | None = None
    output_sha256: str | None = None
    output_bytes = 0
    project_file = project_path / "concat.json"
    client: MCPStdioClient | None = None
    opened_project = False
    try:
        client = MCPStdioClient(
            [_concat_binary(), "--mcp", "headless"],
            cwd=bus_store.ROOT,
            env={"CONCAT_MCP_ROOTS": str(content_root)},
            unset_env=(
                "SOLOCORP_API_KEY",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "GEMINI_API_KEY",
                "GOOGLE_API_KEY",
                "GOOGLE_GENAI_API_KEY",
                "EARSHOT_GEMINI_API_KEY",
                "ELEVENLABS_API_KEY",
                "MAXPLUS_API_KEY",
                "CONCAT_API_ADDRESS",
                "CONCAT_API_TOKEN",
            ),
        )
        concat_version = client.call_tool("concat_version", {}, timeout=30)
        if project_copy_source:
            client.call_tool("project_open", {"path": str(project_path)}, timeout=60)
        else:
            client.call_tool(
                "project_create",
                {
                    "name": project_name,
                    "location": str(project_parent),
                    "video": {"width": width, "height": height, "rateNum": fps, "rateDen": 1},
                },
                timeout=60,
            )
        opened_project = True
        project_data = client.call_tool("timeline_read", {"path": str(project_path)}, timeout=30)
        timeline = project_data.get("timeline", {}) if isinstance(project_data, dict) else {}
        tracks = timeline.get("tracks", []) if isinstance(timeline, dict) else []
        track_ids = [track.get("id") for track in tracks if isinstance(track, dict) and track.get("id")]
        if len(track_ids) < 2:
            raise content_service.ContentServiceError("Concat project does not expose two timeline tracks")
        imported: dict[str, str] = {}
        for index, media in enumerate(sources):
            path = media["path"]
            media_id = imported.get(path)
            if not media_id:
                imported_item = client.call_tool(
                    "media_import", {"path": str(project_path), "file": path}, timeout=60
                )
                media_id = imported_item.get("createdId") if isinstance(imported_item, dict) else None
                if not media_id and isinstance(imported_item, dict):
                    media_items = imported_item.get("media", [])
                    match = next(
                        (
                            media_item
                            for media_item in media_items
                            if isinstance(media_item, dict)
                            and str(media_item.get("path", "")).lower() == path.lower()
                        ),
                        None,
                    )
                    media_id = match.get("id") if match else None
                if not isinstance(media_id, str) or not media_id:
                    raise content_service.ContentServiceError(
                        f"Concat failed to import timeline_media[{index}]"
                    )
                imported[path] = media_id
            default_track = track_ids[0] if media["kind"] == "video" else track_ids[1]
            track_id = media.get("track_id", default_track)
            if track_id not in track_ids:
                raise content_service.ContentServiceError(
                    f"timeline_media[{index}].track_id is not in the Concat project"
                )
            added = client.call_tool(
                "clip_add",
                {
                    "path": str(project_path),
                    "mediaId": media_id,
                    "start": media["start_seconds"],
                    "trackId": track_id,
                },
                timeout=60,
            )
            clip_id = added.get("createdId") if isinstance(added, dict) else None
            if media.get("volume") is not None and clip_id:
                client.call_tool(
                    "clip_update",
                    {"path": str(project_path), "clipId": clip_id, "patch": {"volume": media["volume"]}},
                    timeout=30,
                )

        if caption_rows:
            client.call_tool(
                "captions_add",
                {"path": str(project_path), "captions": caption_rows, "offsetY": 0.35},
                timeout=60,
            )
        client.call_tool("project_save", {"path": str(project_path)}, timeout=60)
        if not project_file.is_file():
            raise content_service.ContentServiceError("Concat did not save its concat.json project file")
        job = client.call_tool(
            "export_start",
            {"path": str(project_path), "output": str(output_path), "crf": crf, "codec": "h264"},
            timeout=60,
        )
        export_job = job.get("job") if isinstance(job, dict) else None
        if not isinstance(export_job, str) or not export_job:
            raise content_service.ContentServiceError("Concat did not return an export job id")
        deadline = time.monotonic() + 1_800
        while True:
            export_result = client.call_tool(
                "export_wait", {"job": export_job, "timeoutSeconds": 600}, timeout=620
            )
            if not isinstance(export_result, dict):
                raise content_service.ContentServiceError("Concat returned an invalid export status")
            if export_result.get("state") != "running":
                break
            if time.monotonic() >= deadline:
                raise content_service.ContentServiceError("Concat export exceeded the 30-minute limit")
        if export_result.get("state") != "done":
            raise content_service.ContentServiceError(
                f"Concat export finished with state {export_result.get('state')}"
            )
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise content_service.ContentServiceError("Concat reported done but did not write an MP4")
        output_probe = _probe_mp4(output_path)
        output_bytes = output_path.stat().st_size
        output_sha256 = _sha256_file(output_path)
        execution_status = "completed"
        failure_message = ""
    except (ContentServiceError, MCPStdioError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        failure_message = str(exc)[:1_200]
    finally:
        if client is not None and opened_project:
            try:
                client.call_tool("project_close", {"path": str(project_path), "save": True}, timeout=30)
            except Exception:
                pass
        if client is not None:
            client.close()

    result_record = {
        "schema_version": 1,
        "job_id": job_id,
        "campaign_id": canonical_id,
        "provider": "concat-mcp",
        "execution_mode": "local_concat_mcp_headless",
        "execution_status": execution_status,
        "script_filename": script_asset["filename"],
        "audio_cue_sheet_filename": cue_asset["filename"],
        "concat_version": concat_version,
        "project_path": project_path.relative_to(bus_store.BUS_ROOT.resolve()).as_posix(),
        "project_file": (
            project_file.relative_to(bus_store.BUS_ROOT.resolve()).as_posix()
            if project_file.is_file()
            else None
        ),
        "output": (
            {
                "path": output_path.relative_to(bus_store.BUS_ROOT.resolve()).as_posix(),
                "sha256": output_sha256,
                "bytes": output_bytes,
                "probe": output_probe,
            }
            if output_sha256
            else None
        ),
        "inputs": [
            {
                "path": item["path"].replace(str(bus_store.BUS_ROOT.resolve()) + os.sep, ""),
                "kind": item["kind"],
                "source_kind": item["source_kind"],
                "start_seconds": item["start_seconds"],
            }
            for item in sources
        ],
        "caption_count": len(caption_rows),
        "caption_source": caption_source,
        "sound_delivery_filename": sound_dependency["filename"] if sound_dependency else None,
        "runtime_gate": "generated_assets_only_pending_independent_concat_runtime_verification",
        "publication_status": "blocked_pending_human_approval_and_rights_review",
        "approval_effect": "none",
        "lifecycle_state": "client_generated",
    }
    if failure_message:
        result_record["error"] = failure_message
    result_asset = _store_campaign_json(
        canonical_id,
        "concat_render_result",
        job_id,
        result_record,
        dependencies,
        expected_campaign_version=expected_campaign_version,
    )
    publish_gate = content_service._review_campaign(canonical_id)
    return {
        "campaign_id": canonical_id,
        "job_id": job_id,
        "execution_status": execution_status,
        "execution_mode": "local_concat_mcp_headless",
        "project_path": result_record["project_path"],
        "project_file": result_record["project_file"],
        "output": result_record["output"],
        "result_artifact": {"filename": result_asset["filename"], "path": result_asset["path"]},
        "caption_count": len(caption_rows),
        "caption_source": caption_source,
        "publish_gate": publish_gate,
        "status": "review_required",
        "approval_required": True,
        "published": False,
        "error": failure_message or None,
    }


def _earshot_command() -> list[str]:
    executable = os.environ.get(
        "EARSHOT_BIN",
        str(Path.home() / ".opencode" / "earshot" / "venv-cpu" / "bin" / "earshot"),
    )
    path = Path(executable).expanduser()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise content_service.ContentServiceError("Earshot executable is unavailable; set EARSHOT_BIN")
    return [str(path.resolve()), "mcp"]


def _earshot_client() -> MCPStdioClient:
    model_cache = os.environ.get(
        "EARSHOT_HOME", str(Path.home() / ".opencode" / "earshot" / "cache")
    )
    return MCPStdioClient(
        _earshot_command(),
        cwd=Path.home() / ".opencode" / "earshot" / "src",
        env={
            "EARSHOT_HOME": model_cache,
            "EARSHOT_THREADS": os.environ.get("EARSHOT_THREADS", "4"),
            "EARSHOT_OFFLINE": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        },
        unset_env=(
            "SOLOCORP_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "GOOGLE_GENAI_API_KEY",
            "EARSHOT_GEMINI_API_KEY",
            "ELEVENLABS_API_KEY",
            "MAXPLUS_API_KEY",
            "CONCAT_API_TOKEN",
        ),
    )


def _store_sound_delivery(
    campaign_id: str,
    artifact_type: str,
    job_id: str,
    report: dict[str, Any],
    report_path: Path,
    *,
    stems: list[dict[str, Any]] | None = None,
    dependencies: list[str] | None = None,
    expected_campaign_version: str | None = None,
) -> dict[str, Any]:
    campaign_key, canonical_id = content_service._campaign_identity(campaign_id)
    campaign = content_service._load_campaign(campaign_key)
    if campaign is None or campaign.get("campaign_id") != canonical_id:
        raise content_service.ContentServiceError(f"campaign not found: {canonical_id}")
    report_data = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
    payload = {
        "schema_version": 1,
        "campaign_id": canonical_id,
        "provider": "earshot",
        "artifact_type": artifact_type,
        "job_id": job_id,
        "execution_status": "completed",
        "report_path": report_path.relative_to(bus_store.BUS_ROOT.resolve()).as_posix(),
        "report_sha256": _sha256_file(report_path),
        "report_bytes": report_path.stat().st_size,
        "report": report,
        "stems": stems or [],
        "publication_status": "review_required",
        "approval_effect": "none",
        "lifecycle_state": "client_generated",
        "media_rights_status": "human_confirmation_required",
        "report_inline": len(report_data.encode("utf-8")) < bus_store.MAX_PAYLOAD_BYTES // 2,
    }
    if not payload["report_inline"]:
        payload["report"] = {"summary": "Report exceeds inline Bus limit; see report_path and report_sha256."}
    return _store_campaign_json(
        canonical_id,
        artifact_type,
        job_id,
        payload,
        dependencies or [],
        expected_campaign_version=expected_campaign_version,
    )


def review_campaign_audio(
    campaign_id: str,
    audio_path: str,
    video_path: str = "",
    cue_times: list[float] | None = None,
) -> dict[str, Any]:
    campaign_key, canonical_id = content_service._campaign_identity(campaign_id)
    campaign = content_service._load_campaign(campaign_key)
    if campaign is None or campaign.get("campaign_id") != canonical_id:
        raise content_service.ContentServiceError(f"campaign not found: {canonical_id}")
    script_asset, _ = _latest_script(campaign, canonical_id)
    cue_asset = _latest_audio_cue(campaign, script_asset)
    expected_campaign_version = campaign.get("version")
    render_asset = next(
        (
            asset
            for asset in reversed(campaign.get("assets", []))
            if asset.get("type") == "concat_render_result"
        ),
        None,
    )
    if render_asset is None:
        raise content_service.ContentServiceError(
            "complete render_campaign_with_concat before reviewing final campaign audio"
        )
    try:
        render_record = json.loads(
            bus_store.fetch_from_bus(content_service.DEPARTMENT, render_asset["filename"])["content"]
        )
    except json.JSONDecodeError as exc:
        raise content_service.ContentServiceError("latest Concat render record is not valid JSON") from exc
    render_output = render_record.get("output")
    if (
        render_record.get("execution_status") != "completed"
        or not isinstance(render_output, dict)
        or not isinstance(render_output.get("path"), str)
        or not isinstance(render_output.get("sha256"), str)
    ):
        raise content_service.ContentServiceError(
            "latest Concat render must complete with a validated output before audio review"
        )
    audio = _resolve_content_path(audio_path, "audio_path")
    if not audio.is_file() or audio.stat().st_size == 0:
        raise content_service.ContentServiceError("audio_path must be a non-empty file")
    expected_output_path = render_output["path"]
    audio_relative_path = audio.relative_to(bus_store.BUS_ROOT.resolve()).as_posix()
    if audio_relative_path != expected_output_path:
        raise content_service.ContentServiceError(
            "audio_path must be the output of the latest completed Concat render"
        )
    if _sha256_file(audio) != render_output["sha256"]:
        raise content_service.ContentServiceError(
            "rendered output checksum changed; render the current campaign again"
        )
    video: Path | None = None
    video = _resolve_content_path(video_path, "video_path") if video_path else audio
    if not video.is_file() or video.suffix.lower() not in _VIDEO_SUFFIXES:
        raise content_service.ContentServiceError("video_path must be a local video file")
    video_relative_path = video.relative_to(bus_store.BUS_ROOT.resolve()).as_posix()
    if video_relative_path != expected_output_path:
        raise content_service.ContentServiceError(
            "video_path must be the output of the latest completed Concat render"
        )
    if cue_times is not None:
        if not isinstance(cue_times, list) or len(cue_times) > 1_000:
            raise content_service.ContentServiceError("cue_times must contain at most 1,000 cue seconds")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
            for value in cue_times
        ):
            raise content_service.ContentServiceError("cue_times must be finite non-negative seconds")

    job_id = f"sound-review-{uuid4().hex}"
    job_dir = _content_root() / "sound" / campaign_key / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    try:
        with _earshot_client() as client:
            measured = _earshot_result_payload(
                client.call_tool("measure", {"path": str(audio), "full": True}, timeout=180)
            )
            timeline_args: dict[str, Any] = {
                "path": str(audio),
                "full": True,
                "detail": "low",
                "video": str(video),
            }
            if cue_times:
                timeline_args["cues"] = [float(value) for value in cue_times]
            timeline = _earshot_result_payload(client.call_tool("timeline", timeline_args, timeout=600))
    except MCPStdioError as exc:
        raise content_service.ContentServiceError(f"Earshot audio review failed: {exc}") from exc

    report = {
        "schema_version": 1,
        "campaign_id": canonical_id,
        "provider": "earshot",
        "audio_path": audio.relative_to(bus_store.BUS_ROOT.resolve()).as_posix(),
        "video_path": video_relative_path,
        "script_filename": script_asset["filename"],
        "audio_cue_sheet_filename": cue_asset["filename"],
        "render_result_filename": render_asset["filename"],
        "render_output_path": expected_output_path,
        "render_output_sha256": render_output["sha256"],
        "measure": measured,
        "timeline": timeline,
        "network_used": False,
    }
    report_path = job_dir / "earshot-audio-review.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    stored = _store_sound_delivery(
        canonical_id,
        "sound_review_report",
        job_id,
        report,
        report_path,
        dependencies=[render_asset["filename"], *render_asset.get("dependencies", [])],
        expected_campaign_version=expected_campaign_version,
    )
    return {
        "campaign_id": canonical_id,
        "job_id": job_id,
        "execution_status": "completed",
        "report_artifact": {"filename": stored["filename"], "path": stored["path"]},
        "report_path": report["audio_path"],
        "report_sha256": _sha256_file(report_path),
        "render_result_filename": render_asset["filename"],
        "render_output_sha256": render_output["sha256"],
        "summary": measured,
        "status": "review_required",
        "approval_effect": "none",
    }


def list_earshot_sounds(category: str = "", kind: str = "") -> Any:
    arguments: dict[str, Any] = {}
    if category:
        arguments["category"] = category
    if kind:
        arguments["kind"] = kind
    try:
        with _earshot_client() as client:
            arguments["full"] = True
            return _earshot_result_payload(client.call_tool("sfx_list", arguments, timeout=30))
    except MCPStdioError as exc:
        raise content_service.ContentServiceError(f"Earshot sound bank lookup failed: {exc}") from exc


def render_campaign_sfx(
    campaign_id: str,
    sound: str,
    start_seconds: float = 0,
    duration_seconds: float | None = None,
    apex_seconds: float | None = None,
    pitch: str = "",
    peak_db: float = -1.0,
    volume: float = 1.0,
) -> dict[str, Any]:
    campaign_key, canonical_id = content_service._campaign_identity(campaign_id)
    campaign = content_service._load_campaign(campaign_key)
    if campaign is None or campaign.get("campaign_id") != canonical_id:
        raise content_service.ContentServiceError(f"campaign not found: {canonical_id}")
    script_asset, _ = _latest_script(campaign, canonical_id)
    cue_asset = _latest_audio_cue(campaign, script_asset)
    expected_campaign_version = campaign.get("version")
    if not isinstance(sound, str) or not re.fullmatch(r"[A-Za-z0-9_./-]{1,100}", sound):
        raise content_service.ContentServiceError("sound must be a valid Earshot bank id")
    if (
        isinstance(start_seconds, bool)
        or not isinstance(start_seconds, (int, float))
        or not math.isfinite(start_seconds)
        or start_seconds < 0
        or start_seconds > 3_600
    ):
        raise content_service.ContentServiceError("start_seconds must be finite and within one hour")
    if duration_seconds is not None and (
        isinstance(duration_seconds, bool)
        or not isinstance(duration_seconds, (int, float))
        or not math.isfinite(duration_seconds)
        or not 0.02 <= duration_seconds <= 30
    ):
        raise content_service.ContentServiceError("duration_seconds must be 0.02-30 seconds")
    if apex_seconds is not None and (
        isinstance(apex_seconds, bool)
        or not isinstance(apex_seconds, (int, float))
        or not math.isfinite(apex_seconds)
        or apex_seconds <= 0
        or (duration_seconds is not None and apex_seconds > duration_seconds)
    ):
        raise content_service.ContentServiceError("apex_seconds must be positive and within the requested duration")
    if pitch and (not isinstance(pitch, str) or not re.fullmatch(r"[A-Za-z0-9.#+-]{1,20}", pitch)):
        raise content_service.ContentServiceError("pitch must be a note name or frequency string")
    if isinstance(peak_db, bool) or not isinstance(peak_db, (int, float)) or not -24 <= peak_db <= 0:
        raise content_service.ContentServiceError("peak_db must be between -24 and 0 dBFS")
    if isinstance(volume, bool) or not isinstance(volume, (int, float)) or not math.isfinite(volume) or not 0 <= volume <= 2:
        raise content_service.ContentServiceError("volume must be between 0 and 2")

    job_id = f"sound-sfx-{uuid4().hex}"
    job_dir = _content_root() / "sound" / campaign_key / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    stem_path = job_dir / "sfx.wav"
    args: dict[str, Any] = {"sound": sound, "out": str(stem_path), "peak_db": float(peak_db)}
    args["full"] = True
    if duration_seconds is not None:
        args["dur"] = float(duration_seconds)
    if apex_seconds is not None:
        args["apex"] = float(apex_seconds)
    if pitch:
        args["pitch"] = pitch
    try:
        with _earshot_client() as client:
            render_report = _earshot_result_payload(client.call_tool("sfx_render", args, timeout=60))
            if not stem_path.is_file() or stem_path.stat().st_size == 0:
                raise content_service.ContentServiceError("Earshot returned without writing the SFX stem")
            measurement = _earshot_result_payload(
                client.call_tool("measure", {"path": str(stem_path), "full": True}, timeout=60)
            )
    except MCPStdioError as exc:
        raise content_service.ContentServiceError(f"Earshot SFX render failed: {exc}") from exc

    stem = {
        "path": stem_path.relative_to(bus_store.BUS_ROOT.resolve()).as_posix(),
        "sha256": _sha256_file(stem_path),
        "bytes": stem_path.stat().st_size,
        "start_seconds": float(start_seconds),
        "volume": float(volume),
        "source_kind": "earshot_sfx",
    }
    report = {
        "schema_version": 1,
        "campaign_id": canonical_id,
        "provider": "earshot",
        "script_filename": script_asset["filename"],
        "audio_cue_sheet_filename": cue_asset["filename"],
        "sound": sound,
        "render": render_report,
        "measure": measurement,
        "network_used": False,
    }
    report_path = job_dir / "earshot-sfx-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    stored = _store_sound_delivery(
        canonical_id,
        "sound_delivery",
        job_id,
        report,
        report_path,
        stems=[stem],
        dependencies=[script_asset["filename"], cue_asset["filename"]],
        expected_campaign_version=expected_campaign_version,
    )
    return {
        "campaign_id": canonical_id,
        "job_id": job_id,
        "execution_status": "completed",
        "sound_delivery_filename": stored["filename"],
        "sound_delivery_path": stored["path"],
        "stem": stem,
        "report_path": report_path.relative_to(bus_store.BUS_ROOT.resolve()).as_posix(),
        "status": "review_required",
        "approval_effect": "none",
    }
