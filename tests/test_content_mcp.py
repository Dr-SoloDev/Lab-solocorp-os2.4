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
        "copywriter",
        "visual-creator",
        "video-editor",
        "trend-scout",
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
        "generate_voiceover",
        "review_publish_gate",
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
