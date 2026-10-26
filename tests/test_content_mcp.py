from __future__ import annotations

import json

import pytest

from solocorp_mcp import bus_store
from solocorp_mcp.departments import content_service
from solocorp_mcp.departments.content_mcp import content_sop, mcp


@pytest.fixture
def isolated_bus(tmp_path, monkeypatch):
    monkeypatch.setattr(bus_store, "BUS_ROOT", tmp_path / "central_bus")
    return tmp_path / "central_bus"


def test_content_department_has_head_and_internal_specialists():
    info = content_service.department_info()
    assert info["head"]["id"] == "content-creator-sek"
    assert {item["id"] for item in info["specialists"]} == {
        "copywriter-kawee",
        "scriptwriter-film",
        "visual-designer-art",
        "audio-designer-sound",
        "content-analyst-ink",
    }


def test_draft_is_written_to_content_bus(isolated_bus):
    result = content_service.create_content_draft(
        "หัวข้อทดลอง", "การทำงานของเอเจนต์", "เจ้าของกิจการขนาดเล็ก", "social_post"
    )
    assert result["status"] == "created"
    # The test redirects the bus outside the repository, so manifests are
    # relative to the configured bus root (production paths are
    # ``central_bus/content/...``).
    assert result["path"].startswith("content/")
    artifact = bus_store.fetch_from_bus("content", result["filename"])
    assert "## Hook" in artifact["content"]
    assert result["human_review_required"] is True


def test_video_and_visual_tools_write_artifacts(isolated_bus):
    video = content_service.create_video_script("คลิปทดลอง", "อธิบายระบบให้คนตัวเล็ก", 60)
    visual = content_service.design_visual_prompt("คนตัวเล็กกับเทคโนโลยี", "LinkedIn", "1:1")
    assert video["filename"].endswith(".md")
    assert visual["filename"].endswith(".md")
    assert "Visual scene" in bus_store.fetch_from_bus("content", video["filename"])["content"]
    assert "Negative Prompt" in bus_store.fetch_from_bus("content", visual["filename"])["content"]


def test_campaign_bundle_tracks_versions_audio_and_human_approval(isolated_bus):
    campaign_id = "spring-launch"
    references = ["https://research.example/report"]
    draft = content_service.create_content_draft(
        "Campaign draft",
        "ข้อเท็จจริงที่ต้องตรวจสอบ",
        "ผู้ติดตามข่าวเทคโนโลยี",
        "article",
        campaign_id,
        references,
    )
    script = content_service.create_video_script(
        "Campaign video", "สรุปประเด็นจากงานวิจัย", 60, campaign_id
    )
    visual = content_service.design_visual_prompt(
        "งานวิจัยกับการทำงาน", "LinkedIn", "16:9", campaign_id
    )
    cue_sheet = content_service.design_audio_experience(
        campaign_id, script["filename"]
    )
    voice_config = content_service.generate_voice_lipsync_prompt(
        campaign_id, script["filename"], "dr-solodev-clone"
    )

    assert draft["status"] == "scaffold"
    assert visual["version"] == "v3"
    assert cue_sheet["version"] == "v4"
    assert voice_config["version"] == "v5"
    assert voice_config["source_references"] == references
    config = json.loads(
        bus_store.fetch_from_bus("content", voice_config["filename"])["content"]
    )
    assert config["provider_api_called"] is False
    assert config["voice_clone_consent"]["confirmed"] is False

    review = content_service.review_publish_gate(campaign_id=campaign_id)
    assert review["status"] == "review_required"
    assert review["version"] == "v5"
    assert review["approval_required"] is True
    assert review["gate_passed"] is False
    assert len(review["manifest"]["assets"]) == 5

    approval = content_service.record_human_approval(
        campaign_id, "v5", "อนุมัติเวอร์ชันนี้หลังตรวจงานโดยมนุษย์แล้ว"
    )
    assert approval["status"] == "approved"
    assert approval["version"] == "v5"
    record = json.loads(
        bus_store.fetch_from_bus("content", approval["approval_record"]["filename"])["content"]
    )
    assert record["gate_passed"] is False
    assert record["overrides_failed_checks"]
    assert "not independently authenticated" in record["recorded_by"]

    updated = content_service.create_content_draft(
        "Campaign update", "ฉบับแก้ไข", "ผู้ติดตามข่าวเทคโนโลยี", "article", campaign_id
    )
    assert updated["version"] == "v6"
    assert updated["status"] == "scaffold"
    with pytest.raises(content_service.ContentServiceError, match="version mismatch"):
        content_service.record_human_approval(
            campaign_id, "v5", "อนุมัติฉบับเก่า"
        )


