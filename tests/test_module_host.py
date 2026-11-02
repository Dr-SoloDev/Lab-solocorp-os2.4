from __future__ import annotations

import json
from pathlib import Path

import pytest

from solocorp_mcp.module_host import ModuleHost, ModuleHostError
from solocorp_mcp.module_registry import ModuleRegistry


class FakeClient:
    def __init__(self) -> None:
        self.closed = False
        self.fail_health = False

    def request(self, method, params, *, timeout):
        if self.fail_health:
            raise RuntimeError("module process exited")
        assert method == "tools/list"
        return {"tools": [{"name": "one"}, {"name": "two"}]}

    def call_tool(self, name, arguments, *, timeout):
        return {"name": name, "arguments": arguments}

    def close(self):
        self.closed = True


@pytest.fixture
def registry(tmp_path: Path) -> ModuleRegistry:
    return ModuleRegistry(
        registry_path=tmp_path / "config" / "module-registry.json",
        state_path=tmp_path / "state" / "module-registry.state.json",
    )


def test_module_host_connects_polls_calls_and_disconnects(registry, tmp_path):
    clients = []

    def factory(command, **kwargs):
        assert command == registry.module_config("content-creator")["command"]
        assert kwargs["cwd"] == tmp_path
        client = FakeClient()
        clients.append(client)
        return client

    host = ModuleHost(registry, client_factory=factory, cwd=tmp_path)
    config_before = Path(registry.path).read_bytes()

    connected = host.connect("content-creator")
    assert connected["connected"] is True
    assert connected["tool_count"] == 2
    assert registry.status()["modules"]["content-creator"]["status"] == "connected"
    assert host.health_all()[0]["connected"] is True
    assert host.call_tool("content-creator", "draft", {"topic": "audio"}) == {
        "name": "draft",
        "arguments": {"topic": "audio"},
    }

    disconnected = host.disconnect("content-creator")
    assert disconnected["disconnected"] is True
    assert clients[0].closed is True
    assert registry.status()["modules"]["content-creator"]["status"] == "enabled"
    assert Path(registry.path).read_bytes() == config_before


def test_module_host_rejects_disabled_and_unknown_modules(registry):
    registry.update("content-creator", "disabled")
    host = ModuleHost(registry, client_factory=lambda *args, **kwargs: FakeClient())

    with pytest.raises(ModuleHostError, match="disabled"):
        host.connect("content-creator")
    with pytest.raises(ModuleHostError, match="not found"):
        host.health("missing")


def test_module_host_records_connect_failure_in_runtime_state(registry):
    def fail_to_start(command, **kwargs):
        raise OSError("could not spawn module")

    host = ModuleHost(registry, client_factory=fail_to_start)
    result = host.connect("content-creator")

    assert result["connected"] is False
    assert "could not spawn module" in result["error"]
    state = json.loads(Path(registry.state_path).read_text(encoding="utf-8"))
    assert state["content-creator"]["status"] == "error"
    assert "could not spawn module" in state["content-creator"]["last_error"]


def test_module_host_health_failure_closes_and_marks_connection(registry):
    client = FakeClient()
    host = ModuleHost(registry, client_factory=lambda *args, **kwargs: client)
    assert host.connect("content-creator")["connected"] is True
    client.fail_health = True

    result = host.health("content-creator")

    assert result["status"] == "error"
    assert result["connected"] is False
    assert client.closed is True
    assert registry.status()["modules"]["content-creator"]["status"] == "error"
