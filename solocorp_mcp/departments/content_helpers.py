"""Orchestration helpers for repeatable Content Creator campaign series."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from . import content_service

DEFAULT_CAMPAIGN_ID = "solocorp-origin-10x10s"
EPISODE_COUNT = 10
MAX_EPISODE_SOURCE_CHARS = 1_500
FF_TRACKING_EPISODE_SHOTS = 20
FF_TRACKING_PALETTES = ("Thermal", "Mono", "Phosphor", "Amber", "Navy", "Neon")

DEFAULT_BEATS: tuple[dict[str, str], ...] = (
    {
        "id": "ep01-origin-time",
        "title_th": "EP01 จุดเริ่มต้น 02:52",
        "angle": "Origin brief ระบุจุดเริ่มต้นเวลา 02:52 น. วันที่ 15 มิ.ย. 2026",
        "visual": "กราฟิกนาฬิกา 02:52 กับ terminal และ Lenovo Z580 แบบภาพสังเคราะห์ ไม่อ้างว่าเป็น footage จริง",
        "source": "User-supplied Origin brief; independently unverified.",
    },
    {
        "id": "ep02-lenovo-z580",
        "title_th": "EP02 Lenovo Z580",
        "angle": "Lenovo Z580 คืออุปกรณ์ตั้งต้นที่ระบุไว้ใน Origin brief",
        "visual": "ภาพ schematic ของ Lenovo Z580 ในฐานะจุดเริ่มต้น ห้ามเติมสภาพเครื่องหรือเหตุการณ์ที่ไม่มีหลักฐาน",
        "source": "User-supplied Origin brief; independently unverified.",
    },
    {
        "id": "ep03-why-ceo",
        "title_th": "EP03 ทำไม AI ต้องมี CEO",
        "angle": "คำถามตั้งต้นคือจะกำหนดเจ้าของงานและผู้ตัดสินใจให้ทีม AI หลายบทบาทอย่างไร",
        "visual": "ภาพแผนผัง AI หลายบทบาทที่เชื่อมกับจุดประสานงานกลาง โดยไม่สร้างจำนวนหรือผลลัพธ์เกินข้อมูล",
        "source": "User-supplied Origin story beat; independently unverified.",
    },
    {
        "id": "ep04-org-chart-gap",
        "title_th": "EP04 ช่องว่างบนผังองค์กร",
        "angle": "README ระบุ 18 Heads บน chart และระบุว่า COO กับ R&D Lab อยู่ใน tree แต่ยังไม่อยู่บน chart",
        "visual": "เทียบ organization chart กับ profile tree โดยติดป้ายช่องว่างว่า not on chart, not missing agents",
        "source": "README.md; profiles/INDEX.md.",
    },
    {
        "id": "ep05-central-bus",
        "title_th": "EP05 Central Bus",
        "angle": "SoloCorp OS แยก control flow ออกจาก data flow และใช้ Central Bus รับส่งข้อมูลระหว่างแผนก",
        "visual": "แผนภาพ Control Layer และ Central Bus ที่เชื่อมแผนกด้วยเส้นทางข้อมูลอย่างชัดเจน",
        "source": "README.md; central_bus/.",
    },
    {
        "id": "ep06-content-pilot",
        "title_th": "EP06 Content Creator pilot",
        "angle": "Content Creator เป็น pilot ที่มี Head เสกประสานผู้เชี่ยวชาญห้าบทบาทตาม SOUL และ service roster",
        "visual": "ภาพทีม production ห้าบทบาททำงานหลัง Creative Director โดยใช้ชื่อจาก profiles/INDEX.md",
        "source": "profiles/15-content-creator/SOUL.md; solocorp_mcp/departments/content_service.py.",
    },
    {
        "id": "ep07-two-mcps",
        "title_th": "EP07 MCP สองตัว",
        "angle": "bus_mcp ดูแลการรับส่งข้อมูล ส่วน content_mcp เปิดเครื่องมือของแผนก Content Creator",
        "visual": "แผนภาพ bus_mcp และ content_mcp เชื่อม Central Bus โดยไม่แสดงการเรียกบริการที่ไม่มีในระบบ",
        "source": "solocorp_mcp/bus_mcp.py; solocorp_mcp/departments/content_mcp.py.",
    },
    {
        "id": "ep08-human-approval",
        "title_th": "EP08 Human Approval Gate",
        "angle": "AI ช่วยสร้าง draft ได้ แต่ Publish Gate ยังคง review_required จนมนุษย์อนุมัติ",
        "visual": "หน้าจอ review_required พร้อมปุ่มรอ human approval ห้ามแสดงตรา approved ก่อนมีการอนุมัติจริง",
        "source": "solocorp_mcp/departments/content_service.py; docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md.",
    },
    {
        "id": "ep09-prototype-to-os",
        "title_th": "EP09 จาก prototype สู่ OS",
        "angle": "SoloCorp OS v2.4 เป็น product-pack line แบบ pre-release ตาม README",
        "visual": "timeline จาก prototype สู่ product pack v2.4 pre-release โดยไม่อ้างว่าเป็น release สุดท้าย",
        "source": "README.md.",
    },
    {
        "id": "ep10-build-together",
        "title_th": "EP10 มาร่วมสร้าง",
        "angle": "ชวนผู้สร้างร่วมทดลองและพัฒนาระบบเปิด โดยบอกสถานะ pre-release อย่างตรงไปตรงมา",
        "visual": "ภาพเชิญชวนผู้สร้างเข้าร่วมพัฒนา พร้อมระบุ SoloCorp OS v2.4 pre-release",
        "source": "README.md; LICENSE.",
    },
)


def _partition(items: list[str], count: int = EPISODE_COUNT) -> list[list[str]]:
    quotient, remainder = divmod(len(items), count)
    groups: list[list[str]] = []
    offset = 0
    for index in range(count):
        size = quotient + (1 if index < remainder else 0)
        groups.append(items[offset:offset + size])
        offset += size
    return groups


def _thai_graphemes(text: str) -> list[str]:
    clusters: list[str] = []
    for character in text:
        if unicodedata.category(character).startswith("M") and clusters:
            clusters[-1] += character
        else:
            clusters.append(character)
    return clusters


def _split_long_text_to_10(text: str) -> list[str]:
    """Split supplied history into ten balanced, non-empty Thai-safe excerpts."""

    raw = str(text or "").strip()
    if not raw:
        raise content_service.ContentServiceError("long_history_text is required")

    sentence_parts = [
        part.strip()
        for part in re.split(r"(?<=[.!?。！？…])\s+|\n+", raw)
        if part.strip()
    ]
    if len(sentence_parts) >= EPISODE_COUNT:
        return [" ".join(group) for group in _partition(sentence_parts)]

    try:
        from pythainlp.tokenize import word_tokenize

        words = [word for word in word_tokenize(raw, keep_whitespace=False) if word.strip()]
    except ImportError:
        words = re.findall(r"\S+", raw)
    if len(words) < EPISODE_COUNT:
        words = _thai_graphemes(raw)
        separator = ""
    else:
        separator = " "
    if len(words) < EPISODE_COUNT:
        raise content_service.ContentServiceError(
            "long_history_text is too short to create ten non-empty episode excerpts"
        )
    return [separator.join(group) for group in _partition(words)]


def _ff_tracking_scenes(episode_number: int) -> list[dict[str, Any]]:
    """Build a 10-second, ASCII-only workflow visualization from the known beat."""

    anchors = {
        1: ["ORIGIN STORY", "USER SUPPLIED", "SOURCE UNVERIFIED", "02:52", "15 JUN 2026", "LENOVO Z580", "ONE CREATOR", "START HERE"],
        2: ["LENOVO Z580", "USER SUPPLIED", "SOURCE UNVERIFIED", "STARTING DEVICE", "ORIGIN CONTEXT", "ONE MACHINE", "START HERE", "BUILD IN STEPS"],
        3: ["WHY AI CEO", "USER SUPPLIED", "SOURCE UNVERIFIED", "DEFINE OWNERS", "SPECIALIST ROLES", "CLEAR HANDOFFS", "CENTRAL BUS", "HUMAN DECIDES"],
    }[episode_number]
    workflow = [
        "READ THE BRIEF",
        "DRAFT THE STORY",
        "WRITE 10S SCRIPT",
        "DESIGN VISUAL",
        "PLAN 20 SHOTS",
        "LOCAL RENDER PLAN",
        "RENDER NOT STARTED",
        "CHECK PROVENANCE",
        "REVIEW REQUIRED",
        "HUMAN APPROVAL",
        "NO AUTO PUBLISH",
        "ITERATE AGAIN",
    ]
    labels = (anchors + workflow)[:FF_TRACKING_EPISODE_SHOTS]
    if len(labels) != FF_TRACKING_EPISODE_SHOTS:
        raise RuntimeError(f"EP{episode_number:02d} does not provide a full ff-tracking shot plan")

    scenes: list[dict[str, Any]] = []
    for shot_index, label in enumerate(labels, start=1):
        scenes.append(
            {
                "scene_id": f"ep{episode_number:02d}-shot-{shot_index:02d}",
                "episode_id": f"EP{episode_number:02d}",
                "kind": "Typing",
                "text": label,
                "palette": FF_TRACKING_PALETTES[(shot_index - 1) % len(FF_TRACKING_PALETTES)],
                "camera": {
                    "tilt_x": 0.16 + (shot_index % 3) * 0.04,
                    "tilt_y": -0.24 + (shot_index % 4) * 0.08,
                    "roll": -0.03 + (shot_index % 3) * 0.03,
                    "zoom_start": 1.8 + (shot_index % 4) * 0.15,
                    "zoom_end": 2.1 + (shot_index % 4) * 0.15,
                    "pan_x": float(((shot_index % 5) - 2) * 30),
                    "pan_y": float(((shot_index % 3) - 1) * 18),
                    "blur": 0.8 + (shot_index % 3) * 0.2,
                    "shake": 0.4,
                },
                "hero": [250.0, 540.0],
                "size": 72.0,
            }
        )
    return scenes


def create_10s_series(
    long_history_text: str,
    campaign_id: str = DEFAULT_CAMPAIGN_ID,
    target_audience: str = "ผู้สร้างเดี่ยวและนักพัฒนาที่กำลังสร้างเครื่องมือ AI",
    content_type: str = "social_post",
    with_audio: bool = False,
    allow_existing: bool = False,
    with_ff_tracking: bool = False,
    ff_tracking_episode_count: int = 3,
) -> list[dict[str, Any]]:
    """Create ten episodes with draft, 10-second script, and visual prompt.

    The default writes 30 scaffold artifacts in ascending campaign versions.
    Set ``with_audio=True`` to add one audio cue sheet per episode. Set
    ``with_ff_tracking=True`` to add one 20-shot, 10-second plan for each of
    the first ``ff_tracking_episode_count`` episodes (default three). This
    helper stores plans only; it does not call an LLM, Rust, or FFmpeg.
    """

    if len(DEFAULT_BEATS) != EPISODE_COUNT:
        raise RuntimeError("Origin series must define exactly ten story beats")
    if not isinstance(with_ff_tracking, bool):
        raise content_service.ContentServiceError("with_ff_tracking must be boolean")
    if with_ff_tracking and (
        isinstance(ff_tracking_episode_count, bool)
        or not isinstance(ff_tracking_episode_count, int)
        or not 1 <= ff_tracking_episode_count <= 3
    ):
        raise content_service.ContentServiceError("ff_tracking_episode_count must be an integer from 1 to 3")
    chunks = _split_long_text_to_10(long_history_text)
    campaign_key, canonical_id = content_service._campaign_identity(campaign_id)
    if not allow_existing and content_service._load_campaign(campaign_key) is not None:
        raise content_service.ContentServiceError(
            f"campaign already exists: {canonical_id}; choose a new campaign_id or set allow_existing=True"
        )
    if len(chunks) != EPISODE_COUNT or any(not chunk.strip() for chunk in chunks):
        raise content_service.ContentServiceError("series input did not split into ten non-empty excerpts")
    if any(len(chunk) > MAX_EPISODE_SOURCE_CHARS for chunk in chunks):
        raise content_service.ContentServiceError(
            f"each history excerpt must be at most {MAX_EPISODE_SOURCE_CHARS} characters; shorten or curate the source"
        )

    results: list[dict[str, Any]] = []
    for episode_number, (beat, excerpt) in enumerate(zip(DEFAULT_BEATS, chunks), start=1):
        episode_id = f"EP{episode_number:02d}"
        source_references = [
            "User-supplied Origin brief and history excerpt; independently unverified.",
            f"{beat['source']} Story beat {episode_id}: {beat['title_th']}.",
        ]
        context = f"{beat['angle']}\n\nUser-supplied history excerpt: {excerpt}"
        inline_context = " ".join(context.split())
        title = beat["title_th"]
        try:
            draft = content_service.create_content_draft(
                title=title,
                topic=context,
                target_audience=target_audience,
                content_type=content_type,
                campaign_id=canonical_id,
                source_references=source_references,
            )
            results.append({**draft, "episode_id": episode_id, "artifact_role": "draft"})

            script = content_service.create_video_script(
                title=title,
                core_message=inline_context,
                duration_seconds=10,
                campaign_id=canonical_id,
                source_references=source_references,
            )
            results.append({**script, "episode_id": episode_id, "artifact_role": "video_script"})

            visual = content_service.design_visual_prompt(
                theme=" ".join(f"{beat['visual']} Episode context: {context}".split()),
                platform="tiktok",
                aspect_ratio="9:16",
                campaign_id=canonical_id,
                source_references=source_references,
            )
            results.append({**visual, "episode_id": episode_id, "artifact_role": "visual_prompt"})

            if with_audio:
                audio = content_service.design_audio_experience(
                    campaign_id=canonical_id,
                    script_filename=script["filename"],
                )
                results.append({**audio, "episode_id": episode_id, "artifact_role": "audio_cue_sheet"})

            if with_ff_tracking and episode_number <= ff_tracking_episode_count:
                tracking = content_service.build_ff_tracking_manifest(
                    campaign_id=canonical_id,
                    scene_definitions=_ff_tracking_scenes(episode_number),
                    camera_params={
                        "tilt_x": 0.2,
                        "tilt_y": -0.2,
                        "roll": 0.0,
                        "zoom_start": 1.8,
                        "zoom_end": 2.4,
                        "pan_x": 0.0,
                        "pan_y": 0.0,
                        "blur": 1.0,
                        "shake": 0.0,
                    },
                )
                results.append(
                    {**tracking, "episode_id": episode_id, "artifact_role": "ff_tracking_manifest"}
                )
        except (content_service.ContentServiceError, OSError, UnicodeError, TypeError) as exc:
            raise content_service.ContentServiceError(
                f"series stopped at {episode_id} after {len(results)} saved artifacts; "
                f"the append-only campaign may be partial: {exc}"
            ) from exc

    expected_count = (
        EPISODE_COUNT * (4 if with_audio else 3)
        + (ff_tracking_episode_count if with_ff_tracking else 0)
    )
    if len(results) != expected_count:
        raise content_service.ContentServiceError(
            f"series created {len(results)} artifacts; expected {expected_count}"
        )
    return results
