from __future__ import annotations

import json
from pathlib import Path

import pytest

from solocorp_mcp import bus_store
from solocorp_mcp.departments import content_helpers, content_mcp, content_service
from solocorp_mcp.departments.content_mcp import content_sop, mcp
from solocorp_mcp.task_tracking import TaskTracker


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
    assert "## Brand Context" in artifact["content"]
    assert "Clear > Clever" in artifact["content"]
    assert result["human_review_required"] is True


def test_video_and_visual_tools_write_artifacts(isolated_bus):
    video = content_service.create_video_script("คลิปทดลอง", "อธิบายระบบให้คนตัวเล็ก", 60)
    visual = content_service.design_visual_prompt("คนตัวเล็กกับเทคโนโลยี", "LinkedIn", "1:1")
    assert video["filename"].endswith(".md")
    assert visual["filename"].endswith(".md")
    assert "Visual scene" in bus_store.fetch_from_bus("content", video["filename"])["content"]
    assert "Negative Prompt" in bus_store.fetch_from_bus("content", visual["filename"])["content"]


def test_campaign_lock_uses_windows_lock_backend_when_fcntl_is_unavailable(isolated_bus, monkeypatch):
    class FakeMsvcrt:
        LK_NBLCK = 1
        LK_UNLCK = 2

        def __init__(self):
            self.operations = []

        def locking(self, fd, operation, length):
            self.operations.append((operation, length))

    fake_msvcrt = FakeMsvcrt()
    monkeypatch.setattr(content_service, "fcntl", None)
    monkeypatch.setattr(content_service, "msvcrt", fake_msvcrt)

    with content_service._campaign_lock("windows-lock-test"):
        assert (isolated_bus / "content" / ".windows-lock-test.lock").read_bytes() == b"\0"

    assert fake_msvcrt.operations == [(FakeMsvcrt.LK_NBLCK, 1), (FakeMsvcrt.LK_UNLCK, 1)]


def test_create_10s_series_writes_30_ordered_artifacts(isolated_bus):
    history = "\n".join(
        (
            "Origin brief ระบุเวลา 02:52 วันที่ 15 มิถุนายน 2026",
            "Lenovo Z580 คืออุปกรณ์ที่ระบุใน brief",
            "เรื่องนี้ตั้งคำถามว่าทีม AI ต้องมีผู้ประสานงานหรือไม่",
            "README ระบุ 18 Heads บน chart และมี COO กับ R&D ใน tree",
            "Central Bus แยก data flow จาก control flow",
            "Content Creator เป็น MCP pilot ที่มี specialist ห้าบทบาท",
            "bus_mcp และ content_mcp มีหน้าที่คนละส่วน",
            "Publish Gate ต้องรอ human approval",
            "SoloCorp OS v2.4 เป็น product pack แบบ pre-release",
            "ผู้สร้างร่วมทดลองและพัฒนาระบบเปิดได้",
        )
    )

    results = content_helpers.create_10s_series(history, campaign_id="solocorp-origin-10x10s")

    assert len(results) == 30
    assert [result["version"] for result in results] == [f"v{index}" for index in range(1, 31)]
    assert [result["type"] for result in results] == [
        kind for _ in range(10) for kind in ("draft", "video_script", "visual_prompt")
    ]
    assert len({result["filename"] for result in results}) == 30
    scripts = [result for result in results if result["type"] == "video_script"]
    assert all(result["duration_seconds"] == 10 for result in scripts)
    sample_script = bus_store.fetch_from_bus("content", scripts[0]["filename"])["content"]
    assert "0–2s" in sample_script
    assert "2–7s" in sample_script
    first_draft = bus_store.fetch_from_bus("content", results[0]["filename"])["content"]
    assert "User-supplied Origin brief" in first_draft
    assert "Brand Context" in first_draft

    campaign_key, _ = content_service._campaign_identity("solocorp-origin-10x10s")
    campaign = content_service._load_campaign(campaign_key)
    assert campaign["version"] == "v30"
    assert campaign["version_number"] == 30
    assert campaign["approved_version"] is None
    assert campaign["review"] is None


def test_split_long_thai_text_returns_ten_nonempty_chunks():
    chunks = content_helpers._split_long_text_to_10("เริ่มจากศูนย์แล้วค่อยๆ สร้างระบบทีละส่วน")
    assert len(chunks) == 10
    assert all(chunk for chunk in chunks)


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


# Department-scoped tools owned by the Content Creator department.
CONTENT_DEPARTMENT_TOOLS = {
    "content_department_info",
    "create_content_draft",
    "create_video_script",
    "design_visual_prompt",
    "design_audio_experience",
    "sound_list_earshot_sfx",
    "sound_render_campaign_sfx",
    "sound_review_campaign_audio",
    "generate_voice_lipsync_prompt",
    "generate_voiceover",
    "review_publish_gate",
    "record_human_approval",
    "save_human_edited_artifact",
    "build_ffmpeg_job_manifest",
    "build_ff_tracking_manifest",
    "record_ffmpeg_job_result",
    "render_campaign_media_local",
    "render_campaign_with_concat",
    "ingest_client_generated_artifact",
    "remove_campaign_asset",
}

# Platform tools mounted on every department MCP: task tracking + registry read.
CONTENT_PLATFORM_TOOLS = {
    "task_create",
    "task_get_status",
    "task_update_status",
    "task_list",
    "module_registry_status",
}

# Admin-only registry writes. A department scope must never expose these.
ADMIN_ONLY_REGISTRY_TOOLS = {"module_registry_update"}


def test_content_server_contract_and_resource():
    names = {tool.name for tool in mcp._tool_manager.list_tools()}
    assert names == CONTENT_DEPARTMENT_TOOLS | CONTENT_PLATFORM_TOOLS
    assert names & ADMIN_ONLY_REGISTRY_TOOLS == set()
    assert "Content Creator SOP" in content_sop()
    assert "เสก" in content_sop()


def test_content_task_tools_cannot_read_or_update_other_departments(tmp_path, monkeypatch):
    tracker = TaskTracker(tmp_path / "tasks")
    monkeypatch.setattr(content_mcp, "_task_tracker", tracker)
    content_task = tracker.create("content", "content-creator", "private content brief")
    qa_task = tracker.create("qa", "qa", "private QA brief")

    get_task = mcp._tool_manager.get_tool("task_get_status").fn
    list_tasks = mcp._tool_manager.get_tool("task_list").fn
    update_task = mcp._tool_manager.get_tool("task_update_status").fn
    create_task = mcp._tool_manager.get_tool("task_create").fn

    assert json.loads(get_task(content_task["task_id"]))["task_id"] == content_task["task_id"]
    assert json.loads(get_task(qa_task["task_id"]))["error"] == "task_not_found"

    listed = json.loads(list_tasks())
    assert [record["task_id"] for record in listed["tasks"]] == [content_task["task_id"]]
    assert json.loads(list_tasks("qa"))["error"] == "task_scope_violation"

    assert json.loads(update_task(qa_task["task_id"], "completed"))["error"] == "task_not_found"
    assert tracker.get(qa_task["task_id"])["status"] == "pending"
    assert json.loads(update_task(content_task["task_id"], "completed"))["status"] == "completed"
    assert json.loads(create_task("qa", "qa", "brief"))["error"] == "task_scope_violation"


