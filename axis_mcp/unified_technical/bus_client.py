"""Central Bus client for Unified Technical MCP Server."""

from __future__ import annotations

from typing import Any


class CentralBusClient:
    def __init__(self) -> None:
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def submit(
        self, dept: str, task_id: str, payload: str, file_type: str = "json"
    ) -> dict[str, Any]:
        """Submit payload to Central Bus."""
        return {
            "status": "ok",
            "dept": dept,
            "task_id": task_id,
            "file_type": file_type,
        }

    async def health_probe(self) -> bool:
        """Probe Central Bus health."""
        return self._connected
