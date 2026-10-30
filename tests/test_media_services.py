from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from solocorp_mcp import bus_store
from solocorp_mcp.departments import content_service, media_service
from solocorp_mcp.departments.sound_mcp import mcp as sound_mcp


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


def test_concat_render_records_project_mp4_and_human_gate(isolated_bus, monkeypatch):
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
    script = _campaign("concat-smoke")
    source = isolated_bus / "content" / "visuals" / "scene.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"synthetic video input")

    result = media_service.render_campaign_with_concat(
        "concat-smoke",
        [
            {
                "path": str(source),
                "kind": "video",
                "start_seconds": 0,
                "source_kind": "generated_visual",
            }
        ],
    )

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
    FakeConcatClient.instances.clear()
    FakeEarshotClient.instances.clear()
    monkeypatch.setattr(media_service, "MCPStdioClient", FakeConcatClient)
    monkeypatch.setattr(media_service, "_earshot_client", FakeEarshotClient)
    monkeypatch.setattr(media_service, "_concat_binary", lambda: "/verified/concat")
    monkeypatch.setattr(
        media_service,
        "_probe_mp4",
        lambda _path: {
            "duration_seconds": 30.0,
            "video_streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
        },
    )
    _campaign("concat-earshot-handoff")
    source = isolated_bus / "content" / "visuals" / "scene.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"synthetic video input")
    sound = media_service.render_campaign_sfx(
        "concat-earshot-handoff",
        "whoosh_fast/crisp",
        start_seconds=4.25,
        duration_seconds=0.8,
        apex_seconds=0.3,
    )

    result = media_service.render_campaign_with_concat(
        "concat-earshot-handoff",
        [
            {
                "path": str(source),
                "kind": "video",
                "start_seconds": 0,
                "source_kind": "generated_visual",
            }
        ],
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
    FakeEarshotClient.instances.clear()
    monkeypatch.setattr(media_service, "_earshot_client", FakeEarshotClient)
    _campaign("sound-review-smoke")
    audio = isolated_bus / "content" / "sound" / "test.wav"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"synthetic test audio")

    result = media_service.review_campaign_audio("sound-review-smoke", str(audio), cue_times=[1.0, 2.5])
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
    assert "video" not in timeline_call
    assert timeline_call["cues"] == [1.0, 2.5]


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


def test_sound_mcp_exposes_only_bus_safe_tools():
    names = {tool.name for tool in sound_mcp._tool_manager.list_tools()}
    assert names == {
        "sound_review_campaign_audio",
        "sound_list_earshot_sfx",
        "sound_render_campaign_sfx",
    }
    assert "llm_critique" not in names