def test_generated_audio_storage_is_binary_safe(isolated_bus):
    result = bus_store.submit_bytes_to_bus(
        "content", "voiceover-test", b"\x00\xffMP3", "mp3"
    )
    assert result["filename"].endswith(".mp3")
    assert (
        (isolated_bus / "content" / result["filename"]).read_bytes()
        == b"\x00\xffMP3"
    )


def test_voiceover_tool_accepts_direct_request_without_approval_flag(monkeypatch):
    calls = {}

    def fake_generate_voiceover(*args):
        calls["args"] = args
        return {"filename": "requested-voiceover.mp3"}

    monkeypatch.setattr(content_mcp, "_generate_voiceover", fake_generate_voiceover)
    raw = mcp._tool_manager.get_tool("generate_voiceover").fn(
        "ทดสอบ", "ข้อความสั้น", "voice-id"
    )
    result = json.loads(raw)
    assert result["filename"] == "requested-voiceover.mp3"
    assert calls["args"] == (
        "ทดสอบ",
        "ข้อความสั้น",
        "voice-id",
        "eleven_v4",
        "th",
        None,
    )


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


def test_ff_tracking_manifest_stores_validated_plan_without_execution(isolated_bus):
    campaign_id = "ff-tracking-manifest-test"
    script = content_service.create_video_script(
        "Tracking test", "Show a clear scripted workflow", 10, campaign_id
    )
    result = content_service.build_ff_tracking_manifest(
        campaign_id,
        [
            {
                "scene_id": "scene-01",
                "episode_id": "EP01",
                "kind": "Typing",
                "text": "READ THE BRIEF",
                "palette": "Thermal",
                "camera": {"zoom_start": 1.5},
                "hero": [400, 540],
                "size": 72,
            }
        ],
        {"tilt_x": 0.15},
    )

    stored = json.loads(bus_store.fetch_from_bus("content", result["filename"])["content"])
    scene = stored["scene_definitions"][0]
    assert result["scene_count"] == 1
    assert result["planned_duration_seconds"] == 0.5
    assert result["render_ready"] is False
    assert result["execution_status"] == "not_started"
    assert result["approval_required"] is True
    assert result["published"] is False
    assert stored["scene_definitions"][0]["scene_id"] == "scene-01"
    assert scene["cam"]["tilt_x"] == 0.15
    assert scene["cam"]["zoom"] == [1.5, 2.2]
    assert scene["hero"] == [400.0, 540.0]
    assert stored["script_filename"] == script["filename"]
    assert stored["execution"]["automatic_execution"] is False
    assert stored["publication"]["published"] is False
    assert stored["upstream_contract"]["json_manifest_consumed_by_stock_renderer"] is False

    campaign = content_service._load_campaign("ff-tracking-manifest-test")
    assert campaign["version"] == "v2"
    assert campaign["approved_version"] is None
    assert campaign["review"] is None


@pytest.mark.parametrize(
    ("scenes", "camera_params", "message"),
    [
        ([{"text": "สวัสดี", "kind": "Typing"}], None, "printable ASCII"),
        ([{"text": "VALID", "kind": "Typing", "palette": "Unknown"}], None, "palette is unsupported"),
        ([{"text": "VALID", "kind": "Typing"}], {"shake": 13}, "shake must be between"),
    ],
)
def test_ff_tracking_manifest_rejects_invalid_inputs_without_appending(
    isolated_bus, scenes, camera_params, message
):
    campaign_id = "ff-tracking-invalid-test"
    content_service.create_video_script("Tracking test", "A scripted workflow", 10, campaign_id)
    with pytest.raises(content_service.ContentServiceError, match=message):
        content_service.build_ff_tracking_manifest(campaign_id, scenes, camera_params)

    campaign = content_service._load_campaign("ff-tracking-invalid-test")
    assert campaign["version"] == "v1"
    assert all(asset["type"] != "ff_tracking_job_manifest" for asset in campaign["assets"])


def _local_render_script(scene_count=6):
    scenes = [
        ("0", "15", "Hook: ภาระงานของผู้สร้าง", "คุณเคยรู้สึกไหมว่าต้องแบกงานหลายอย่างไว้คนเดียว?"),
        ("15", "30", "Architecture: Control Layer กับ Central Bus", "SoloCorp OS แยกชั้นสั่งการออกจากชั้นส่งผ่านข้อมูลจริง"),
        ("30", "45", "Departments: ทีมงานเสมือน", "เปลี่ยน AI ตัวเดียวให้กลายเป็นทีมงานเสมือนที่มีเจ้าของงานชัดเจน"),
        ("45", "60", "Local Engine: ประมวลผลในเครื่อง", "สร้างเสียงและภาพด้วยเครื่องมือท้องถิ่นโดยไม่พึ่ง Cloud"),
        ("60", "75", "Publish Gate: Human in the Loop", "คุณยังเป็นผู้ตัดสินใจขั้นสุดท้ายก่อนเผยแพร่เสมอ"),
        ("75", "90", "The Power of One: ก้าวถัดไป", "SoloCorp OS พร้อมให้ผู้สร้างเริ่มต้นจากสิ่งที่สำคัญกับตัวเอง"),
    ]
    rows = [
        f'| {start}-{end}s | {visual} | VO: "{voice}" BGM: local synthetic bed. |'
        for start, end, visual, voice in scenes[:scene_count]
    ]
    return "# Local media test\n\n**Duration:** 90 seconds\n\n" + "\n".join(rows) + "\n"


def test_local_media_render_records_cli_and_keeps_publish_gate(isolated_bus, monkeypatch):
    campaign_id = "local-media-render-test"
    script = content_service.ingest_client_generated_artifact(
        campaign_id,
        "video_script",
        _local_render_script(),
        {"client": "codex", "provider": "openai", "model": "test"},
        ["local synthetic fixture"],
    )
    content_service.design_visual_prompt("synthetic scenes", "short-form", "9:16", campaign_id)
    content_service.design_audio_experience(campaign_id, script["filename"])

    def fake_pipeline(payload):
        output_dir = Path(payload["output_dir"])
        output_dir.mkdir(parents=True)
        video_path = output_dir / "test_render.mp4"
        video_path.write_bytes(b"synthetic mp4 placeholder")
        return {
            "status": "completed",
            "execution_mode": "local_ffmpeg_cli",
            "video": {
                "path": str(video_path),
                "bytes": video_path.stat().st_size,
                "sha256": "a" * 64,
                "codec": "h264",
                "width": 1080,
                "height": 1920,
            },
        }

    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", fake_pipeline)
    result = content_service.render_campaign_media_local(campaign_id)

    assert result["execution_status"] == "completed"
    assert result["execution_mode"] == "local_ffmpeg_cli"
    assert result["status"] == "review_required"
    assert result["approval_required"] is True
    assert result["published"] is False
    assert result["publish_gate"]["status"] == "review_required"
    assert result["publish_gate"]["gate_passed"] is False

    campaign = content_service._load_campaign("local-media-render-test")
    job = next(asset for asset in campaign["assets"] if asset["type"] == "local_media_render_job")
    recorded = next(asset for asset in campaign["assets"] if asset["type"] == "local_media_render_result")
    assert job["provider"] == "ffmpeg-cli"
    assert job["execution_status"] == "in_progress"
    assert recorded["execution_status"] == "completed"
    assert recorded["media_rights_status"] == "human_confirmation_required"
    assert campaign["approved_version"] is None


