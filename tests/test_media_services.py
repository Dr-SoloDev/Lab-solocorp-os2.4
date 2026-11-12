from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from axis_mcp import bus_store
from axis_mcp.departments import content_service, media_service
from axis_mcp.departments.content_mcp import mcp as content_mcp


@pytest.fixture
def isolated_bus(tmp_path, monkeypatch):
    root = tmp_path / "central_bus"
    monkeypatch.setattr(bus_store, "BUS_ROOT", root)
    return root


def _campaign(campaign_id: str) -> dict:
    script = content_service.create_video_script(
        "Concat test", "แสดงการประกอบวิดีโอ", 30, campaign_id
    )
    content_service.design_audio_experience(campaign_id, script["filename"])
    return script


class FakeConcatClient:
    instances = []

    def __init__(self, command, *, cwd=None, env=None, **kwargs):
        self.command = command
        self.cwd = cwd
        self.env = env or {}
        self.calls = []
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def call_tool(self, name, arguments=None, timeout=60):
        args = arguments or {}
        self.calls.append((name, args))
        if name == "concat_version":
            return {"concat": "0.2.8", "mcp": {"mode": "headless"}}
        if name == "project_create":
            project = Path(args["location"]) / args["name"]
            project.mkdir()
            (project / "concat.json").write_text("{}", encoding="utf-8")
            return {"project": {"name": args["name"]}}
        if name == "project_open":
            return {"project": {"name": Path(args["path"]).name}}
        if name == "timeline_read":
            return {
                "timeline": {
                    "tracks": [{"id": "T1"}, {"id": "T2"}, {"id": "T3"}],
                    "clips": [],
                }
            }
        if name == "media_import":
            return {"createdId": f"M{len(self.calls)}"}
        if name == "clip_add":
            return {"createdId": f"C{len(self.calls)}"}
        if name == "project_save":
            path = Path(args["path"])
            (path / "concat.json").write_text("{\"saved\":true}", encoding="utf-8")
            return {}
        if name == "export_start":
            Path(args["output"]).write_bytes(b"fake-mp4" * 100)
            return {"job": "export-1"}
        if name == "export_wait":
            return {"state": "done", "total": 30}
        return {}

    def close(self):
        return None


class FakeEarshotClient:
    instances = []

    def __init__(self):
        self.calls = []
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def call_tool(self, name, arguments=None, timeout=60):
        args = arguments or {}
        self.calls.append((name, args))
        if name == "sfx_render":
            Path(args["out"]).write_bytes(b"RIFF" + b"synthetic-sfx" * 200)
            return {"sound": args["sound"], "audit": {"ok": True, "clipping": False}}
        if name == "measure":
            return {"duration_seconds": 1.0, "integrated_lufs": -18.0, "true_peak_dbtp": -2.0}
        if name == "timeline":
            return {"events": [], "sync": {"matched_cues": 0}}
        if name == "sfx_list":
            return {"sounds": [{"id": "whoosh_fast/crisp"}]}
        raise AssertionError(f"unexpected Earshot tool: {name}")


def _configure_concat(monkeypatch):
    FakeConcatClient.instances.clear()
    monkeypatch.setattr(media_service, "MCPStdioClient", FakeConcatClient)
    monkeypatch.setattr(media_service, "_concat_binary", lambda: "/verified/concat")
    monkeypatch.setattr(
        media_service,
        "_probe_mp4",
        lambda _path: {
            "duration_seconds": 30.0,
            "video_streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
        },
    )


def _render_concat(campaign_id, isolated_bus, sound_delivery_filename=""):
    source = isolated_bus / "content" / "visuals" / f"{campaign_id}.mp4"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"synthetic video input")
    return media_service.render_campaign_with_concat(
        campaign_id,
        [
            {
                "path": str(source),
                "kind": "video",
                "start_seconds": 0,
                "source_kind": "generated_visual",
            }
        ],
        sound_delivery_filename=sound_delivery_filename,
    )


