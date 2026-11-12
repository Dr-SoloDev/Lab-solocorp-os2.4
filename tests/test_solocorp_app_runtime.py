"""App shell pages, module toggle and API — the Phase 1 gate itself.

The registry, module host, provider store and task tracker are injected with
temp paths and a fake stdio client, so these tests never start a real MCP
process and never touch the tracked ``config/module-registry.json``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from axis_mcp.module_host import ModuleHost
from axis_mcp.module_registry import ModuleRegistry
from axis_mcp.task_tracking import TaskTracker
from solocorp_app.app import create_app
from solocorp_app.provider import ProviderStore
from solocorp_app.runtime import AppRuntime

BASE_URL = "http://127.0.0.1:8766"
RUNTIME_ONLY_FIELDS = ("last_checked", "response_time_ms", "last_error")


class FakeClient:
    """Stands in for a real stdio MCP process."""

    def __init__(self) -> None:
        self.closed = False
        self.fail = False

    def request(self, method, params, *, timeout):
        if self.fail:
            raise RuntimeError("module process exited")
        assert method == "tools/list"
        return {"tools": [{"name": "draft_content"}, {"name": "create_campaign"}]}

    def call_tool(self, name, arguments, *, timeout):  # pragma: no cover - Phase 2
        return {"name": name, "arguments": arguments}

    def close(self) -> None:
        self.closed = True


def wait_for(predicate, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return bool(predicate())


@pytest.fixture
def shell(tmp_path: Path):
    registry = ModuleRegistry(
        registry_path=tmp_path / "config" / "module-registry.json",
        state_path=tmp_path / "state" / "module-registry.state.json",
    )
    clients: list[FakeClient] = []

    def factory(command, **kwargs):
        client = FakeClient()
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
        )
    runtime.close()


def csrf(shell) -> str:
    token = shell.client.cookies.get("solocorp_csrf")
    if not token:
        # Same path a browser takes: load a page, then submit its form.
        shell.client.get("/modules")
        token = shell.client.cookies.get("solocorp_csrf")
    assert token, "the loopback boundary must issue a CSRF cookie"
    return token


def module_state(shell, module_id: str) -> dict:
    modules = shell.client.get("/api/modules").json()["modules"]
    return next(module for module in modules if module["id"] == module_id)


def read_config(shell) -> dict:
    return json.loads(shell.registry.path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------- pages


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        ("/chat", "Phase 2"),
        ("/modules", "Modules"),
        ("/tasks", "Task History"),
        ("/settings", "Configure provider"),
    ],
)
def test_phase1_pages_render(shell, path, marker):
    response = shell.client.get(path)

    assert response.status_code == 200
    assert marker in response.text
    assert response.headers["content-security-policy"].startswith("default-src 'self'")


def test_root_redirects_to_chat(shell):
    response = shell.client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/chat"


def test_modules_page_lists_declared_capabilities(shell):
    html = shell.client.get("/modules").text

    assert "content-creator" in html
    assert "Content Creator" in html
    assert "Create department" not in html
    # FR-01: declared capabilities and version are visible, not hidden behind
    # a vendor name.
    module = module_state(shell, "content-creator")
    assert module["capabilities"] == ["tools", "resources"]
    assert module["version"] == "0.1.0"


def test_modules_page_counts_are_rendered_and_refreshable(shell):
    shell.registry.update("content-creator", "disabled")

    html = shell.client.get("/modules").text

    # Server-rendered truth first...
    assert 'data-count="enabled">4 enabled' in html
    assert 'data-count="connected">0 connected' in html
    # ...and the hooks the poller rewrites, so a connected card can never sit
    # next to a stale "0 connected" chip (the page contradicting itself reads
    # as a status bug, PRD §9).
    for key in ("total", "enabled", "connected", "error"):
        assert f'data-count="{key}"' in html


def test_forms_carry_a_usable_token_on_first_load(shell):
    html = shell.client.get("/modules").text

    assert 'name="csrf_token"' in html
    assert f'value="{csrf(shell)}"' in html


# --------------------------------------------------------------------- toggle


def test_disable_writes_intent_and_clears_observation(shell):
    shell.host.connect("content-creator")
    assert module_state(shell, "content-creator")["status_text"] == "connected"

    response = shell.client.post(
        "/modules/content-creator/toggle",
        data={"csrf_token": csrf(shell)},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "notice=module-disabled" in response.headers["location"]
    assert read_config(shell)["content-creator"]["status"] == "disabled"
    assert module_state(shell, "content-creator")["enabled"] is False
    assert module_state(shell, "content-creator")["observation"] is None
    assert module_state(shell, "content-creator")["status_text"] == "disabled"
    assert shell.registry.status()["stale_state"] == []


def test_enable_connects_the_module_and_keeps_observation_out_of_config(shell):
    shell.registry.update("content-creator", "disabled")
    before = read_config(shell)["content-creator"]

    response = shell.client.post(
        "/modules/content-creator/toggle",
        data={"csrf_token": csrf(shell)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "notice=module-enabled" in response.headers["location"]

    assert wait_for(
        lambda: module_state(shell, "content-creator")["observation"] == "connected"
    )

    after = read_config(shell)["content-creator"]
    assert after["status"] == "enabled"
    assert before["command"] == after["command"]
    for field in RUNTIME_ONLY_FIELDS:
        assert field not in after

    observation = shell.client.get("/api/modules").json()["modules"]
    entry = next(m for m in observation if m["id"] == "content-creator")
    assert entry["status_text"] == "connected"
    assert entry["response_time_ms"] is not None


def test_toggle_twice_returns_to_the_original_intent(shell):
    shell.registry.update("content-creator", "disabled")
    original = shell.registry.path.read_bytes()
    token = csrf(shell)

    shell.client.post("/modules/content-creator/toggle", data={"csrf_token": token})
    assert read_config(shell)["content-creator"]["status"] == "enabled"

    shell.client.post("/modules/content-creator/toggle", data={"csrf_token": token})
    config = read_config(shell)["content-creator"]
    assert config["status"] == "disabled"
    assert config["command"] == json.loads(original)["content-creator"]["command"]


def test_toggle_rejects_an_unknown_module_with_a_notice(shell):
    response = shell.client.post(
        "/modules/not-a-module/toggle",
        data={"csrf_token": csrf(shell)},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "notice=module-unknown" in response.headers["location"]
    assert set(read_config(shell)) == {
        "solocorp",
        "central-bus",
        "content-creator",
        "engineering",
        "qa",
        "_meta",
    }


def test_toggle_rejects_a_traversal_style_module_id(shell):
    response = shell.client.post(
        "/modules/..%2F..%2Fetc/toggle",
        data={"csrf_token": csrf(shell)},
        follow_redirects=False,
    )

    assert response.status_code in (303, 404)
    if response.status_code == 303:
        assert "notice=module-unknown" in response.headers["location"]
    assert shell.registry.path.exists()


# --------------------------------------------------------------------- health


def test_check_health_on_disabled_module_is_a_no_op(shell):
    shell.registry.update("content-creator", "disabled")

    response = shell.client.post(
        "/modules/content-creator/check",
        data={"csrf_token": csrf(shell)},
        follow_redirects=False,
    )

    assert response.status_code == 303
    state_path = shell.registry.state_path
    assert not state_path.exists() or "content-creator" not in json.loads(
        state_path.read_text(encoding="utf-8")
    )


def test_check_health_connects_an_enabled_idle_module(shell):
    shell.registry.update("content-creator", "enabled")

    response = shell.client.post(
        "/modules/content-creator/check",
        data={"csrf_token": csrf(shell)},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert wait_for(lambda: len(shell.clients) == 1)
    assert wait_for(
        lambda: module_state(shell, "content-creator")["observation"] == "connected"
    )


def test_check_all_probes_only_live_connections(shell):
    shell.host.connect("qa")
    shell.clients[0].fail = True

    response = shell.client.post(
        "/modules/check-all",
        data={"csrf_token": csrf(shell)},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert module_state(shell, "qa")["status_text"] == "error"
    assert "module process exited" in (module_state(shell, "qa")["last_error"] or "")


# ------------------------------------------------------------------- api/health


def test_api_modules_returns_one_view_per_declared_module(shell):
    payload = shell.client.get("/api/modules").json()

    assert set(payload) == {"modules", "counts", "registry"}
    assert payload["counts"]["total"] == 5
    assert payload["counts"]["enabled"] == 5
    assert payload["registry"]["valid"] is True
    module = payload["modules"][0]
    assert {
        "id",
        "name",
        "version",
        "capabilities",
        "dependencies",
        "permissions",
        "intent",
        "observation",
        "status_text",
        "last_error",
    } <= set(module)


def test_healthz_reports_registry_and_provider_state(shell):
    payload = shell.client.get("/healthz").json()

    assert payload["status"] == "ok"
    assert payload["registry_valid"] is True
    assert payload["provider_state"] == "unconfigured"
    assert payload["modules"]["total"] == 5


# ---------------------------------------------------------------------- tasks


def test_tasks_page_renders_the_task_envelope(shell):
    record = shell.tracker.create(
        dept="content", module="content-creator", brief="secret brief text"
    )
    shell.tracker.update_status(record["task_id"], "failed", error_detail="no module")

    response = shell.client.get("/tasks")

    assert response.status_code == 200
    assert record["task_id"] in response.text
    assert "no module" in response.text
    # The brief stays out of the list view (TaskTracker default).
    assert "secret brief text" not in response.text


def test_tasks_page_is_empty_without_records(shell):
    response = shell.client.get("/tasks")

    assert response.status_code == 200
    assert "No tasks yet" in response.text


# ------------------------------------------------------- stale observations


def test_start_clears_observations_left_by_a_previous_process(tmp_path: Path):
    """A ``connected`` entry from an earlier run must not be shown as live.

    Incident from the first live run (2026-11-12): the state file still held
    ``qa: connected`` from 2026-11-02 and the Modules page reported a
    connection that did not exist. The poller only re-probes connections this
    host owns, so the lie would have persisted for the whole session.
    """

    registry = ModuleRegistry(
        registry_path=tmp_path / "config" / "module-registry.json",
        state_path=tmp_path / "state" / "module-registry.state.json",
    )
    registry.state_path.parent.mkdir(parents=True, exist_ok=True)
    registry.state_path.write_text(
        json.dumps(
            {
                "qa": {
                    "status": "connected",
                    "last_checked": "2026-11-02T03:59:09.498370+00:00",
                    "response_time_ms": 1338.36,
                    "last_error": None,
                },
                "_meta": {"total_modules": 1, "schema_version": 2},
            }
        ),
        encoding="utf-8",
    )
    runtime = AppRuntime(
        registry=registry,
        host=ModuleHost(
            registry, client_factory=lambda *a, **k: FakeClient(), cwd=tmp_path
        ),
        provider=ProviderStore(
            config_path=tmp_path / "config" / "provider.json",
            credentials_path=tmp_path / "config" / "provider.credentials.json",
            env={},
        ),
        tracker=TaskTracker(tmp_path / "tasks"),
        health_interval=0,
    )

    with TestClient(create_app(runtime), base_url=BASE_URL) as client:
        modules = client.get("/api/modules").json()["modules"]

    qa = next(module for module in modules if module["id"] == "qa")
    assert qa["observation"] is None
    assert qa["status_text"] == "enabled"
    assert qa["last_error"] is None
    assert "qa" not in json.loads(registry.state_path.read_text(encoding="utf-8"))
    runtime.close()


# ------------------------------------------- clear-credential regressions (QA)
#
# BUG-1: corrupt provider.json + POST clear → 500 (unhandled ProviderError).
# BUG-2: clear with nothing stored → 303 provider-cleared (lie).


def test_clear_credential_with_corrupt_config_is_structured_not_500(shell):
    """BUG-1: a corrupt config must yield 400 + error, never a bare 500."""

    shell.provider.config_path.parent.mkdir(parents=True, exist_ok=True)
    shell.provider.config_path.write_text("{ this is not json ", encoding="utf-8")

    # The GET page still renders the failed state (200), per PRD §9.
    assert shell.client.get("/settings").status_code == 200

    response = shell.client.post(
        "/settings/provider/clear-credential",
        data={"csrf_token": csrf(shell)},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "not valid JSON" in response.text


def test_clear_credential_with_nothing_stored_reports_noop(shell):
    """BUG-2: no credential stored must not claim "removed"."""

    assert shell.provider.clear_credential() is False  # precondition: empty

    response = shell.client.post(
        "/settings/provider/clear-credential",
        data={"csrf_token": csrf(shell)},
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = response.headers["location"]
    assert "notice=provider-nothing" in location
    assert "notice=provider-cleared" not in location


def test_clear_credential_reports_cleared_only_when_removed(shell):
    shell.provider.save(provider="openai", model="gpt-test", api_key="sk-live-key")

    response = shell.client.post(
        "/settings/provider/clear-credential",
        data={"csrf_token": csrf(shell)},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "notice=provider-cleared" in response.headers["location"]

    follow = shell.client.post(
        "/settings/provider/clear-credential",
        data={"csrf_token": csrf(shell)},
        follow_redirects=False,
    )
    assert "notice=provider-nothing" in follow.headers["location"]