def test_local_media_render_rejects_non_six_scene_storyboard(isolated_bus):
    campaign_id = "local-media-invalid-storyboard"
    content_service.ingest_client_generated_artifact(
        campaign_id,
        "video_script",
        _local_render_script(scene_count=5),
        {"client": "codex", "provider": "openai", "model": "test"},
    )
    with pytest.raises(
        content_service.ContentServiceError,
        match="supports six 15-second scenes or ten 10-second episodes",
    ):
        content_service.render_campaign_media_local(campaign_id)


def test_local_media_render_failed_pipeline_is_not_review_required(isolated_bus, monkeypatch):
    campaign_id = "local-media-render-failed-test"
    content_service.ingest_client_generated_artifact(
        campaign_id,
        "video_script",
        _local_render_script(),
        {"client": "codex", "provider": "openai", "model": "test"},
    )

    def failing_pipeline(payload):
        output_dir = Path(payload["output_dir"])
        output_dir.mkdir(parents=True)
        # Simulate a partial MP4 left behind by a renderer that died mid-step.
        (output_dir / "partial.mp4").write_bytes(b"partial mp4")
        raise content_service.ContentServiceError("local media render failed: boom")

    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", failing_pipeline)
    result = content_service.render_campaign_media_local(campaign_id)

    assert result["execution_status"] == "failed"
    assert result["status"] == "failed"
    assert result["status"] != "review_required"
    assert result["approval_required"] is False
    assert result["published"] is False
    assert result["render"] is None
    assert result["error"] == "local media render failed: boom"
    assert result["publish_gate"]["gate_passed"] is False

    campaign = content_service._load_campaign("local-media-render-failed-test")
    recorded = next(asset for asset in campaign["assets"] if asset["type"] == "local_media_render_result")
    assert recorded["execution_status"] == "failed"
    assert campaign["approved_version"] is None
    local_media = isolated_bus / "content" / "local_media"
    assert sorted(local_media.rglob("*.mp4")) == []


def _fake_local_success_pipeline(calls):
    def fake_pipeline(payload):
        calls.append(payload)
        output_dir = Path(payload["output_dir"])
        output_dir.mkdir(parents=True)
        video_path = output_dir / "test_render.mp4"
        video_path.write_bytes(b"synthetic mp4 placeholder")
        return {
            "status": "completed",
            "execution_mode": "local_ffmpeg_cli",
            "video": {
                "path": str(video_path),
                "bytes": video_path.stat().st_size,
                "sha256": "a" * 64,
                "codec": "h264",
                "width": 1080,
                "height": 1920,
            },
        }

    return fake_pipeline


def test_local_media_render_explicit_filename_bypasses_newer_scaffold(isolated_bus, monkeypatch):
    campaign_id = "local-media-explicit-script-test"
    real = content_service.ingest_client_generated_artifact(
        campaign_id,
        "video_script",
        _local_render_script(),
        {"client": "codex", "provider": "openai", "model": "test"},
    )
    # A newer 4-scene scaffold becomes "latest" and fails 6x15/10x10 validation.
    scaffold = content_service.create_video_script(
        "Scaffold trap", "ข้อความหลัก", 60, campaign_id
    )
    assert scaffold["filename"] != real["filename"]

    calls = []
    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", _fake_local_success_pipeline(calls))
    result = content_service.render_campaign_media_local(campaign_id, real["filename"])

    assert result["execution_status"] == "completed"
    assert result["script_filename"] == real["filename"]
    assert len(calls) == 1
    assert len(calls[0]["scenes"]) == 6
    campaign = content_service._load_campaign("local-media-explicit-script-test")
    job = next(asset for asset in campaign["assets"] if asset["type"] == "local_media_render_job")
    assert job["filename"]
    job_record = json.loads(bus_store.fetch_from_bus("content", job["filename"])["content"])
    assert job_record["script_filename"] == real["filename"]


def test_local_media_render_omitted_filename_keeps_latest_behavior(isolated_bus, monkeypatch):
    campaign_id = "local-media-omitted-script-test"
    script = content_service.ingest_client_generated_artifact(
        campaign_id,
        "video_script",
        _local_render_script(),
        {"client": "codex", "provider": "openai", "model": "test"},
    )
    calls = []
    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", _fake_local_success_pipeline(calls))
    result = content_service.render_campaign_media_local(campaign_id)

    assert result["execution_status"] == "completed"
    assert result["script_filename"] == script["filename"]
    assert len(calls) == 1
    assert len(calls[0]["scenes"]) == 6


def test_local_media_render_bad_filename_no_render_no_mp4(isolated_bus, monkeypatch):
    campaign_id = "local-media-bad-filename-test"
    content_service.ingest_client_generated_artifact(
        campaign_id,
        "video_script",
        _local_render_script(),
        {"client": "codex", "provider": "openai", "model": "test"},
    )
    calls = []
    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", _fake_local_success_pipeline(calls))

    with pytest.raises(content_service.ContentServiceError, match="script_filename not found"):
        content_service.render_campaign_media_local(campaign_id, "missing-script.md")

    assert calls == []
    campaign = content_service._load_campaign("local-media-bad-filename-test")
    assert all(asset["type"] != "local_media_render_job" for asset in campaign["assets"])
    local_media = isolated_bus / "content" / "local_media"
    assert not local_media.exists() or sorted(local_media.rglob("*.mp4")) == []


def test_local_media_render_wrong_type_filename_rejected(isolated_bus, monkeypatch):
    campaign_id = "local-media-wrong-type-test"
    draft = content_service.create_content_draft(
        "Not a script", "หัวข้อทดสอบ", "ผู้อ่าน", "article", campaign_id
    )
    calls = []
    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", _fake_local_success_pipeline(calls))

    with pytest.raises(content_service.ContentServiceError, match="video_script"):
        content_service.render_campaign_media_local(campaign_id, draft["filename"])

    assert calls == []
    local_media = isolated_bus / "content" / "local_media"
    assert not local_media.exists() or sorted(local_media.rglob("*.mp4")) == []


def test_local_media_render_script_from_another_campaign_rejected(isolated_bus, monkeypatch):
    other = content_service.ingest_client_generated_artifact(
        "local-media-other-campaign",
        "video_script",
        _local_render_script(),
        {"client": "codex", "provider": "openai", "model": "test"},
    )
    campaign_id = "local-media-cross-campaign-test"
    content_service.ingest_client_generated_artifact(
        campaign_id,
        "video_script",
        _local_render_script(),
        {"client": "codex", "provider": "openai", "model": "test"},
    )
    calls = []
    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", _fake_local_success_pipeline(calls))

    with pytest.raises(
        content_service.ContentServiceError, match="does not belong to campaign"
    ):
        content_service.render_campaign_media_local(campaign_id, other["filename"])

    assert calls == []
    local_media = isolated_bus / "content" / "local_media"
    assert not local_media.exists() or sorted(local_media.rglob("*.mp4")) == []