def test_concat_render_records_project_mp4_and_human_gate(isolated_bus, monkeypatch):
    _configure_concat(monkeypatch)
    _campaign("concat-smoke")
    result = _render_concat("concat-smoke", isolated_bus)

    assert result["execution_status"] == "completed"
    assert result["approval_required"] is True
    assert result["published"] is False
    assert result["caption_count"] == 4
    assert result["caption_source"] == "video_script"
    assert result["project_file"].endswith("concat.json")
    assert result["output"]["sha256"] == hashlib.sha256(
        (isolated_bus / result["output"]["path"]).read_bytes()
    ).hexdigest()
    record = json.loads(
        bus_store.fetch_from_bus("content", result["result_artifact"]["filename"])["content"]
    )
    assert record["provider"] == "concat-mcp"
    assert record["execution_status"] == "completed"
    assert record["approval_effect"] == "none"
    names = [name for name, _args in FakeConcatClient.instances[0].calls]
    assert "captions_add" in names
    assert "export_start" in names
    campaign = content_service._load_campaign("concat-smoke")
    assert campaign["approved_version"] is None


def test_concat_consumes_earshot_delivery_as_audio_track(isolated_bus, monkeypatch):
    _configure_concat(monkeypatch)
    FakeEarshotClient.instances.clear()
    monkeypatch.setattr(media_service, "_earshot_client", FakeEarshotClient)
    _campaign("concat-earshot-handoff")
    sound = media_service.render_campaign_sfx(
        "concat-earshot-handoff",
        "whoosh_fast/crisp",
        start_seconds=4.25,
        duration_seconds=0.8,
        apex_seconds=0.3,
    )

    result = _render_concat(
        "concat-earshot-handoff",
        isolated_bus,
        sound_delivery_filename=sound["sound_delivery_filename"],
    )

    record = json.loads(
        bus_store.fetch_from_bus("content", result["result_artifact"]["filename"])["content"]
    )
    assert record["sound_delivery_filename"] == sound["sound_delivery_filename"]
    assert any(item["source_kind"] == "earshot_sfx" for item in record["inputs"])
    clip_calls = [
        args for name, args in FakeConcatClient.instances[0].calls if name == "clip_add"
    ]
    assert len(clip_calls) == 2
    assert result["approval_required"] is True
    assert result["published"] is False


def test_earshot_review_stores_measurements_and_timeline_in_bus(isolated_bus, monkeypatch):
    _configure_concat(monkeypatch)
    FakeEarshotClient.instances.clear()
    monkeypatch.setattr(media_service, "_earshot_client", FakeEarshotClient)
    _campaign("sound-review-smoke")
    render = _render_concat("sound-review-smoke", isolated_bus)
    output_path = isolated_bus / render["output"]["path"]

    result = media_service.review_campaign_audio(
        "sound-review-smoke", str(output_path), cue_times=[1.0, 2.5]
    )
    payload = json.loads(
        bus_store.fetch_from_bus("content", result["report_artifact"]["filename"])["content"]
    )
    assert result["execution_status"] == "completed"
    assert payload["provider"] == "earshot"
    assert payload["report"]["network_used"] is False
    assert payload["report"]["measure"]["integrated_lufs"] == -18.0
    assert [name for name, _args in FakeEarshotClient.instances[0].calls] == ["measure", "timeline"]
    timeline_call = FakeEarshotClient.instances[0].calls[1][1]
    assert timeline_call["detail"] == "low"
    assert timeline_call["video"] == str(output_path)
    assert timeline_call["cues"] == [1.0, 2.5]
    assert payload["report"]["render_result_filename"] == render["result_artifact"]["filename"]
    assert payload["report"]["render_output_sha256"] == render["output"]["sha256"]


def test_earshot_review_requires_a_concat_render(isolated_bus):
    _campaign("sound-review-before-render")

    with pytest.raises(content_service.ContentServiceError, match="complete render_campaign_with_concat"):
        media_service.review_campaign_audio("sound-review-before-render", "not-used.mp4")


def test_earshot_review_rejects_a_different_or_changed_render(isolated_bus, monkeypatch):
    _configure_concat(monkeypatch)
    FakeEarshotClient.instances.clear()
    monkeypatch.setattr(media_service, "_earshot_client", FakeEarshotClient)
    _campaign("sound-review-render-identity")
    render = _render_concat("sound-review-render-identity", isolated_bus)
    output_path = isolated_bus / render["output"]["path"]
    copy_path = output_path.with_name("other-render.mp4")
    copy_path.write_bytes(output_path.read_bytes())

    with pytest.raises(content_service.ContentServiceError, match="output of the latest completed Concat render"):
        media_service.review_campaign_audio("sound-review-render-identity", str(copy_path))

    output_path.write_bytes(b"changed after Concat validation")
    with pytest.raises(content_service.ContentServiceError, match="checksum changed"):
        media_service.review_campaign_audio("sound-review-render-identity", str(output_path))


