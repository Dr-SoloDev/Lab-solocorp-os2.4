"""Central Bus MCP server.

Run with ``python -m axis_mcp.bus_mcp`` from a compatible MCP client.
The server exposes storage primitives only; department behavior lives in the
department-specific server that uses the same ``bus_store`` library.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .bus_store import (
    BusStoreError,
    as_json,
    fetch_from_bus as _fetch_from_bus,
    list_department_bus as _list_department_bus,
    submit_to_bus as _submit_to_bus,
)

mcp = FastMCP(
    "central-bus",
    instructions=(
        "SoloCorp Central Bus. Store and retrieve department payload files. "
        "Return compact JSON manifests; do not put large work products in chat."
    ),
)


def _error(exc: Exception) -> str:
    return as_json({"status": "error", "error": type(exc).__name__, "message": str(exc)})


@mcp.tool()
def submit_to_bus(
    dept: str, task_id: str, payload_content: str, file_type: str = "md"
) -> str:
    """Write a department payload and return its JSON artifact manifest."""

    try:
        return as_json(_submit_to_bus(dept, task_id, payload_content, file_type))
    except (BusStoreError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def fetch_from_bus(dept: str, filename: str) -> str:
    """Fetch one department payload as JSON, including its text content."""

    try:
        return as_json(_fetch_from_bus(dept, filename))
    except (BusStoreError, FileNotFoundError, OSError, UnicodeError) as exc:
        return _error(exc)


@mcp.tool()
def list_department_bus(dept: str) -> str:
    """List payload manifests for one department."""

    try:
        return as_json(_list_department_bus(dept))
    except (BusStoreError, OSError) as exc:
        return _error(exc)


if __name__ == "__main__":
    mcp.run()