def test_local_media_render_explicit_filename_via_mcp_tool(isolated_bus, monkeypatch):
    campaign_id = "local-media-mcp-explicit-test"
    real = content_service.ingest_client_generated_artifact(
        campaign_id,
        "video_script",
        _local_render_script(),
        {"client": "codex", "provider": "openai", "model": "test"},
    )
    content_service.create_video_script("Scaffold via MCP", "ข้อความหลัก", 60, campaign_id)
    calls = []
    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", _fake_local_success_pipeline(calls))

    fn = mcp._tool_manager.get_tool("render_campaign_media_local").fn
    payload = json.loads(fn(campaign_id, real["filename"]))
    assert payload["status"] == "review_required"
    assert payload["script_filename"] == real["filename"]
    assert len(calls) == 1

    # Omitted MCP arg keeps latest (scaffold) behavior and surfaces a clear error.
    payload_error = json.loads(fn(campaign_id))
    assert payload_error["status"] == "error"
    assert "local render" in payload_error["message"]
    assert len(calls) == 1  # no second pipeline run for the failing latest pick


# --- A1: campaign asset removal -------------------------------------------------


def _campaign_with_two_assets():
    campaign_id = "a1-removal-test"
    bad = content_service.create_content_draft(
        "Draft มีคำต้องห้าม",
        "สินค้านี้การันตีผลลัพธ์ 100%",
        "ผู้ประกอบการขนาดเล็ก",
        "social_post",
        campaign_id,
    )
    good = content_service.create_video_script(
        "สคริปต์สะอาด", "ใช้ระบบให้เป็น", 30, campaign_id
    )
    return campaign_id, bad, good


def test_remove_campaign_asset_drops_manifest_entry_and_bumps_version(isolated_bus):
    campaign_id, bad, good = _campaign_with_two_assets()
    key, _ = content_service._campaign_identity(campaign_id)
    before = content_service._load_campaign(key)
    assert len(before["assets"]) == 2

    result = content_service.remove_campaign_asset(
        campaign_id, bad["filename"], "banned claim"
    )

    assert result["operation_status"] == "removed"
    assert result["removed"]["filename"] == bad["filename"]
    assert result["version"] == f"v{int(before['version_number']) + 1}"
    assert result["remaining_asset_count"] == 1
    assert result["file_retained_on_bus"] is True
    assert result["review_reset"] is True
    assert result["approval_reset"] is True

    campaign = content_service._load_campaign(key)
    assert [a["filename"] for a in campaign["assets"]] == [good["filename"]]
    assert campaign["review"] is None
    assert campaign["approved_version"] is None
    assert campaign["removal_records"][-1]["filename"] == bad["filename"]
    assert campaign["removal_records"][-1]["reason"] == "banned claim"
    # payload bytes survive — removal is manifest-level, reversible, auditable
    fetched = bus_store.fetch_from_bus("content", bad["filename"])
    assert "# Draft มีคำต้องห้าม" in fetched["content"]


def test_removed_asset_no_longer_drags_campaign_redaction(isolated_bus):
    campaign_id, bad, good = _campaign_with_two_assets()

    first = content_service.review_publish_gate(campaign_id=campaign_id)
    redaction_check = next(c for c in first["checks"] if c["check"] == "redaction")
    assert redaction_check["ok"] is False, "banned phrase must fail redaction while listed"

    content_service.remove_campaign_asset(campaign_id, bad["filename"])

    second = content_service.review_publish_gate(campaign_id=campaign_id)
    redaction_check = next(c for c in second["checks"] if c["check"] == "redaction")
    assert redaction_check["ok"] is True, "redaction must recompute over remaining assets only"
    listed = [a["filename"] for a in second["manifest"]["assets"]]
    assert bad["filename"] not in listed
    assert good["filename"] in listed
    assert bad["filename"] in second["manifest"]["removed_assets"]


def test_remove_campaign_asset_rejects_unknown_targets(isolated_bus):
    campaign_id, bad, good = _campaign_with_two_assets()
    with pytest.raises(
        content_service.ContentServiceError, match="asset not found in campaign"
    ):
        content_service.remove_campaign_asset(campaign_id, "nope.md")
    with pytest.raises(content_service.ContentServiceError, match="filename is required"):
        content_service.remove_campaign_asset(campaign_id, "   ")
    with pytest.raises(content_service.ContentServiceError, match="campaign not found"):
        content_service.remove_campaign_asset("missing-campaign", "nope.md")


def test_remove_campaign_asset_reports_dependents(isolated_bus):
    campaign_id = "a1-dependents-test"
    script = content_service.create_video_script(
        "สคริปต์ต้นทาง", "ข้อความหลัก", 30, campaign_id
    )
    cue = content_service.design_audio_experience(campaign_id, script["filename"])

    result = content_service.remove_campaign_asset(campaign_id, script["filename"])

    assert result["dependent_assets"] == [cue["filename"]]
    assert result["remaining_asset_count"] == 1


def test_remove_campaign_asset_invalidates_prior_approval(isolated_bus):
    campaign_id, bad, good = _campaign_with_two_assets()
    review = content_service.review_publish_gate(campaign_id=campaign_id)
    content_service.record_human_approval(
        campaign_id, review["version"], "อนุมัติรอบแรก"
    )
    key, _ = content_service._campaign_identity(campaign_id)
    assert content_service._load_campaign(key)["approved_version"] == review["version"]

    content_service.remove_campaign_asset(campaign_id, bad["filename"])

    campaign = content_service._load_campaign(key)
    assert campaign["approved_version"] is None
    assert campaign["status"] != "approved"
    # approval history is append-only; only the active approval is cleared
    assert len(campaign["approval_records"]) == 1
    assert campaign["removal_records"][-1]["reason"] is None


def test_remove_campaign_asset_mcp_tool(isolated_bus):
    campaign_id, bad, good = _campaign_with_two_assets()
    raw = mcp._tool_manager.get_tool("remove_campaign_asset").fn(
        campaign_id, bad["filename"], "ทดสอบผ่าน MCP"
    )
    payload = json.loads(raw)
    assert payload["operation_status"] == "removed"

    raw_error = mcp._tool_manager.get_tool("remove_campaign_asset").fn(
        campaign_id, "missing.md", ""
    )
    payload_error = json.loads(raw_error)
    assert payload_error["status"] == "error"
    assert "asset not found" in payload_error["message"]


# --- Publish Gate approval consistency (CEO Path A) ------------------------------
#
# Bug: record_human_approval(vN) returned approved while an immediate
# review_publish_gate returned review_required / blocked despite
# manifest.approved_version == vN. _review_campaign ignored approved_version.
# These tests pin the fix: gate reflects approval iff approved_version equals
# the current version, stays truthful about failed checks, and never publishes.


def _gate_approval_campaign(campaign_id):
    references = ["https://research.example/report"]
    content_service.create_content_draft(
        "Gate draft",
        "ข้อเท็จจริงที่ต้องตรวจสอบ",
        "ผู้ติดตามข่าวเทคโนโลยี",
        "article",
        campaign_id,
        references,
    )
    script = content_service.create_video_script(
        "Gate video", "สรุปประเด็นจากงานวิจัย", 60, campaign_id
    )
    content_service.design_visual_prompt(
        "งานวิจัยกับการทำงาน", "LinkedIn", "16:9", campaign_id
    )
    content_service.design_audio_experience(campaign_id, script["filename"])
    return campaign_id