def test_media_campaign_cannot_be_approved_until_latest_audio_review(isolated_bus, monkeypatch):
    _configure_concat(monkeypatch)
    FakeEarshotClient.instances.clear()
    monkeypatch.setattr(media_service, "_earshot_client", FakeEarshotClient)
    campaign_id = "sound-approval-order"
    _campaign(campaign_id)
    render = _render_concat(campaign_id, isolated_bus)
    campaign = content_service._load_campaign(campaign_id)
    assert campaign["review"]["media_workflow"]["ready_for_human_review"] is False

    with pytest.raises(content_service.ContentServiceError, match="current Concat render and Earshot review"):
        content_service.record_human_approval(campaign_id, campaign["version"], "review pending")

    output_path = isolated_bus / render["output"]["path"]
    media_service.review_campaign_audio(campaign_id, str(output_path))
    latest_gate = content_service.review_publish_gate(campaign_id=campaign_id)
    assert latest_gate["media_workflow"]["ready_for_human_review"] is True

    current = content_service._load_campaign(campaign_id)
    approval = content_service.record_human_approval(
        campaign_id, current["version"], "Reviewed the current render and audio QA report"
    )
    assert approval["status"] == "approved"


def test_concat_rejects_media_outside_central_bus(tmp_path, isolated_bus):
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"synthetic")
    with pytest.raises(content_service.ContentServiceError, match="inside central_bus/content"):
        media_service._validate_media_items(
            [
                {
                    "path": str(outside),
                    "kind": "video",
                    "start_seconds": 0,
                    "source_kind": "generated_visual",
                }
            ]
        )


def test_earshot_sfx_delivery_is_saved_for_content_handoff(isolated_bus, monkeypatch):
    FakeEarshotClient.instances.clear()
    monkeypatch.setattr(media_service, "_earshot_client", FakeEarshotClient)
    _campaign("sound-smoke")

    result = media_service.render_campaign_sfx(
        "sound-smoke", "whoosh_fast/crisp", start_seconds=4.25, duration_seconds=0.8, apex_seconds=0.3
    )
    payload = json.loads(
        bus_store.fetch_from_bus("content", result["sound_delivery_filename"])["content"]
    )
    stem = payload["stems"][0]
    stem_file = isolated_bus / stem["path"]
    assert stem_file.is_file()
    assert stem["sha256"] == hashlib.sha256(stem_file.read_bytes()).hexdigest()
    assert stem["start_seconds"] == 4.25
    assert payload["provider"] == "earshot"
    assert payload["report"]["network_used"] is False
    assert [name for name, _args in FakeEarshotClient.instances[0].calls] == [
        "sfx_render",
        "measure",
    ]


def test_earshot_sfx_list_returns_structured_bus_safe_data(monkeypatch):
    FakeEarshotClient.instances.clear()
    monkeypatch.setattr(media_service, "_earshot_client", FakeEarshotClient)

    result = media_service.list_earshot_sounds(category="whoosh_fast")

    assert result["sounds"][0]["id"] == "whoosh_fast/crisp"
    assert FakeEarshotClient.instances[0].calls == [
        ("sfx_list", {"category": "whoosh_fast", "full": True})
    ]


@pytest.mark.parametrize(
    "footer",
    [
        'JSON (compact): {"status":"ok"}',
        'JSON: {"status":"ok"}',
    ],
)
def test_earshot_result_payload_parses_json_footer(footer):
    assert media_service._earshot_result_payload(f"summary\n{footer}") == {"status": "ok"}


def test_content_mcp_owns_sound_tools():
    names = {tool.name for tool in content_mcp._tool_manager.list_tools()}
    assert {
        "sound_review_campaign_audio",
        "sound_list_earshot_sfx",
        "sound_render_campaign_sfx",
    } <= names
    assert "sound_department_info" not in names
    assert "llm_critique" not in names
