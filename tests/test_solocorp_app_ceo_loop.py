"""Phase 2 CEO loop tests: POST /chat → terminal task, no real MCP process.

Covers DoD 1–5: happy completed, disabled→failed, timeout→failed+disconnected,
tool error→failed, brief 400 no-task, legacy file readable without rewrite.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from axis_mcp.departments.mcp_stdio import MCPStdioError
from axis_mcp.module_host import ModuleHost, ModuleHostError
from axis_mcp.module_registry import ModuleRegistry
from axis_mcp.task_tracking import TaskTracker
from solocorp_app import APP_VERSION
from solocorp_app.app import create_app
from solocorp_app.ceo_loop import (
    CEO_TURN_BUDGET_S,
    TOOL_TIMEOUTS,
    map_error,
    route_brief,
    timeout_for_tool,
    validate_brief,
)
from solocorp_app.provider import ProviderStore
from solocorp_app.runtime import AppRuntime

BASE_URL = "http://127.0.0.1:8766"


class FakeClient:
    """Stands in for a real stdio MCP process (controllable per test)."""

    def __init__(self, state: dict) -> None:
        self._state = state
        self.closed = False

    def request(self, method, params, *, timeout):
        if self._state.get("connect_fail"):
            raise RuntimeError("module process exited")
        assert method == "tools/list"
        return {"tools": [{"name": "content_department_info"}]}

    def call_tool(self, name, arguments, *, timeout):
        self._state.setdefault("calls", []).append((name, arguments, timeout))
        mode = self._state.get("call_mode", "ok")
        if mode == "ok":
            return {"filename": "content/ceo-loop-test.md"}
        if mode == "timeout":
            raise MCPStdioError("MCP request timed out: tools/call")
        if mode == "tool_error":
            raise MCPStdioError("tool failed detail boom")
        if mode == "generic":
            return {"name": name, "arguments": arguments}
        raise AssertionError(f"unknown call_mode: {mode}")

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def shell(tmp_path: Path):
    state: dict = {"call_mode": "ok"}
    registry = ModuleRegistry(
        registry_path=tmp_path / "config" / "module-registry.json",
        state_path=tmp_path / "state" / "module-registry.state.json",
    )
    clients: list[FakeClient] = []

    def factory(command, **kwargs):
        client = FakeClient(state)
        clients.append(client)
        return client

    host = ModuleHost(registry, client_factory=factory, cwd=tmp_path)
    provider = ProviderStore(
        config_path=tmp_path / "config" / "provider.json",
        credentials_path=tmp_path / "config" / "provider.credentials.json",
        env={},
    )
    tracker = TaskTracker(tmp_path / "tasks")
    runtime = AppRuntime(
        registry=registry,
        host=host,
        provider=provider,
        tracker=tracker,
        health_interval=0,
    )
    app = create_app(runtime)
    with TestClient(app, base_url=BASE_URL) as client:
        yield SimpleNamespace(
            client=client,
            runtime=runtime,
            registry=registry,
            host=host,
            provider=provider,
            tracker=tracker,
            tmp=tmp_path,
            clients=clients,
            state=state,
        )
    runtime.close()


def csrf(shell) -> str:
    token = shell.client.cookies.get("solocorp_csrf")
    if not token:
        shell.client.get("/chat")
        token = shell.client.cookies.get("solocorp_csrf")
    assert token, "the loopback boundary must issue a CSRF cookie"
    return token


# 1. happy path ------------------------------------------------------------


def test_happy_path_completed_with_envelope_mirror(shell):
    response = shell.client.post(
        "/chat",
        data={"csrf_token": csrf(shell), "brief": "ทำสคริปต์ tiktok 6x15 ทดสอบ"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Phase 2" not in response.text or "Send to CEO loop" in response.text
    tasks = shell.runtime.tasks()
    assert len(tasks) == 1
    task = tasks[0]
    assert task["status"] == "completed"
    assert task["completed_at"]
    assert task["started_at"]
    assert isinstance(task["route_reason"], str) and task["route_reason"]
    assert len(task["route_reason"]) <= 500
    assert isinstance(task["artifact_refs"], list) and task["artifact_refs"]
    assert task["result_ref"] == task["artifact_refs"][0]
    assert task["app_version"] == APP_VERSION
    assert task["error"] is None
    # chat page shows the terminal task inline
    assert task["task_id"] in response.text
    assert "completed" in response.text
    assert "/tasks" in response.text


def test_post_json_returns_task_envelope(shell):
    token = csrf(shell)
    response = shell.client.post(
        "/chat",
        json={"brief": "json brief tiktok test"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["task_id"].startswith("task-")
    assert payload["artifact_refs"]
    assert payload["result_ref"] == payload["artifact_refs"][0]


# 2. disabled --------------------------------------------------------------


def test_disabled_failed_with_module_disabled_hint(shell):
    shell.registry.update("content-creator", "disabled")

    response = shell.client.post(
        "/chat",
        data={"csrf_token": csrf(shell), "brief": "ทำสคริปต์ tiktok 6x15 ทดสอบ"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert response.status_code != 500
    tasks = shell.runtime.tasks()
    assert len(tasks) == 1
    task = tasks[0]
    assert task["status"] == "failed"
    assert task["completed_at"]
    assert task["error"] is not None
    assert task["error"]["code"] == "MODULE_DISABLED"
    assert "Modules" in task["error"]["hint"] or "Enable" in task["error"]["hint"]
    assert task["module"] == "content-creator"
    # no silent reroute to another module
    assert {t["module"] for t in tasks} == {"content-creator"}


# 3. timeout ----------------------------------------------------------------


def test_timeout_failed_and_disconnected(shell):
    shell.state["call_mode"] = "timeout"

    response = shell.client.post(
        "/chat",
        data={"csrf_token": csrf(shell), "brief": "brief ที่ทำให้ timeout"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    tasks = shell.runtime.tasks()
    assert len(tasks) == 1
    task = tasks[0]
    assert task["status"] == "failed"
    assert task["completed_at"]
    assert task["error"]["code"] in ("TOOL_FAILED", "MODULE_ERROR")
    # R5: timeout must disconnect immediately, no zombie connection
    assert shell.host._connection("content-creator") is None


# 4. tool error -------------------------------------------------------------


def test_tool_error_failed_with_hint(shell):
    shell.state["call_mode"] = "tool_error"

    turn = shell.runtime.run_ceo_turn("brief ที่ tool ล้ม")

    assert turn["task"]["status"] == "failed"
    assert turn["error"]["code"] == "TOOL_FAILED"
    assert turn["error"]["hint"]
    assert turn["task"]["completed_at"]
    assert turn["task"]["error"]["message"] == turn["task"]["error_detail"]


# 5. brief 400 --------------------------------------------------------------


def test_brief_invalid_400_without_task(shell):
    before = len(shell.runtime.tasks())

    empty = shell.client.post(
        "/chat",
        data={"csrf_token": csrf(shell), "brief": "   "},
        follow_redirects=False,
    )
    assert empty.status_code == 400
    assert "brief must be 1-2000 characters" in empty.text

    long_brief = "x" * 2001
    too_long = shell.client.post(
        "/chat",
        data={"csrf_token": csrf(shell), "brief": long_brief},
        follow_redirects=False,
    )
    assert too_long.status_code == 400

    assert len(shell.runtime.tasks()) == before


# 6. legacy file ------------------------------------------------------------


def test_legacy_task_file_readable_without_rewrite(shell):
    legacy_id = "task-aaaabbbbcccc"
    legacy = {
        "task_id": legacy_id,
        "dept": "content",
        "module": "content-creator",
        "task_type": "content",
        "status": "completed",
        "brief": "secret legacy brief",
        "created_at": "2026-11-01T00:00:00+00:00",
        "started_at": "2026-11-01T00:00:01+00:00",
        "completed_at": "2026-11-01T00:00:02+00:00",
        "result_ref": "content/old.md",
        "error_detail": None,
    }
    path = shell.tracker.root / f"{legacy_id}.json"
    path.write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")
    digest_before = hashlib.sha256(path.read_bytes()).hexdigest()
    mtime_before = path.stat().st_mtime_ns

    tasks = shell.runtime.tasks()
    found = next(t for t in tasks if t["task_id"] == legacy_id)
    assert found["artifact_refs"] == ["content/old.md"]
    assert found["result_ref"] == "content/old.md"
    assert "secret legacy brief" not in json.dumps(tasks)

    html = shell.client.get("/tasks").text
    assert legacy_id in html
    assert "content/old.md" in html

    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest_before
    assert path.stat().st_mtime_ns == mtime_before


# 7. terminal guarantee + pure helpers --------------------------------------


def test_no_pending_leak_and_pure_router_contract():
    assert CEO_TURN_BUDGET_S == 180.0
    assert TOOL_TIMEOUTS["default"] == 60.0
    assert TOOL_TIMEOUTS["render_*"] == 150.0
    assert TOOL_TIMEOUTS["tools/list"] == 5.0
    assert timeout_for_tool("render_campaign_media_local", 200.0) == 150.0
    assert timeout_for_tool("content_department_info", 200.0) == 60.0
    assert timeout_for_tool("tools/list", 200.0) == 5.0

    try:
        validate_brief("   ")
        raise AssertionError("should have raised")
    except ValueError as exc:
        assert "1-2000" in str(exc)

    modules = [
        {
            "id": "content-creator",
            "enabled": True,
            "observation": "connected",
            "capabilities": ["tools", "resources"],
        }
    ]
    module_id, tool, args, reason = route_brief("ทำสคริปต์", modules)
    assert module_id == "content-creator"
    assert tool
    assert args["brief"] == "ทำสคริปต์"
    assert reason and len(reason) <= 500

    err = map_error(ModuleHostError("module content-creator is disabled"))
    assert err["code"] == "MODULE_DISABLED"
    assert err["hint"]


def test_chat_page_has_form_and_no_inline_script(shell):
    html = shell.client.get("/chat").text

    assert 'method="post"' in html
    assert 'action="/chat"' in html
    assert 'name="brief"' in html
    assert 'name="csrf_token"' in html
    assert "Not wired yet" not in html
    # CSP: no inline script in the Phase 2 template (base shell script is src-only)
    assert "<script>" not in html
    assert "onclick" not in html.lower()


# 8. P2-08 strict: secret brief never leaks in list/single-task -----------


def test_p2_08_secret_brief_never_leaks_in_list_or_single_task(shell):
    """P2-08 strict: brief with ``sk-`` must not appear in any API echo.

    Raw stays in TaskTracker JSON on disk for debug; list (``runtime.tasks``)
    and single-task JSON (``POST /chat`` response) must both be clean.
    Envelope v2 (route_reason/artifact_refs/app_version/error) stays intact.
    """

    secret = "sk-abc123SECRET456xyz"
    brief = f"ทำสคริปต์ tiktok ทดสอบ {secret}"
    token = csrf(shell)
    response = shell.client.post(
        "/chat",
        json={"brief": brief},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    # envelope v2 intact
    assert payload["status"] == "completed"
    assert isinstance(payload["route_reason"], str) and payload["route_reason"]
    assert len(payload["route_reason"]) <= 500
    assert payload["artifact_refs"]
    assert payload["result_ref"] == payload["artifact_refs"][0]
    assert payload["app_version"] == APP_VERSION
    # strict: no secret in single-task echo
    dumped = json.dumps(payload, ensure_ascii=False)
    assert secret not in dumped
    assert "sk-abc123" not in dumped
    assert brief not in dumped
    # redacted marker present, raw secret gone
    assert payload.get("brief") != brief
    assert "[redacted]" in (payload.get("brief") or "")

    # strict: no secret in list/tasks
    tasks = shell.runtime.tasks()
    list_dumped = json.dumps(tasks, ensure_ascii=False)
    assert secret not in list_dumped
    assert "sk-abc123" not in list_dumped

    # strict: no secret in HTML echoes (tasks page + chat re-render)
    html_tasks = shell.client.get("/tasks").text
    assert secret not in html_tasks
    assert "sk-abc123" not in html_tasks

    form_resp = shell.client.post(
        "/chat",
        data={"csrf_token": csrf(shell), "brief": brief},
        follow_redirects=False,
    )
    assert form_resp.status_code == 200
    assert secret not in form_resp.text
    assert "sk-abc123" not in form_resp.text.lower()

    # raw stays on disk for debug (design: redact echo, not storage)
    task_id = payload["task_id"]
    raw = json.loads(
        (shell.tracker.root / f"{task_id}.json").read_text(encoding="utf-8")
    )
    assert raw["brief"] == brief


def test_p2_08_long_brief_preview_and_secret_hint():
    """Preview budget (120 + marker) + secret hint live next to validate."""

    from solocorp_app.ceo_loop import (
        BRIEF_PREVIEW_CHARS,
        BRIEF_SECRET_HINT,
        contains_possible_secret,
        redact_brief_for_api,
    )

    assert BRIEF_PREVIEW_CHARS == 120
    assert "sk-" in BRIEF_SECRET_HINT or "secret" in BRIEF_SECRET_HINT.lower()
    assert contains_possible_secret("key sk-abc123xyz here") is True
    assert contains_possible_secret("hello world brief") is False

    long_brief = "ก" * 200
    redacted = redact_brief_for_api(long_brief)
    assert long_brief not in redacted
    assert redacted.endswith(" [redacted]")
    assert len(redacted) <= BRIEF_PREVIEW_CHARS + len(" [redacted]")

    # redacted marker present, raw secret gone
    assert redact_brief_for_api("hello brief") == "hello brief"
    masked = redact_brief_for_api("token sk-abc123SECRET456")
    assert "sk-abc123" not in masked
    assert "[redacted]" in masked

    # validate_brief behavior unchanged (length only)
    assert validate_brief("  hello  ") == "hello"