def test_approved_current_version_gate_reflects_approval(isolated_bus):
    campaign_id = _gate_approval_campaign("gate-approval-consistent-test")

    first = content_service.review_publish_gate(campaign_id=campaign_id)
    assert first["status"] == "review_required"
    assert first["approval_required"] is True
    assert first["publish_action"] == "blocked_until_human_approval"
    assert first["gate_passed"] is False
    assert first["published"] is False
    assert first["overrides_failed_checks"] == []
    failed_before = {c["check"] for c in first["checks"] if not c["ok"]}
    assert failed_before

    approval = content_service.record_human_approval(
        campaign_id, first["version"], "อนุมัติเวอร์ชันที่ตรวจแล้ว"
    )
    assert approval["status"] == "approved"
    assert approval["approval_required"] is False
    assert approval["gate_passed"] is False
    assert approval["published"] is False
    assert set(approval["overrides_failed_checks"]) == failed_before

    second = content_service.review_publish_gate(campaign_id=campaign_id)
    assert second["version"] == first["version"]
    assert second["status"] == "approved"
    assert second["approval_required"] is False
    assert second["publish_action"] == "approved_pending_separate_publish_step"
    assert second["publish_action"] != "blocked_until_human_approval"
    # gate_passed stays truthful: failed checks are still listed, not hidden.
    assert second["gate_passed"] is False
    failed_after = {c["check"] for c in second["checks"] if not c["ok"]}
    assert failed_after == failed_before
    assert set(second["overrides_failed_checks"]) == failed_before
    # Approval never publishes.
    assert second["published"] is False
    assert second["manifest"]["approved_version"] == second["version"]
    key, _ = content_service._campaign_identity(campaign_id)
    campaign = content_service._load_campaign(key)
    assert campaign["status"] == "approved"
    assert campaign["approved_version"] == second["version"]
    report = bus_store.fetch_from_bus("content", second["report"]["filename"])["content"]
    assert "approved" in report.lower()
    assert "not published" in report.lower()


def test_gate_rerun_after_approval_keeps_newest_manifest_snapshot_approved(isolated_bus):
    """Regression — incident 2026-11-07 campaign_synth_phase1_20261107.

    Exact sequence: review_publish_gate -> record_human_approval(v5) ->
    review_publish_gate again ~4s later. The second call used to save a newer
    manifest snapshot with status=review_required while approved_version=v5
    and approval_records were still intact, so the newest manifest of an
    approved campaign read as unapproved. Every snapshot written after the
    approval must keep reflecting approved; only the approval-invalidating
    paths (new asset / asset removal) may clear it.
    """
    campaign_id = _gate_approval_campaign("gate-rerun-latest-manifest-test")
    key, _ = content_service._campaign_identity(campaign_id)
    prefix = f"campaign-{key}-manifest_"

    def snapshots():
        found = []
        for item in bus_store.list_department_bus("content")["files"]:
            filename = item["filename"]
            if not filename.startswith(prefix) or not filename.endswith(".json"):
                continue
            snap = json.loads(bus_store.fetch_from_bus("content", filename)["content"])
            if snap.get("campaign_key") == key:
                found.append((int(snap.get("revision", 0)), filename, snap))
        return sorted(found)

    first = content_service.review_publish_gate(campaign_id=campaign_id)
    approval = content_service.record_human_approval(
        campaign_id, first["version"], "อนุมัติแล้ว ก่อน re-run gate"
    )
    approved_revision, approved_file, approved_snap = snapshots()[-1]
    assert approved_snap["status"] == "approved"
    assert approved_snap["approved_version"] == first["version"]

    # The incident's second call: an immediate gate re-run after approval.
    second = content_service.review_publish_gate(campaign_id=campaign_id)
    assert second["campaign_manifest"]["filename"] != approved_file

    after_approval = [
        item for item in snapshots() if item[0] > approved_revision
    ]
    assert after_approval, "gate re-run must save a newer manifest snapshot"
    for revision, filename, snap in after_approval:
        assert snap["status"] == "approved", filename
        assert snap["review"]["status"] == "approved", filename
        assert snap["approved_version"] == first["version"], filename
        assert snap["version"] == first["version"], filename
        assert len(snap["approval_records"]) == 1, filename

    newest_revision, newest_file, newest_snap = snapshots()[-1]
    assert newest_revision > approved_revision
    assert newest_snap["status"] == "approved"
    assert (
        newest_snap["approval_records"][-1]["filename"]
        == approval["approval_record"]["filename"]
    )
    assert second["status"] == "approved"
    assert second["approval_required"] is False
    assert second["publish_action"] == "approved_pending_separate_publish_step"


def test_asset_change_invalidates_prior_approval_and_gate_blocks_again(isolated_bus):
    campaign_id = _gate_approval_campaign("gate-approval-invalidate-test")
    review = content_service.review_publish_gate(campaign_id=campaign_id)
    approved_version = review["version"]
    content_service.record_human_approval(
        campaign_id, approved_version, "อนุมัติรอบแรก"
    )
    approved_review = content_service.review_publish_gate(campaign_id=campaign_id)
    assert approved_review["status"] == "approved"
    assert approved_review["approval_required"] is False

    updated = content_service.create_content_draft(
        "Gate update", "ฉบับแก้ไข", "ผู้ติดตามข่าวเทคโนโลยี", "article", campaign_id
    )
    assert updated["version"] != approved_version
    key, _ = content_service._campaign_identity(campaign_id)
    assert content_service._load_campaign(key)["approved_version"] is None

    blocked = content_service.review_publish_gate(campaign_id=campaign_id)
    assert blocked["version"] == updated["version"]
    assert blocked["status"] == "review_required"
    assert blocked["approval_required"] is True
    assert blocked["publish_action"] == "blocked_until_human_approval"
    assert blocked["published"] is False
    assert blocked["overrides_failed_checks"] == []


def test_unapproved_gate_remains_blocked(isolated_bus):
    campaign_id = _gate_approval_campaign("gate-no-approval-test")
    review = content_service.review_publish_gate(campaign_id=campaign_id)
    key, _ = content_service._campaign_identity(campaign_id)
    assert content_service._load_campaign(key)["approved_version"] is None
    assert review["status"] == "review_required"
    assert review["approval_required"] is True
    assert review["publish_action"] == "blocked_until_human_approval"
    assert review["published"] is False
    assert review["overrides_failed_checks"] == []


def test_failed_render_gate_does_not_claim_approval(isolated_bus, monkeypatch):
    campaign_id = "gate-failed-render-test"
    content_service.ingest_client_generated_artifact(
        campaign_id,
        "video_script",
        _local_render_script(),
        {"client": "codex", "provider": "openai", "model": "test"},
    )

    def failing_pipeline(payload):
        output_dir = Path(payload["output_dir"])
        output_dir.mkdir(parents=True)
        (output_dir / "partial.mp4").write_bytes(b"partial mp4")
        raise content_service.ContentServiceError("local media render failed: boom")

    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", failing_pipeline)
    result = content_service.render_campaign_media_local(campaign_id)
    assert result["execution_status"] == "failed"
    assert result["status"] == "failed"
    assert result["published"] is False
    gate = result["publish_gate"]
    assert gate["status"] == "review_required"
    assert gate["approval_required"] is True
    assert gate["publish_action"] == "blocked_render_failed"
    assert gate["gate_passed"] is False
    assert gate["published"] is False


