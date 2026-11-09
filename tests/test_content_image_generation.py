"""Unit tests for generate_image (NVIDIA NIM FLUX.3 Klein default; OpenRouter legacy).

All provider HTTP is mocked (transport-level). No real paid generation runs
in CI. Live smoke tests are script-driven only (never in pytest).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os

import pytest

from axis_mcp import bus_store
from axis_mcp.departments import content_mcp as content_mcp_module
from axis_mcp.departments import content_service
from axis_mcp.departments.content_mcp import mcp as content_mcp

FAKE_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"fake-jpeg-payload" * 64


@pytest.fixture
def isolated_bus(tmp_path, monkeypatch):
    root = tmp_path / "central_bus"
    monkeypatch.setattr(bus_store, "BUS_ROOT", root)
    monkeypatch.setattr(content_service, "load_dotenv", lambda *a, **k: None)
    # Never leak the host environment's real keys into mocked tests.
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    return root


@pytest.fixture
def openrouter_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-fake-key-for-mock")
    return "test-fake-key-for-mock"


@pytest.fixture
def nvidia_key(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-fake-nvidia-key-for-mock")
    return "test-fake-nvidia-key-for-mock"


def _mock_provider(monkeypatch, image_bytes: bytes = FAKE_JPEG_BYTES):
    captured: dict = {}

    def _fake_request(payload, api_key):
        captured["payload"] = payload
        captured["api_key_set"] = bool(api_key)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return {
            "choices": [
                {
                    "message": {
                        "images": [
                            {"image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                        ]
                    }
                }
            ]
        }

    monkeypatch.setattr(content_service, "_openrouter_request", _fake_request)
    return captured


def _mock_nvidia(monkeypatch, image_bytes: bytes = FAKE_JPEG_BYTES):
    captured: dict = {}

    def _fake_request(payload, api_key):
        captured["payload"] = payload
        captured["api_key_set"] = bool(api_key)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return {"artifacts": [{"base64": encoded, "finishReason": "SUCCESS"}]}

    monkeypatch.setattr(content_service, "_nvidia_request", _fake_request)
    return captured


def test_generate_image_missing_key_returns_missing_api_key(isolated_bus):
    result = content_service.generate_image("a quiet pagoda at dawn")
    assert result["status"] == "error"
    assert result["error"] == "missing_api_key"


def test_generate_image_tmp_output_rejected_as_write_out_of_bounds(
    isolated_bus, openrouter_key
):
    result = content_service.generate_image(
        "a quiet pagoda at dawn", output_filename="/tmp/evil.jpg"
    )
    assert result["status"] == "error"
    assert result["error"] == "write_out_of_bounds"


def test_generate_image_profiles_output_rejected_as_write_out_of_bounds(
    isolated_bus, openrouter_key
):
    result = content_service.generate_image(
        "a quiet pagoda at dawn", output_filename="profiles/15-content-creator/SOUL.jpg"
    )
    assert result["status"] == "error"
    assert result["error"] == "write_out_of_bounds"


def test_generate_image_tmp_reference_rejected_as_write_out_of_bounds(
    isolated_bus, openrouter_key
):
    result = content_service.generate_image(
        "a quiet pagoda at dawn", reference_image_path="/tmp/ref.jpg"
    )
    assert result["status"] == "error"
    assert result["error"] == "write_out_of_bounds"


def test_generate_image_mocked_success_saves_with_hash(
    isolated_bus, openrouter_key, monkeypatch
):
    captured = _mock_provider(monkeypatch)
    result = content_service.generate_image(
        "a quiet pagoda at dawn",
        aspect_ratio="16:9",
        resolution="1K",
        format="jpeg",
        provider="openrouter",
    )
    assert result["status"] == "ok"
    assert result["provider"] == "openrouter"
    assert result["model"] == content_service.OPENROUTER_MODEL
    assert result["cost_estimate_usd"] == pytest.approx(0.008)
    assert result["gate_passed"] is False
    assert result["published"] is False
    assert result["approval_required"] is True
    image_file = isolated_bus / result["image_path"]
    if not image_file.is_file():
        # image_path may be relative to the repo ROOT in production; in the
        # isolated fixture it falls back to relative-to-BUS_ROOT ("content/...").
        image_file = isolated_bus / "content" / image_file.name
    assert image_file.is_file()
    content = image_file.read_bytes()
    assert content == FAKE_JPEG_BYTES
    assert result["sha256"] == hashlib.sha256(content).hexdigest()
    assert result["size_bytes"] == len(content)
    # Provenance manifest was stored on the bus.
    manifest_file = isolated_bus / result["image_manifest"]["path"]
    if not manifest_file.is_file():
        manifest_file = isolated_bus / result["image_manifest"]["filename"]
    assert manifest_file.is_file()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["sha256"] == result["sha256"]
    assert manifest["provider"] == "openrouter"
    # Provider payload contract: chat completions + modalities, single shot.
    payload = captured["payload"]
    assert payload["model"] == content_service.OPENROUTER_MODEL
    assert payload["modalities"] == ["image"]
    assert payload["image_config"] == {
        "aspect_ratio": "16:9",
        "size": "1K",
        "output_format": "image/jpeg",
    }


def test_generate_image_empty_prompt_raises(isolated_bus, openrouter_key):
    with pytest.raises(content_service.ContentServiceError, match="prompt is required"):
        content_service.generate_image("   ")


def test_generate_image_overlength_prompt_raises_before_http(isolated_bus):
    # IMAGE_MAX_PROMPT_CHARS is enforced in generate_image itself, before any
    # provider dispatch — no key and no HTTP needed for this error.
    with pytest.raises(
        content_service.ContentServiceError,
        match="prompt exceeds the 2000-character image-generation limit",
    ):
        content_service.generate_image("x" * 2001)


def test_generate_image_tool_registered_and_wrapper_preserves_error_codes(isolated_bus):
    names = {tool.name for tool in content_mcp._tool_manager.list_tools()}
    assert "generate_image" in names
    raw = content_mcp_module.generate_image("a quiet pagoda at dawn")
    parsed = json.loads(raw)
    assert parsed["status"] == "error"
    assert parsed["error"] == "missing_api_key"
    raw = content_mcp_module.generate_image(
        "ok prompt", output_filename="/tmp/evil.jpg"
    )
    parsed = json.loads(raw)
    # Missing-key state is checked after structural validation, but OOB is
    # validated first, so the path error must surface even without a key.
    assert parsed["error"] == "write_out_of_bounds"


@pytest.mark.skipif(
    os.environ.get("OPENROUTER_LIVE_TEST") != "1", reason="manual live smoke (paid)"
)
def test_generate_image_live_smoke(isolated_bus):
    """Manual, paid smoke test — never runs in CI (OPENROUTER_LIVE_TEST=1 to opt in)."""
    result = content_service.generate_image(
        "a quiet pagoda at dawn",
        aspect_ratio="16:9",
        resolution="1K",
        format="jpeg",
        provider="openrouter",
    )
    assert result["status"] == "ok"
    assert result["sha256"]


# ---------------------------------------------------------------------------
# NVIDIA NIM provider (default) — mocked
# ---------------------------------------------------------------------------


def test_generate_image_nvidia_mocked_success_saves_jpg_with_hash(
    isolated_bus, nvidia_key, monkeypatch
):
    captured = _mock_nvidia(monkeypatch)
    result = content_service.generate_image(
        "a quiet pagoda at dawn", aspect_ratio="1:1"
    )
    assert result["status"] == "ok"
    image_file = isolated_bus / result["image_path"]
    if not image_file.is_file():
        image_file = isolated_bus / "content" / image_file.name
    assert image_file.is_file()
    assert image_file.name.endswith(".jpg")
    blob = image_file.read_bytes()
    assert blob == FAKE_JPEG_BYTES
    assert blob.startswith(b"\xff\xd8\xff\xe0")
    assert result["sha256"] == hashlib.sha256(blob).hexdigest()
    assert result["size_bytes"] == len(blob)
    assert result["provider"] == "nvidia-nim"
    assert result["model"] == content_service.NVIDIA_NIM_MODEL
    assert result["format"] == "jpeg"
    assert result["actual_format"] == "jpeg"
    assert result["width"] == 1024
    assert result["height"] == 1024
    assert result["steps"] == content_service.NVIDIA_NIM_STEPS_DEFAULT
    assert result["gate_passed"] is False
    assert result["published"] is False
    assert result["approval_required"] is True
    # Provenance manifest stored on the bus with license note.
    manifest_file = isolated_bus / result["image_manifest"]["path"]
    if not manifest_file.is_file():
        manifest_file = isolated_bus / result["image_manifest"]["filename"]
    assert manifest_file.is_file()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["sha256"] == result["sha256"]
    assert manifest["provider"] == "nvidia-nim"
    assert "license_note" in manifest and "non-commercial" in manifest["license_note"]
    assert manifest["actual_format"] == "jpeg"
    # Payload contract: NIM endpoint fields, single-shot.
    payload = captured["payload"]
    assert payload["prompt"] == "a quiet pagoda at dawn"
    assert payload["width"] == 1024
    assert payload["height"] == 1024
    assert payload["steps"] == content_service.NVIDIA_NIM_STEPS_DEFAULT
    assert "image" not in payload  # no reference image supplied
    assert captured["api_key_set"] is True


def test_generate_image_nvidia_missing_key_returns_missing_api_key(isolated_bus):
    result = content_service.generate_image("a quiet pagoda at dawn")
    assert result["status"] == "error"
    assert result["error"] == "missing_api_key"


def test_generate_image_nvidia_out_of_bounds_rejected_before_http(
    isolated_bus, nvidia_key, monkeypatch
):
    def _explosive(payload, api_key):  # must never be called for OOB paths
        raise AssertionError("HTTP transport must not be reached")

    monkeypatch.setattr(content_service, "_nvidia_request", _explosive)
    result = content_service.generate_image(
        "a quiet pagoda at dawn", output_filename="/tmp/evil.jpg"
    )
    assert result["status"] == "error"
    assert result["error"] == "write_out_of_bounds"


def test_generate_image_nvidia_unsupported_aspect(
    isolated_bus, nvidia_key, monkeypatch
):
    def _explosive(payload, api_key):
        raise AssertionError("HTTP transport must not be reached")

    monkeypatch.setattr(content_service, "_nvidia_request", _explosive)
    result = content_service.generate_image(
        "a quiet pagoda at dawn", aspect_ratio="5:4"
    )
    assert result["status"] == "error"
    assert result["error"] == "unsupported_aspect"
    assert "5:4" in result["message"]


def test_generate_image_nvidia_png_request_saved_as_jpg(
    isolated_bus, nvidia_key, monkeypatch
):
    captured = _mock_nvidia(monkeypatch)
    result = content_service.generate_image(
        "a quiet pagoda at dawn", aspect_ratio="1:1", format="png"
    )
    assert result["status"] == "ok"
    assert result["requested_format"] == "png"
    assert result["format"] == "jpeg"
    assert result["actual_format"] == "jpeg"
    assert "format_note" in result
    image_file = isolated_bus / result["image_path"]
    if not image_file.is_file():
        image_file = isolated_bus / "content" / image_file.name
    assert image_file.name.endswith(".jpg")  # never .png


def test_generate_image_nvidia_unknown_provider_rejected(isolated_bus, nvidia_key):
    with pytest.raises(
        content_service.ContentServiceError,
        match="provider must be one of: nvidia, openrouter",
    ):
        content_service.generate_image("a quiet pagoda at dawn", provider="fireworks")


def test_generate_image_tool_still_registered_with_nvidia_default(isolated_bus):
    names = {tool.name for tool in content_mcp._tool_manager.list_tools()}
    assert "generate_image" in names
    # Default provider is nvidia: no NVIDIA_API_KEY -> missing_api_key on the bus.
    raw = json.loads(content_mcp_module.generate_image("a quiet pagoda at dawn"))
    assert raw["status"] == "error"
    assert raw["error"] == "missing_api_key"
