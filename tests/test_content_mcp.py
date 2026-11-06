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