def test_failed_render_gate_uses_blocked_render_failed_action(isolated_bus, monkeypatch):
    campaign_id = "gate-failed-render-token-test"
    content_service.ingest_client_generated_artifact(
        campaign_id,
        "video_script",
        _local_render_script(),
        {"client": "codex", "provider": "openai", "model": "test"},
    )

    def failing_pipeline(payload):
        output_dir = Path(payload["output_dir"])
        output_dir.mkdir(parents=True)
        (output_dir / "partial.mp4").write_bytes(b"partial mp4")
        raise content_service.ContentServiceError("local media render failed: boom")

    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", failing_pipeline)
    result = content_service.render_campaign_media_local(campaign_id)
    assert result["publish_gate"]["publish_action"] == "blocked_render_failed"
    assert result["publish_gate"]["status"] == "review_required"
    assert result["publish_gate"]["approval_required"] is True
    assert result["publish_gate"]["gate_passed"] is False
    assert result["publish_gate"]["published"] is False
    # A fresh gate review keeps the blocked-render-failed token.
    gate = content_service.review_publish_gate(campaign_id=campaign_id)
    assert gate["publish_action"] == "blocked_render_failed"
    assert gate["status"] == "review_required"
    assert gate["approval_required"] is True
    assert gate["gate_passed"] is False
    assert gate["published"] is False


def test_record_human_approval_rejected_after_failed_render(isolated_bus, monkeypatch):
    campaign_id = "gate-approval-after-failed-render"
    content_service.ingest_client_generated_artifact(
        campaign_id,
        "video_script",
        _local_render_script(),
        {"client": "codex", "provider": "openai", "model": "test"},
    )

    def failing_pipeline(payload):
        output_dir = Path(payload["output_dir"])
        output_dir.mkdir(parents=True)
        (output_dir / "partial.mp4").write_bytes(b"partial mp4")
        raise content_service.ContentServiceError("local media render failed: boom")

    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", failing_pipeline)
    rendered = content_service.render_campaign_media_local(campaign_id)
    assert rendered["execution_status"] == "failed"
    version = rendered["publish_gate"]["version"]
    key, _ = content_service._campaign_identity(campaign_id)
    before = content_service._load_campaign(key)
    assert before["approval_records"] == []

    with pytest.raises(
        content_service.ContentServiceError, match="render failed"
    ):
        content_service.record_human_approval(
            campaign_id, version, "อนุมัติแม้ render ล้มเหลว"
        )

    after = content_service._load_campaign(key)
    assert after["approval_records"] == []
    assert after["approved_version"] is None
    gate = content_service.review_publish_gate(campaign_id=campaign_id)
    assert gate["publish_action"] == "blocked_render_failed"
    assert gate["published"] is False


def test_record_human_approval_is_idempotent(isolated_bus):
    campaign_id = _gate_approval_campaign("gate-approval-idempotent-test")
    review = content_service.review_publish_gate(campaign_id=campaign_id)
    first = content_service.record_human_approval(
        campaign_id, review["version"], "อนุมัติครั้งแรก"
    )
    assert first["status"] == "approved"
    assert first["published"] is False
    key, _ = content_service._campaign_identity(campaign_id)
    assert len(content_service._load_campaign(key)["approval_records"]) == 1

    second = content_service.record_human_approval(
        campaign_id, review["version"], "อนุมัติซ้ำเวอร์ชันเดียวกัน"
    )
    assert second["status"] == "approved"
    assert second["version"] == review["version"]
    assert second["approval_required"] is False
    assert second["published"] is False
    assert second["approval_record"]["filename"] == first["approval_record"]["filename"]
    assert second["approval_record"]["path"] == first["approval_record"]["path"]
    campaign = content_service._load_campaign(key)
    assert len(campaign["approval_records"]) == 1
    assert campaign["approval_records"][0]["filename"] == first["approval_record"]["filename"]
    assert campaign["approved_version"] == review["version"]


# --- Phase 3: per-step status, opt-in fallbacks, degraded gate, render lock ----

import importlib.util
import subprocess
import wave


