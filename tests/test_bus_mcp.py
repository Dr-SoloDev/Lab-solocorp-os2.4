from __future__ import annotations

import json

import pytest

from axis_mcp import bus_store
from axis_mcp.bus_mcp import mcp


def test_bus_round_trip_and_listing(tmp_path, monkeypatch):
    monkeypatch.setattr(bus_store, "BUS_ROOT", tmp_path / "central_bus")

    manifest = bus_store.submit_to_bus("content", "brief-001", "hello", "md")
    assert manifest["status"] == "submitted"
    assert manifest["path"].startswith("content/")

    fetched = bus_store.fetch_from_bus("content", manifest["filename"])
    assert fetched["content"] == "hello"
    listing = bus_store.list_department_bus("content")
    assert listing["count"] == 1
    assert listing["files"][0]["filename"] == manifest["filename"]


def test_bus_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(bus_store, "BUS_ROOT", tmp_path / "central_bus")
    with pytest.raises(bus_store.BusStoreError):
        bus_store.submit_to_bus("../secrets", "task", "x")

    manifest = bus_store.submit_to_bus("content", "task", "x")
    with pytest.raises(bus_store.BusStoreError):
        bus_store.fetch_from_bus("content", f"../{manifest['filename']}")


def test_bus_mcp_exposes_storage_contract():
    names = {tool.name for tool in mcp._tool_manager.list_tools()}
    assert names == {"submit_to_bus", "fetch_from_bus", "list_department_bus"}


def test_bus_tool_returns_json(tmp_path, monkeypatch):
    monkeypatch.setattr(bus_store, "BUS_ROOT", tmp_path / "central_bus")
    from axis_mcp import bus_mcp

    payload = json.loads(bus_mcp.submit_to_bus("content", "json-test", "ok"))
    assert payload["status"] == "submitted"
    assert payload["filename"].endswith(".md")
