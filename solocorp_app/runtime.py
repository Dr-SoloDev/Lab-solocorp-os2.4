"""App runtime: one object that owns the registry, the module host and polling.

The runtime is the only place the app talks to modules. It never imports a
department's code and it never invents status words: configured intent comes
from ``ModuleRegistry.module_config()`` (``enabled``/``disabled``) and the live
observation comes from the registry's state file (``connecting`` /
``connected`` / ``error``), exactly as the design note §5.3 requires.

Phase 1 deliberately does **not** auto-connect every enabled module at startup:
starting five stdio processes on boot would make the shell slow and noisy, and
the gate only needs a working toggle. A module connects when the user enables
it and is probed while a connection exists.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from axis_mcp.module_host import ModuleHost, ModuleHostError
from axis_mcp.module_registry import ModuleRegistry
from axis_mcp.module_registry_schema import RUNTIME_STATUSES
from axis_mcp.task_tracking import TaskTracker

from .provider import ProviderStore

DEFAULT_HEALTH_INTERVAL = 5.0


class UnknownModuleError(LookupError):
    """The requested module id is not declared in the registry config."""


class AppRuntime:
    """Registry + module host + health polling behind one small interface."""

    def __init__(
        self,
        *,
        registry: ModuleRegistry | None = None,
        host: ModuleHost | None = None,
        provider: ProviderStore | None = None,
        tracker: TaskTracker | None = None,
        health_interval: float = DEFAULT_HEALTH_INTERVAL,
    ) -> None:
        self.registry = registry or ModuleRegistry()
        self.host = host or ModuleHost(self.registry)
        self.provider = provider or ProviderStore()
        self.tracker = tracker
        self.health_interval = health_interval
        self._stop_event = threading.Event()
        self._poll_thread: threading.Thread | None = None
        self._connect_pool = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="solocorp-connect"
        )
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- module

    def modules(self) -> list[dict[str, Any]]:
        """Merged per-module view for the Modules page and ``/api/modules``."""

        status = self.registry.status()
        merged = status.get("modules", {})
        view: list[dict[str, Any]] = []
        for module_id in sorted(merged):
            config = self.registry.module_config(module_id) or {}
            live = merged[module_id]
            observation = (
                live.get("status") if live.get("status") in RUNTIME_STATUSES else None
            )
            enabled = config.get("status") == "enabled"
            view.append(
                {
                    "id": module_id,
                    "name": config.get("name") or module_id,
                    "description": config.get("description") or "",
                    "version": config.get("version"),
                    "transport": config.get("transport"),
                    "capabilities": config.get("capabilities") or [],
                    "dependencies": config.get("dependencies") or [],
                    "permissions": config.get("permissions") or [],
                    "entry_repo": config.get("entry_repo"),
                    "enabled": enabled,
                    "intent": config.get("status") or "unknown",
                    "observation": observation,
                    "status_text": _status_text(enabled, observation),
                    "last_checked": live.get("last_checked") if observation else None,
                    "response_time_ms": (
                        live.get("response_time_ms") if observation else None
                    ),
                    "last_error": live.get("last_error") if observation else None,
                }
            )
        return view

    def counts(self) -> dict[str, int]:
        modules = self.modules()
        return {
            "total": len(modules),
            "enabled": sum(1 for module in modules if module["enabled"]),
            "disabled": sum(1 for module in modules if not module["enabled"]),
            "connected": sum(
                1 for module in modules if module["observation"] == "connected"
            ),
            "error": sum(1 for module in modules if module["observation"] == "error"),
        }

    def registry_health(self) -> dict[str, Any]:
        """Registry validity + derived-state warnings, without touching modules."""

        status = self.registry.status()
        return {
            "valid": status.get("valid", False),
            "errors": status.get("errors", []),
            "warnings": status.get("warnings", []),
            "registry_path": status.get("registry_path"),
            "state_path": status.get("state_path"),
            "last_updated": status.get("last_updated"),
        }

    def set_enabled(self, module_id: str, enabled: bool) -> dict[str, Any]:
        """Persist the operator's intent, then reconcile the live connection.

        ``enabled``/``disabled`` is written by ``ModuleRegistry.update`` to the
        tracked config only. Disabling disconnects and clears the observation;
        enabling schedules a connect on a worker thread so the request returns
        immediately while the state file moves ``connecting`` → ``connected``
        (or ``error``).
        """

        config = self.registry.module_config(module_id)
        if config is None:
            raise UnknownModuleError(module_id)

        target_status = "enabled" if enabled else "disabled"
        self.registry.update(module_id, target_status)

        if not enabled:
            self.host.disconnect(module_id)
            return {
                "module_id": module_id,
                "intent": target_status,
                "observation": None,
                "status_text": "disabled",
            }

        with self._lock:
            self._connect_pool.submit(self._connect_safely, module_id)
        return {
            "module_id": module_id,
            "intent": target_status,
            "observation": "connecting",
            "status_text": "connecting",
        }

    def check_health(self, module_id: str) -> dict[str, Any]:
        """Probe one module: no-op when disabled, connect when enabled and idle."""

        config = self.registry.module_config(module_id)
        if config is None:
            raise UnknownModuleError(module_id)
        if config.get("status") != "enabled":
            self.host.disconnect(module_id)
            return {"module_id": module_id, "status": "disabled", "connected": False}

        observation = self._observation(module_id)
        if observation == "connected":
            return self.host.health(module_id)

        with self._lock:
            self._connect_pool.submit(self._connect_safely, module_id)
        return {
            "module_id": module_id,
            "status": "connecting",
            "connected": False,
            "note": "starting module process",
        }

    def check_all(self) -> list[dict[str, Any]]:
        """Probe every live connection; report what was probed."""

        try:
            return self.host.health_all()
        except Exception as exc:  # noqa: BLE001 - report, never crash the page
            return [{"status": "error", "error": f"{type(exc).__name__}: {exc}"}]

    def call_tool(
        self,
        module_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Pass-through used by the Phase 2 CEO loop; kept on the same interface."""

        return self.host.call_tool(module_id, tool_name, arguments)

    def _observation(self, module_id: str) -> str | None:
        for module in self.modules():
            if module["id"] == module_id:
                return module["observation"]
        return None

    def _connect_safely(self, module_id: str) -> None:
        """Worker-thread connect: record failure in state, never raise outward."""

        try:
            self.host.connect(module_id)
        except (ModuleHostError, ValueError):
            # host.connect already recorded the observation for these.
            return
        except Exception as exc:  # noqa: BLE001 - a worker must not die silently
            detail = f"{type(exc).__name__}: {exc}"[:200]
            try:
                self.registry.record_runtime_state(
                    module_id, "error", last_error=detail
                )
            except Exception:  # noqa: BLE001 - registry may be unreadable
                pass

    # ------------------------------------------------------------------ tasks

    def tasks(self) -> list[dict[str, Any]]:
        """Task history for the Task History page (brief stays hidden)."""

        tracker = self.tracker or TaskTracker()
        try:
            return tracker.list_tasks()
        except OSError:
            return []

    def tasks_summary(self, *, cap: int = 200) -> dict[str, Any]:
        """Count TaskTracker by status with a cap (PR2.1 Product v1.0 — D4).

        Read-only aggregate for ``/api/live/status`` contract v1.0::

            {"total": int, "by_status": {status: count}, "updated_at": iso}

        Single source of truth = :meth:`tasks` (TaskTracker JSON). Never
        raises — a broken tracker reads as all-zero, never a 500.
        Does not touch :meth:`tasks` behavior.
        """

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            tasks = self.tasks()
        except Exception:  # noqa: BLE001 - fail-open for the dashboard
            return {"total": 0, "by_status": {}, "updated_at": now}
        if not isinstance(tasks, list):
            return {"total": 0, "by_status": {}, "updated_at": now}
        by_status: dict[str, int] = {}
        for record in tasks[: max(1, cap)]:
            status = record.get("status") if isinstance(record, dict) else None
            key = str(status) if status else "pending"
            by_status[key] = by_status.get(key, 0) + 1
        return {"total": len(tasks), "by_status": by_status, "updated_at": now}

    # -------------------------------------------------------------- lifecycle

    def start(self) -> None:
        """Reset stale observations, then start the health poller.

        A ``connected`` entry in the state file means *this host process* had a
        live module process. After a restart nothing is connected, so any
        observation left by a previous run is stale by definition — and since
        the poller only re-probes modules this host owns, a stale ``connected``
        would otherwise be displayed forever (a failure reported as success,
        PRD §9). Clearing at startup makes the first render true.
        """

        self._reset_stale_observations()

        if self.health_interval <= 0 or self._poll_thread is not None:
            return
        self._stop_event.clear()
        thread = threading.Thread(
            target=self._poll_loop, name="solocorp-health", daemon=True
        )
        self._poll_thread = thread
        thread.start()

    def _reset_stale_observations(self) -> int:
        """Drop observations for modules this host is not connected to."""

        cleared = 0
        for module in self.modules():
            if module["observation"] is None:
                continue
            try:
                self.registry.clear_runtime_state(module["id"])
            except (ValueError, OSError):
                continue
            cleared += 1
        return cleared

    def _poll_loop(self) -> None:
        while not self._stop_event.wait(self.health_interval):
            try:
                self.host.health_all()
            except Exception:  # noqa: BLE001 - one bad module must not stop polling
                continue

    def close(self) -> None:
        """Stop polling, disconnect every module and drain the worker pool."""

        self._stop_event.set()
        thread, self._poll_thread = self._poll_thread, None
        if thread is not None:
            thread.join(timeout=max(self.health_interval * 2, 1.0))
        try:
            self.host.close_all()
        finally:
            self._connect_pool.shutdown(wait=False, cancel_futures=True)


def _status_text(enabled: bool, observation: str | None) -> str:
    """One label per module state, derived from the two status layers."""

    if observation == "connected":
        return "connected"
    if observation == "connecting":
        return "connecting"
    if observation == "error":
        return "error"
    return "enabled" if enabled else "disabled"
