"""Module registry for SoloCorp department MCP modules.

Tracks enable/disable status, transport type, human-readable description,
and real-time connection state (enabled / connecting / connected / error)
for every department MCP that can be connected through the SoloCorp OS App.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = ROOT / "central_bus" / "content" / "module-registry.json"

VALID_STATUSES = {"enabled", "disabled", "connecting", "connected", "error"}

DEFAULT_MODULES: dict[str, dict[str, Any]] = {
    "solocorp": {
        "status": "enabled",
        "transport": "stdio",
        "command": [".venv/bin/python3", "-m", "solocorp_mcp.server"],
        "description": "Core MCP — Organization & Routing",
    },
    "central-bus": {
        "status": "enabled",
        "transport": "stdio",
        "command": [".venv/bin/python3", "-m", "solocorp_mcp.bus_mcp"],
        "description": "Central Bus — Storage & Queue",
    },
    "content-creator": {
        "status": "enabled",
        "transport": "stdio",
        "command": [".venv/bin/python3", "-m", "solocorp_mcp.departments.content_mcp"],
        "description": "Content Creator Department",
    },
    "sound-studio": {
        "status": "enabled",
        "transport": "stdio",
        "command": [".venv/bin/python3", "-m", "solocorp_mcp.departments.sound_mcp"],
        "description": "Sound Studio Department",
    },
    "engineering": {
        "status": "enabled",
        "transport": "stdio",
        "command": [".venv/bin/python3", "-m", "solocorp_mcp.departments.engineering_mcp"],
        "description": "Engineering Department",
    },
    "qa": {
        "status": "enabled",
        "transport": "stdio",
        "command": [".venv/bin/python3", "-m", "solocorp_mcp.departments.qa_mcp"],
        "description": "QA Department",
    },
}


class ModuleRegistry:
    """Read/write module registry with connection heartbeat support."""

    def __init__(self, registry_path: Path | None = None) -> None:
        self.path = registry_path or DEFAULT_REGISTRY_PATH
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._save(DEFAULT_MODULES)

    def _load(self) -> dict[str, Any]:
        with open(self.path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save(self, data: dict[str, Any]) -> None:
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def status(self) -> dict[str, Any]:
        """Return full module registry with summary statistics."""

        data = self._load()
        modules = {
            key: value
            for key, value in data.items()
            if key != "_meta"
        }
        meta = data.get("_meta", {})

        connected_count = sum(
            1 for value in modules.values() if value.get("status") == "connected"
        )
        error_count = sum(
            1 for value in modules.values() if value.get("status") == "error"
        )
        disabled_count = sum(
            1 for value in modules.values() if value.get("status") == "disabled"
        )
        connecting_count = sum(
            1 for value in modules.values() if value.get("status") == "connecting"
        )
        enabled_count = sum(
            1 for value in modules.values() if value.get("status") == "enabled"
        )

        return {
            "registry_path": str(self.path),
            "modules": modules,
            "count": len(modules),
            "connected_count": connected_count,
            "error_count": error_count,
            "disabled_count": disabled_count,
            "connecting_count": connecting_count,
            "enabled_count": enabled_count,
            "last_updated": meta.get("last_updated", "never"),
        }

    def update(
        self,
        module_id: str,
        status: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update one module's status manually. Returns the updated entry."""

        if status not in VALID_STATUSES:
            raise ValueError(
                f"status must be one of: {', '.join(sorted(VALID_STATUSES))}"
            )

        data = self._load()
        modules = {
            key: value
            for key, value in data.items()
            if key != "_meta"
        }

        previous = modules.get(module_id, {})
        modules[module_id] = {
            "status": status,
            "transport": previous.get("transport", "stdio"),
            "command": previous.get("command"),
            "description": description or previous.get("description", ""),
            "updated_at": self._now(),
            # Preserve connection metadata when manually updating
            "last_checked": previous.get("last_checked"),
            "response_time_ms": previous.get("response_time_ms"),
            "last_error": previous.get("last_error"),
        }
        data = {**modules, "_meta": {
            "last_updated": self._now(),
            "total_modules": len(modules),
        }}
        self._save(data)

        return {
            "module_id": module_id,
            "status": status,
            "description": modules[module_id]["description"],
            "updated": True,
        }

    def heartbeat(self, module_id: str, timeout: float = 5.0) -> dict[str, Any]:
        """Attempt a real stdio connection to the module and record result.

        Sets status to ``connected`` on success, ``error`` on failure.
        Records ``last_checked``, ``response_time_ms``, and ``last_error``.
        """

        from .departments.mcp_stdio import MCPStdioClient, MCPStdioError

        data = self._load()
        modules = {
            key: value
            for key, value in data.items()
            if key != "_meta"
        }

        if module_id not in modules:
            raise ValueError(f"module {module_id} not found in registry")

        entry = modules[module_id]
        command = entry.get("command")

        if not command:
            entry["status"] = "error"
            entry["last_checked"] = self._now()
            entry["last_error"] = "no command configured"
            entry["response_time_ms"] = None
            data = {**modules, "_meta": {"last_updated": self._now(), "total_modules": len(modules)}}
            self._save(data)
            return {
                "module_id": module_id,
                "status": "error",
                "connected": False,
                "error": "no command configured",
                "response_time_ms": None,
            }

        entry["status"] = "connecting"
        data = {**modules, "_meta": {"last_updated": self._now(), "total_modules": len(modules)}}
        self._save(data)

        start = time.perf_counter()
        client = None
        try:
            client = MCPStdioClient(
                command,
                cwd=str(ROOT),
                startup_timeout=timeout,
            )
            # Call list_tools as a lightweight connectivity check
            result = client.request("tools/list", {}, timeout=timeout)
            elapsed_ms = (time.perf_counter() - start) * 1000

            entry["status"] = "connected"
            entry["last_checked"] = self._now()
            entry["response_time_ms"] = round(elapsed_ms, 2)
            entry["last_error"] = None

            connected = True
            error = None
        except MCPStdioError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            entry["status"] = "error"
            entry["last_checked"] = self._now()
            entry["response_time_ms"] = round(elapsed_ms, 2)
            entry["last_error"] = str(exc)[:200]

            connected = False
            error = str(exc)[:200]
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - start) * 1000
            entry["status"] = "error"
            entry["last_checked"] = self._now()
            entry["response_time_ms"] = round(elapsed_ms, 2)
            entry["last_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

            connected = False
            error = f"{type(exc).__name__}: {str(exc)[:200]}"
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:  # noqa: BLE001
                    pass

        data = {**modules, "_meta": {"last_updated": self._now(), "total_modules": len(modules)}}
        self._save(data)

        return {
            "module_id": module_id,
            "status": entry["status"],
            "connected": connected,
            "error": error,
            "response_time_ms": entry["response_time_ms"],
        }
