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


def _create_ffmpeg_job(isolated_bus, campaign_id="ffmpeg-bridge-test", operations=None):
    script = content_service.create_video_script(
        "Bridge test script", "อธิบายการทำงาน", 30, campaign_id
    )
    cue = content_service.design_audio_experience(campaign_id, script["filename"])
    content_dir = isolated_bus / "content"
    source = content_dir / "synthetic-input.mp4"
    source.write_bytes(b"synthetic test fixture; never passed to FFmpeg")
    output = content_dir / "synthetic-preview.mp4"
    operations = operations or [
        {
            "tool": "cut",
            "arguments": {
                "input": str(source),
                "output": str(output),
                "start": "0",
                "duration": "1",
                "fast": True,
            },
        }
    ]
    job = content_service.build_ffmpeg_job_manifest(
        campaign_id, script["filename"], cue["filename"], operations
    )
    return job, script, cue, source, output


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


def test_client_generated_artifact_tracks_provenance_and_gate(isolated_bus):
    campaign_id = "client-generated-pilot"
    references = ["https://research.example/source"]
    provenance = {"client": "codex", "provider": "openai", "model": "gpt-test"}
    content = "## Hook\n\nA test draft.\n\n## Body\n\nSource-grounded content.\n"

    result = content_service.ingest_client_generated_artifact(
        campaign_id,
        "article",
        content,
        provenance,
        references,
    )

    assert result["status"] == "client_generated"
    assert result["lifecycle_state"] == "client_generated"
    assert result["provenance"] == provenance
    assert result["provenance_status"] == "client_supplied_unverified"
    assert result["source_references"] == references
    assert bus_store.fetch_from_bus("content", result["filename"])["content"] == content

    manifest = json.loads(
        bus_store.fetch_from_bus("content", result["campaign_manifest"]["filename"])["content"]
    )
    stored = manifest["assets"][-1]
    assert stored["status"] == "client_generated"
    assert stored["provenance"] == provenance
    assert stored["provenance_status"] == "client_supplied_unverified"
    assert stored["source_references"] == references

    review = content_service.review_publish_gate(campaign_id=campaign_id)
    assert review["status"] == "review_required"
    assert review["approval_required"] is True
    assert review["publish_action"] == "blocked_until_human_approval"
    assert review["manifest"]["assets"][0]["provenance"] == provenance
    report = bus_store.fetch_from_bus("content", review["report"]["filename"])["content"]
    assert "Client-supplied provenance" in report
    assert "self-reported; not authenticated" in report


def test_client_generated_provenance_rejects_credentials_and_unknown_fields(isolated_bus):
    args = {
        "campaign_id": "invalid-provenance-pilot",
        "artifact_type": "article",
        "content": "A short draft.",
        "source_references": [],
    }
    with pytest.raises(content_service.ContentServiceError, match="unsupported provenance fields"):
        content_service.ingest_client_generated_artifact(
            **args,
            provenance={"client": "codex", "api_key": "do-not-store"},
        )

    with pytest.raises(content_service.ContentServiceError, match="credentials must not be sent"):
        content_service.ingest_client_generated_artifact(
            **args,
            provenance={"client": "codex", "provider": "Bearer secret-token-value"},
        )

    with pytest.raises(content_service.ContentServiceError, match="provenance.model must be text"):
        content_service.ingest_client_generated_artifact(
            **args,
            provenance={"client": "codex", "provider": "openai", "model": 42},
        )


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
        "build_ffmpeg_job_manifest",
        "record_ffmpeg_job_result",
        "ingest_client_generated_artifact",
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


def test_ffmpeg_job_manifest_is_versioned_and_records_reported_completion(isolated_bus):
    job, script, cue, source, output = _create_ffmpeg_job(isolated_bus)
    manifest = json.loads(
        bus_store.fetch_from_bus("content", job["filename"])["content"]
    )
    assert job["version"] == "v3"
    assert manifest["provider_contract_version"] == "2.17.1"
    assert manifest["execution"] == {
        "status": "not_started",
        "automatic_execution": False,
        "runtime_gate": "blocked_pending_independent_runtime_verification",
    }
    assert manifest["script_filename"] == script["filename"]
    assert manifest["audio_cue_filename"] == cue["filename"]
    assert manifest["operations"][0]["arguments"]["input"] == str(source)
    assert manifest["operations"][0]["arguments"]["output"] == str(output)

    actual_result = {
        "content": [{"type": "text", "text": "cut completed"}],
        "structuredContent": {
            "status": "completed",
            "exit_code": 0,
            "output": str(output),
        },
    }
    recorded = content_service.record_ffmpeg_job_result(
        "ffmpeg-bridge-test", job["job_id"], job["version"], 0, actual_result
    )
    record = json.loads(
        bus_store.fetch_from_bus("content", recorded["filename"])["content"]
    )
    assert recorded["version"] == "v4"
    assert recorded["execution_status"] == "reported_completed"
    assert recorded["operation_tool"] == "cut"
    assert record["mcp_result"] == actual_result
    assert record["operation_index"] == 0
    campaign = content_service._load_campaign("ffmpeg-bridge-test")
    assert campaign["status"] == "scaffold"
    assert campaign["approved_version"] is None
    assert campaign["review"] is None


