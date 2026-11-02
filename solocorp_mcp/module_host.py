"""Lifecycle manager for local MCP module processes."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable

from . import module_registry
from .departments.mcp_stdio import MCPStdioClient, MCPStdioError
from .module_registry import ModuleRegistry


class ModuleHostError(RuntimeError):
    """A module could not be connected or used by the host."""


class ModuleHost:
    """Own persistent stdio connections for enabled registry modules."""

    def __init__(
        self,
        registry: ModuleRegistry | None = None,
        *,
        client_factory: Callable[..., Any] = MCPStdioClient,
        cwd: Path | None = None,
        startup_timeout: float = 15.0,
        request_timeout: float = 5.0,
    ) -> None:
        self.registry = registry or ModuleRegistry()
        self.client_factory = client_factory
        self.cwd = cwd or module_registry.ROOT
        self.startup_timeout = startup_timeout
        self.request_timeout = request_timeout
        self._connections: dict[str, Any] = {}
        self._module_locks: dict[str, threading.RLock] = {}
        self._guard = threading.Lock()

    def _lock_for(self, module_id: str) -> threading.RLock:
        with self._guard:
            return self._module_locks.setdefault(module_id, threading.RLock())

    def _config(self, module_id: str) -> dict[str, Any]:
        config = self.registry.module_config(module_id)
        if config is None:
            raise ModuleHostError(f"module {module_id} not found in registry")
        return config

    def _connection(self, module_id: str) -> Any | None:
        with self._guard:
            return self._connections.get(module_id)

    def connect(self, module_id: str) -> dict[str, Any]:
        """Start an enabled stdio module and verify its MCP tool endpoint."""

        with self._lock_for(module_id):
            config = self._config(module_id)
            if config.get("status") != "enabled":
                self._disconnect_locked(module_id)
                raise ModuleHostError(f"module {module_id} is disabled")
            if config.get("transport", "stdio") != "stdio":
                raise ModuleHostError(
                    f"unsupported transport for {module_id}: {config.get('transport')}"
                )

            existing = self._connection(module_id)
            if existing is not None:
                result = self._probe(module_id, existing)
                if result["connected"]:
                    return result

            command = config.get("command")
            if not isinstance(command, list) or not command:
                detail = "no command configured"
                self.registry.record_runtime_state(
                    module_id, "error", last_error=detail
                )
                return {
                    "module_id": module_id,
                    "status": "error",
                    "connected": False,
                    "error": detail,
                }

            self.registry.record_runtime_state(module_id, "connecting")
            started = time.perf_counter()
            client = None
            try:
                client = self.client_factory(
                    command,
                    cwd=self.cwd,
                    startup_timeout=self.startup_timeout,
                )
                response = client.request(
                    "tools/list", {}, timeout=self.request_timeout
                )
                tools = response.get("tools")
                if not isinstance(tools, list):
                    raise MCPStdioError("MCP server returned an invalid tools/list response")
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                with self._guard:
                    self._connections[module_id] = client
                self.registry.record_runtime_state(
                    module_id, "connected", response_time_ms=elapsed_ms
                )
                return {
                    "module_id": module_id,
                    "status": "connected",
                    "connected": True,
                    "response_time_ms": elapsed_ms,
                    "tool_count": len(tools),
                }
            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                if client is not None:
                    with self._guard:
                        if self._connections.get(module_id) is client:
                            del self._connections[module_id]
                    self._close_client(client)
                detail = f"{type(exc).__name__}: {exc}"[:200]
                self.registry.record_runtime_state(
                    module_id,
                    "error",
                    response_time_ms=elapsed_ms,
                    last_error=detail,
                )
                return {
                    "module_id": module_id,
                    "status": "error",
                    "connected": False,
                    "response_time_ms": elapsed_ms,
                    "error": detail,
                }

    def disconnect(self, module_id: str) -> dict[str, Any]:
        """Stop a module process and clear its live observation."""

        with self._lock_for(module_id):
            config = self._config(module_id)
            self._disconnect_locked(module_id)
            return {
                "module_id": module_id,
                "status": config.get("status", "enabled"),
                "connected": False,
                "disconnected": True,
            }

    def _disconnect_locked(self, module_id: str) -> None:
        with self._guard:
            client = self._connections.pop(module_id, None)
        if client is not None:
            self._close_client(client)
        if self.registry.module_config(module_id) is not None:
            self.registry.clear_runtime_state(module_id)

    @staticmethod
    def _close_client(client: Any) -> None:
        try:
            client.close()
        except Exception:
            pass

    def _probe(self, module_id: str, client: Any) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            response = client.request(
                "tools/list", {}, timeout=self.request_timeout
            )
            tools = response.get("tools")
            if not isinstance(tools, list):
                raise MCPStdioError("MCP server returned an invalid tools/list response")
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            with self._guard:
                if self._connections.get(module_id) is client:
                    del self._connections[module_id]
            self._close_client(client)
            detail = f"{type(exc).__name__}: {exc}"[:200]
            self.registry.record_runtime_state(
                module_id,
                "error",
                response_time_ms=elapsed_ms,
                last_error=detail,
            )
            return {
                "module_id": module_id,
                "status": "error",
                "connected": False,
                "response_time_ms": elapsed_ms,
                "error": detail,
            }

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        self.registry.record_runtime_state(
            module_id, "connected", response_time_ms=elapsed_ms
        )
        return {
            "module_id": module_id,
            "status": "connected",
            "connected": True,
            "response_time_ms": elapsed_ms,
            "tool_count": len(tools),
        }

    def health(self, module_id: str) -> dict[str, Any]:
        """Probe one active module; report configured intent if it is stopped."""

        with self._lock_for(module_id):
            config = self._config(module_id)
            if config.get("status") != "enabled":
                self._disconnect_locked(module_id)
                return {
                    "module_id": module_id,
                    "status": "disabled",
                    "connected": False,
                }
            client = self._connection(module_id)
            if client is None:
                return {
                    "module_id": module_id,
                    "status": "enabled",
                    "connected": False,
                    "error": "module is not connected",
                }
            return self._probe(module_id, client)

    def health_all(self) -> list[dict[str, Any]]:
        """Poll every active module; intended for the app runtime health loop."""

        with self._guard:
            module_ids = sorted(self._connections)
        return [self.health(module_id) for module_id in module_ids]

    def call_tool(
        self,
        module_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        *,
        timeout: float = 60.0,
    ) -> Any:
        """Call a tool through the host-owned module connection."""

        with self._lock_for(module_id):
            config = self._config(module_id)
            if config.get("status") != "enabled":
                self._disconnect_locked(module_id)
                raise ModuleHostError(f"module {module_id} is disabled")
            if self._connection(module_id) is None:
                connection = self.connect(module_id)
                if not connection["connected"]:
                    raise ModuleHostError(
                        connection.get("error", f"module {module_id} is unavailable")
                    )
            client = self._connection(module_id)
            if client is None:
                raise ModuleHostError(f"module {module_id} is unavailable")
            try:
                return client.call_tool(tool_name, arguments or {}, timeout=timeout)
            except MCPStdioError as exc:
                raise ModuleHostError(str(exc)) from exc

    def close_all(self) -> None:
        """Stop all host-owned processes, typically during app shutdown."""

        with self._guard:
            module_ids = sorted(self._connections)
        for module_id in module_ids:
            with self._lock_for(module_id):
                self._disconnect_locked(module_id)
