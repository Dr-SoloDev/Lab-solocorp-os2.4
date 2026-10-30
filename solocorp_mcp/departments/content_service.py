"""Content Creator domain logic shared by MCP adapters and future clients."""

from __future__ import annotations

import errno
import os
import time
import hashlib
import json
import math
import re
import subprocess
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised on Windows
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:  # pragma: no cover - exercised on POSIX
    msvcrt = None  # type: ignore[assignment]

from dotenv import load_dotenv
from solocorp_mcp.bus_store import (
    MAX_PAYLOAD_BYTES,
    as_json,
    fetch_from_bus,
    list_department_bus,
    submit_bytes_to_bus,
    submit_to_bus,
)
from solocorp_mcp import bus_store
from solocorp_skills.redact import gate_report_md, publish_gate, redact

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "profiles" / "15-content-creator" / "SOUL.md"
BRAND_GUIDELINES_PATH = ROOT / "docs" / "brand" / "BRAND-GUIDELINES-v1.md"
DEPARTMENT = "content"
CONTENT_TYPES = {"article", "social_post", "newsletter"}
CLIENT_GENERATED_ARTIFACT_TYPES = {
    "article",
    "draft",
    "social_post",
    "newsletter",
    "video_script",
    "visual_prompt",
    "voiceover_transcript",
    "audio_cue_sheet",
}
PRIMARY_CONTENT_ARTIFACT_TYPES = {
    "draft",
    "article",
    "social_post",
    "newsletter",
    "video_script",
    "voiceover_transcript",
}
VOICEOVER_MODELS = {"eleven_v4"}
MAX_VOICEOVER_CHARACTERS = 2_000
SPECIALISTS = (
    {
        "id": "copywriter-kawee",
        "name": "กวี",
        "role": "Copywriter & Narrative Architect",
    },
    {
        "id": "scriptwriter-film",
        "name": "ฟิล์ม",
        "role": "Video Script & Storyboard Director",
    },
    {
        "id": "visual-designer-art",
        "name": "อาร์ต",
        "role": "Visual Concept & Prompt Architect",
    },
    {
        "id": "audio-designer-sound",
        "name": "ซาวด์",
        "role": "Sound Design, SFX & Lip-Sync Architect",
    },
    {
        "id": "content-analyst-ink",
        "name": "อิงค์",
        "role": "Content Strategist & Publish Gate Manager",
    },
)
LIFECYCLE_STATES = {
    "scaffold",
    "client_generated",
    "llm_generated",
    "human_edited",
    "review_required",
    "approved",
}
FFMPEG_SCHEMA_VERSION = "2.17.1"
FFMPEG_MAX_OPERATIONS = 12
FFMPEG_MAX_RESULT_BYTES = 64 * 1024
FF_TRACKING_REPOSITORY = "https://github.com/mrsarac/ff-tracking"
FF_TRACKING_FPS = 30
FF_TRACKING_SCENE_FRAMES = 15
FF_TRACKING_MAX_SCENES = 120
FF_TRACKING_PALETTES = {"Paper", "Thermal", "Mono", "Phosphor", "Amber", "Navy", "Neon"}
FF_TRACKING_KINDS = {"Cursor", "Typing", "Collapse", "Done"}
FF_TRACKING_CAMERA_DEFAULTS: dict[str, float] = {
    "tilt_x": 0.25,
    "tilt_y": -0.2,
    "roll": 0.0,
    "zoom_start": 2.0,
    "zoom_end": 2.2,
    "pan_x": 0.0,
    "pan_y": 0.0,
    "blur": 1.0,
    "shake": 0.0,
}
LOCAL_SCENE_ROW = re.compile(
    r'^\|\s*(\d+)\s*-\s*(\d+)s\s*\|\s*([^|]+?)\s*\|\s*VO:\s*"([^"]+)"',
    re.MULTILINE,
)