def test_ffmpeg_job_result_preserves_actual_failure_without_approval(isolated_bus):
    job, _, _, _, _ = _create_ffmpeg_job(isolated_bus, "ffmpeg-failure-test")
    actual_result = {
        "content": [{"type": "text", "text": "check failed (exit 1)"}],
        "isError": True,
        "structuredContent": {
            "status": "failed",
            "exit_code": 1,
            "error": {"kind": "input", "code": "INPUT_INVALID"},
        },
    }
    recorded = content_service.record_ffmpeg_job_result(
        "ffmpeg-failure-test", job["job_id"], job["version"], 0, actual_result
    )
    record = json.loads(
        bus_store.fetch_from_bus("content", recorded["filename"])["content"]
    )
    assert recorded["execution_status"] == "reported_failure"
    assert record["mcp_result"] == actual_result
    assert record["provider_exit_code"] == 1
    assert record["approval_effect"] == "none"


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        ({"tool": "shell", "arguments": {}}, "unsupported ffmpeg-skill tool"),
        (
            {"tool": "cut", "arguments": {"input": "x", "output": "y", "argv": ["--help"]}},
            "unsupported cut arguments",
        ),
        (
            {"tool": "cut", "arguments": {"input": "x", "output": "y", "fast": "yes"}},
            "must be boolean",
        ),
        (
            {"tool": "cut", "arguments": {"input": "/tmp/private.mp4", "output": "/tmp/out.mp4"}},
            "inside central_bus/content",
        ),
    ],
)
def test_ffmpeg_manifest_rejects_unsupported_operations_and_paths(
    isolated_bus, operation, message
):
    campaign_id = f"invalid-{len(message)}"
    _, script, cue, source, output = _create_ffmpeg_job(isolated_bus, campaign_id)
    operation = json.loads(json.dumps(operation))
    if operation.get("tool") == "cut":
        args = operation["arguments"]
        if args.get("input") == "x":
            args["input"] = str(source)
        if args.get("output") == "y":
            args["output"] = str(output)
    with pytest.raises(content_service.ContentServiceError, match=message):
        content_service.build_ffmpeg_job_manifest(
            campaign_id, script["filename"], cue["filename"], [operation]
        )


def test_ffmpeg_result_rejects_stale_job_version_and_media_blocks(isolated_bus):
    job, _, _, _, _ = _create_ffmpeg_job(isolated_bus, "ffmpeg-stale-test")
    with pytest.raises(content_service.ContentServiceError, match="version mismatch"):
        content_service.record_ffmpeg_job_result(
            "ffmpeg-stale-test", job["job_id"], "v99", 0, {"content": []}
        )
    with pytest.raises(content_service.ContentServiceError, match="bounded text block"):
        content_service.record_ffmpeg_job_result(
            "ffmpeg-stale-test",
            job["job_id"],
            job["version"],
            0,
            {"content": [{"type": "image", "data": "AA==", "mimeType": "image/png"}]},
        )
    with pytest.raises(content_service.ContentServiceError, match="operation_index"):
        content_service.record_ffmpeg_job_result(
            "ffmpeg-stale-test", job["job_id"], job["version"], 1, {"content": []}
        )


def test_ffmpeg_result_rejects_campaign_mismatch_and_unknown_job(isolated_bus):
    job, _, _, _, _ = _create_ffmpeg_job(isolated_bus, "ffmpeg-campaign-a")
    _create_ffmpeg_job(isolated_bus, "ffmpeg-campaign-b")
    empty_result = {"content": []}

    with pytest.raises(content_service.ContentServiceError, match="job_id must identify"):
        content_service.record_ffmpeg_job_result(
            "ffmpeg-campaign-b", job["job_id"], job["version"], 0, empty_result
        )
    with pytest.raises(content_service.ContentServiceError, match="job_id must identify"):
        content_service.record_ffmpeg_job_result(
            "ffmpeg-campaign-a", "ffmpeg-unknown-job", job["version"], 0, empty_result
        )
