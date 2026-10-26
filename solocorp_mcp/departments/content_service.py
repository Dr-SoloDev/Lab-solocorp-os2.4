"""Content Creator domain logic shared by MCP adapters and future clients."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from solocorp_mcp.bus_store import as_json, fetch_from_bus, submit_to_bus
from solocorp_skills.redact import gate_report_md, publish_gate, redact

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "profiles" / "15-content-creator" / "SOUL.md"
BRAND_GUIDELINES_PATH = ROOT / "docs" / "brand" / "BRAND-GUIDELINES-v1.md"
DEPARTMENT = "content"
CONTENT_TYPES = {"article", "social_post", "newsletter"}
SPECIALISTS = (
    {"id": "copywriter", "responsibility": "โครงร่าง คอปปี้ และ hook"},
    {"id": "visual-creator", "responsibility": "แนวทางภาพและ visual direction"},
    {"id": "video-editor", "responsibility": "โครงสคริปต์และจังหวะวิดีโอ"},
    {"id": "trend-scout", "responsibility": "บริบทแพลตฟอร์มและแนวโน้ม"},
)


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
    return {**result, "status": "created", "department": "content-creator", **extra}


def create_content_draft(
    title: str,
    topic: str,
    target_audience: str,
    content_type: str = "article",
) -> dict[str, Any]:
    title = _required(title, "title")
    topic = _required(topic, "topic")
    audience = _required(target_audience, "target_audience")
    kind = str(content_type or "article").strip().lower()
    if kind not in CONTENT_TYPES:
        raise ContentServiceError(
            f"content_type must be one of: {', '.join(sorted(CONTENT_TYPES))}"
        )

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
        f"{sections}\n"
    )
    result = submit_to_bus(DEPARTMENT, f"{slugify(title)}_draft", content, "md")
    return _manifest(result, title=title, content_type=kind, human_review_required=True)


def create_video_script(
    title: str, core_message: str, duration_seconds: int = 60
) -> dict[str, Any]:
    title = _required(title, "title")
    message = _required(core_message, "core_message")
    if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, int):
        raise ContentServiceError("duration_seconds must be an integer")
    if duration_seconds < 15 or duration_seconds > 3_600:
        raise ContentServiceError("duration_seconds must be between 15 and 3,600")

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
    )
    result = submit_to_bus(DEPARTMENT, f"{slugify(title)}_script", script, "md")
    return _manifest(result, title=title, duration_seconds=duration_seconds, human_review_required=True)


def design_visual_prompt(
    theme: str, platform: str, aspect_ratio: str = "16:9"
) -> dict[str, Any]:
    theme = _required(theme, "theme")
    platform = _required(platform, "platform")
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
    )
    result = submit_to_bus(DEPARTMENT, f"{slugify(theme)}_visual_prompt", prompt, "md")
    return _manifest(
        result, theme=theme, platform=platform, aspect_ratio=aspect_ratio, human_review_required=True
    )


def review_publish_gate(filename: str) -> dict[str, Any]:
    fetched = fetch_from_bus(DEPARTMENT, filename)
    redaction = redact(fetched["content"])
    gate = publish_gate(fetched["content"], redaction=redaction)
    report = gate_report_md(redaction, gate)
    report_result = submit_to_bus(
        DEPARTMENT,
        f"{slugify(Path(filename).stem, 'review')}_publish_gate",
        report,
        "md",
    )
    return {
        "status": "review_required" if not gate.passed else "ready_for_human_approval",
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


def sop_resource() -> str:
    parts = [
        "# Content Creator SOP\n",
        "หัวหน้าแผนก: เสก (Sek)\n",
        "Specialists: Copywriter · Visual Creator · Video Editor · Trend Scout\n",
        "\n## Operating rules\n",
        "1. ทุกชิ้นต้องมีเป้าหมาย กลุ่มเป้าหมาย และแพลตฟอร์ม\n",
        "2. ทุก output เป็น draft จนกว่ามนุษย์จะผ่าน Publish Gate\n",
        "3. ห้ามเผยแพร่ข้อมูลลับ ชื่อลูกค้า พาธภายใน คีย์ หรือ claim ที่ไม่มีหลักฐาน\n",
        "4. เก็บ payload จริงใน `central_bus/content/` และคืน path แบบย่อให้ client\n",
    ]
    for label, path in (("Brand voice", BRAND_GUIDELINES_PATH), ("Department profile", PROFILE_PATH)):
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
            parts.extend([f"\n## {label}\n", text[:6_000]])
    return "\n".join(parts)[:14_000]


def result_json(value: dict[str, Any]) -> str:
    return as_json(value)