# Pinned subset of the installed ffmpeg-skill 2.17.1 tools/list schema.
# Raw argv and arbitrary tool arguments are intentionally not accepted.
_FFMPEG_ARGUMENTS: dict[str, dict[str, Any]] = {
    "probe": {
        "inputs": "paths", "analyze": "boolean", "compact": "boolean",
        "field": "string", "json_brief": "boolean",
    },
    "check": {
        "input": "path", "aspect": "string", "content": "boolean",
        "dry_run": "boolean", "fast": "boolean", "json_brief": "boolean",
        "lufs": "number", "max_duration": "number", "max_mb": "number",
        "no_loudness": "boolean", "platform": "platform", "tp": "number",
    },
    "cut": {
        "input": "path", "output": "path", "start": "string", "end": "string",
        "duration": "string", "accurate": "boolean", "dry_run": "boolean",
        "fast": "boolean", "overwrite": "boolean", "codec": "codec",
        "preset": "preset", "quality": "integer",
    },
    "silence": {
        "input": "path", "output": "path", "threshold": "number",
        "min_silence": "number", "min_keep": "number", "margin": "number",
        "max_cuts": "integer", "dry_run": "boolean", "fast": "boolean",
        "overwrite": "boolean", "quality": "integer",
    },
    "loudness": {
        "input": "path", "output": "path", "lufs": "number", "tp": "number",
        "lra": "number", "measure_only": "boolean", "dry_run": "boolean",
        "fast": "boolean", "overwrite": "boolean",
    },
    "fit": {
        "input": "path", "output": "path", "aspect": "string", "fit": "fit",
        "width": "integer", "height": "integer", "crop_x": "number",
        "crop_y": "number", "dry_run": "boolean", "fast": "boolean",
        "overwrite": "boolean", "codec": "codec", "quality": "integer",
    },
    "caption": {
        "input": "path", "output": "path", "language": "string",
        "platform": "platform", "mode": "caption_mode", "position": "position",
        "size": "integer", "bold": "boolean", "box": "boolean",
        "karaoke": "boolean", "dry_run": "boolean", "overwrite": "boolean",
    },
    "look": {
        "input": "path", "output": "path", "tiles": "string",
        "width": "integer", "at": "strings", "no_timecode": "boolean",
        "ink": "boolean", "dry_run": "boolean", "overwrite": "boolean",
    },
}
_FFMPEG_REQUIRED_ARGUMENTS = {
    "probe": {"inputs"},
    "check": {"input"},
    "cut": {"input", "output"},
    "silence": {"input", "output"},
    "loudness": {"input"},
    "fit": {"input", "output"},
    "caption": {"input", "output"},
    "look": {"input", "output"},
}
_FFMPEG_ENUMS = {
    "codec": {"h264", "hevc", "av1", "prores"},
    "preset": {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow", "placebo"},
    "fit": {"pad", "crop", "blur"},
    "caption_mode": {"burn", "mux"},
    "position": {"bottom", "bottom-left", "bottom-right", "center", "top", "top-left", "top-right"},
    "platform": {"broadcast", "custom", "facebook", "fb", "ig", "instagram", "linkedin", "podcast", "reels", "shorts", "tiktok", "twitter", "x", "youtube", "youtube-shorts", "yt", "yt-shorts"},
}


class ContentServiceError(ValueError):
    """A user-correctable content request error."""


def _required(value: str, label: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise ContentServiceError(f"{label} is required")
    if len(value) > 2_000:
        raise ContentServiceError(f"{label} is too long (maximum 2,000 characters)")
    return value


def slugify(value: str, fallback: str = "content") -> str:
    """Create a filename-safe slug while retaining Thai characters."""

    value = unicodedata.normalize("NFKC", str(value or "").strip().lower())
    value = re.sub(r"[^\w\-]+", "-", value, flags=re.UNICODE)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value[:64] or fallback


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _campaign_identity(campaign_id: str) -> tuple[str, str]:
    original = _required(campaign_id, "campaign_id")
    normalized = slugify(original)
    if len(normalized) > 42:
        suffix = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]
        normalized = f"{normalized[:33]}-{suffix}"
    return normalized, original


@contextmanager
def _campaign_lock(campaign_key: str) -> Iterator[None]:
    directory = bus_store.BUS_ROOT / DEPARTMENT
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / f".{campaign_key}.lock"
    with lock_path.open("a+b") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            lock_backend = "fcntl"
        elif msvcrt is not None:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            while True:
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    lock_backend = "msvcrt"
                    break
                except OSError as exc:
                    if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        raise
                    time.sleep(0.05)
        else:
            raise ContentServiceError("cross-process campaign locking is unsupported on this platform")
        try:
            yield
        finally:
            if lock_backend == "fcntl":
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            else:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _load_campaign(campaign_key: str) -> dict[str, Any] | None:
    prefix = f"campaign-{campaign_key}-manifest_"
    snapshots: list[dict[str, Any]] = []
    for item in list_department_bus(DEPARTMENT)["files"]:
        filename = item["filename"]
        if not filename.startswith(prefix) or not filename.endswith(".json"):
            continue
        raw = fetch_from_bus(DEPARTMENT, filename)["content"]
        try:
            snapshot = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ContentServiceError("campaign manifest is not valid JSON") from exc
        if snapshot.get("campaign_key") == campaign_key:
            snapshots.append(snapshot)
    if not snapshots:
        return None
    return max(
        snapshots,
        key=lambda item: (int(item.get("revision", 0)), item.get("updated_at", "")),
    )


def _save_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    campaign["revision"] = int(campaign.get("revision", 0)) + 1
    campaign["updated_at"] = _now()
    task_id = f"campaign-{campaign['campaign_key']}-manifest"
    result = submit_to_bus(
        DEPARTMENT,
        task_id[:64],
        json.dumps(campaign, ensure_ascii=False, sort_keys=True, indent=2),
        "json",
    )
    return {"filename": result["filename"], "path": result["path"]}


def _validated_source_references(
    source_references: list[str] | None,
) -> list[str] | None:
    if source_references is None:
        return None
    if not isinstance(source_references, list) or len(source_references) > 30:
        raise ContentServiceError("source_references must be a list of at most 30 strings")
    references: list[str] = []
    for reference in source_references:
        if not isinstance(reference, str):
            raise ContentServiceError("each source reference must be text")
        value = reference.strip()
        if not value or len(value) > 500:
            raise ContentServiceError("source references must contain 1-500 characters")
        if value not in references:
            references.append(value)
    return references


def _validated_provenance(provenance: Any) -> dict[str, str | None]:
    if not isinstance(provenance, dict):
        raise ContentServiceError("provenance must be an object")
    allowed = {"client", "provider", "model"}
    unknown = set(provenance) - allowed
    if unknown:
        raise ContentServiceError(
            f"unsupported provenance fields: {', '.join(sorted(map(str, unknown)))}"
        )

    secret_pattern = re.compile(
        r"(?i)(?:\b(?:sk|ccsk|ghp|xox[baprs])-[-A-Za-z0-9_]{12,}|\bbearer\s+\S+)"
    )
    result: dict[str, str | None] = {}
    for field, max_length in (("client", 80), ("provider", 80), ("model", 120)):
        raw = provenance.get(field)
        if raw is None and field != "client":
            result[field] = None
            continue
        if not isinstance(raw, str):
            raise ContentServiceError(f"provenance.{field} must be text")
        value = _required(raw, f"provenance.{field}")
        if len(value) > max_length or "\n" in value or "\r" in value:
            raise ContentServiceError(
                f"provenance.{field} must be a single-line identifier of at most {max_length} characters"
            )
        if secret_pattern.search(value):
            raise ContentServiceError(
                f"provenance.{field} looks like a credential; credentials must not be sent to MCP"
            )
        result[field] = value
    return result


def _merge_references(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        for reference in group:
            if reference not in merged:
                merged.append(reference)
    return merged


def _asset_task_id(campaign_id: str | None, artifact_type: str, label: str) -> str:
    slug = slugify(label)
    if not campaign_id:
        return slug
    campaign_key, _ = _campaign_identity(campaign_id)
    prefix = f"campaign-{campaign_key}-{artifact_type}-"
    return f"{prefix}{slug[: max(1, 64 - len(prefix))]}"[:64].rstrip("-")


def _source_reference_section(source_references: list[str] | None) -> str:
    references = source_references or []
    if references:
        lines = ["## Source References", ""]
        lines.extend(f"- {reference}" for reference in references)
        lines.extend(["", "> User-supplied references; independently unverified."])
    else:
        lines = [
            "## Source References",
            "",
            "- None supplied; factual claims remain unverified.",
        ]
    return "\n".join(lines) + "\n"


def _brand_guidelines_context() -> str:
    try:
        source = BRAND_GUIDELINES_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContentServiceError(
            f"approved brand guidelines could not be read: {BRAND_GUIDELINES_PATH}"
        ) from exc

    sections: list[str] = []
    for title in ("Brand Foundation", "Voice & Tone"):
        heading = re.search(rf"(?m)^## \d+\. {re.escape(title)}\s*$", source)
        if heading is None:
            raise ContentServiceError(f"brand guidelines are missing the {title} section")
        following = re.search(r"(?m)^## \d+\. ", source[heading.end():])
        end = heading.end() + following.start() if following else len(source)
        sections.append(source[heading.start():end].strip())
    return "Source: docs/brand/BRAND-GUIDELINES-v1.md\n\n" + "\n\n".join(sections)


def _store_assets(
    campaign_id: str | None,
    assets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Write artifact payloads and append one versioned campaign snapshot."""

    if not campaign_id:
        results = []
        for asset in assets:
            if asset["lifecycle_state"] not in LIFECYCLE_STATES:
                raise ContentServiceError("unsupported artifact lifecycle state")
            writer = submit_bytes_to_bus if asset.get("binary") else submit_to_bus
            result = writer(DEPARTMENT, asset["task_id"], asset["content"], asset["extension"])
            results.append(
                {
                    **result,
                    "status": "created",
                    "type": asset["type"],
                    "lifecycle_state": asset["lifecycle_state"],
                    "operation_status": "created",
                    "source_references": asset.get("source_references") or [],
                    "dependencies": asset.get("dependencies", []),
                    "human_review_required": True,
                }
            )
        return results

    campaign_key, canonical_id = _campaign_identity(campaign_id)
    with _campaign_lock(campaign_key):
        campaign = _load_campaign(campaign_key)
        if campaign is None:
            campaign = {
                "schema_version": 1,
                "campaign_id": canonical_id,
                "campaign_key": campaign_key,
                "version_number": 0,
                "version": "v0",
                "revision": 0,
                "status": "scaffold",
                "created_at": _now(),
                "updated_at": _now(),
                "source_references": [],
                "assets": [],
                "review": None,
                "approval_records": [],
            }
        elif campaign.get("campaign_id") != canonical_id:
            raise ContentServiceError("campaign_id conflicts with an existing campaign key")

        expected_version = assets[0].get("expected_campaign_version")
        if expected_version is not None and campaign.get("version") != expected_version:
            raise ContentServiceError(
                "campaign changed before the artifact batch was stored; retry with current assets"
            )

        version_number = int(campaign.get("version_number", 0)) + 1
        version = f"v{version_number}"
        inherited = campaign.get("source_references", [])
        stored: list[dict[str, Any]] = []
        outputs: list[dict[str, Any]] = []
        for asset in assets:
            if asset["lifecycle_state"] not in LIFECYCLE_STATES:
                raise ContentServiceError("unsupported artifact lifecycle state")
            supplied = asset.get("source_references")
            references = _merge_references(
                inherited,
                supplied if supplied is not None else [],
            )
            writer = submit_bytes_to_bus if asset.get("binary") else submit_to_bus
            result = writer(DEPARTMENT, asset["task_id"], asset["content"], asset["extension"])
            record = {
                "filename": result["filename"],
                "path": result["path"],
                "type": asset["type"],
                "version": version,
                "status": asset["lifecycle_state"],
                "source_references": references,
                "source_reference_status": (
                    "user_supplied_unverified" if references else "none_provided"
                ),
                "media_rights_status": asset.get(
                    "media_rights_status", "human_confirmation_required"
                ),
                "dependencies": asset.get("dependencies", []),
                "created_at": result["created_at"],
                **asset.get("metadata", {}),
            }
            stored.append(record)
            outputs.append(
                {
                    **result,
                    "campaign_id": canonical_id,
                    "version": version,
                    "type": asset["type"],
                    "status": asset["lifecycle_state"],
                    "lifecycle_state": asset["lifecycle_state"],
                    "operation_status": "created",
                    "source_references": references,
                    "source_reference_status": record["source_reference_status"],
                    "dependencies": record["dependencies"],
                    "human_review_required": True,
                    **asset.get("metadata", {}),
                }
            )

        campaign["version_number"] = version_number
        campaign["version"] = version
        campaign["status"] = assets[-1]["lifecycle_state"]
        campaign["source_references"] = _merge_references(
            inherited,
            *(asset.get("source_references") or [] for asset in assets),
        )
        campaign["assets"].extend(stored)
        campaign["review"] = None
        campaign["approved_version"] = None
        manifest_file = _save_campaign(campaign)
        for output in outputs:
            output["campaign_manifest"] = manifest_file
        return outputs


def department_info() -> dict[str, Any]:
    return {
        "status": "ok",
        "department": "content-creator",
        "head": {
            "id": "content-creator-sek",
            "name": "เสก (Sek)",
            "role": "Head of Content Creation",
            "profile": "profiles/15-content-creator/SOUL.md",
        },
        "specialists": list(SPECIALISTS),
        "control_rule": "Client ส่งงานผ่านหัวหน้า; specialist เป็น implementation ภายในแผนก",
        "data_root": "central_bus/content/",
    }


def _manifest(result: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        **result,
        "status": result.get("status", "created"),
        "department": "content-creator",
        "lifecycle_state": result.get("lifecycle_state", "scaffold"),
        **extra,
    }


def create_content_draft(
    title: str,
    topic: str,
    target_audience: str,
    content_type: str = "article",
    campaign_id: str | None = None,
    source_references: list[str] | None = None,
) -> dict[str, Any]:
    title = _required(title, "title")
    topic = _required(topic, "topic")
    audience = _required(target_audience, "target_audience")
    references = _validated_source_references(source_references)
    kind = str(content_type or "article").strip().lower()
    if kind not in CONTENT_TYPES:
        raise ContentServiceError(
            f"content_type must be one of: {', '.join(sorted(CONTENT_TYPES))}"
        )
    brand_context = _brand_guidelines_context()

    if kind == "social_post":
        sections = (
            "## Hook\n\n[ประโยคเปิดที่หยุดการเลื่อนดู]\n\n"
            "## Body\n\n[ประเด็นหลักและตัวอย่างที่เป็นประโยชน์]\n\n"
            "## CTA\n\n[คำถามเปิดเพื่อชวนสนทนา]\n\n"
            "## Hashtags\n\n[แฮชแท็กที่เกี่ยวข้อง]"
        )
    elif kind == "newsletter":
        sections = (
            "## Subject\n\n[หัวข้ออีเมล]\n\n"
            "## Opening\n\n[บริบทสั้น ๆ สำหรับผู้อ่าน]\n\n"
            "## Main Story\n\n[เนื้อหาหลักและสิ่งที่นำไปใช้ได้]\n\n"
            "## Next Step\n\n[คำถามหรือขั้นตอนถัดไป]"
        )
    else:
        sections = (
            "## Hook\n\n[ประโยคเปิดที่บอกคุณค่าของบทความ]\n\n"
            "## Outline\n\n1. [ปัญหาของผู้อ่าน]\n2. [หลักคิดหรือวิธีแก้]\n3. [ตัวอย่างและขั้นตอน]\n\n"
            "## Draft\n\n[เขียนเนื้อหาจริงในส่วนนี้]\n\n"
            "## Review Notes\n\n[หลักฐาน แหล่งอ้างอิง และสิ่งที่ยังต้องตรวจ]"
        )

    content = (
        f"# {title}\n\n"
        f"> **Content type:** {kind}\n"
        f"> **Topic:** {topic}\n"
        f"> **Target audience:** {audience}\n"
        f"> **Created at:** {_now()}\n\n"
        "## Brief\n\n"
        f"ชิ้นงานนี้มีเป้าหมายเพื่อช่วย **{audience}** เข้าใจเรื่อง **{topic}** "
        "ด้วยภาษาที่ชัดเจนและเหมาะกับแพลตฟอร์ม ก่อนเผยแพร่ต้องผ่าน Publish Gate\n\n"
        "## Brand Context\n\n"
        f"{brand_context}\n\n"
        f"{sections}\n"
        f"\n{_source_reference_section(references)}"
    )
    result = _store_assets(
        campaign_id,
        [
            {
                "task_id": _asset_task_id(campaign_id, "draft", title),
                "content": content,
                "extension": "md",
                "type": "draft",
                "lifecycle_state": "scaffold",
                "source_references": references,
            }
        ],
    )[0]
    return {
        **result,
        "department": "content-creator",
        "title": title,
        "content_type": kind,
        "lifecycle_state": "scaffold",
    }


def create_video_script(
    title: str,
    core_message: str,
    duration_seconds: int = 60,
    campaign_id: str | None = None,
    source_references: list[str] | None = None,
) -> dict[str, Any]:
    title = _required(title, "title")
    message = _required(core_message, "core_message")
    references = _validated_source_references(source_references)
    if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, int):
        raise ContentServiceError("duration_seconds must be an integer")
    if duration_seconds < 10 or duration_seconds > 3_600:
        raise ContentServiceError("duration_seconds must be between 10 and 3,600")

    if duration_seconds == 10:
        hook_end, body_end, example_end = 2, 7, 9
    else:
        hook_end = max(3, round(duration_seconds * 0.08))
        body_end = max(hook_end + 1, round(duration_seconds * 0.62))
        example_end = max(body_end + 1, round(duration_seconds * 0.86))
    script = (
        f"# Video Script — {title}\n\n"
        f"> **Duration:** {duration_seconds} seconds\n"
        f"> **Core message:** {message}\n\n"
        "| เวลา | Visual scene | Voiceover / Audio |\n"
        "|:--|:--|:--|\n"
        f"| 0–{hook_end}s | Hook: ภาพที่ทำให้หยุดดู | เปิดด้วยปัญหาหรือคำถามที่เกี่ยวกับ {message} |\n"
        f"| {hook_end}–{body_end}s | Context: ภาพสถานการณ์จริง | อธิบายปัญหาและเหตุผลที่เรื่องนี้สำคัญ |\n"
        f"| {body_end}–{example_end}s | Example: สาธิตหรือหลักฐาน | แสดงวิธีคิด ตัวอย่าง หรือขั้นตอนที่ทำตามได้ |\n"
        f"| {example_end}–{duration_seconds}s | Close: ภาพสรุป | สรุปหนึ่งประโยคและปิดด้วยคำถามเปิด |\n\n"
        "## Production Notes\n\n"
        "- ตรวจสิทธิ์ของภาพ เพลง ฟอนต์ และ footage ใน origin log\n"
        "- ใส่ซับไตเติลที่อ่านได้บนมือถือ\n"
        "- ห้ามเผยแพร่จนกว่ามนุษย์จะตรวจ Publish Gate\n"
        f"\n{_source_reference_section(references)}"
    )
    result = _store_assets(
        campaign_id,
        [
            {
                "task_id": _asset_task_id(campaign_id, "script", title),
                "content": script,
                "extension": "md",
                "type": "video_script",
                "lifecycle_state": "scaffold",
                "source_references": references,
            }
        ],
    )[0]
    return {
        **result,
        "department": "content-creator",
        "title": title,
        "duration_seconds": duration_seconds,
        "lifecycle_state": "scaffold",
    }


def design_visual_prompt(
    theme: str,
    platform: str,
    aspect_ratio: str = "16:9",
    campaign_id: str | None = None,
    source_references: list[str] | None = None,
) -> dict[str, Any]:
    theme = _required(theme, "theme")
    platform = _required(platform, "platform")
    references = _validated_source_references(source_references)
    if not re.fullmatch(r"\d{1,4}:\d{1,4}", str(aspect_ratio or "")):
        raise ContentServiceError("aspect_ratio must use the form WIDTH:HEIGHT, e.g. 16:9")

    prompt = (
        f"# Visual Prompt — {slugify(theme)}\n\n"
        f"- **Theme:** {theme}\n- **Platform:** {platform}\n"
        f"- **Aspect ratio:** {aspect_ratio}\n\n"
        "## Prompt\n\n"
        f"Create a clear, platform-native visual about {theme}. Use a human, honest, "
        "practical editorial style with strong subject hierarchy, readable negative space, "
        "and a single focal point. Keep the visual consistent with SoloCorp's brand voice: "
        "clear, sincere, and hands-on. Do not invent logos, customer data, or claims.\n\n"
        "## Negative Prompt\n\n"
        "No watermark, no fake text, no unlicensed logos, no exaggerated success claims, "
        "no identifiable private information.\n\n"
        "## Asset Origin\n\n"
        "Record the generator, source assets, license, and human approval in origin.md before publish.\n"
        f"\n{_source_reference_section(references)}"
    )
    result = _store_assets(
        campaign_id,
        [
            {
                "task_id": _asset_task_id(campaign_id, "visual", theme),
                "content": prompt,
                "extension": "md",
                "type": "visual_prompt",
                "lifecycle_state": "scaffold",
                "source_references": references,
            }
        ],
    )[0]
    return {
        **result,
        "department": "content-creator",
        "theme": theme,
        "platform": platform,
        "aspect_ratio": aspect_ratio,
        "lifecycle_state": "scaffold",
    }


def _campaign_script(campaign_id: str, script_filename: str) -> tuple[dict[str, Any], str]:
    campaign_key, canonical_id = _campaign_identity(campaign_id)
    campaign = _load_campaign(campaign_key)
    if campaign is None or campaign.get("campaign_id") != canonical_id:
        raise ContentServiceError(f"campaign not found: {canonical_id}")
    filename = str(script_filename or "").strip()
    script_asset = next(
        (
            asset
            for asset in reversed(campaign.get("assets", []))
            if asset.get("filename") == filename
            and asset.get("type") == "video_script"
        ),
        None,
    )
    if script_asset is None:
        raise ContentServiceError(
            "script_filename must identify a video script in this campaign"
        )
    script = fetch_from_bus(DEPARTMENT, filename)["content"]
    return script_asset, script


def _campaign_ffmpeg_sources(
    campaign_id: str,
    script_filename: str,
    audio_cue_filename: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    campaign_key, canonical_id = _campaign_identity(campaign_id)
    campaign = _load_campaign(campaign_key)
    if campaign is None or campaign.get("campaign_id") != canonical_id:
        raise ContentServiceError(f"campaign not found: {canonical_id}")

    script_asset, _ = _campaign_script(canonical_id, script_filename)
    latest_script = next(
        (asset for asset in reversed(campaign.get("assets", [])) if asset.get("type") == "video_script"),
        None,
    )
    if latest_script is None or latest_script.get("filename") != script_asset.get("filename"):
        raise ContentServiceError("script_filename must identify the latest campaign video script")

    cue_filename = str(audio_cue_filename or "").strip()
    cue_asset = next(
        (
            asset
            for asset in reversed(campaign.get("assets", []))
            if asset.get("filename") == cue_filename
            and asset.get("type") == "audio_cue_sheet"
            and script_asset["filename"] in asset.get("dependencies", [])
        ),
        None,
    )
    if cue_asset is None:
        raise ContentServiceError(
            "audio_cue_filename must identify a cue sheet for the latest campaign script"
        )
    latest_cue = next(
        (
            asset
            for asset in reversed(campaign.get("assets", []))
            if asset.get("type") == "audio_cue_sheet"
            and script_asset["filename"] in asset.get("dependencies", [])
        ),
        None,
    )
    if latest_cue is None or latest_cue.get("filename") != cue_filename:
        raise ContentServiceError("audio_cue_filename must identify the latest cue sheet for this script")
    return campaign, script_asset, cue_asset


def _ffmpeg_bus_path(
    value: Any,
    label: str,
    *,
    produced_paths: set[str],
    output: bool = False,
) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 2_000:
        raise ContentServiceError(f"{label} must be an absolute local path")
    raw_path = Path(value)
    if not raw_path.is_absolute() or ".." in raw_path.parts:
        raise ContentServiceError(f"{label} must be an absolute path inside central_bus/content")
    if any(ord(ch) < 32 for ch in value):
        raise ContentServiceError(f"{label} contains a control character")

    root = (bus_store.BUS_ROOT / DEPARTMENT).resolve()
    resolved = raw_path.resolve(strict=False)
    if not resolved.is_relative_to(root) or resolved == root:
        raise ContentServiceError(f"{label} must be inside central_bus/content")

    cursor = raw_path
    while cursor != root and cursor != cursor.parent:
        if cursor.is_symlink():
            raise ContentServiceError(f"{label} cannot use symlinks")
        cursor = cursor.parent
    if cursor != root:
        raise ContentServiceError(f"{label} must be inside central_bus/content")

    normalized = str(resolved)
    exists = resolved.exists()
    if output:
        if exists:
            raise ContentServiceError(f"{label} already exists; overwrite is not allowed")
        if not resolved.parent.is_dir():
            raise ContentServiceError(f"{label} parent directory must already exist")
    elif exists:
        if not resolved.is_file():
            raise ContentServiceError(f"{label} must point to a regular file")
    elif normalized not in produced_paths:
        raise ContentServiceError(f"{label} must exist or be produced by an earlier operation")
    return normalized


def _validate_ffmpeg_operations(operations: Any) -> list[dict[str, Any]]:
    if not isinstance(operations, list) or not operations or len(operations) > FFMPEG_MAX_OPERATIONS:
        raise ContentServiceError(
            f"operations must be a list of 1-{FFMPEG_MAX_OPERATIONS} supported ffmpeg-skill calls"
        )

    normalized: list[dict[str, Any]] = []
    produced_paths: set[str] = set()
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict) or set(operation) != {"tool", "arguments"}:
            raise ContentServiceError(
                f"operations[{index}] must contain only tool and arguments"
            )
        tool = operation.get("tool")
        if not isinstance(tool, str) or tool not in _FFMPEG_ARGUMENTS:
            raise ContentServiceError(f"operations[{index}] uses an unsupported ffmpeg-skill tool")
        arguments = operation.get("arguments")
        if not isinstance(arguments, dict):
            raise ContentServiceError(f"operations[{index}].arguments must be an object")
        allowed = _FFMPEG_ARGUMENTS[tool]
        unknown = set(arguments) - set(allowed)
        if unknown:
            raise ContentServiceError(
                f"operations[{index}] has unsupported {tool} arguments: {', '.join(sorted(unknown))}"
            )
        missing = _FFMPEG_REQUIRED_ARGUMENTS[tool] - set(arguments)
        if missing:
            raise ContentServiceError(
                f"operations[{index}] is missing required {tool} arguments: {', '.join(sorted(missing))}"
            )

        clean_args: dict[str, Any] = {}
        input_paths: list[str] = []
        output_paths: list[str] = []
        for name, value in arguments.items():
            kind = allowed[name]
            if kind == "path":
                if name == "output":
                    path = _ffmpeg_bus_path(
                        value, f"operations[{index}].arguments.{name}",
                        produced_paths=produced_paths, output=True,
                    )
                    output_paths.append(path)
                else:
                    path = _ffmpeg_bus_path(
                        value, f"operations[{index}].arguments.{name}",
                        produced_paths=produced_paths,
                    )
                    input_paths.append(path)
                clean_args[name] = path
            elif kind == "paths":
                if not isinstance(value, list) or not value or len(value) > 8:
                    raise ContentServiceError(f"operations[{index}].arguments.{name} must be a list of 1-8 paths")
                paths = [
                    _ffmpeg_bus_path(
                        item, f"operations[{index}].arguments.{name}[{item_index}]",
                        produced_paths=produced_paths,
                    )
                    for item_index, item in enumerate(value)
                ]
                input_paths.extend(paths)
                clean_args[name] = paths
            elif kind == "strings":
                if not isinstance(value, list) or len(value) > 32 or any(
                    not isinstance(item, str) or len(item) > 200 for item in value
                ):
                    raise ContentServiceError(f"operations[{index}].arguments.{name} must be a list of short strings")
                clean_args[name] = value
            elif kind in _FFMPEG_ENUMS:
                if not isinstance(value, str) or value not in _FFMPEG_ENUMS[kind]:
                    raise ContentServiceError(f"operations[{index}].arguments.{name} has an unsupported value")
                clean_args[name] = value
            elif kind == "boolean":
                if not isinstance(value, bool):
                    raise ContentServiceError(f"operations[{index}].arguments.{name} must be boolean")
                if name == "overwrite" and value:
                    raise ContentServiceError("FFmpeg job manifests cannot enable overwrite")
                clean_args[name] = value
            elif kind == "integer":
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ContentServiceError(f"operations[{index}].arguments.{name} must be an integer")
                if name in {"width", "height", "quality", "max_cuts", "size"} and value <= 0:
                    raise ContentServiceError(f"operations[{index}].arguments.{name} must be positive")
                clean_args[name] = value
            elif kind == "number":
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ContentServiceError(f"operations[{index}].arguments.{name} must be a finite number")
                clean_args[name] = value
            elif kind == "string":
                if not isinstance(value, str) or not value or len(value) > 1_000 or any(
                    ord(ch) < 32 for ch in value
                ):
                    raise ContentServiceError(f"operations[{index}].arguments.{name} must be short text")
                if name in {"start", "end", "duration"} and not re.fullmatch(
                    r"\d{1,3}(?::\d{1,2}){0,2}(?:\.\d{1,3})?", value
                ):
                    raise ContentServiceError(f"operations[{index}].arguments.{name} must be a numeric time")
                if name == "aspect" and not re.fullmatch(r"\d{1,5}:\d{1,5}", value):
                    raise ContentServiceError(f"operations[{index}].arguments.aspect must use WIDTH:HEIGHT")
                if name == "tiles" and not re.fullmatch(r"\d{1,2}x\d{1,2}", value):
                    raise ContentServiceError(f"operations[{index}].arguments.tiles must use COLUMNSxROWS")
                if name == "field" and not re.fullmatch(r"[\w.,:_+-]{1,100}", value):
                    raise ContentServiceError("probe field contains unsupported characters")
                clean_args[name] = value
            else:
                raise ContentServiceError("unsupported ffmpeg-skill contract type")

        if tool != "probe" and not input_paths:
            raise ContentServiceError(f"operations[{index}] must include an input path")
        if tool == "loudness" and not clean_args.get("measure_only") and "output" not in clean_args:
            raise ContentServiceError("loudness requires output unless measure_only is true")
        for path in output_paths:
            if path in produced_paths:
                raise ContentServiceError(f"operations[{index}] repeats an output path")
            produced_paths.add(path)
        normalized.append({"tool": tool, "arguments": clean_args})
    return normalized


def build_ffmpeg_job_manifest(
    campaign_id: str,
    script_filename: str,
    audio_cue_filename: str,
    operations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Store a versioned ffmpeg-skill call plan; never execute the plan."""

    canonical_id = _required(campaign_id, "campaign_id")
    script_filename = _required(script_filename, "script_filename")
    audio_cue_filename = _required(audio_cue_filename, "audio_cue_filename")
    campaign, script_asset, cue_asset = _campaign_ffmpeg_sources(
        canonical_id, script_filename, audio_cue_filename
    )
    normalized_operations = _validate_ffmpeg_operations(operations)
    job_id = f"ffmpeg-{uuid4().hex}"
    job_manifest = {
        "schema_version": 1,
        "job_id": job_id,
        "campaign_id": canonical_id,
        "provider": "ffmpeg-skill",
        "provider_contract_version": FFMPEG_SCHEMA_VERSION,
        "script_filename": script_asset["filename"],
        "script_version": script_asset["version"],
        "audio_cue_filename": cue_asset["filename"],
        "audio_cue_version": cue_asset["version"],
        "operations": normalized_operations,
        "execution": {
            "status": "not_started",
            "automatic_execution": False,
            "runtime_gate": "blocked_pending_independent_runtime_verification",
        },
        "lifecycle_state": "scaffold",
    }
    result = _store_assets(
        canonical_id,
        [
            {
                "task_id": _asset_task_id(canonical_id, "ffmpeg-job", job_id),
                "content": json.dumps(job_manifest, ensure_ascii=False, sort_keys=True, indent=2),
                "extension": "json",
                "type": "ffmpeg_job_manifest",
                "lifecycle_state": "scaffold",
                "dependencies": [script_filename, audio_cue_filename],
                "metadata": {
                    "job_id": job_id,
                    "provider": "ffmpeg-skill",
                    "provider_contract_version": FFMPEG_SCHEMA_VERSION,
                    "execution_status": "not_started",
                },
                "expected_campaign_version": campaign.get("version"),
            }
        ],
    )[0]
    return _manifest(
        result,
        job_id=job_id,
        campaign_version=result.get("version"),
        script_filename=script_filename,
        audio_cue_filename=audio_cue_filename,
        provider="ffmpeg-skill",
        provider_contract_version=FFMPEG_SCHEMA_VERSION,
        execution_status="not_started",
        automatic_execution=False,
        runtime_gate="blocked_pending_independent_runtime_verification",
    )


def _ff_tracking_camera(value: Any, defaults: dict[str, float], label: str) -> dict[str, Any]:
    if value is None:
        overrides: dict[str, Any] = {}
    elif isinstance(value, dict):
        overrides = value
    else:
        raise ContentServiceError(f"{label} must be an object")

    unknown = set(overrides) - set(defaults)
    if unknown:
        raise ContentServiceError(f"{label} has unsupported camera keys: {', '.join(sorted(unknown))}")
    clean = {**defaults, **overrides}
    bounds = {
        "tilt_x": (-1.2, 1.2),
        "tilt_y": (-1.2, 1.2),
        "roll": (-0.5, 0.5),
        "zoom_start": (1.0, 5.0),
        "zoom_end": (1.0, 5.0),
        "pan_x": (-900.0, 900.0),
        "pan_y": (-500.0, 500.0),
        "blur": (0.0, 3.0),
        "shake": (0.0, 12.0),
    }
    normalized: dict[str, float] = {}
    for key, (minimum, maximum) in bounds.items():
        number = clean[key]
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
            raise ContentServiceError(f"{label}.{key} must be a finite number")
        if not minimum <= number <= maximum:
            raise ContentServiceError(f"{label}.{key} must be between {minimum} and {maximum}")
        normalized[key] = float(number)
    return {
        "tilt_x": normalized["tilt_x"],
        "tilt_y": normalized["tilt_y"],
        "roll": normalized["roll"],
        "zoom": [normalized["zoom_start"], normalized["zoom_end"]],
        "pan": [normalized["pan_x"], normalized["pan_y"]],
        "blur": normalized["blur"],
        "shake": normalized["shake"],
    }


def _validate_ff_tracking_scenes(
    scene_definitions: Any,
    camera_params: Any,
) -> list[dict[str, Any]]:
    if not isinstance(scene_definitions, list) or not 1 <= len(scene_definitions) <= FF_TRACKING_MAX_SCENES:
        raise ContentServiceError(
            f"scene_definitions must be a list of 1-{FF_TRACKING_MAX_SCENES} scenes"
        )
    base_camera = _ff_tracking_camera(
        camera_params, FF_TRACKING_CAMERA_DEFAULTS, "camera_params"
    )
    # Convert the normalized camera shape back to input keys for per-scene merging.
    base_values = {
        "tilt_x": base_camera["tilt_x"],
        "tilt_y": base_camera["tilt_y"],
        "roll": base_camera["roll"],
        "zoom_start": base_camera["zoom"][0],
        "zoom_end": base_camera["zoom"][1],
        "pan_x": base_camera["pan"][0],
        "pan_y": base_camera["pan"][1],
        "blur": base_camera["blur"],
        "shake": base_camera["shake"],
    }
    allowed_keys = {"scene_id", "episode_id", "kind", "text", "palette", "camera", "hero", "size"}
    scenes: list[dict[str, Any]] = []
    scene_ids: set[str] = set()
    for index, raw in enumerate(scene_definitions, start=1):
        if not isinstance(raw, dict):
            raise ContentServiceError(f"scene_definitions[{index - 1}] must be an object")
        unknown = set(raw) - allowed_keys
        if unknown:
            raise ContentServiceError(
                f"scene_definitions[{index - 1}] has unsupported keys: {', '.join(sorted(unknown))}"
            )
        scene_id = raw.get("scene_id", f"scene-{index:02d}")
        if not isinstance(scene_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", scene_id):
            raise ContentServiceError(f"scene_definitions[{index - 1}].scene_id must be a short ASCII id")
        if scene_id in scene_ids:
            raise ContentServiceError(f"scene_definitions[{index - 1}].scene_id is duplicated")
        scene_ids.add(scene_id)
        episode_id = raw.get("episode_id")
        if episode_id is not None and (
            not isinstance(episode_id, str) or not re.fullmatch(r"EP\d{2}", episode_id)
        ):
            raise ContentServiceError(f"scene_definitions[{index - 1}].episode_id must use EPnn format")
        kind = raw.get("kind", "Typing")
        if not isinstance(kind, str) or kind not in FF_TRACKING_KINDS:
            raise ContentServiceError(f"scene_definitions[{index - 1}].kind is unsupported")
        text = raw.get("text", "")
        if (
            not isinstance(text, str)
            or len(text) > 80
            or not text.isascii()
            or any(ord(character) < 32 or ord(character) > 126 for character in text)
        ):
            raise ContentServiceError(
                f"scene_definitions[{index - 1}].text must be at most 80 printable ASCII characters"
            )
        if kind in {"Typing", "Cursor"} and not text.strip():
            raise ContentServiceError(f"scene_definitions[{index - 1}].text is required for {kind}")
        redaction = redact(text)
        if not redaction.ok:
            labels = sorted(
                {
                    finding["label"]
                    for finding in redaction.blocked + redaction.flagged + redaction.banned
                }
            )
            raise ContentServiceError(
                f"scene_definitions[{index - 1}].text failed redaction checks ({', '.join(labels)}); "
                "no manifest was stored"
            )
        palette = raw.get("palette", "Thermal")
        if not isinstance(palette, str) or palette not in FF_TRACKING_PALETTES:
            raise ContentServiceError(f"scene_definitions[{index - 1}].palette is unsupported")
        scene_camera = _ff_tracking_camera(
            raw.get("camera"), base_values, f"scene_definitions[{index - 1}].camera"
        )
        hero = raw.get("hero", [300.0, 540.0])
        if not isinstance(hero, (list, tuple)) or len(hero) != 2:
            raise ContentServiceError(f"scene_definitions[{index - 1}].hero must contain x and y")
        hero_values: list[float] = []
        for axis, value, maximum in (("x", hero[0], 1860.0), ("y", hero[1], 1040.0)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ContentServiceError(f"scene_definitions[{index - 1}].hero.{axis} must be finite")
            if not 60.0 <= value <= maximum:
                raise ContentServiceError(f"scene_definitions[{index - 1}].hero.{axis} is outside the render canvas")
            hero_values.append(float(value))
        size = raw.get("size", 72.0)
        if isinstance(size, bool) or not isinstance(size, (int, float)) or not math.isfinite(size):
            raise ContentServiceError(f"scene_definitions[{index - 1}].size must be finite")
        if not 24.0 <= size <= 160.0:
            raise ContentServiceError(f"scene_definitions[{index - 1}].size must be between 24 and 160")
        if hero_values[0] + len(text) * float(size) * 0.6 > 1860.0:
            raise ContentServiceError(f"scene_definitions[{index - 1}].text does not fit the render canvas")
        scenes.append(
            {
                "scene_id": scene_id,
                "episode_id": episode_id,
                "kind": kind,
                "text": text,
                "palette": palette,
                "cam": scene_camera,
                "hero": hero_values,
                "size": float(size),
            }
        )
    return scenes


def build_ff_tracking_manifest(
    campaign_id: str,
    scene_definitions: list[dict[str, Any]],
    camera_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store a validated ff-tracking scene plan without running its renderer."""

    campaign_key, canonical_id = _campaign_identity(_required(campaign_id, "campaign_id"))
    campaign = _load_campaign(campaign_key)
    if campaign is None or campaign.get("campaign_id") != canonical_id:
        raise ContentServiceError(f"campaign not found: {canonical_id}")
    script_asset = next(
        (asset for asset in reversed(campaign.get("assets", [])) if asset.get("type") == "video_script"),
        None,
    )
    if script_asset is None:
        raise ContentServiceError("campaign has no video script for ff-tracking")

    scenes = _validate_ff_tracking_scenes(scene_definitions, camera_params)
    job_id = f"ff-tracking-{uuid4().hex}"
    planned_duration = len(scenes) * FF_TRACKING_SCENE_FRAMES / FF_TRACKING_FPS
    job_manifest = {
        "schema_version": 1,
        "job_id": job_id,
        "campaign_id": canonical_id,
        "provider": "ff-tracking",
        "provider_repository": FF_TRACKING_REPOSITORY,
        "provider_license": "MIT",
        "script_filename": script_asset["filename"],
        "script_version": script_asset.get("version"),
        "scene_count": len(scenes),
        "fps": FF_TRACKING_FPS,
        "frames_per_scene": FF_TRACKING_SCENE_FRAMES,
        "planned_duration_seconds": planned_duration,
        "target_dimensions": {"width": 1920, "height": 1080},
        "scene_definitions": scenes,
        "storytelling_mode": "scripted_workflow_visualization",
        "exposes_model_chain_of_thought": False,
        "upstream_contract": {
            "scene_source": "hud/src/lib.rs::SCENE_LIST",
            "stock_scene_count": 12,
            "stock_frames_per_scene": 15,
            "stock_fps": 30,
            "stock_duration_seconds": 6.0,
            "stock_output_dimensions": {"width": 1920, "height": 1080},
            "json_manifest_consumed_by_stock_renderer": False,
        },
        "render_ready": False,
        "render_blocker": "a local adapter must materialize this JSON into Rust SCENE_LIST before stock tools/render.sh can use it",
        "execution": {
            "status": "not_started",
            "automatic_execution": False,
            "runtime_gate": "blocked_pending_scene_materializer_and_local_engine_verification",
        },
        "publication": {
            "status": "review_required",
            "approval_required": True,
            "published": False,
        },
        "lifecycle_state": "scaffold",
    }
    result = _store_assets(
        canonical_id,
        [
            {
                "task_id": _asset_task_id(canonical_id, "ff-tracking-job", job_id),
                "content": json.dumps(job_manifest, ensure_ascii=False, sort_keys=True, indent=2),
                "extension": "json",
                "type": "ff_tracking_job_manifest",
                "lifecycle_state": "scaffold",
                "dependencies": [script_asset["filename"]],
                "source_references": script_asset.get("source_references", []),
                "metadata": {
                    "job_id": job_id,
                    "provider": "ff-tracking",
                    "execution_status": "not_started",
                    "render_ready": False,
                    "approval_required": True,
                },
                "expected_campaign_version": campaign.get("version"),
            }
        ],
    )[0]
    return _manifest(
        result,
        job_id=job_id,
        provider="ff-tracking",
        scene_count=len(scenes),
        planned_duration_seconds=planned_duration,
        render_ready=False,
        execution_status="not_started",
        approval_required=True,
        published=False,
    )


def _validated_ffmpeg_result(response: Any) -> tuple[dict[str, Any], str, str | None, int | None]:
    if not isinstance(response, dict):
        raise ContentServiceError("execution_result must be an MCP result object")
    if set(response) - {"isError", "content", "structuredContent", "_meta"}:
        raise ContentServiceError("execution_result contains unsupported MCP result fields")
    if "isError" in response and not isinstance(response["isError"], bool):
        raise ContentServiceError("execution_result.isError must be boolean")

    content = response.get("content", [])
    if not isinstance(content, list) or len(content) > 16:
        raise ContentServiceError("execution_result.content must be a list of at most 16 text blocks")
    for index, block in enumerate(content):
        if (
            not isinstance(block, dict)
            or block.get("type") != "text"
            or not isinstance(block.get("text"), str)
            or len(block["text"]) > 16_000
        ):
            raise ContentServiceError(
                f"execution_result.content[{index}] must be a bounded text block; media is not stored"
            )

    structured = response.get("structuredContent")
    if structured is not None and not isinstance(structured, dict):
        raise ContentServiceError("execution_result.structuredContent must be an object")
    if not content and structured is None:
        raise ContentServiceError("execution_result must include content or structuredContent")
    if "_meta" in response and not isinstance(response["_meta"], dict):
        raise ContentServiceError("execution_result._meta must be an object")

    try:
        encoded = json.dumps(response, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ContentServiceError("execution_result must contain JSON-compatible values") from exc
    if len(encoded.encode("utf-8")) > FFMPEG_MAX_RESULT_BYTES:
        raise ContentServiceError(
            f"execution_result exceeds the {FFMPEG_MAX_RESULT_BYTES}-byte result limit"
        )

    provider_status = structured.get("status") if structured else None
    if provider_status is not None and not isinstance(provider_status, str):
        raise ContentServiceError("execution_result.structuredContent.status must be text")
    exit_code = structured.get("exit_code") if structured else None
    if exit_code is not None and (isinstance(exit_code, bool) or not isinstance(exit_code, int)):
        raise ContentServiceError("execution_result.structuredContent.exit_code must be an integer")

    if response.get("isError") is True or provider_status == "failed" or (exit_code is not None and exit_code != 0):
        execution_status = "reported_failure"
    elif provider_status == "completed" and exit_code == 0:
        execution_status = "reported_completed"
    else:
        execution_status = "unclassified"
    return response, execution_status, provider_status, exit_code


def record_ffmpeg_job_result(
    campaign_id: str,
    job_id: str,
    job_version: str,
    operation_index: int,
    execution_result: dict[str, Any],
) -> dict[str, Any]:
    """Record the actual MCP response for a stored job without approving it."""

    campaign_key, canonical_id = _campaign_identity(campaign_id)
    normalized_job_id = _required(job_id, "job_id")
    normalized_version = _required(job_version, "job_version")
    campaign = _load_campaign(campaign_key)
    if campaign is None or campaign.get("campaign_id") != canonical_id:
        raise ContentServiceError(f"campaign not found: {canonical_id}")
    job_asset = next(
        (
            asset
            for asset in reversed(campaign.get("assets", []))
            if asset.get("type") == "ffmpeg_job_manifest"
            and asset.get("job_id") == normalized_job_id
        ),
        None,
    )
    if job_asset is None:
        raise ContentServiceError("job_id must identify an FFmpeg job manifest in this campaign")
    if job_asset.get("version") != normalized_version:
        raise ContentServiceError(
            f"job version mismatch; the manifest is {job_asset.get('version')}"
        )
    if isinstance(operation_index, bool) or not isinstance(operation_index, int):
        raise ContentServiceError("operation_index must be an integer")
    try:
        job_manifest = json.loads(
            fetch_from_bus(DEPARTMENT, job_asset["filename"])["content"]
        )
    except (json.JSONDecodeError, KeyError) as exc:
        raise ContentServiceError("stored FFmpeg job manifest is not valid JSON") from exc
    if (
        job_manifest.get("job_id") != normalized_job_id
        or job_manifest.get("campaign_id") != canonical_id
        or job_manifest.get("provider") != "ffmpeg-skill"
        or job_manifest.get("provider_contract_version")
        != job_asset.get("provider_contract_version", FFMPEG_SCHEMA_VERSION)
    ):
        raise ContentServiceError("job_id does not match the stored FFmpeg job manifest")
    planned_operations = job_manifest.get("operations")
    if (
        not isinstance(planned_operations, list)
        or operation_index < 0
        or operation_index >= len(planned_operations)
        or not isinstance(planned_operations[operation_index], dict)
    ):
        raise ContentServiceError("operation_index must identify a call in the stored job manifest")
    operation_tool = planned_operations[operation_index].get("tool")

    response, execution_status, provider_status, exit_code = _validated_ffmpeg_result(
        execution_result
    )
    result_id = f"ffmpeg-result-{uuid4().hex}"
    record = {
        "schema_version": 1,
        "result_id": result_id,
        "job_id": normalized_job_id,
        "job_filename": job_asset["filename"],
        "job_version": normalized_version,
        "operation_index": operation_index,
        "operation_tool": operation_tool,
        "campaign_id": canonical_id,
        "provider": "ffmpeg-skill",
        "provider_contract_version": job_asset.get("provider_contract_version", FFMPEG_SCHEMA_VERSION),
        "execution_status": execution_status,
        "provider_status": provider_status,
        "provider_exit_code": exit_code,
        "mcp_is_error": response.get("isError"),
        "mcp_result": response,
        "lifecycle_state": "scaffold",
        "approval_effect": "none",
    }
    result = _store_assets(
        canonical_id,
        [
            {
                "task_id": _asset_task_id(canonical_id, "ffmpeg-result", result_id),
                "content": json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2),
                "extension": "json",
                "type": "ffmpeg_execution_result",
                "lifecycle_state": "scaffold",
                "dependencies": [job_asset["filename"]],
                "metadata": {
                    "result_id": result_id,
                    "job_id": normalized_job_id,
                    "job_version": normalized_version,
                    "operation_index": operation_index,
                    "operation_tool": operation_tool,
                    "execution_status": execution_status,
                    "provider_status": provider_status,
                    "provider_exit_code": exit_code,
                    "mcp_is_error": response.get("isError"),
                    "approval_effect": "none",
                },
            }
        ],
    )[0]
    return _manifest(
        result,
        result_id=result_id,
        job_id=normalized_job_id,
        job_version=normalized_version,
        operation_index=operation_index,
        operation_tool=operation_tool,
        execution_status=execution_status,
        provider_status=provider_status,
        provider_exit_code=exit_code,
        approval_effect="none",
        campaign_status="scaffold",
    )


def _local_media_scenes(script: str) -> list[dict[str, Any]]:
    scenes = []
    for match in LOCAL_SCENE_ROW.finditer(script):
        start, end = int(match.group(1)), int(match.group(2))
        description = match.group(3).strip()
        voiceover = match.group(4).strip()
        scene_seconds = end - start
        expected_start = len(scenes) * scene_seconds
        if scene_seconds not in {10, 15} or start != expected_start:
            raise ContentServiceError("local scenes must be contiguous 10- or 15-second segments")
        if scenes and scene_seconds != scenes[0]["end_seconds"] - scenes[0]["start_seconds"]:
            raise ContentServiceError("all local render scenes must use the same duration")
        if not description or not voiceover:
            raise ContentServiceError("every render scene requires a visual and voiceover")
        title, separator, visual_description = description.partition(" — ")
        title = title.strip() or f"Scene {len(scenes) + 1:02d}"
        scenes.append(
            {
                "start_seconds": start,
                "end_seconds": end,
                "kicker": f"SCENE {len(scenes) + 1:02d}",
                "title": title[:90],
                "description": (visual_description if separator else description)[:420],
                "voiceover": voiceover,
            }
        )
    if not scenes:
        raise ContentServiceError("local render found no timed scenes with VO text")
    scene_seconds = scenes[0]["end_seconds"] - scenes[0]["start_seconds"]
    if (len(scenes), scene_seconds) not in {(6, 15), (10, 10)}:
        raise ContentServiceError("local render supports six 15-second scenes or ten 10-second episodes")
    return scenes


def _execute_local_media_pipeline(payload: dict[str, Any]) -> dict[str, Any]:
    command = [str(ROOT / ".venv" / "bin" / "python"), str(ROOT / "scripts" / "render_campaign_media_local.py")]
    if not Path(command[0]).is_file():
        command[0] = os.environ.get("PYTHON", "python3")
    environment = os.environ.copy()
    environment["SOLOCORP_BUS_ROOT"] = str(bus_store.BUS_ROOT)
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=3600,
            cwd=ROOT,
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ContentServiceError("local media render exceeded the 60-minute limit") from exc
    if completed.returncode != 0:
        detail = completed.stderr[-1600:].strip() or completed.stdout[-1600:].strip()
        raise ContentServiceError(f"local media render failed: {detail or completed.returncode}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ContentServiceError("local media renderer returned invalid JSON") from exc
    if not isinstance(result, dict) or result.get("status") != "completed":
        raise ContentServiceError("local media renderer did not report completed status")
    return result


def render_campaign_media_local(campaign_id: str) -> dict[str, Any]:
    """Render script-derived synthetic media locally and leave the campaign gated."""

    campaign_key, canonical_id = _campaign_identity(campaign_id)
    campaign = _load_campaign(campaign_key)
    if campaign is None or campaign.get("campaign_id") != canonical_id:
        raise ContentServiceError(f"campaign not found: {canonical_id}")
    script_asset = next(
        (asset for asset in reversed(campaign.get("assets", [])) if asset.get("type") == "video_script"),
        None,
    )
    if script_asset is None:
        raise ContentServiceError("campaign has no video script to render")
    script = fetch_from_bus(DEPARTMENT, script_asset["filename"])["content"]
    scenes = _local_media_scenes(script)
    scene_seconds = scenes[0]["end_seconds"] - scenes[0]["start_seconds"]
    duration_seconds = scenes[-1]["end_seconds"]

    rights_file = ROOT / "tools" / "piper" / "model-rights.json"
    try:
        model_rights = json.loads(rights_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContentServiceError("local Piper model rights record is missing or invalid") from exc
    model_license = _required(str(model_rights.get("license", "")), "model license")
    commercial_use = model_rights.get("commercial_use")
    if not isinstance(commercial_use, bool):
        raise ContentServiceError("local Piper voice model must have an explicit commercial_use boolean")
    voice_rights_status = (
        "commercial_permitted_pending_human_confirmation"
        if commercial_use
        else "noncommercial_only_human_confirmation_required"
    )

    job_id = f"local-media-{uuid4().hex}"
    content_root = (bus_store.BUS_ROOT / "content").resolve()
    output_dir = content_root / "local_media" / campaign_key / job_id
    if not output_dir.resolve().is_relative_to(content_root):
        raise ContentServiceError("local media output path escapes central_bus/content")
    job_manifest = {
        "schema_version": 1,
        "job_id": job_id,
        "campaign_id": canonical_id,
        "provider": "ffmpeg-cli",
        "tts_provider": "piper-local",
        "visual_provider": "three.js-pdoom-local",
        "script_filename": script_asset["filename"],
        "script_version": script_asset.get("version"),
        "execution": {
            "status": "in_progress",
            "automatic_execution": False,
            "requested_by": "content-creator MCP tool call",
            "runtime_gate": "synthetic_inputs_only_pending_independent_ffmpeg_verification",
        },
        "scope": "generated voice, original synthetic 3D scenes, scene-level captions, local FFmpeg CLI",
        "scene_count": len(scenes),
        "scene_seconds": scene_seconds,
        "duration_seconds": duration_seconds,
        "voice_model_license": model_license,
        "voice_model_rights_status": voice_rights_status,
        "publication_status": "blocked_pending_human_approval_and_rights_review",
        "output_directory": output_dir.relative_to(bus_store.BUS_ROOT.resolve()).as_posix(),
        "lifecycle_state": "scaffold",
    }
    job_asset = _store_assets(
        canonical_id,
        [
            {
                "task_id": _asset_task_id(canonical_id, "local-media-job", job_id),
                "content": json.dumps(job_manifest, ensure_ascii=False, sort_keys=True, indent=2),
                "extension": "json",
                "type": "local_media_render_job",
                "lifecycle_state": "scaffold",
                "dependencies": [script_asset["filename"]],
                "metadata": {
                    "job_id": job_id,
                    "provider": "ffmpeg-cli",
                    "execution_status": "in_progress",
                    "media_rights_status": "human_confirmation_required",
                },
                "expected_campaign_version": campaign.get("version"),
            }
        ],
    )[0]

    payload = {
        "campaign_id": campaign_key,
        "output_dir": str(output_dir),
        "model_license": model_license,
        "scene_seconds": scene_seconds,
        "duration_seconds": duration_seconds,
        "scenes": scenes,
    }
    try:
        render = _execute_local_media_pipeline(payload)
        video = render.get("video", {})
        video_path = Path(str(video.get("path", ""))).resolve(strict=True)
        if not video_path.is_relative_to(output_dir.resolve()) or not video_path.is_file():
            raise ContentServiceError("local renderer output must be a file inside its isolated job directory")
        if not isinstance(video.get("sha256"), str) or len(video["sha256"]) != 64:
            raise ContentServiceError("local renderer did not return a valid output SHA-256")
        execution_status = "completed"
        result_record = {
            "schema_version": 1,
            "job_id": job_id,
            "campaign_id": canonical_id,
            "provider": "ffmpeg-cli",
            "execution_status": execution_status,
            "execution_mode": render.get("execution_mode"),
            "render": render,
            "lifecycle_state": "scaffold",
            "approval_effect": "none",
        }
    except (ContentServiceError, OSError, ValueError, TypeError, KeyError) as exc:
        execution_status = "failed"
        result_record = {
            "schema_version": 1,
            "job_id": job_id,
            "campaign_id": canonical_id,
            "provider": "ffmpeg-cli",
            "execution_status": execution_status,
            "error": type(exc).__name__,
            "message": str(exc)[:1600],
            "lifecycle_state": "scaffold",
            "approval_effect": "none",
        }

    result_asset = _store_assets(
        canonical_id,
        [
            {
                "task_id": _asset_task_id(canonical_id, "local-media-result", job_id),
                "content": json.dumps(result_record, ensure_ascii=False, sort_keys=True, indent=2),
                "extension": "json",
                "type": "local_media_render_result",
                "lifecycle_state": "scaffold",
                "dependencies": [job_asset["filename"], script_asset["filename"]],
                "metadata": {
                    "job_id": job_id,
                    "provider": "ffmpeg-cli",
                    "execution_status": execution_status,
                    "media_rights_status": "human_confirmation_required",
                },
            }
        ],
    )[0]
    review = _review_campaign(canonical_id)
    return {
        "campaign_id": canonical_id,
        "job_id": job_id,
        "execution_status": execution_status,
        "execution_mode": "local_ffmpeg_cli",
        "job_manifest": {"filename": job_asset["filename"], "path": job_asset["path"]},
        "result_record": {"filename": result_asset["filename"], "path": result_asset["path"]},
        "render": result_record.get("render"),
        "error": result_record.get("message") if execution_status == "failed" else None,
        "publish_gate": review,
        "status": "review_required",
        "approval_required": True,
        "published": False,
    }


def design_audio_experience(
    campaign_id: str,
    script_filename: str,
) -> dict[str, Any]:
    """Create a rule-based audio cue sheet from a stored campaign script."""

    campaign_id = _required(campaign_id, "campaign_id")
    script_filename = _required(script_filename, "script_filename")
    script_asset, script = _campaign_script(campaign_id, script_filename)
    duration_match = re.search(r"\*\*Duration:\*\*\s*(\d+)\s*seconds", script)
    duration_seconds = int(duration_match.group(1)) if duration_match else None
    scenes: list[tuple[str, str, str]] = []
    for line in script.splitlines():
        if not line.strip().startswith("|"):
            continue
        columns = [column.strip() for column in line.strip().strip("|").split("|")]
        if (
            len(columns) >= 3
            and re.match(r"^\d+\s*(?:[–-]\s*\d+)?\s*s$", columns[0], re.I)
        ):
            scenes.append((columns[0], columns[1], columns[2]))
    if not scenes:
        raise ContentServiceError("video script has no timestamped scenes to analyze")

    cue_rows = [
        "| Timestamp | Scene | Voice / emphasis | BGM and SFX proposal |",
        "|:--|:--|:--|:--|",
    ]
    for timestamp, scene, voiceover in scenes:
        cue_rows.append(
            f"| {timestamp} | {scene} | Clear, conversational delivery; "
            f"pause briefly before the key point. Source line: {voiceover} | "
            "Keep a restrained instrumental bed; use a soft transition cue only if needed. |"
        )
    content = (
        f"# Audio Cue Sheet — {campaign_id}\n\n"
        f"> **Source script:** {script_filename}\n"
        f"> **Total duration:** {duration_seconds if duration_seconds is not None else 'confirm with editor'} seconds\n"
        "> **Status:** proposal; human confirmation required\n\n"
        "## Mix Direction\n\n"
        "- **BGM mood:** restrained, focused, warm instrumental; confirm against the campaign brief.\n"
        "- **Voice emotion:** natural and clear; avoid overstating claims.\n"
        "- **SFX:** minimal transition accents only; no unlicensed samples.\n"
        "- **Pause / emphasis:** leave a short pause before each key message; tune to the final performance.\n\n"
        "## Cues\n\n"
        + "\n".join(cue_rows)
        + "\n\n## Rights and Consent\n\n"
        "Confirm BGM/SFX license and voice-clone consent before any provider use or publication.\n"
    )
    result = _store_assets(
        campaign_id,
        [
            {
                "task_id": _asset_task_id(campaign_id, "audio-cue", script_filename),
                "content": content,
                "extension": "md",
                "type": "audio_cue_sheet",
                "lifecycle_state": "scaffold",
                "source_references": script_asset.get("source_references"),
                "dependencies": [script_filename],
            }
        ],
    )[0]
    return {**result, "lifecycle_state": "scaffold", "duration_seconds": duration_seconds}


def generate_voice_lipsync_prompt(
    campaign_id: str,
    script_filename: str,
    voice_profile: str,
) -> dict[str, Any]:
    """Store a voice/lip-sync configuration without calling any provider."""

    campaign_id = _required(campaign_id, "campaign_id")
    script_filename = _required(script_filename, "script_filename")
    profile = _required(voice_profile, "voice_profile")
    script_asset, script = _campaign_script(campaign_id, script_filename)
    script_text = script[:2_000]
    config = {
        "campaign_id": campaign_id,
        "source_script": script_filename,
        "voice_profile": profile,
        "voice_direction": "Natural, clear, conversational; preserve the script's wording.",
        "lip_sync_model": "Hedra",
        "input_text_source": "stored_video_script",
        "script_excerpt": script_text[:2_000],
        "provider_api_called": False,
        "voice_clone_consent": {
            "required_before_provider_use": True,
            "confirmed": False,
            "confirmation_source": None,
        },
        "media_rights": {
            "music_and_sfx_license_confirmation_required": True,
            "status": "human_confirmation_required",
        },
        "source_references": script_asset.get("source_references", []),
        "source_reference_status": script_asset.get(
            "source_reference_status", "none_provided"
        ),
        "lifecycle_state": "scaffold",
    }
    result = _store_assets(
        campaign_id,
        [
            {
                "task_id": _asset_task_id(campaign_id, "voice-config", script_filename),
                "content": json.dumps(config, ensure_ascii=False, sort_keys=True, indent=2),
                "extension": "json",
                "type": "voice_lipsync_config",
                "lifecycle_state": "scaffold",
                "source_references": script_asset.get("source_references"),
                "dependencies": [script_filename],
            }
        ],
    )[0]
    return {
        **result,
        "lifecycle_state": "scaffold",
        "provider_api_called": False,
        "voice_clone_consent_required": True,
    }


def save_human_edited_artifact(
    campaign_id: str,
    source_filename: str,
    edited_content: str,
    edit_note: str,
) -> dict[str, Any]:
    """Store a human-edited text artifact as a new campaign version."""

    campaign_key, canonical_id = _campaign_identity(campaign_id)
    filename = _required(source_filename, "source_filename")
    note = _required(edit_note, "edit_note")
    if not isinstance(edited_content, str) or not edited_content.strip():
        raise ContentServiceError("edited_content is required")
    if len(edited_content.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ContentServiceError(f"edited_content exceeds {MAX_PAYLOAD_BYTES} bytes")
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in {"md", "txt", "json"}:
        raise ContentServiceError("only text artifacts can be human-edited")

    campaign = _load_campaign(campaign_key)
    if campaign is None or campaign.get("campaign_id") != canonical_id:
        raise ContentServiceError(f"campaign not found: {canonical_id}")
    source_asset = next(
        (asset for asset in reversed(campaign.get("assets", [])) if asset.get("filename") == filename),
        None,
    )
    if source_asset is None:
        raise ContentServiceError("source_filename must identify an artifact in this campaign")
    if source_asset.get("type") in {"voiceover_audio"}:
        raise ContentServiceError("binary audio artifacts cannot be human-edited as text")
    _required(source_asset.get("type"), "source artifact type")

    result = _store_assets(
        canonical_id,
        [
            {
                "task_id": _asset_task_id(canonical_id, "human-edit", filename),
                "content": edited_content,
                "extension": extension,
                "type": source_asset["type"],
                "lifecycle_state": "human_edited",
                "source_references": source_asset.get("source_references"),
                "dependencies": source_asset.get("dependencies", []),
                "metadata": {
                    "supersedes": filename,
                    "edit_note": note,
                },
            }
        ],
    )[0]
    return {**result, "lifecycle_state": "human_edited"}


def ingest_client_generated_artifact(
    campaign_id: str,
    artifact_type: str,
    content: str,
    provenance: dict[str, str],
    source_references: list[str] | None = None,
) -> dict[str, Any]:
    """Store client-authored content without mislabeling its origin."""

    canonical_id = _campaign_identity(campaign_id)[1]
    kind = _required(artifact_type, "artifact_type").lower()
    if kind not in CLIENT_GENERATED_ARTIFACT_TYPES:
        raise ContentServiceError(
            f"artifact_type must be one of: {', '.join(sorted(CLIENT_GENERATED_ARTIFACT_TYPES))}"
        )
    if not isinstance(content, str) or not content.strip():
        raise ContentServiceError("content is required")
    if len(content.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ContentServiceError(f"content exceeds {MAX_PAYLOAD_BYTES} bytes")

    references = _validated_source_references(source_references)
    validated_provenance = _validated_provenance(provenance)
    task_id = _asset_task_id(canonical_id, "client-generated", f"{kind}-{uuid4().hex}")
    return _store_assets(
        canonical_id,
        [
            {
                "task_id": task_id,
                "content": content,
                "extension": "md",
                "type": kind,
                "lifecycle_state": "client_generated",
                "source_references": references,
                "metadata": {
                    "provenance": validated_provenance,
                    "provenance_status": "client_supplied_unverified",
                },
            }
        ],
    )[0]


def generate_voiceover(
    title: str,
    text: str,
    voice_id: str,
    approved: bool = False,
    model_id: str = "eleven_v4",
    language_code: str = "th",
    campaign_id: str | None = None,
) -> dict[str, Any]:
    """Generate one explicitly approved ElevenLabs voiceover draft."""

    if not isinstance(approved, bool) or not approved:
        raise ContentServiceError(
            "paid voice generation requires approved=true for this request"
        )
    title = _required(title, "title")
    text = _required(text, "text")
    voice_id = _required(voice_id, "voice_id")
    if len(voice_id) > 128 or any(ord(ch) < 33 for ch in voice_id):
        raise ContentServiceError("voice_id must be a single ID of at most 128 characters")
    if len(text) > MAX_VOICEOVER_CHARACTERS:
        raise ContentServiceError(
            f"text exceeds the {MAX_VOICEOVER_CHARACTERS}-character voice-generation limit"
        )
    model = str(model_id or "").strip()
    if model not in VOICEOVER_MODELS:
        raise ContentServiceError(
            f"model_id must be one of: {', '.join(sorted(VOICEOVER_MODELS))}"
        )
    language = str(language_code or "").strip().lower()
    if not re.fullmatch(r"[a-z]{2,3}", language):
        raise ContentServiceError("language_code must be a 2- or 3-letter language code")

    load_dotenv(dotenv_path=ROOT / ".env", override=False)
    if not os.environ.get("ELEVENLABS_API_KEY"):
        raise ContentServiceError(
            "ELEVENLABS_API_KEY is not available from the project .env file"
        )

    try:
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs()
        chunks = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model,
            language_code=language,
            output_format="mp3_44100_128",
        )
        audio = b"".join(chunks)
    except Exception as exc:
        # SDK exception text may contain request details; keep credentials and
        # user input out of the MCP error response.
        status_code = getattr(exc, "status_code", None)
        body = getattr(exc, "body", None)
        detail = body.get("detail") if isinstance(body, dict) else None
        api_message = detail.get("message") if isinstance(detail, dict) else None
        if status_code == 401 and isinstance(api_message, str):
            secret = os.environ.get("ELEVENLABS_API_KEY", "")
            if secret:
                api_message = api_message.replace(secret, "[redacted]")
            raise ContentServiceError(
                f"ElevenLabs authorization failed (HTTP 401): {api_message[:240]}"
            ) from exc
        raise ContentServiceError(
            f"ElevenLabs request failed (HTTP {status_code or 'unknown'})"
        ) from exc
    if not audio:
        raise ContentServiceError("ElevenLabs returned an empty audio response")

    slug = slugify(title)
    transcript = (
        f"# Voiceover Draft — {title}\n\n"
        f"> **Model:** {model}\n"
        f"> **Language:** {language}\n"
        f"> **Characters:** {len(text)}\n"
        "> **Audio:** stored alongside this script in the Content bus\n\n"
        "## Script\n\n"
        f"{text}\n\n"
        "## Review\n\n"
        "Human review is required before publication.\n"
    )
    stored = _store_assets(
        campaign_id,
        [
            {
                "task_id": (
                    _asset_task_id(campaign_id, "voiceover", title)
                    if campaign_id
                    else f"voiceover-{slug[:50]}"
                ),
                "content": audio,
                "extension": "mp3",
                "binary": True,
                "type": "voiceover_audio",
                "lifecycle_state": "llm_generated",
            },
            {
                "task_id": (
                    _asset_task_id(campaign_id, "voice-script", title)
                    if campaign_id
                    else f"voiceover-script-{slug[:43]}"
                ),
                "content": transcript,
                "extension": "md",
                "type": "voiceover_transcript",
                "lifecycle_state": "llm_generated",
            },
        ],
    )
    audio_result, transcript_result = stored
    return _manifest(
        audio_result,
        title=title,
        model_id=model,
        language_code=language,
        output_format="mp3_44100_128",
        characters=len(text),
        transcript={
            "filename": transcript_result["filename"],
            "path": transcript_result["path"],
        },
        human_review_required=True,
        publish_action="blocked_until_human_approval",
        lifecycle_state="llm_generated",
    )


def _campaign_manifest_summary(campaign: dict[str, Any]) -> dict[str, Any]:
    return {
        "campaign_id": campaign["campaign_id"],
        "version": campaign["version"],
        "status": campaign["status"],
        "source_references": campaign.get("source_references", []),
        "assets": [
            {
                "filename": asset["filename"],
                "version": asset["version"],
                "type": asset["type"],
                "status": asset["status"],
                "source_references": asset.get("source_references", []),
                "provenance": asset.get("provenance"),
                "provenance_status": asset.get("provenance_status"),
            }
            for asset in campaign.get("assets", [])
        ],
        "review": campaign.get("review"),
        "approved_version": campaign.get("approved_version"),
    }


def _campaign_check(
    check: str,
    ok: bool,
    detail: str,
) -> dict[str, Any]:
    return {"check": check, "ok": bool(ok), "detail": detail}


def _review_campaign(campaign_id: str) -> dict[str, Any]:
    campaign_key, canonical_id = _campaign_identity(campaign_id)
    with _campaign_lock(campaign_key):
        campaign = _load_campaign(campaign_key)
        if campaign is None or campaign.get("campaign_id") != canonical_id:
            raise ContentServiceError(f"campaign not found: {canonical_id}")

        text_assets: list[tuple[dict[str, Any], str]] = []
        for asset in campaign.get("assets", []):
            extension = Path(asset["filename"]).suffix.lower()
            if extension not in {".md", ".txt", ".json"}:
                continue
            text_assets.append((asset, fetch_from_bus(DEPARTMENT, asset["filename"])["content"]))

        all_text = "\n\n".join(content for _, content in text_assets)
        primary_text = "\n\n".join(
            content
            for asset, content in text_assets
            if asset.get("type") in PRIMARY_CONTENT_ARTIFACT_TYPES
        )
        redaction = redact(all_text)
        gate = publish_gate(primary_text, redaction=redaction)
        assets = campaign.get("assets", [])
        types = {asset.get("type") for asset in assets}
        latest_script = next(
            (asset for asset in reversed(assets) if asset.get("type") == "video_script"),
            None,
        )
        audio_cue_is_current = (
            latest_script is None
            or any(
                asset.get("type") == "audio_cue_sheet"
                and latest_script["filename"] in asset.get("dependencies", [])
                for asset in assets
            )
        )
        source_references = campaign.get("source_references", [])
        checks = [
            _campaign_check(
                "dependencies: primary content",
                bool(types & PRIMARY_CONTENT_ARTIFACT_TYPES),
                "พบ draft/script" if types & PRIMARY_CONTENT_ARTIFACT_TYPES else "ต้องมี draft หรือ video script",
            ),
            _campaign_check(
                "dependencies: visual prompt",
                "visual_prompt" in types,
                "พบ visual prompt" if "visual_prompt" in types else "ยังไม่มี visual prompt",
            ),
            _campaign_check(
                "dependencies: audio cue sheet",
                "video_script" not in types or audio_cue_is_current,
                "audio cue อ้างถึงสคริปต์ล่าสุด" if audio_cue_is_current else "ต้องสร้าง audio cue sheet ใหม่จากสคริปต์ล่าสุด",
            ),
            _campaign_check(
                "claims: source references supplied",
                bool(source_references),
                f"พบ {len(source_references)} รายการ" if source_references else "ยังไม่มีแหล่งอ้างอิง",
            ),
            _campaign_check(
                "claims: source verification",
                False,
                "ระบบยังไม่ได้ตรวจสอบแหล่งอ้างอิงโดยอิสระ; ต้องให้มนุษย์ยืนยัน",
            ),
            _campaign_check(
                "media rights",
                bool(assets) and all(
                    asset.get("media_rights_status") == "confirmed" for asset in assets
                ),
                "ต้องยืนยันลิขสิทธิ์ภาพ/เพลง/เสียงก่อนเผยแพร่",
            ),
            _campaign_check(
                "redaction",
                redaction.ok,
                "ไม่พบรายการค้างตรวจ" if redaction.ok else "พบข้อมูลที่ต้อง redact หรือให้มนุษย์ตรวจ",
            ),
        ]
        checks.extend(
            {
                "check": item["rule"],
                "ok": item["ok"],
                "detail": item.get("detail", ""),
            }
            for item in gate.checks
            if item["rule"].startswith("R")
        )
        gate_passed = all(item["ok"] for item in checks)
        report_lines = [
            "# Campaign Publish Gate",
            "",
            f"- **Campaign:** {canonical_id}",
            f"- **Version reviewed:** {campaign['version']}",
            "- **Decision:** review_required; human approval is still required.",
            "",
            "## Checks",
        ]
        report_lines.extend(
            f"- {'PASS' if item['ok'] else 'REVIEW'} — {item['check']}: {item['detail']}"
            for item in checks
        )
        client_provenance = [
            asset
            for asset in assets
            if asset.get("provenance_status") == "client_supplied_unverified"
        ]
        if client_provenance:
            report_lines.extend(["", "## Client-supplied provenance"])
            report_lines.extend(
                "- `{}; client={}; provider={}; model={}` (self-reported; not authenticated)".format(
                    asset["filename"],
                    asset["provenance"].get("client", ""),
                    asset["provenance"].get("provider") or "unspecified",
                    asset["provenance"].get("model") or "unspecified",
                )
                for asset in client_provenance
            )
        report_lines.extend(["", "## Redaction and R1–R5 detail", gate_report_md(redaction, gate)])
        report_task = _asset_task_id(canonical_id, "publish-gate", campaign["version"])
        report_result = submit_to_bus(DEPARTMENT, report_task, "\n".join(report_lines), "md")
        review = {
            "status": "review_required",
            "version": campaign["version"],
            "gate_passed": gate_passed,
            "checks": checks,
            "report": {
                "filename": report_result["filename"],
                "path": report_result["path"],
            },
            "reviewed_at": _now(),
        }
        campaign["status"] = "review_required"
        campaign["review"] = review
        manifest_file = _save_campaign(campaign)
        return {
            "campaign_id": canonical_id,
            "version": campaign["version"],
            "status": "review_required",
            "gate_passed": gate_passed,
            "approval_required": True,
            "checks": checks,
            "manifest": _campaign_manifest_summary(campaign),
            "campaign_manifest": manifest_file,
            "report": review["report"],
            "publish_action": "blocked_until_human_approval",
        }


def review_publish_gate(
    filename: str | None = None,
    campaign_id: str | None = None,
) -> dict[str, Any]:
    if campaign_id:
        campaign_key, canonical_id = _campaign_identity(campaign_id)
        if _load_campaign(campaign_key) is not None:
            return _review_campaign(canonical_id)
    if not filename and campaign_id:
        # Backward-compatible positional calls used to pass a filename only.
        filename = campaign_id
    if not filename:
        raise ContentServiceError("campaign_id or filename is required")

    fetched = fetch_from_bus(DEPARTMENT, filename)
    redaction = redact(fetched["content"])
    gate = publish_gate(fetched["content"], redaction=redaction)
    report = gate_report_md(redaction, gate)
    report_task = f"{slugify(Path(filename).stem, 'review')[:51]}_publish_gate"
    report_result = submit_to_bus(
        DEPARTMENT,
        report_task,
        report,
        "md",
    )
    return {
        "status": "review_required",
        "department": "content-creator",
        "filename": fetched["filename"],
        "gate_passed": gate.passed,
        "approval_required": True,
        "redaction": redaction.summary(),
        "checks": gate.checks,
        "report": {
            "filename": report_result["filename"],
            "path": report_result["path"],
        },
        "publish_action": "blocked_until_human_approval",
    }


def record_human_approval(
    campaign_id: str,
    version: str,
    approver_note: str,
) -> dict[str, Any]:
    campaign_key, canonical_id = _campaign_identity(campaign_id)
    note = _required(approver_note, "approver_note")
    normalized_version = str(version or "").strip().lower()
    if normalized_version.isdigit():
        normalized_version = f"v{normalized_version}"
    if not re.fullmatch(r"v\d+", normalized_version):
        raise ContentServiceError("version must use vN format, for example v3")

    with _campaign_lock(campaign_key):
        campaign = _load_campaign(campaign_key)
        if campaign is None or campaign.get("campaign_id") != canonical_id:
            raise ContentServiceError(f"campaign not found: {canonical_id}")
        if normalized_version != campaign.get("version"):
            raise ContentServiceError(
                f"approval version mismatch; current campaign version is {campaign.get('version')}"
            )
        review = campaign.get("review") or {}
        if review.get("version") != normalized_version:
            raise ContentServiceError("run review_publish_gate for this exact campaign version first")
        failed_checks = [
            item.get("check", "unknown")
            for item in review.get("checks", [])
            if not item.get("ok")
        ]

        approval = {
            "campaign_id": canonical_id,
            "version": normalized_version,
            "status": "approved",
            "recorded_at": _now(),
            "recorded_by": "human MCP caller; identity is not independently authenticated",
            "approver_note": note,
            "gate_passed": bool(review.get("gate_passed")),
            "overrides_failed_checks": failed_checks,
            "review_report": review.get("report"),
        }
        approval_result = submit_to_bus(
            DEPARTMENT,
            _asset_task_id(canonical_id, "approval", normalized_version),
            json.dumps(approval, ensure_ascii=False, sort_keys=True, indent=2),
            "json",
        )
        approval_record = {
            **approval,
            "filename": approval_result["filename"],
            "path": approval_result["path"],
        }
        campaign.setdefault("approval_records", []).append(approval_record)
        campaign["status"] = "approved"
        campaign["approved_version"] = normalized_version
        manifest_file = _save_campaign(campaign)
        return {
            "campaign_id": canonical_id,
            "version": normalized_version,
            "status": "approved",
            "approval_required": False,
            "gate_passed": bool(review.get("gate_passed")),
            "overrides_failed_checks": failed_checks,
            "approval_record": {
                "filename": approval_result["filename"],
                "path": approval_result["path"],
            },
            "campaign_manifest": manifest_file,
        }


def sop_resource() -> str:
    parts = [
        "# Content Creator SOP\n",
        "หัวหน้าแผนก: เสก (Sek)\n",
        "Specialists: Kawee (copy), Film (script), Art (visual), Sound (audio), Ink (strategy and publish gate).\n",
        "Lifecycle: scaffold → client_generated → llm_generated → human_edited → review_required → approved; state changes require evidence.\n",
        "Client/provider/model provenance is client-supplied and unverified; API keys must never be sent to MCP.\n",
        "Audio cue and voice/lip-sync tools only create files; they never call external providers.\n",
        "\n## Operating rules\n",
        "1. ทุกชิ้นต้องมีเป้าหมาย กลุ่มเป้าหมาย และแพลตฟอร์ม\n",
        "2. ทุก output เป็น draft จนกว่ามนุษย์จะผ่าน Publish Gate\n",
        "3. ห้ามเผยแพร่ข้อมูลลับ ชื่อลูกค้า พาธภายใน คีย์ หรือ claim ที่ไม่มีหลักฐาน\n",
        "4. เก็บ payload จริงใน `central_bus/content/` และคืน path แบบย่อให้ client\n",
        "5. ElevenLabs เป็นบริการคิดเครดิต; voiceover ทุกครั้งต้องส่ง `approved=true`\n",
    ]
    for label, path in (("Brand voice", BRAND_GUIDELINES_PATH), ("Department profile", PROFILE_PATH)):
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
            parts.extend([f"\n## {label}\n", text[:6_000]])
    return "\n".join(parts)[:14_000]


def result_json(value: dict[str, Any]) -> str:
    return as_json(value)
