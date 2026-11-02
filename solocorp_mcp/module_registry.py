"""Module registry for SoloCorp department MCP modules.

Two files, two lifetimes:

* **Config** (``config/module-registry.json``, git-tracked) — what the human
  decided: which modules exist, their transport, command and whether they are
  enabled or disabled. Changes only when a person changes it.
* **State** (``central_bus/module-registry.state.json``, git-ignored) — what
  the runtime observed: ``connecting`` / ``connected`` / ``error``,
  ``last_checked``, ``response_time_ms``, ``last_error``. Written on every
  heartbeat.

Keeping them apart means a health check never dirties a tracked file. The
public read model (``status()``) still returns one merged view per module, so
callers see ``enabled``/``disabled`` plus live connection detail as before.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# Tracked config — belongs in git.
DEFAULT_CONFIG_PATH = ROOT / "config" / "module-registry.json"

# Runtime observation — never in git.
DEFAULT_STATE_PATH = ROOT / "central_bus" / "module-registry.state.json"

VALID_STATUSES = {"enabled", "disabled", "connecting", "connected", "error"}

# Statuses that describe intent and therefore live in the tracked config.
PERSISTENT_STATUSES = {"enabled", "disabled"}

# Statuses that describe an observation and therefore live in the state file.
RUNTIME_STATUSES = VALID_STATUSES - PERSISTENT_STATUSES

# Backwards-compatible alias: the registry file used before the split.
LEGACY_REGISTRY_PATH = ROOT / "central_bus" / "content" / "module-registry.json"

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
    """Read/write module config and connection state from two separate files."""

    def __init__(
        self,
        registry_path: Path | None = None,
        state_path: Path | None = None,
    ) -> None:
        self.path = Path(registry_path) if registry_path else DEFAULT_CONFIG_PATH
        self.state_path = Path(state_path) if state_path else DEFAULT_STATE_PATH
        self._ensure_initialized()

    # ------------------------------------------------------------------ setup

    def _ensure_initialized(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._save_config(
                {
                    key: value
                    for key, value in DEFAULT_MODULES.items()
                }
            )

    # ------------------------------------------------------------------- i/o

    def _save_config(self, modules: dict[str, Any]) -> None:
        data = {
            **{
                key: self._persistent_view(value)
                for key, value in modules.items()
                if key != "_meta"
            },
            "_meta": {
                "last_updated": self._now(),
                "total_modules": len(
                    [k for k in modules if k != "_meta"]
                ),
            },
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def _save_state(self, state: dict[str, Any]) -> None:
        data = {
            **{key: value for key, value in state.items() if key != "_meta"},
            "_meta": {
                "last_updated": self._now(),
                "total_modules": len([k for k in state if k != "_meta"]),
            },
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return {}

    def _load_config(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self._read_json(self.path).items()
            if key != "_meta"
        }

    def _load_state(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self._read_json(self.state_path).items()
            if key != "_meta"
        }

    @staticmethod
    def _persistent_view(entry: dict[str, Any]) -> dict[str, Any]:
        """Strip runtime observations so they never reach the tracked file."""

        status = entry.get("status", "enabled")
        if status in RUNTIME_STATUSES:
            status = entry.get("enabled", "enabled")
            status = "enabled" if status not in PERSISTENT_STATUSES else status

        return {
            "status": status,
            "transport": entry.get("transport", "stdio"),
            "command": entry.get("command"),
            "description": entry.get("description", ""),
        }

    @staticmethod
    def _runtime_view(entry: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": entry["status"],
            "last_checked": entry.get("last_checked"),
            "response_time_ms": entry.get("response_time_ms"),
            "last_error": entry.get("last_error"),
        }

    def _merged(self) -> dict[str, dict[str, Any]]:
        """Config entry + runtime observation, runtime wins for live fields."""

        merged = {key: dict(value) for key, value in self._load_config().items()}
        for module_id, state in self._load_state().items():
            if module_id not in merged:
                continue
            merged[module_id].update(
                {key: value for key, value in state.items() if value is not None}
            )
        return merged

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ---------------------------------------------------------------- read API

    def status(self) -> dict[str, Any]:
        """Return the merged view of every module with summary statistics."""

        data = self._load_config()
        modules = self._merged()
        meta = self._read_json(self.path).get("_meta", {})

        def count(status: str) -> int:
            return sum(
                1 for value in modules.values() if value.get("status") == status
            )

        return {
            "registry_path": str(self.path),
            "state_path": str(self.state_path),
            "modules": modules,
            "count": len(modules),
            "connected_count": count("connected"),
            "error_count": count("error"),
            "disabled_count": count("disabled"),
            "connecting_count": count("connecting"),
            "enabled_count": count("enabled"),
            "last_updated": meta.get("last_updated", "never"),
        }

    # --------------------------------------------------------------- write API

    def update(
        self,
        module_id: str,
        status: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update one module by hand.

        ``enabled``/``disabled`` change the tracked config. A runtime status
        (``connected``/``connecting``/``error``) is an observation, so it is
        written to the state file instead — the tracked config never carries
        a heartbeat result.
        """

        if status not in VALID_STATUSES:
            raise ValueError(
                f"status must be one of: {', '.join(sorted(VALID_STATUSES))}"
            )

        modules = self._load_config()
        previous = modules.get(module_id, {})

        if status in PERSISTENT_STATUSES:
            modules[module_id] = {
                **_persistent_entry_defaults(previous),
                "status": status,
                "description": description or previous.get("description", ""),
                "updated_at": self._now(),
            }
            self._save_config(modules)
        else:
            if module_id not in modules:
                raise ValueError(f"module {module_id} not found in registry")
            state = self._load_state()
            state[module_id] = {
                **state.get(module_id, {}),
                **self._runtime_view({"status": status}),
            }
            self._save_state(state)

        return {
            "module_id": module_id,
            "status": status,
            "description": modules.get(module_id, previous).get("description", ""),
            "updated": True,
        }

    def heartbeat(self, module_id: str, timeout: float = 5.0) -> dict[str, Any]:
        """Attempt a real stdio connection and record the result in state only."""

        import time

        from .departments.mcp_stdio import MCPStdioClient, MCPStdioError

        modules = self._load_config()
        if module_id not in modules:
            raise ValueError(f"module {module_id} not found in registry")

        entry = modules[module_id]
        command = entry.get("command")

        if not command:
            self._record_state(
                module_id,
                status="error",
                response_time_ms=None,
                last_error="no command configured",
            )
            return {
                "module_id": module_id,
                "status": "error",
                "connected": False,
                "error": "no command configured",
                "response_time_ms": None,
            }

        self._record_state(module_id, status="connecting")

        start = time.perf_counter()
        client = None
        try:
            client = MCPStdioClient(
                command,
                cwd=str(ROOT),
                startup_timeout=timeout,
            )
            # Call list_tools as a lightweight connectivity check
            client.request("tools/list", {}, timeout=timeout)
            elapsed_ms = (time.perf_counter() - start) * 1000

            status = "connected"
            connected = True
            error = None
            self._record_state(
                module_id,
                status=status,
                response_time_ms=round(elapsed_ms, 2),
                last_error=None,
            )
        except MCPStdioError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            status = "error"
            connected = False
            error = str(exc)[:200]
            self._record_state(
                module_id,
                status=status,
                response_time_ms=round(elapsed_ms, 2),
                last_error=error,
            )
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - start) * 1000
            status = "error"
            connected = False
            error = f"{type(exc).__name__}: {str(exc)[:200]}"
            self._record_state(
                module_id,
                status=status,
                response_time_ms=round(elapsed_ms, 2),
                last_error=error,
            )
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:  # noqa: BLE001
                    pass

        return {
            "module_id": module_id,
            "status": status,
            "connected": connected,
            "error": error,
            "response_time_ms": self._load_state().get(module_id, {}).get(
                "response_time_ms"
            ),
        }

    def _record_state(
        self,
        module_id: str,
        status: str,
        response_time_ms: float | None = None,
        last_error: str | None = None,
    ) -> None:
        state = self._load_state()
        entry = {
            **_runtime_entry_defaults(state.get(module_id, {})),
            "status": status,
            "last_checked": self._now(),
        }
        if response_time_ms is not None:
            entry["response_time_ms"] = response_time_ms
        if last_error is not None or status in ("connected", "connecting"):
            entry["last_error"] = last_error
        state[module_id] = entry
        self._save_state(state)


def _persistent_entry_defaults(previous: dict[str, Any]) -> dict[str, Any]:
    return {
        "transport": previous.get("transport", "stdio"),
        "command": previous.get("command"),
    }


def _runtime_entry_defaults(previous: dict[str, Any]) -> dict[str, Any]:
    return {
        "response_time_ms": previous.get("response_time_ms"),
        "last_error": previous.get("last_error"),
    }