def _load_renderer(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "render_campaign_media_local_mod",
        Path(__file__).resolve().parents[1] / "scripts" / "render_campaign_media_local.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = tmp_path
    mod.CONTENT_DIR = tmp_path / "content"
    mod.CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    model_dir = tmp_path / "tools" / "piper" / "models"
    model_dir.mkdir(parents=True)
    (model_dir / "th_TH-tsync2-medium.onnx").write_bytes(b"fake model")
    (model_dir / "th_TH-tsync2-medium.onnx.json").write_text("{}")
    return mod


def _fake_renderer_run(mod, *, fail_tts_index=None, fail_visual=False, bitrate="300000"):
    def write_wav(path, seconds, rate=8000):
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(b"\x00" * (int(seconds * rate) * 2))

    def fake_run(command, *, input_text=None, timeout=900):
        joined = " ".join(command)
        ok = subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if "local_tts_piper.py" in joined:
            out_path = Path(command[command.index("--output") + 1])
            idx = int(out_path.stem.split("-")[1])
            if fail_tts_index is not None and idx == fail_tts_index:
                return subprocess.CompletedProcess(command, 1, stdout="", stderr="piper boom")
            write_wav(out_path, 5)
            ok.stdout = json.dumps({"status": "ok", "scene_index": idx})
            return ok
        if "render_pdoom_scenes.mjs" in joined:
            if fail_visual:
                return subprocess.CompletedProcess(command, 1, stdout="", stderr="node boom")
            image_dir = Path(command[2])
            frames = []
            for i in range(1, 7):
                frame = image_dir / f"scene-{i:02d}.png"
                frame.write_bytes(b"PNG")
                frames.append(str(frame))
            ok.stdout = json.dumps({"frames": frames})
            return ok
        if "color=" in joined:
            Path(command[-1]).write_bytes(b"PNGCARD")
            return ok
        if "silenceremove" in joined:
            write_wav(Path(command[-1]), 15, rate=48000)
            return ok
        if "concat=n=" in joined and "amix" in joined:
            write_wav(Path(command[-1]), 90)
            return ok
        if "loudnorm" in joined and "print_format=json" in joined:
            ok.stderr = json.dumps(
                {
                    "input_i": -20.0,
                    "input_lra": 5.0,
                    "input_tp": -3.0,
                    "input_thresh": -30.0,
                    "target_offset": 0.1,
                }
            )
            return ok
        if "loudnorm" in joined:
            write_wav(Path(command[-1]), 90)
            return ok
        if "libx264" in joined:
            Path(command[-1]).write_bytes(b"MP4BYTES")
            return ok
        if command[0] == mod.FFPROBE:
            ok.stdout = json.dumps(
                {
                    "streams": [
                        {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920, "avg_frame_rate": "30/1"},
                        {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2, "index": 1},
                    ],
                    "format": {"duration": "90.0", "bit_rate": bitrate},
                }
            )
            return ok
        if "ebur128" in joined:
            ok.stderr = "Integrated loudness:\n I: -16.0 LUFS\nTrue peak:\n Peak: -2.0 dBFS"
            return ok
        raise AssertionError(f"unexpected command: {command}")

    return fake_run


def _renderer_payload(mod, **extra):
    scenes = [
        {
            "start_seconds": i * 15,
            "end_seconds": (i + 1) * 15,
            "title": f"Title {i + 1}",
            "description": f"Visual {i + 1}",
            "voiceover": f"voice {i + 1}",
        }
        for i in range(6)
    ]
    return {
        "campaign_id": "testcamp",
        "output_dir": str(mod.CONTENT_DIR / "job1"),
        "model_license": "test",
        "scene_seconds": 15,
        "duration_seconds": 90,
        "scenes": scenes,
        **extra,
    }


def test_renderer_steps_and_sync_report_on_success(tmp_path):
    mod = _load_renderer(tmp_path)
    mod._run = _fake_renderer_run(mod)  # type: ignore[method-assign]
    result = mod.render(_renderer_payload(mod))

    assert set(result["steps"]) == {
        "input_validation", "piper_tts", "synthetic_visuals", "ffmpeg_assembly", "output_audit",
    }
    assert all(step["status"] == "completed" for step in result["steps"].values())
    assert all(step["started_at"] and step["finished_at"] for step in result["steps"].values())
    assert result["degraded"] is False
    assert result["fallbacks"]["tts"]["used"] is False
    assert len(result["sync_report"]) == 6
    assert result["sync_report"][0] == {
        "scene_id": "scene-01",
        "start_sec": 0,
        "end_sec": 15,
        "voice_duration_sec": 5.0,
        "padded_duration_sec": 15.0,
        "drift_ms": 0.0,
    }
    assert result["video"]["bitrate_bps"] == 300000
    assert result["video"]["file_exists"] is True
    assert result["video"]["size_bytes"] > 0
    assert result["steps"]["output_audit"]["output"]["bitrate_bps"] == 300000


def test_renderer_tts_silence_fallback_degraded(tmp_path):
    mod = _load_renderer(tmp_path)
    mod._run = _fake_renderer_run(mod, fail_tts_index=3)  # type: ignore[method-assign]
    result = mod.render(_renderer_payload(mod, tts_fallback="silence"))

    assert result["degraded"] is True
    assert result["steps"]["piper_tts"]["fallback_used"] is True
    assert result["steps"]["piper_tts"]["fallback_scenes"] == ["scene-03"]
    assert result["voice_segments"][2]["status"] == "fallback_silence"
    assert result["voice_segments"][2]["fallback"] is True
    # Silent buffer is the full slot; no fake voice claim (status is not "ok").
    assert result["voice_segments"][2]["duration_seconds"] == 15
    assert result["sync_report"][2]["voice_duration_sec"] == 15.0
    assert result["fallbacks"]["tts"] == {"requested": "silence", "used": True, "scenes": ["scene-03"]}


def test_renderer_tts_fail_without_fallback_aborts(tmp_path):
    mod = _load_renderer(tmp_path)
    mod._run = _fake_renderer_run(mod, fail_tts_index=3)  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="Piper scene 3") as excinfo:
        mod.render(_renderer_payload(mod))
    assert excinfo.value.steps["piper_tts"]["status"] == "failed"  # type: ignore[attr-defined]
    assert excinfo.value.steps["piper_tts"]["error"] == "RuntimeError"  # type: ignore[attr-defined]


def test_renderer_visual_static_card_fallback_degraded(tmp_path):
    mod = _load_renderer(tmp_path)
    mod._run = _fake_renderer_run(mod, fail_visual=True)  # type: ignore[method-assign]
    result = mod.render(_renderer_payload(mod, visual_fallback="static_card"))

    assert result["degraded"] is True
    assert result["steps"]["synthetic_visuals"]["fallback_used"] is True
    assert result["steps"]["synthetic_visuals"]["fallback_scenes"] == [
        "scene-01", "scene-02", "scene-03", "scene-04", "scene-05", "scene-06",
    ]
    # Scene count and order preserved; every frame is a static card on disk.
    assert len(result["frames"]) == 6
    for i, frame in enumerate(result["frames"]):
        assert frame.endswith(f"scene-{i + 1:02d}-static-card.png")
        assert Path(frame).stat().st_size > 0


def test_renderer_visual_fail_without_fallback_aborts(tmp_path):
    mod = _load_renderer(tmp_path)
    mod._run = _fake_renderer_run(mod, fail_visual=True)  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="Three.js scene renderer"):
        mod.render(_renderer_payload(mod))


def test_renderer_rejects_bad_fallback_values(tmp_path):
    mod = _load_renderer(tmp_path)
    mod._run = _fake_renderer_run(mod)  # type: ignore[method-assign]
    with pytest.raises(ValueError, match="tts_fallback must be one of"):
        mod.render(_renderer_payload(mod, tts_fallback="static_card"))
    with pytest.raises(ValueError, match="visual_fallback must be one of"):
        mod.render(_renderer_payload(mod, visual_fallback="silence"))


def _ingest_local_script(campaign_id):
    return content_service.ingest_client_generated_artifact(
        campaign_id,
        "video_script",
        _local_render_script(),
        {"client": "codex", "provider": "openai", "model": "test"},
    )


def _degraded_fake_pipeline(payload, *, degraded=True):
    output_dir = Path(payload["output_dir"])
    output_dir.mkdir(parents=True)
    video_path = output_dir / "test_render.mp4"
    video_path.write_bytes(b"synthetic mp4 placeholder")
    steps = {
        "input_validation": {"name": "input_validation", "status": "completed", "fallback_used": False, "fallback_scenes": []},
        "piper_tts": {"name": "piper_tts", "status": "completed", "fallback_used": degraded, "fallback_scenes": ["scene-02"] if degraded else []},
        "synthetic_visuals": {"name": "synthetic_visuals", "status": "completed", "fallback_used": False, "fallback_scenes": []},
        "ffmpeg_assembly": {"name": "ffmpeg_assembly", "status": "completed", "fallback_used": False, "fallback_scenes": []},
        "output_audit": {"name": "output_audit", "status": "completed", "fallback_used": False, "fallback_scenes": []},
    }
    sync = [
        {"scene_id": f"scene-{i + 1:02d}", "start_sec": i * 15, "end_sec": (i + 1) * 15,
         "voice_duration_sec": 15.0 if (degraded and i == 1) else 5.0,
         "padded_duration_sec": 15.0, "drift_ms": 0.0}
        for i in range(6)
    ]
    return {
        "status": "completed",
        "execution_mode": "local_ffmpeg_cli",
        "steps": steps,
        "degraded": degraded,
        "fallbacks": {
            "tts": {"requested": payload.get("tts_fallback", "abort"), "used": degraded, "scenes": ["scene-02"] if degraded else []},
            "visual": {"requested": payload.get("visual_fallback", "abort"), "used": False, "scenes": []},
        },
        "sync_report": sync,
        "voice_segments": [
            {"status": "fallback_silence", "scene_id": "scene-02", "fallback": True} if (degraded and i == 1)
            else {"status": "ok", "scene_index": i + 1}
            for i in range(6)
        ],
        "video": {
            "path": str(video_path),
            "bytes": video_path.stat().st_size,
            "sha256": "a" * 64,
            "codec": "h264",
            "width": 1080,
            "height": 1920,
            "bitrate_bps": 300000,
        },
    }


