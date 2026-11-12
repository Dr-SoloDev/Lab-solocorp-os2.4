"""Schema validation for module registry config and state files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from axis_mcp.module_registry_schema import (
    RegistrySchemaError,
    read_json_document,
    validate_config,
    validate_state,
    validate_merged,
)


def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_valid_config_passes(tmp_path: Path) -> None:
    config = {
        "qa": {
            "status": "enabled",
            "transport": "stdio",
            "command": [".venv/bin/python3", "-m", "axis_mcp.departments.qa_mcp"],
            "description": "QA Department",
        }
    }
    assert validate_config(config) == []


def test_config_unknown_field_rejected(tmp_path: Path) -> None:
    config = {
        "qa": {
            "status": "enabled",
            "transport": "stdio",
            "command": [".venv/bin/python3"],
            "bogus": 123,
        }
    }
    errors = validate_config(config)
    assert any("unknown field" in e for e in errors)


def test_config_missing_required_field_rejected(tmp_path: Path) -> None:
    config = {
        "qa": {
            "status": "enabled",
            "transport": "stdio",
        }
    }
    errors = validate_config(config)
    assert any("command" in e for e in errors)


def test_config_invalid_status_rejected(tmp_path: Path) -> None:
    config = {
        "qa": {
            "status": "running",
            "transport": "stdio",
            "command": [".venv/bin/python3"],
        }
    }
    errors = validate_config(config)
    assert any("status" in e for e in errors)


def test_config_invalid_transport_rejected(tmp_path: Path) -> None:
    config = {
        "qa": {
            "status": "enabled",
            "transport": "http",
            "command": [".venv/bin/python3"],
        }
    }
    errors = validate_config(config)
    assert any("transport" in e for e in errors)


def test_config_invalid_command_rejected(tmp_path: Path) -> None:
    config = {
        "qa": {
            "status": "enabled",
            "transport": "stdio",
            "command": [],
        }
    }
    errors = validate_config(config)
    assert any("command" in e for e in errors)


def test_valid_state_passes(tmp_path: Path) -> None:
    state = {
        "qa": {
            "status": "connected",
            "last_checked": "2026-11-02T03:59:09.498370+00:00",
            "response_time_ms": 1338.36,
            "last_error": None,
        }
    }
    assert validate_state(state, {"qa"}) == []


def test_state_unknown_module_rejected(tmp_path: Path) -> None:
    state = {
        "ghost": {
            "status": "connected",
            "last_checked": "2026-11-02T03:59:09.498370+00:00",
        }
    }
    errors = validate_state(state, {"qa"})
    assert any("not declared in config" in e for e in errors)


def test_state_invalid_status_rejected(tmp_path: Path) -> None:
    state = {
        "qa": {
            "status": "running",
            "last_checked": "2026-11-02T03:59:09.498370+00:00",
        }
    }
    errors = validate_state(state, {"qa"})
    assert any("status" in e for e in errors)


def test_merged_cross_validation(tmp_path: Path) -> None:
    config = {"qa": {"status": "enabled", "transport": "stdio", "command": ["x"]}}
    state = {"nonexistent": {"status": "connected", "last_checked": "now"}}
    errors = validate_merged(config, state)
    assert any("not declared in config" in e for e in errors)


def test_read_json_document_rejects_non_utf8(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_bytes(b'{"qa": {"description": "caf\xe9"}}')

    with pytest.raises(RegistrySchemaError, match="not valid UTF-8"):
        read_json_document(path)
