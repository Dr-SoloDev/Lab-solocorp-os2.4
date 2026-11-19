"""Live dashboard (Phase A): /live page + /api/sessions + /api/bus/queue + /api/live/status.

Fail-open ทุก endpoint: ไม่มี opencode CLI / ไม่มี DB / ไม่มี queue ไฟล์
ก็ต้องตอบ 200 ด้วย payload ว่าง — ห้าม 500 (PRD §9).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from axis_mcp.module_host import ModuleHost
from axis_mcp.module_registry import ModuleRegistry
from axis_mcp.task_tracking import TaskTracker
from solocorp_app.app import create_app
from solocorp_app.live import list_sessions, normalize_session, queue_depths
from solocorp_app.provider import ProviderStore
from solocorp_app.runtime import AppRuntime

BASE_URL = "http://127.0.0.1:8766"


class FakeClient:
    def request(self, method, params, *, timeout):
        return {"tools": []}

    def close(self) -> None:
        pass


@pytest.fixture
def shell(tmp_path: Path):
    registry = ModuleRegistry(
        registry_path=tmp_path / "config" / "module-registry.json",
        state_path=tmp_path / "state" / "module-registry.state.json",
    )
    host = ModuleHost(
        registry, client_factory=lambda *a, **k: FakeClient(), cwd=tmp_path
    )
    provider = ProviderStore(
        config_path=tmp_path / "config" / "provider.json",
        credentials_path=tmp_path / "config" / "provider.credentials.json",
        env={},
    )
    runtime = AppRuntime(
        registry=registry,
        host=host,
        provider=provider,
        tracker=TaskTracker(tmp_path / "tasks"),
        health_interval=0,
    )
    app = create_app(runtime)
    with TestClient(app, base_url=BASE_URL) as client:
        yield SimpleNamespace(client=client, runtime=runtime, tmp=tmp_path)
    runtime.close()


# ------------------------------------------------------------------ pages/APIs


def test_live_page_renders_without_sessions(shell):
    response = shell.client.get("/live")

    assert response.status_code == 200
    assert "Live Dashboard" in response.text
    assert "data-live" in response.text
    assert "/api/live/status" in response.text
    assert "3s" in response.text or "3 วินาที" in response.text


def test_api_sessions_is_fail_open_json(shell):
    response = shell.client.get("/api/sessions")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) >= {"sessions", "count", "source", "updated_at"}
    assert isinstance(payload["sessions"], list)
    assert payload["count"] == len(payload["sessions"])
    assert payload["source"] in ("cli", "db", "none")


def test_api_bus_queue_counts_jsonl_lines(shell, tmp_path: Path):
    from solocorp_app import live as live_module

    queue_dir = tmp_path / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    (queue_dir / "high.jsonl").write_text('{"a": 1}\n{"a": 2}\n', encoding="utf-8")
    (queue_dir / "normal.jsonl").write_text('{"b": 1}\n', encoding="utf-8")

    original = live_module.DEFAULT_QUEUE_DIR
    live_module.DEFAULT_QUEUE_DIR = queue_dir
    try:
        response = shell.client.get("/api/bus/queue")
    finally:
        live_module.DEFAULT_QUEUE_DIR = original

    assert response.status_code == 200
    payload = response.json()
    assert payload["queues"]["high"] == 2
    assert payload["queues"]["normal"] == 1
    assert payload["total"] >= 3


def test_api_live_status_combines_everything(shell):
    response = shell.client.get("/api/live/status")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) >= {
        "sessions",
        "session_count",
        "queues",
        "queue_total",
        "modules",
        "provider_state",
        "registry_valid",
        "updated_at",
    }
    assert payload["modules"]["total"] == 5
    assert payload["provider_state"] in (
        "configured",
        "unconfigured",
        "failed",
        "unknown",
    )
    assert isinstance(payload["module_states"], list)


def test_live_endpoints_need_no_csrf_and_have_security_headers(shell):
    for path in ("/live", "/api/sessions", "/api/bus/queue", "/api/live/status"):
        response = shell.client.get(path)
        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"


def test_nav_includes_live(shell):
    html = shell.client.get("/modules").text
    assert 'href="/live"' in html


# ------------------------------------------------------------------ unit


def test_normalize_session_never_raises():
    assert normalize_session(None)["id"]
    assert normalize_session("abc")["id"] == "abc"
    row = normalize_session(
        {"id": "s1", "title": "hello", "model": "m", "status": "done"}
    )
    assert (row["id"], row["title"], row["model"], row["outcome"]) == (
        "s1",
        "hello",
        "m",
        "done",
    )


def test_list_sessions_with_fake_cli(tmp_path: Path):
    fake = tmp_path / "fake-opencode"
    fake.write_text(
        "#!/usr/bin/env python3\nimport json,sys\n"
        'json.dump([{"id": "s1", "title": "t", "model": "m"}], sys.stdout)\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    envelope = list_sessions(10, queue_cli=[str(fake)])
    assert envelope["source"] == "cli"
    assert envelope["count"] == 1
    assert envelope["sessions"][0]["id"] == "s1"


def test_list_sessions_fail_open_when_nothing_exists(tmp_path: Path):
    envelope = list_sessions(
        10,
        queue_cli=["/nonexistent-opencode-cli-xyz"],
        db_path=tmp_path / "nope.db",
    )
    assert envelope["source"] == "none"
    assert envelope["sessions"] == []
    assert envelope["error"]


def test_queue_depths_missing_dir_is_zero(tmp_path: Path):
    envelope = queue_depths(queue_dir=tmp_path / "no-such-queue")
    assert envelope["total"] == 0
    assert envelope["queues"]["high"] == 0
