"""axis-status MCP server — one read-only tool, one schema.

Run with ``python -m axis_mcp.status.server`` from a compatible MCP client.
``--smoke`` prints one JSON snapshot and exits 0 without starting the stdio
server, so CI and the D2 evidence harness can call it directly.
"""

from __future__ import annotations

import json
import sys

from mcp.server.fastmcp import FastMCP

from .aggregator import TOOL_VERSION, aggregate

INSTRUCTIONS = (
    "Read-only AXIS status. One call returns the state of busd, CTO, Content, "
    "MCP freshness, git, browse and codegraph in the axis.status/1 schema. "
    "No writes, no approvals, no external network."
)

mcp = FastMCP("axis-status", instructions=INSTRUCTIONS)


@mcp.tool()
def axis_status(force: bool = False) -> dict:
    """Return the unified AXIS status snapshot (7 sources, ≤2s, read-only).

    Args:
        force: Bypass the 10 s cache and measure every source again.
    """

    return aggregate(force=force)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--smoke" in args:
        snapshot = aggregate(force=True)
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return 0
    if "--version" in args:
        print(TOOL_VERSION)
        return 0
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
