"""Tool-surface tests for C1 registry writes and structured errors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from solocorp_mcp.module_registry import ModuleRegistry

ADMIN_KEY = "sk-solocorp-admin-local-dev-001"


@pytest.fixture()
def registry(tmp_path: Path) -> ModuleRegistry:
    return ModuleRegistry(
        registry_path=tmp_path / "config" / "module-registry.json",
        state_path=tmp_path / "state" / "module-registry.state.json",
    )


def _complete_entry() -> dict:
    return {
        "status": "enabled",
        "transport": "stdio",
        "command": ["/bin/echo", "hello"],
        "description": "stub module",
    }


def _server(monkeypatch: pytest.MonkeyPatch, registry: ModuleRegistry):
    monkeypatch.setenv("SOLOCORP_API_KEY", ADMIN_KEY)
    import solocorp_mcp.server as server_module

    monkeypatch.setattr(server_module, "_module_registry", registry)
    return server_module.create_server()


def test_update_tool_accepts_command_and_transport(
    registry: ModuleRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    mcp = _server(monkeypatch, registry)
    raw = mcp._tool_manager.get_tool("module_registry_update").fn(
        "qa", "enabled", "", ["/bin/echo", "tool"], "stdio"
    )

    payload = json.loads(raw)
    assert payload["updated"] is True
    assert registry.module_config("qa")["command"] == ["/bin/echo", "tool"]


def test_register_tool_end_to_end(
    registry: ModuleRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    mcp = _server(monkeypatch, registry)
    tool = mcp._tool_manager.get_tool("module_registry_register").fn

    raw = tool("ghost", _complete_entry())
    payload = json.loads(raw)
    assert payload["module_id"] == "ghost"
    assert registry.status()["modules"]["ghost"]["status"] == "enabled"

    duplicate = json.loads(tool("ghost", _complete_entry()))
    assert duplicate["status"] == "error"
    assert "already registered" in duplicate["message"]


def test_call_department_tool_reports_registry_invalid_not_module_not_found(
    registry: ModuleRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    Path(registry.path).write_text("{broken", encoding="utf-8")
    mcp = _server(monkeypatch, registry)

    raw = mcp._tool_manager.get_tool("solocorp_call_department_tool").fn(
        "qa", "qa_department_info", "{}"
    )
    payload = json.loads(raw)

    assert payload["status"] == "error"
    assert payload["error"] == "registry_invalid"
    assert payload["error"] != "module_not_found"
    assert payload["errors"]
