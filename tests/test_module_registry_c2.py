"""C2 registry schema tests: manifest fields, permissions, version gate.

Red-first: this file was written before the implementation. Every test below
failed first with the reason noted in its group header (missing symbol, or a
behaviour the old code did not have).

Coverage map (CMD-006 decision note §5 and exit criteria F1–F10):

* F1  — a v1 config (no ``_meta`` / ``_meta.schema_version = 1``) loads on v2
* F2  — a newer config raises ``RegistryDowngradeError`` / ``error_kind``
* F3  — the ``permissions`` enum (pass / unknown / duplicate / not a list /
        absent / empty list / order)
* F4  — ``VALID_PERMISSION_LEVELS`` is the ``auth.SCOPE_LEVELS`` vocabulary
* F5  — FR-07: importing a department MCP writes no config, calling its tool
        without ``SOLOCORP_API_KEY`` works, and a host call succeeds
* F6  — the department ``module_registry_status`` tool is public
* F7  — ``DEFAULT_MODULES`` and the tracked config validate
* F10 — C1 read contracts are preserved (status 15 keys, validate 5 + kind)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from solocorp_mcp import module_registry
from solocorp_mcp.auth import SCOPE_LEVELS
from solocorp_mcp.module_host import ModuleHost
from solocorp_mcp.module_registry import ModuleRegistry
from solocorp_mcp.module_registry_schema import (
    INFRA_DEPENDENCIES,
    SCHEMA_VERSION,
    TRANSPORT_ENTRY_FIELDS,
    VALID_PERMISSION_LEVELS,
    RegistryDowngradeError,
    RegistrySchemaError,
    load_and_validate_config,
    validate_config,
    validate_meta,
)

ROOT = Path(__file__).resolve().parent.parent
REPAIR_SCRIPT = ROOT / "scripts" / "registry-repair.py"

MANIFEST_FIELDS = frozenset(
    {"name", "version", "capabilities", "dependencies", "permissions", "entry_repo"}
)


# ── helpers ───────────────────────────────────────────────────────────


def _entry(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "status": "enabled",
        "transport": "stdio",
        "command": ["/bin/echo", "hello"],
        "name": "QA",
        "version": "0.1.0",
        "capabilities": ["tools"],
        "dependencies": [],
        "permissions": ["public"],
        "entry_repo": "internal",
        "description": "QA Department",
    }
    entry.update(overrides)
    return entry


def _config(entry: dict[str, Any] | None = None, module_id: str = "qa") -> dict[str, Any]:
    return {module_id: entry if entry is not None else _entry()}


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _newer_version() -> int:
    return SCHEMA_VERSION + 1


@pytest.fixture()
def registry(tmp_path: Path) -> ModuleRegistry:
    return ModuleRegistry(
        registry_path=tmp_path / "config" / "module-registry.json",
        state_path=tmp_path / "state" / "module-registry.state.json",
    )


@pytest.fixture()
def config_path(tmp_path: Path) -> Path:
    return tmp_path / "config" / "module-registry.json"


# ── F1: newer code reads older config ─────────────────────────────────


def test_v1_config_without_meta_loads(config_path: Path) -> None:
    _write(
        config_path,
        {
            "qa": {
                "status": "enabled",
                "transport": "stdio",
                "command": ["/bin/echo"],
                "description": "legacy",
            }
        },
    )

    loaded = load_and_validate_config(config_path)

    assert loaded["qa"]["description"] == "legacy"
    assert "permissions" not in loaded["qa"]


def test_v1_config_with_declared_version_1_loads(config_path: Path) -> None:
    document = {**_config(), "_meta": {"schema_version": 1, "total_modules": 1}}
    _write(config_path, document)

    loaded = load_and_validate_config(config_path)

    assert set(loaded) == {"qa", "_meta"}


def test_registry_reads_v1_config_then_writes_current_version(
    config_path: Path, tmp_path: Path
) -> None:
    _write(
        config_path,
        {
            "qa": {
                "status": "enabled",
                "transport": "stdio",
                "command": ["/bin/echo"],
                "description": "legacy",
            }
        },
    )
    registry = ModuleRegistry(
        registry_path=config_path,
        state_path=tmp_path / "state" / "module-registry.state.json",
    )

    assert registry.validate()["valid"] is True

    registry.update("qa", "disabled")
    saved = _read(config_path)

    assert saved["_meta"]["schema_version"] == SCHEMA_VERSION
    assert saved["qa"]["status"] == "disabled"
    assert saved["qa"]["description"] == "legacy"
    # v2 never invents manifest values the human did not declare.
    assert "permissions" not in saved["qa"]


# ── F2: older code refuses newer config, and says why ────────────────


def test_newer_schema_raises_downgrade_error(config_path: Path) -> None:
    _write(config_path, {**_config(), "_meta": {"schema_version": _newer_version()}})

    with pytest.raises(RegistryDowngradeError) as excinfo:
        load_and_validate_config(config_path)

    # Classified, not a raw ValueError: callers can tell this apart.
    assert isinstance(excinfo.value, RegistrySchemaError)
    message = str(excinfo.value)
    assert "schema_version" in message
    assert "rollback" in message.lower()


def test_validate_meta_never_raises_on_newer_schema() -> None:
    errors = validate_meta({"schema_version": _newer_version()}, "config")

    assert errors
    assert "schema_version" in errors[0]


def test_downgrade_is_detected_before_field_validation(config_path: Path) -> None:
    # The version gate must run first, otherwise a user sees a pile of
    # "unknown field" noise instead of one actionable sentence (§1.8).
    document = {**_config(_entry(permissions=["public"])), "_meta": {"schema_version": _newer_version()}}
    _write(config_path, document)

    with pytest.raises(RegistryDowngradeError) as excinfo:
        load_and_validate_config(config_path)

    assert "unknown field" not in str(excinfo.value)


def test_status_and_validate_classify_downgrade(
    config_path: Path, tmp_path: Path
) -> None:
    _write(config_path, {**_config(), "_meta": {"schema_version": _newer_version()}})
    registry = ModuleRegistry(
        registry_path=config_path,
        state_path=tmp_path / "state" / "module-registry.state.json",
    )

    status = registry.status()
    assert status["valid"] is False
    assert status["error_kind"] == "downgrade"
    assert any("schema_version" in error for error in status["errors"])

    result = registry.validate()
    assert result["valid"] is False
    assert result["error_kind"] == "downgrade"


def test_error_kind_covers_valid_corrupt_invalid_and_missing(
    registry: ModuleRegistry,
) -> None:
    assert registry.status()["valid"] is True
    assert registry.status()["error_kind"] is None
    assert registry.validate()["error_kind"] is None

    config_path = Path(registry.path)
    config_path.write_text("{not json", encoding="utf-8")
    assert registry.status()["error_kind"] == "corrupt"
    assert registry.validate()["error_kind"] == "corrupt"

    _write(config_path, {"qa": {"status": "banana"}})
    assert registry.status()["error_kind"] == "invalid"
    assert registry.validate()["error_kind"] == "invalid"

    config_path.unlink()
    assert registry.status()["error_kind"] == "invalid"
    assert registry.validate()["error_kind"] == "invalid"


def test_status_never_raises_on_unhashable_enum_values(
    registry: ModuleRegistry,
) -> None:
    config_path = Path(registry.path)
    document = _read(config_path)
    document["qa"]["transport"] = ["stdio"]
    document["qa"]["status"] = {"value": "enabled"}
    _write(config_path, document)

    status = registry.status()

    assert status["valid"] is False
    assert status["error_kind"] == "invalid"
    assert status["modules"] == {}

    state_path = Path(registry.state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    _write(config_path, {**_config(), "_meta": {"schema_version": SCHEMA_VERSION}})
    state_path.write_text(
        json.dumps(
            {
                "qa": {
                    "status": ["connected"],
                    "last_checked": "2026-11-06T00:00:00+00:00",
                }
            }
        ),
        encoding="utf-8",
    )

    tolerant = registry.status()
    assert tolerant["valid"] is True
    assert tolerant["state_error"] is not None


def test_newer_state_meta_is_ignored_and_rewritten_by_the_next_heartbeat(
    registry: ModuleRegistry,
) -> None:
    # State is derived data (CMD-006 §2.4 D2-6): the read path validates the
    # *entries*, not the state's own `_meta`, so a newer state file never turns
    # into a config error and needs no manual step. The next heartbeat stamps
    # the running build's version.
    state_path = Path(registry.state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "_meta": {"schema_version": _newer_version()},
                "qa": {
                    "status": "connected",
                    "last_checked": "2026-11-06T00:00:00+00:00",
                },
            }
        ),
        encoding="utf-8",
    )

    status = registry.status()
    assert status["valid"] is True
    assert status["error_kind"] is None
    assert status["state_error"] is None
    assert status["modules"]["qa"]["status"] == "connected"

    registry.record_runtime_state("qa", "connected")

    assert _read(state_path)["_meta"]["schema_version"] == SCHEMA_VERSION


def test_unknown_state_entry_field_quarantines_state_but_not_config(
    registry: ModuleRegistry,
) -> None:
    state_path = Path(registry.state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "qa": {
                    "status": "connected",
                    "last_checked": "2026-11-06T00:00:00+00:00",
                    "observed_version": "0.2.0",  # field this build does not know
                }
            }
        ),
        encoding="utf-8",
    )

    status = registry.status()

    assert status["valid"] is True
    assert status["error_kind"] is None
    assert status["state_error"] is not None
    assert any("unknown field" in warning for warning in status["warnings"])


# ── F3: permissions enum ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "permissions",
    [["public"], ["public", "team"], ["admin", "public", "team"], []],
)
def test_permissions_accept_declared_levels(permissions: list[str]) -> None:
    assert validate_config(_config(_entry(permissions=permissions))) == []


def test_permissions_absent_is_allowed() -> None:
    entry = _entry()
    del entry["permissions"]

    assert validate_config(_config(entry)) == []


def test_permissions_unknown_level_is_error() -> None:
    errors = validate_config(_config(_entry(permissions=["public", "internal"])))

    assert any("permissions" in error and "internal" in error for error in errors)


def test_permissions_duplicate_is_error() -> None:
    errors = validate_config(_config(_entry(permissions=["public", "public"])))

    assert any("duplicate" in error for error in errors)


def test_permissions_must_be_a_list() -> None:
    errors = validate_config(_config(_entry(permissions="team")))

    assert any("permissions" in error and "list" in error for error in errors)


def test_permissions_items_must_be_strings() -> None:
    errors = validate_config(_config(_entry(permissions=["public", 2])))

    assert any("permissions" in error and "list" in error for error in errors)


def test_permissions_order_is_not_validated() -> None:
    assert validate_config(_config(_entry(permissions=["team", "public"]))) == []


# ── F4: one vocabulary, imported from auth ───────────────────────────


def test_permission_levels_are_the_auth_vocabulary() -> None:
    assert set(VALID_PERMISSION_LEVELS) == set(SCOPE_LEVELS)
    assert isinstance(VALID_PERMISSION_LEVELS, frozenset)


# ── manifest fields: name ────────────────────────────────────────────


@pytest.mark.parametrize("name", ["Content Creator", "QA", "a" * 64])
def test_name_accepts_valid_values(name: str) -> None:
    assert validate_config(_config(_entry(name=name))) == []


@pytest.mark.parametrize(
    ("name", "needle"),
    [
        ("", "1-64"),
        ("a" * 65, "1-64"),
        (" x", "whitespace"),
        ("x ", "whitespace"),
        ("a\nb", "newline"),
    ],
)
def test_name_rejects_invalid_values(name: str, needle: str) -> None:
    errors = validate_config(_config(_entry(name=name)))

    assert any("name" in error and needle in error for error in errors)


# ── manifest fields: version ─────────────────────────────────────────


@pytest.mark.parametrize(
    "version", ["0.1.0", "10.20.30", "1.0.0-rc.1", "1.0.0+build.5"]
)
def test_version_accepts_semver_subset(version: str) -> None:
    assert validate_config(_config(_entry(version=version))) == []


@pytest.mark.parametrize("version", ["1.0", "v1.0.0", "1.0.0.0", "1.0.0-"])
def test_version_rejects_non_semver(version: str) -> None:
    errors = validate_config(_config(_entry(version=version)))

    assert any("version" in error for error in errors)


def test_version_rejects_over_48_characters() -> None:
    version = "1.0.0-" + "a" * 45

    errors = validate_config(_config(_entry(version=version)))

    assert any("48" in error for error in errors)


# ── manifest fields: capabilities ────────────────────────────────────


def test_capabilities_accept_known_primitives() -> None:
    assert validate_config(_config(_entry(capabilities=["tools", "resources", "prompts"]))) == []


def test_capabilities_reject_unknown_primitive() -> None:
    errors = validate_config(_config(_entry(capabilities=["plugins"])))

    assert any("capabilities" in error and "plugins" in error for error in errors)


def test_capabilities_reject_duplicates() -> None:
    errors = validate_config(_config(_entry(capabilities=["tools", "tools"])))

    assert any("duplicate" in error for error in errors)


def test_capabilities_must_be_a_list() -> None:
    errors = validate_config(_config(_entry(capabilities="tools")))

    assert any("capabilities" in error and "list" in error for error in errors)


# ── manifest fields: dependencies ────────────────────────────────────


def test_dependencies_accept_infra_and_declared_modules() -> None:
    assert INFRA_DEPENDENCIES == frozenset({"busd"})
    config = {
        "qa": _entry(dependencies=["busd", "content-creator"]),
        "content-creator": _entry(),
    }

    assert validate_config(config) == []


def test_dependencies_reject_dangling_module() -> None:
    errors = validate_config(_config(_entry(dependencies=["ghost"])))

    assert any("ghost" in error for error in errors)


def test_dependencies_reject_self_reference() -> None:
    errors = validate_config(_config(_entry(dependencies=["qa"])))

    assert any("itself" in error for error in errors)


def test_dependencies_reject_empty_token() -> None:
    errors = validate_config(_config(_entry(dependencies=[""])))

    assert any("dependencies" in error for error in errors)


def test_dependencies_must_be_a_list_of_strings() -> None:
    errors = validate_config(_config(_entry(dependencies=[1])))

    assert any("dependencies" in error and "list" in error for error in errors)


# ── manifest fields: entry_repo ──────────────────────────────────────


@pytest.mark.parametrize(
    "entry_repo",
    ["internal", "/no/such/path/on/this/machine", "https://example.com/repo.git"],
)
def test_entry_repo_is_not_stat_against_the_filesystem(entry_repo: str) -> None:
    assert validate_config(_config(_entry(entry_repo=entry_repo))) == []


@pytest.mark.parametrize(
    ("entry_repo", "needle"),
    [("", "1-512"), (" x", "whitespace"), ("x ", "whitespace"), ("a\nb", "newline")],
)
def test_entry_repo_rejects_invalid_values(entry_repo: str, needle: str) -> None:
    errors = validate_config(_config(_entry(entry_repo=entry_repo)))

    assert any("entry_repo" in error and needle in error for error in errors)


def test_entry_repo_rejects_over_512_characters() -> None:
    errors = validate_config(_config(_entry(entry_repo="a" * 513)))

    assert any("512" in error for error in errors)


# ── transport: command is required per transport ─────────────────────


def test_transport_entry_fields_declare_command_for_stdio() -> None:
    assert TRANSPORT_ENTRY_FIELDS == {"stdio": frozenset({"command"})}


def test_command_is_required_for_stdio_transport() -> None:
    entry = _entry()
    del entry["command"]

    errors = validate_config(_config(entry))

    assert any("command" in error and "stdio" in error for error in errors)


def test_unknown_transport_does_not_demand_command() -> None:
    entry = _entry(transport="http")
    del entry["command"]

    errors = validate_config(_config(entry))

    assert any("transport" in error for error in errors)
    assert not any("command" in error for error in errors)


@pytest.mark.parametrize("value", [["stdio"], {"name": "stdio"}, 2])
def test_unhashable_or_non_string_enum_values_are_errors_not_crashes(
    value: Any,
) -> None:
    # status() promises never to raise; a hand-edited list/dict where an enum
    # value belongs must come back as an error list, not a TypeError.
    errors = validate_config(_config(_entry(transport=value, status=value)))

    assert any("transport" in error for error in errors)
    assert any("status" in error for error in errors)


# ── write path: canonical order, no rewrite on read, .bak ────────────


def test_save_writes_permissions_in_canonical_level_order(
    registry: ModuleRegistry,
) -> None:
    registry.register("admin-mod", _entry(permissions=["admin", "public", "team"]))

    saved = _read(Path(registry.path))

    assert saved["admin-mod"]["permissions"] == ["public", "team", "admin"]


def test_read_does_not_reorder_or_rewrite_the_config(
    registry: ModuleRegistry,
) -> None:
    config_path = Path(registry.path)
    document = _read(config_path)
    document["qa"]["permissions"] = ["team", "public"]
    _write(config_path, document)
    before = config_path.read_bytes()

    status = registry.status()

    assert status["valid"] is True
    assert config_path.read_bytes() == before


def test_config_write_snapshots_the_previous_file(registry: ModuleRegistry) -> None:
    config_path = Path(registry.path)
    before = _read(config_path)

    registry.update("qa", "disabled")

    backup = config_path.with_name(config_path.name + ".bak")
    assert backup.exists()
    assert _read(backup) == before
    assert _read(config_path)["qa"]["status"] == "disabled"


def test_state_write_does_not_snapshot(registry: ModuleRegistry) -> None:
    registry.record_runtime_state("qa", "connected")

    state_path = Path(registry.state_path)
    assert not state_path.with_name(state_path.name + ".bak").exists()


# ── F5: FR-07 — standalone import and call need no API key ───────────


def _sandbox(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    shutil.copytree(
        ROOT / "solocorp_mcp",
        sandbox / "solocorp_mcp",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    env = {
        **os.environ,
        "PYTHONPATH": str(sandbox),
        "SOLOCORP_BUS_ROOT": str(tmp_path / "bus"),
        "SOLOCORP_TASKS_ROOT": str(tmp_path / "tasks"),
        "SOLOCORP_QA_RESULTS_ROOT": str(tmp_path / "qa_results"),
    }
    env.pop("SOLOCORP_API_KEY", None)
    return sandbox, env


def _run_python(code: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )


def test_department_import_creates_no_registry_config(tmp_path: Path) -> None:
    sandbox, env = _sandbox(tmp_path)

    result = _run_python(
        "import solocorp_mcp.departments.content_mcp\n"
        "import solocorp_mcp.departments.engineering_mcp\n"
        "import solocorp_mcp.departments.qa_mcp\n",
        sandbox,
        env,
    )

    assert result.returncode == 0, result.stderr[-2000:]
    assert not (sandbox / "config" / "module-registry.json").exists()


def test_department_tool_seeds_only_its_own_module(tmp_path: Path) -> None:
    sandbox, env = _sandbox(tmp_path)
    code = (
        "import json\n"
        "from solocorp_mcp.departments import content_mcp\n"
        "raw = content_mcp.mcp._tool_manager.get_tool('module_registry_status').fn()\n"
        "payload = json.loads(raw)\n"
        "print(json.dumps({'valid': payload['valid'], 'modules': sorted(payload['modules'])}))\n"
    )

    result = _run_python(code, sandbox, env)

    assert result.returncode == 0, result.stderr[-2000:]
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload == {"valid": True, "modules": ["content-creator"]}

    saved = _read(sandbox / "config" / "module-registry.json")
    assert set(saved) == {"content-creator", "_meta"}
    assert saved["_meta"]["schema_version"] == SCHEMA_VERSION


def test_fr07_host_calls_content_tool_without_api_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SOLOCORP_API_KEY", raising=False)
    monkeypatch.setenv("SOLOCORP_BUS_ROOT", str(tmp_path / "bus"))
    monkeypatch.setenv("SOLOCORP_TASKS_ROOT", str(tmp_path / "tasks"))

    registry = ModuleRegistry(
        registry_path=tmp_path / "config" / "module-registry.json",
        state_path=tmp_path / "state" / "module-registry.state.json",
    )
    host = ModuleHost(
        registry,
        cwd=module_registry.ROOT,
        startup_timeout=60.0,
        request_timeout=60.0,
    )
    try:
        result = host.call_tool(
            "content-creator",
            "create_content_draft",
            {
                "title": "FR-07 standalone check",
                "topic": "a department MCP call without an API key",
                "target_audience": "QA",
            },
        )
    finally:
        host.close_all()

    assert isinstance(result, dict)
    # FastMCP wraps a ``str`` return in {"result": "<json>"}; a structured
    # return arrives as the payload itself.
    payload = json.loads(result["result"]) if "result" in result else result
    assert payload["status"] == "created"
    assert payload["department"] == "content-creator"


# ── F6: the department status tool is public ─────────────────────────


def test_department_status_tool_works_without_api_key(
    registry: ModuleRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SOLOCORP_API_KEY", raising=False)
    from solocorp_mcp.departments import content_mcp

    monkeypatch.setattr(content_mcp, "_module_registry", registry)

    raw = content_mcp.mcp._tool_manager.get_tool("module_registry_status").fn()

    payload = json.loads(raw)
    assert payload["valid"] is True
    assert payload["count"] == 5
    assert "error" not in payload


# ── F7: shipped defaults and the tracked config validate ─────────────


def test_default_modules_validate_and_declare_every_manifest_field() -> None:
    assert validate_config(module_registry.DEFAULT_MODULES) == []

    for module_id, entry in module_registry.DEFAULT_MODULES.items():
        missing = MANIFEST_FIELDS - set(entry)
        assert not missing, (module_id, missing)


def test_tracked_config_validates_with_current_schema() -> None:
    document = _read(module_registry.DEFAULT_CONFIG_PATH)

    assert validate_config(document) == []
    assert document["_meta"]["schema_version"] == SCHEMA_VERSION
    assert document["_meta"]["total_modules"] == 5


def test_tracked_config_permissions_match_declared_scopes() -> None:
    document = _read(module_registry.DEFAULT_CONFIG_PATH)

    assert document["solocorp"]["permissions"] == ["public", "team", "admin"]
    # The department status tool is public (§4.2), so content-creator has no
    # team-scoped tool left in the department MCP.
    assert document["content-creator"]["permissions"] == ["public"]
    assert document["qa"]["permissions"] == ["public"]
    assert document["engineering"]["permissions"] == ["public"]
    assert document["central-bus"]["permissions"] == ["public"]


# ── F10: C1 contracts are additive only ──────────────────────────────

STATUS_CONTRACT_KEYS = {
    "registry_path",
    "state_path",
    "modules",
    "count",
    "connected_count",
    "error_count",
    "disabled_count",
    "connecting_count",
    "enabled_count",
    "last_updated",
    "valid",
    "errors",
    "warnings",
    "stale_state",
    "state_error",
}
VALIDATE_CONTRACT_KEYS = {"valid", "errors", "warnings", "stale_state", "state_error"}


def test_status_keeps_every_c1_key(registry: ModuleRegistry) -> None:
    assert STATUS_CONTRACT_KEYS <= set(registry.status())


def test_validate_keeps_c1_keys_plus_error_kind(registry: ModuleRegistry) -> None:
    assert set(registry.validate()) == VALIDATE_CONTRACT_KEYS | {"error_kind"}


# ── rollback repair script ───────────────────────────────────────────


def _repair(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPAIR_SCRIPT), *args],
        text=True,
        capture_output=True,
        timeout=120,
    )


def _v2_document() -> dict[str, Any]:
    return {**_config(), "_meta": {"schema_version": SCHEMA_VERSION, "total_modules": 1}}


def test_registry_repair_dry_run_changes_nothing(config_path: Path) -> None:
    _write(config_path, _v2_document())
    before = config_path.read_bytes()

    result = _repair("--path", str(config_path), "--to-schema", "1", "--keep-modules")

    assert result.returncode == 0, result.stderr
    assert config_path.read_bytes() == before
    assert "permissions" in result.stdout


def test_registry_repair_strips_newer_fields_and_keeps_modules(
    config_path: Path,
) -> None:
    _write(config_path, _v2_document())

    result = _repair(
        "--path", str(config_path), "--to-schema", "1", "--keep-modules", "--yes"
    )

    assert result.returncode == 0, result.stderr
    saved = _read(config_path)
    assert set(saved) == {"qa", "_meta"}
    assert saved["qa"] == {
        "status": "enabled",
        "transport": "stdio",
        "command": ["/bin/echo", "hello"],
        "description": "QA Department",
    }
    assert saved["_meta"]["schema_version"] == 1