def test_local_render_success_persists_steps_and_sync(isolated_bus, monkeypatch):
    campaign_id = "phase3-steps-test"
    _ingest_local_script(campaign_id)
    monkeypatch.setattr(
        content_service, "_execute_local_media_pipeline",
        lambda payload: _degraded_fake_pipeline(payload, degraded=False),
    )
    result = content_service.render_campaign_media_local(campaign_id)

    assert result["degraded"] is False
    assert result["tts_fallback"] == "abort"
    assert result["visual_fallback"] == "abort"
    assert set(result["steps"]) == {
        "input_validation", "piper_tts", "synthetic_visuals", "ffmpeg_assembly", "output_audit",
    }
    assert len(result["sync_report"]) == 6
    assert result["render"]["video"]["bitrate_bps"] == 300000

    campaign = content_service._load_campaign("phase3-steps-test")
    job = next(asset for asset in campaign["assets"] if asset["type"] == "local_media_render_job")
    job_record = json.loads(bus_store.fetch_from_bus("content", job["filename"])["content"])
    assert job_record["tts_fallback"] == "abort"
    assert job_record["fallback_requested"] is False
    recorded = next(asset for asset in campaign["assets"] if asset["type"] == "local_media_render_result")
    assert recorded["degraded"] is False
    result_record = json.loads(bus_store.fetch_from_bus("content", recorded["filename"])["content"])
    assert result_record["steps"] == result["steps"]
    assert result_record["sync_report"] == result["sync_report"]


def test_local_render_bad_fallback_values_rejected(isolated_bus, monkeypatch):
    campaign_id = "phase3-bad-fallback-test"
    _ingest_local_script(campaign_id)
    calls = []
    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", _fake_local_success_pipeline(calls))

    with pytest.raises(content_service.ContentServiceError, match="tts_fallback must be one of"):
        content_service.render_campaign_media_local(campaign_id, None, "bogus")
    with pytest.raises(content_service.ContentServiceError, match="visual_fallback must be one of"):
        content_service.render_campaign_media_local(campaign_id, None, None, "silence")
    assert calls == []
    campaign = content_service._load_campaign("phase3-bad-fallback-test")
    assert all(asset["type"] != "local_media_render_job" for asset in campaign["assets"])


def test_local_render_concurrent_lock_rejects_second(isolated_bus, monkeypatch):
    import fcntl

    campaign_id = "phase3-lock-test"
    _ingest_local_script(campaign_id)
    calls = []
    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", _fake_local_success_pipeline(calls))

    lock_path = isolated_bus / "content" / ".local_render.lock"
    with lock_path.open("a+b") as held:
        fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(content_service.ContentServiceError, match="another local render in progress"):
            content_service.render_campaign_media_local(campaign_id)

    assert calls == []
    campaign = content_service._load_campaign("phase3-lock-test")
    assert all(asset["type"] != "local_media_render_job" for asset in campaign["assets"])
    local_media = isolated_bus / "content" / "local_media"
    assert not local_media.exists() or sorted(local_media.rglob("*.mp4")) == []


def test_local_render_tts_fallback_degraded_gate_and_approval(isolated_bus, monkeypatch):
    campaign_id = "phase3-degraded-gate-test"
    _ingest_local_script(campaign_id)
    monkeypatch.setattr(
        content_service, "_execute_local_media_pipeline",
        lambda payload: _degraded_fake_pipeline(payload, degraded=True),
    )
    result = content_service.render_campaign_media_local(campaign_id, None, "silence")

    assert result["execution_status"] == "completed"
    assert result["degraded"] is True
    assert result["tts_fallback"] == "silence"
    assert result["render"]["voice_segments"][1]["status"] == "fallback_silence"
    gate = result["publish_gate"]
    assert gate["degraded"] is True
    assert gate["gate_passed"] is False
    degraded_check = next(
        item for item in gate["checks"]
        if item["check"] == "media: local render used fallback (degraded)"
    )
    assert degraded_check["ok"] is False

    campaign = content_service._load_campaign("phase3-degraded-gate-test")
    job = next(asset for asset in campaign["assets"] if asset["type"] == "local_media_render_job")
    job_record = json.loads(bus_store.fetch_from_bus("content", job["filename"])["content"])
    assert job_record["tts_fallback"] == "silence"
    assert job_record["fallback_requested"] is True
    recorded = next(asset for asset in campaign["assets"] if asset["type"] == "local_media_render_result")
    assert recorded["degraded"] is True

    # Degraded alone must not block human approval; it is recorded as an override.
    approval = content_service.record_human_approval(
        campaign_id, gate["version"], "อนุมัติแบบรับทราบ degraded media แล้ว"
    )
    assert approval["status"] == "approved"
    assert approval["published"] is False
    assert "media: local render used fallback (degraded)" in approval["overrides_failed_checks"]

    reviewed = content_service.review_publish_gate(campaign_id=campaign_id)
    assert reviewed["status"] == "approved"
    assert reviewed["degraded"] is True
    assert reviewed["gate_passed"] is False
    assert reviewed["published"] is False


def test_local_render_fallback_params_via_mcp_tool(isolated_bus, monkeypatch):
    campaign_id = "phase3-mcp-fallback-test"
    _ingest_local_script(campaign_id)
    calls = []
    monkeypatch.setattr(
        content_service, "_execute_local_media_pipeline",
        lambda payload: (calls.append(payload), _degraded_fake_pipeline(payload, degraded=True))[1],
    )
    fn = mcp._tool_manager.get_tool("render_campaign_media_local").fn
    payload = json.loads(fn(campaign_id, "", "silence", ""))
    assert payload["status"] == "review_required"
    assert payload["degraded"] is True
    assert payload["tts_fallback"] == "silence"
    assert calls[0]["tts_fallback"] == "silence"
    assert calls[0]["visual_fallback"] == "abort"


def test_local_render_failed_steps_persisted(isolated_bus, monkeypatch):
    campaign_id = "phase3-failed-steps-test"
    _ingest_local_script(campaign_id)

    def failing_with_steps(payload):
        output_dir = Path(payload["output_dir"])
        output_dir.mkdir(parents=True)
        error = content_service.ContentServiceError("local media render failed: boom")
        error.steps = {"piper_tts": {"name": "piper_tts", "status": "failed", "error": "RuntimeError", "message": "boom"}}  # type: ignore[attr-defined]
        raise error

    monkeypatch.setattr(content_service, "_execute_local_media_pipeline", failing_with_steps)
    result = content_service.render_campaign_media_local(campaign_id)

    assert result["execution_status"] == "failed"
    assert result["degraded"] is False
    assert result["steps"]["piper_tts"]["status"] == "failed"
    campaign = content_service._load_campaign("phase3-failed-steps-test")
    recorded = next(asset for asset in campaign["assets"] if asset["type"] == "local_media_render_result")
    result_record = json.loads(bus_store.fetch_from_bus("content", recorded["filename"])["content"])
    assert result_record["steps"]["piper_tts"]["status"] == "failed"
    assert result_record["degraded"] is False