def test_human_edit_versions_artifact_and_invalidates_old_audio_cue(isolated_bus):
    campaign_id = "edited-campaign"
    script = content_service.create_video_script(
        "Original script", "ข้อความหลัก", 30, campaign_id
    )
    content_service.design_audio_experience(campaign_id, script["filename"])
    original = bus_store.fetch_from_bus("content", script["filename"])["content"]
    edited = content_service.save_human_edited_artifact(
        campaign_id,
        script["filename"],
        original + "\n## Human edit\n\nเพิ่มข้อจำกัดที่ตรวจแล้ว\n",
        "แก้ข้อความตามข้อมูลที่ตรวจสอบ",
    )
    assert edited["status"] == "human_edited"
    assert edited["version"] == "v3"
    assert edited["supersedes"] == script["filename"]

    review = content_service.review_publish_gate(campaign_id=campaign_id)
    audio_check = next(
        item for item in review["checks"]
        if item["check"] == "dependencies: audio cue sheet"
    )
    assert audio_check["ok"] is False


def test_publish_gate_creates_report_and_never_publishes(isolated_bus):
    draft = content_service.create_content_draft(
        "Gate test", "หลักฐานและความโปร่งใส", "ผู้สร้างระบบ", "social_post"
    )
    result = content_service.review_publish_gate(draft["filename"])
    assert result["status"] == "review_required"
    assert result["approval_required"] is True
    assert result["publish_action"] == "blocked_until_human_approval"
    report = bus_store.fetch_from_bus("content", result["report"]["filename"])
    assert "Publish Gate" in report["content"]


def test_publish_gate_truncates_long_report_task_id(isolated_bus):
    artifact = bus_store.submit_to_bus("content", "x" * 64, "# Draft\n\nSafe text", "md")
    result = content_service.review_publish_gate(artifact["filename"])
    assert result["report"]["filename"].endswith(".md")


def test_content_server_contract_and_resource():
    names = {tool.name for tool in mcp._tool_manager.list_tools()}
    assert names == {
        "content_department_info",
        "create_content_draft",
        "create_video_script",
        "design_visual_prompt",
        "design_audio_experience",
        "generate_voice_lipsync_prompt",
        "generate_voiceover",
        "review_publish_gate",
        "record_human_approval",
        "save_human_edited_artifact",
    }
    assert "Content Creator SOP" in content_sop()
    assert "เสก" in content_sop()


def test_generated_audio_storage_is_binary_safe(isolated_bus):
    result = bus_store.submit_bytes_to_bus(
        "content", "voiceover-test", b"\x00\xffMP3", "mp3"
    )
    assert result["filename"].endswith(".mp3")
    assert (
        (isolated_bus / "content" / result["filename"]).read_bytes()
        == b"\x00\xffMP3"
    )


def test_voiceover_requires_per_request_approval(isolated_bus):
    raw = mcp._tool_manager.get_tool("generate_voiceover").fn(
        "ทดสอบ", "ข้อความสั้น", "voice-id", False
    )
    result = json.loads(raw)
    assert result["status"] == "error"
    assert "approved=true" in result["message"]


def test_mcp_tool_errors_are_json(isolated_bus):
    raw = mcp._tool_manager.get_tool("create_video_script").fn("", "x", 60)
    result = json.loads(raw)
    assert result["status"] == "error"
    assert result["error"] == "ContentServiceError"
