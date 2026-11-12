"""Loopback boundary, CSRF and the fail-fast entry point.

The app has no login (single local user), so these guards are the whole
exposure control: loopback bind, Host allowlist, CSRF token (design note §7).
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from axis_mcp.module_host import ModuleHost
from axis_mcp.module_registry import ModuleRegistry
from axis_mcp.task_tracking import TaskTracker
from solocorp_app.__main__ import (
    EXIT_BAD_CONFIG,
    EXIT_PORT_UNAVAILABLE,
    PortUnavailableError,
    bind_socket,
    main,
    resolve_binding,
)
from solocorp_app.app import create_app
from solocorp_app.provider import ProviderStore
from solocorp_app.runtime import AppRuntime
from solocorp_app.security import host_is_loopback, origin_matches, split_host

BASE_URL = "http://127.0.0.1:8766"


@pytest.fixture
def runtime(tmp_path: Path) -> AppRuntime:
    registry = ModuleRegistry(
        registry_path=tmp_path / "config" / "module-registry.json",
        state_path=tmp_path / "state" / "module-registry.state.json",
    )
    host = ModuleHost(registry, client_factory=lambda *a, **k: None, cwd=tmp_path)
    provider = ProviderStore(
        config_path=tmp_path / "config" / "provider.json",
        credentials_path=tmp_path / "config" / "provider.credentials.json",
        env={},
    )
    instance = AppRuntime(
        registry=registry,
        host=host,
        provider=provider,
        tracker=TaskTracker(tmp_path / "tasks"),
        health_interval=0,
    )
    yield instance
    instance.close()


# --------------------------------------------------------------------- unit


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("127.0.0.1:8766", True),
        ("127.0.0.1", True),
        ("localhost:8766", True),
        ("LOCALHOST", True),
        ("[::1]:8766", True),
        ("::1", True),
        ("example.com", False),
        ("127.0.0.1.evil.test", False),
        ("0.0.0.0:8766", False),
        ("", False),
        (None, False),
    ],
)
def test_host_is_loopback(header, expected):
    assert host_is_loopback(header) is expected


def test_split_host_handles_ipv6_and_ports():
    assert split_host("[::1]:8766") == ("::1", "8766")
    assert split_host("127.0.0.1:8766") == ("127.0.0.1", "8766")
    assert split_host("localhost") == ("localhost", None)
    assert split_host("[::1") == ("", None)


@pytest.mark.parametrize(
    ("origin", "host", "expected"),
    [
        (None, "127.0.0.1:8766", True),
        ("http://127.0.0.1:8766", "127.0.0.1:8766", True),
        ("https://127.0.0.1:8766", "127.0.0.1:8766", True),
        ("http://evil.test", "127.0.0.1:8766", False),
        ("file:///etc/passwd", "127.0.0.1:8766", False),
        ("", "127.0.0.1:8766", True),
    ],
)
def test_origin_matches(origin, host, expected):
    assert origin_matches(origin, host) is expected


@pytest.mark.parametrize(
    ("sec_fetch_site", "expected"),
    [
        ("same-origin", True),
        ("same-site", False),
        ("cross-site", False),
        ("none", False),
        (None, False),
    ],
)
def test_opaque_origin_needs_a_same_origin_assertion(sec_fetch_site, expected):
    assert origin_matches("null", "127.0.0.1:8766", sec_fetch_site) is expected


def test_a_real_origin_still_wins_over_a_same_origin_claim():
    assert origin_matches("http://evil.test", "127.0.0.1:8766", "same-origin") is False


# ------------------------------------------------------------------ boundary


def test_non_loopback_host_is_refused(runtime):
    app = create_app(runtime)
    with TestClient(app, base_url="http://evil.example") as client:
        response = client.get("/modules")

    assert response.status_code == 400
    assert "loopback" in response.json()["detail"].lower()


def test_cross_origin_mutation_is_refused(runtime):
    app = create_app(runtime)
    with TestClient(app, base_url=BASE_URL) as client:
        token = client.cookies.get("solocorp_csrf")
        response = client.post(
            "/modules/content-creator/toggle",
            data={"csrf_token": token},
            headers={"Origin": "http://evil.example"},
        )

    assert response.status_code == 403
    assert "cross-origin" in response.json()["detail"]


def test_mutation_without_a_csrf_token_is_refused(runtime):
    app = create_app(runtime)
    with TestClient(app, base_url=BASE_URL) as client:
        client.get("/modules")
        response = client.post("/modules/content-creator/toggle")

    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]
    assert runtime.registry.module_config("content-creator")["status"] == "enabled"


def test_desktop_browser_opaque_origin_form_post_is_accepted(runtime):
    """Regression: OpenCode desktop (Electron) sends ``Origin: null``.

    Verified live on 2026-11-12 — the same-origin form POST carried
    ``origin: null`` with ``sec-fetch-site: same-origin``, and a strict
    "null is not loopback" rule made every UI toggle fail with 403.
    """

    app = create_app(runtime)
    with TestClient(app, base_url=BASE_URL) as client:
        client.get("/modules")
        token = client.cookies.get("solocorp_csrf")
        response = client.post(
            "/modules/content-creator/toggle",
            data={"csrf_token": token},
            headers={"Origin": "null", "Sec-Fetch-Site": "same-origin"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert runtime.registry.module_config("content-creator")["status"] == "disabled"


def test_opaque_origin_from_a_cross_site_request_is_still_refused(runtime):
    app = create_app(runtime)
    with TestClient(app, base_url=BASE_URL) as client:
        client.get("/modules")
        token = client.cookies.get("solocorp_csrf")
        response = client.post(
            "/modules/content-creator/toggle",
            data={"csrf_token": token},
            headers={"Origin": "null", "Sec-Fetch-Site": "cross-site"},
        )

    assert response.status_code == 403
    assert runtime.registry.module_config("content-creator")["status"] == "enabled"


def test_mutation_with_a_wrong_csrf_token_is_refused(runtime):
    app = create_app(runtime)
    with TestClient(app, base_url=BASE_URL) as client:
        client.get("/modules")
        response = client.post(
            "/modules/content-creator/toggle", data={"csrf_token": "not-the-token"}
        )

    assert response.status_code == 403


def test_csrf_header_works_for_a_scripted_client(runtime):
    app = create_app(runtime)
    with TestClient(app, base_url=BASE_URL) as client:
        client.get("/modules")
        token = client.cookies.get("solocorp_csrf")
        response = client.post(
            "/modules/qa/toggle",
            headers={"X-CSRF-Token": token},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert runtime.registry.module_config("qa")["status"] == "disabled"


def test_csrf_cookie_is_http_only_and_same_site(runtime):
    app = create_app(runtime)
    with TestClient(app, base_url=BASE_URL) as client:
        response = client.get("/chat")

    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=strict" in set_cookie


def test_security_headers_are_present(runtime):
    app = create_app(runtime)
    with TestClient(app, base_url=BASE_URL) as client:
        response = client.get("/modules")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


# ----------------------------------------------------------------- entrypoint


def test_resolve_binding_defaults_to_loopback_8766():
    assert resolve_binding(env={}, argv=[]) == ("127.0.0.1", 8766)


def test_resolve_binding_honours_environment_and_arguments():
    assert resolve_binding(env={"SOLOCORP_APP_PORT": "9000"}, argv=[]) == (
        "127.0.0.1",
        9000,
    )
    assert resolve_binding(env={}, argv=["--port", "9100"]) == ("127.0.0.1", 9100)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "example.com"])
def test_resolve_binding_refuses_non_loopback(host, capsys):
    with pytest.raises(ValueError, match="loopback-only"):
        resolve_binding(env={"SOLOCORP_APP_HOST": host}, argv=[])

    exit_code = main(["--host", host])
    assert exit_code == EXIT_BAD_CONFIG
    assert "loopback-only" in capsys.readouterr().err


@pytest.mark.parametrize("port", ["not-a-port", "0", "70000"])
def test_resolve_binding_rejects_bad_ports(port):
    with pytest.raises(ValueError):
        resolve_binding(env={"SOLOCORP_APP_PORT": port}, argv=[])


def test_bind_socket_fails_fast_when_the_port_is_taken():
    taken = bind_socket("127.0.0.1", 0)
    try:
        port = taken.getsockname()[1]
        taken.listen(1)
        with pytest.raises(PortUnavailableError, match="cannot bind"):
            bind_socket("127.0.0.1", port)

        exit_code = main(["--port", str(port)])
        assert exit_code == EXIT_PORT_UNAVAILABLE
    finally:
        taken.close()


def test_bind_socket_returns_a_bound_socket():
    sock = bind_socket("127.0.0.1", 0)
    try:
        assert isinstance(sock, socket.socket)
        host, port = sock.getsockname()[:2]
        assert host == "127.0.0.1"
        assert port > 0
    finally:
        sock.close()
