"""Live dashboard PR2.1 hardening: /live + /api/live/status only.

Fail-open ทุก endpoint: ไม่มี opencode CLI / ไม่มี queue ไฟล์
ก็ต้องตอบ 200 ด้วย payload ว่าง — ห้าม 500 (PRD §9).

PR2.1 contract (D1-D7):
- 2 routes เท่านั้น: GET /live + GET /api/live/status
  (/api/sessions + /api/bus/queue ตัดออกจาก router — D6)
- sessions = CLI อย่างเดียว ไม่มี DB fallback (D3)
- cache: sessions 15s / queue 5s + cache_hit + single-flight (D1/D2)
- queue cap 50k lines / 8MB + skip *.offset + archive/ (D5)
- tasks_summary (app-tasks) แยกจาก queue_total (bus-queue) + ป้าย source คู่ (D4)
- live.js แยกไฟล์ + visibility/backoff, app.js frozen ไม่แตะ (D7)
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
from solocorp_app import live as live_module
from solocorp_app.app import create_app
from solocorp_app.live import (
    CLI_TIMEOUT_S,
    MAX_BYTES_PER_FILE,
    MAX_LINES_PER_FILE,
    TTL_QUEUE_S,
    TTL_SESSIONS_S,
    list_sessions,
    normalize_session,
    queue_depths,
)
from solocorp_app.provider import ProviderStore
from solocorp_app.runtime import AppRuntime

BASE_URL = "http://127.0.0.1:8766"
DENY_KEYS = {"api_key", "api_key_ref", "brief", "credential", "secret"}


class FakeClient:
    def request(self, method, params, *, timeout):
        return {"tools": []}

    def close(self) -> None:
        pass


@pytest.fixture
def shell(tmp_path: Path):
    live_module.clear_live_cache()
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
    live_module.clear_live_cache()


def _payload_keys(payload: object) -> set[str]:
    found: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(key, str):
                    found.add(key)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


# ------------------------------------------------------------------ pages/APIs


def test_live_page_renders_without_sessions(shell):
    response = shell.client.get("/live")

    assert response.status_code == 200
    assert "Live Dashboard" in response.text
    assert "data-live" in response.text
    assert "/api/live/status" in response.text
    assert "3s" in response.text or "3 วินาที" in response.text
    # D4: ป้าย source คู่ + D7: live.js แยกไฟล์
    assert "bus-queue" in response.text
    assert "app-tasks" in response.text
    assert "/static/live.js" in response.text
    assert "Task History" in response.text


def test_api_live_status_matches_pr21_contract(shell):
    response = shell.client.get("/api/live/status")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) >= {
        "sessions",
        "session_count",
        "session_source",
        "queues",
        "queue_total",
        "queue_source",
        "tasks_summary",
        "tasks_source",
        "modules",
        "provider_state",
        "registry_valid",
        "cache_hit",
        "updated_at",
    }
    assert payload["session_source"] in ("cli", "none")
    assert payload["queue_source"] == "bus-queue"
    assert payload["tasks_source"] == "app-tasks"
    assert set(payload["tasks_summary"]) == {
        "pending",
        "running",
        "completed",
        "failed",
        "total",
    }
    assert isinstance(payload["cache_hit"], bool)
    assert payload["modules"]["total"] == 5
    assert payload["provider_state"] in (
        "configured",
        "unconfigured",
        "failed",
        "unknown",
    )
    assert isinstance(payload["module_states"], list)


def test_pr21_only_two_live_routes(shell):
    assert shell.client.get("/api/live/status").status_code == 200
    assert shell.client.get("/live").status_code == 200
    # D6: ตัดออกจาก router — ต้อง 404 ไม่ใช่ 200
    assert shell.client.get("/api/sessions").status_code == 404
    assert shell.client.get("/api/bus/queue").status_code == 404


def test_live_endpoints_need_no_csrf_and_have_security_headers(shell):
    for path in ("/live", "/api/live/status"):
        response = shell.client.get(path)
        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"
    api = shell.client.get("/api/live/status")
    assert "max-age=3" in api.headers.get("cache-control", "")


def test_nav_includes_live(shell):
    html = shell.client.get("/modules").text
    assert 'href="/live"' in html


def test_live_payload_has_no_secrets(shell):
    payload = shell.client.get("/api/live/status").json()
    keys = _payload_keys(payload)
    leaked = DENY_KEYS & {k.lower() for k in keys}
    assert not leaked, f"secret keys leaked in live payload: {leaked}"
    for session in payload["sessions"]:
        assert set(session) <= {
            "id",
            "title",
            "agent",
            "model",
            "tokens",
            "outcome",
            "time",
        }


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


def test_cli_timeout_is_shorter_than_poll_interval():
    assert CLI_TIMEOUT_S == 1.5
    assert CLI_TIMEOUT_S < 3.0


def test_cache_ttls_are_15s_and_5s():
    assert TTL_SESSIONS_S == 15.0
    assert TTL_QUEUE_S == 5.0


def test_no_db_fallback_in_live_module():
    import solocorp_app.live as mod

    assert not hasattr(mod, "_sessions_from_db"), "D3: _sessions_from_db must be gone"
    assert not hasattr(mod, "DEFAULT_OPENCODE_DB"), "D3: DEFAULT_OPENCODE_DB gone"
    assert "sqlite3" not in dir(mod) or mod.__dict__.get("sqlite3") is None


def test_list_sessions_with_fake_cli(tmp_path: Path):
    live_module.clear_live_cache()
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
    live_module.clear_live_cache()
    envelope = list_sessions(10, queue_cli=["/nonexistent-opencode-cli-xyz"])
    assert envelope["source"] == "none"
    assert envelope["sessions"] == []
    assert envelope["error"]


def test_list_sessions_never_returns_db_source(tmp_path: Path):
    live_module.clear_live_cache()
    envelope = list_sessions(10, queue_cli=["/nonexistent-opencode-cli-xyz"])
    assert envelope["source"] != "db"


def test_sessions_cache_hit_second_poll_spawns_cli_once(tmp_path: Path, monkeypatch):
    live_module.clear_live_cache()
    calls = {"n": 0}

    def fake_cli(limit: int, *, command=None):
        calls["n"] += 1
        return ([{"id": "s1", "title": "t"}], None)

    monkeypatch.setattr(live_module, "_sessions_from_cli", fake_cli)
    first = list_sessions(10)
    second = list_sessions(10)
    assert first["source"] == "cli"
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["sessions"] == first["sessions"]
    assert calls["n"] == 1


def test_queue_depths_counts_jsonl_lines(tmp_path: Path):
    live_module.clear_live_cache()
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    (queue_dir / "high.jsonl").write_text('{"a": 1}\n{"a": 2}\n', encoding="utf-8")
    (queue_dir / "normal.jsonl").write_text('{"b": 1}\n', encoding="utf-8")

    envelope = queue_depths(queue_dir=queue_dir)
    assert envelope["queues"]["high"] == 2
    assert envelope["queues"]["normal"] == 1
    assert envelope["total"] >= 3
    assert envelope["queue_source"] == "bus-queue"


def test_queue_depths_skips_offset_and_archive(tmp_path: Path):
    live_module.clear_live_cache()
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    (queue_dir / "high.jsonl").write_text('{"a": 1}\n', encoding="utf-8")
    # ไฟล์ offset / archive ต้องไม่ถูกนับ (D5)
    (queue_dir / "high.jsonl.offset").write_text('{"a": 99}\n', encoding="utf-8")
    archive = queue_dir / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "high.jsonl").write_text('{"a": 100}\n' * 10, encoding="utf-8")

    envelope = queue_depths(queue_dir=queue_dir)
    assert envelope["queues"]["high"] == 1


def test_queue_depths_respects_line_cap(tmp_path: Path, monkeypatch):
    live_module.clear_live_cache()
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    (queue_dir / "normal.jsonl").write_text('{"b": 1}\n' * 10, encoding="utf-8")
    monkeypatch.setattr(live_module, "MAX_LINES_PER_FILE", 3)

    envelope = queue_depths(queue_dir=queue_dir)
    assert envelope["queues"]["normal"] == 3


def test_queue_caps_are_50k_and_8mb():
    assert MAX_LINES_PER_FILE == 50_000
    assert MAX_BYTES_PER_FILE == 8_000_000


def test_queue_depths_missing_dir_is_zero(tmp_path: Path):
    live_module.clear_live_cache()
    envelope = queue_depths(queue_dir=tmp_path / "no-such-queue")
    assert envelope["total"] == 0
    assert envelope["queues"]["high"] == 0


def test_tasks_summary_is_separate_from_queue_total(shell):
    record = shell.runtime.tracker.create(
        dept="content", module="content-creator", brief="secret brief text"
    )
    shell.runtime.tracker.update_status(
        record["task_id"], "failed", error_detail="nope"
    )

    payload = shell.client.get("/api/live/status").json()
    summary = payload["tasks_summary"]
    assert summary["total"] >= 1
    assert summary["failed"] >= 1
    # tasks_summary มาจาก TaskTracker — brief ต้องไม่รั่วผ่าน live
    assert "secret brief text" not in json.dumps(payload)
    # queue_total มาจาก bus/queue — คนละมิติ คนละตัวเลข (D4 split-brain ปิด)
    assert isinstance(payload["queue_total"], int)
