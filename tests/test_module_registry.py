"""Config/state split for the module registry.

These tests lock the invariant behind audit finding P2/P1-1: a heartbeat must
never dirty a tracked file. Config (what a human decided) lives in git; state
(what the runtime observed) does not.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from solocorp_mcp import module_registry
from solocorp_mcp.module_registry import ModuleRegistry


@pytest.fixture()
def registry(tmp_path: Path) -> ModuleRegistry:
    config = tmp_path / "config" / "module-registry.json"
    state = tmp_path / "state" / "module-registry.state.json"
    return ModuleRegistry(registry_path=config, state_path=state)


def _config_bytes(registry: ModuleRegistry) -> bytes:
    return Path(registry.path).read_bytes()


def test_default_paths_keep_config_out_of_bus_content() -> None:
    assert "content" not in module_registry.DEFAULT_CONFIG_PATH.parts
    assert "content" not in module_registry.DEFAULT_STATE_PATH.parts
    assert module_registry.DEFAULT_CONFIG_PATH.name == "module-registry.json"
    assert module_registry.DEFAULT_STATE_PATH.name == "module-registry.state.json"


def test_sound_capability_is_not_registered_as_a_separate_department() -> None:
    assert "sound-studio" not in module_registry.DEFAULT_MODULES
    assert "content-creator" in module_registry.DEFAULT_MODULES


def test_initial_config_is_persistent_only(registry: ModuleRegistry) -> None:
    saved = json.loads(Path(registry.path).read_text(encoding="utf-8"))
    for module_id, entry in saved.items():
        if module_id == "_meta":
            continue
        assert entry["status"] in module_registry.PERSISTENT_STATUSES
        assert "last_checked" not in entry
        assert "response_time_ms" not in entry
        assert "last_error" not in entry


def test_heartbeat_failure_writes_state_only(registry: ModuleRegistry) -> None:
    # A module whose command cannot connect fails deterministically.
    saved = json.loads(Path(registry.path).read_text(encoding="utf-8"))
    saved["ghost"] = {
        "status": "enabled",
        "transport": "stdio",
        "command": [sys.executable, "-m", "nonexistent.module"],
        "description": "no command configured",
    }
    Path(registry.path).write_text(json.dumps(saved), encoding="utf-8")

    before = _config_bytes(registry)
    result = registry.heartbeat("ghost")

    assert result["status"] == "error"
    assert result["connected"] is False
    assert _config_bytes(registry) == before, "heartbeat must not touch tracked config"

    state = json.loads(Path(registry.state_path).read_text(encoding="utf-8"))
    assert state["ghost"]["status"] == "error"
    assert state["ghost"]["last_error"] == "MCP server exited before responding"


def test_status_merges_config_and_state(registry: ModuleRegistry) -> None:
    saved = json.loads(Path(registry.path).read_text(encoding="utf-8"))
    saved["ghost"] = {
        "status": "enabled",
        "transport": "stdio",
        "command": [sys.executable, "-m", "nonexistent.module"],
        "description": "no command configured",
    }
    Path(registry.path).write_text(json.dumps(saved), encoding="utf-8")
    registry.heartbeat("ghost")

    status = registry.status()
    assert status["modules"]["ghost"]["status"] == "error"
    assert status["modules"]["ghost"]["transport"] == "stdio"
    assert status["error_count"] == 1
    assert status["state_path"].endswith("module-registry.state.json")

    # The tracked config still says enabled: the decision is unchanged.
    on_disk = json.loads(Path(registry.path).read_text(encoding="utf-8"))
    assert on_disk["ghost"]["status"] == "enabled"


def test_update_enabled_disable_goes_to_config(registry: ModuleRegistry) -> None:
    before = json.loads(Path(registry.path).read_text(encoding="utf-8"))
    assert before["qa"]["status"] == "enabled"

    registry.update("qa", "disabled", description="paused for maintenance")

    after = json.loads(Path(registry.path).read_text(encoding="utf-8"))
    assert after["qa"]["status"] == "disabled"
    assert after["qa"]["description"] == "paused for maintenance"
    assert not Path(registry.state_path).exists()


def test_update_with_runtime_status_goes_to_state(registry: ModuleRegistry) -> None:
    config_before = _config_bytes(registry)
    registry.update("qa", "connected")

    assert _config_bytes(registry) == config_before
    state = json.loads(Path(registry.state_path).read_text(encoding="utf-8"))
    assert state["qa"]["status"] == "connected"


def test_update_rejects_unknown_status(registry: ModuleRegistry) -> None:
    with pytest.raises(ValueError, match="status must be one of"):
        registry.update("qa", "banana")


def test_update_unknown_module_runtime_status_raises(registry: ModuleRegistry) -> None:
    with pytest.raises(ValueError, match="not found in registry"):
        registry.update("does-not-exist", "connected")
