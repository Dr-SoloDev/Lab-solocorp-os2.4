"""
AO Adapter — Abstract base class + registry + Central Bus integration.

Every AO agent type (CEO, Orchestrator, Architect, Engineering, QA) has a
concrete adapter that defines:
  1. How to build a prompt from a context dict
  2. How to parse the agent's raw response into structured JSON
  3. How to invoke the AO CLI (inherited from the base)

Usage:
    adapter = REGISTRY["architect"]()
    result = adapter.invoke({"task": "Design auth system", "project_id": "PRJ-1"})
    print(result)  # {"design": "...", "decisions": [...], ...}
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from .client import AOClient, AOResult

log = logging.getLogger("govctl.ao.adapter")

# ---------------------------------------------------------------------------
# Constants — bus message types for AO integration
# ---------------------------------------------------------------------------

AO_REQUEST_TYPE = "AO_REQUEST"
AO_RESPONSE_TYPE = "AO_RESPONSE"
AO_ERROR_TYPE = "AO_ERROR"

# ---------------------------------------------------------------------------
# Abstract Base
# ---------------------------------------------------------------------------


class AgentAdapter(ABC):
    """Base adapter for an AO agent type.

    Subclasses must implement:
      - ``build_prompt(context)`` — turn a context dict into a prompt string
      - ``parse_response(raw)`` — turn AO CLI stdout into a structured dict

    Subclasses may override:
      - ``agent_id`` — short identifier (default: class name lowercased)
      - ``display_name`` — human-readable Thai name
      - ``description`` — one-liner explaining when to use this agent
    """

    # Metadata — override in subclasses
    agent_id: ClassVar[str] = ""           # e.g. "architect"
    display_name: ClassVar[str] = ""       # e.g. "สถาปนิกซอฟต์แวร์"
    description: ClassVar[str] = ""        # e.g. "ออกแบบ system architecture และ ADR"

    def __init__(self, ao_client: AOClient | None = None):
        self._client = ao_client or AOClient()

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    @abstractmethod
    def build_prompt(self, context: dict[str, Any]) -> str:
        """Build an AO prompt from the given *context* dict.

        The context typically contains:
          - project_id, phase, trace_id (routing info)
          - task, objective (what to do)
          - input_data (supporting material)
          - constraints (boundaries / rules)
        """
        ...

    @abstractmethod
    def parse_response(self, raw: str) -> dict[str, Any]:
        """Parse AO CLI stdout into a structured dict.

        Should return at minimum:
          {"status": "success" | "error", "output": ..., ...}
        """
        ...

    # ------------------------------------------------------------------
    # Template method
    # ------------------------------------------------------------------

    def invoke(
        self,
        context: dict[str, Any],
        timeout: int = 300,
        agent_args: list[str] | None = None,
    ) -> dict[str, Any]:
        """Full invoke lifecycle: build prompt → call AO CLI → parse response.

        Returns a dict with at minimum:
          agent_id, status, output, trace_id (from context)

        On failure, returns a structured error dict instead of raising.
        """
        trace_id = context.get("trace_id", "no-trace")
        log.info("[%s] Invoking %s adapter (timeout=%ds)", trace_id, self.agent_id, timeout)

        # 1. Build prompt
        try:
            prompt = self.build_prompt(context)
        except Exception as exc:
            log.exception("[%s] build_prompt failed", trace_id)
            return self._error_result(trace_id, f"build_prompt failed: {exc}")

        log.debug("[%s] Prompt (%d chars):\n%s", trace_id, len(prompt), prompt[:500])

        # 2. Call AO CLI
        ao_result: AOResult = self._client.invoke(
            prompt=prompt,
            agent_type=self.agent_id,
            timeout=timeout,
            agent_args=agent_args,
        )

        if not ao_result.success:
            log.error("[%s] AO CLI failed (exit=%d): %s",
                      trace_id, ao_result.exit_code, ao_result.stderr)
            return self._error_result(
                trace_id,
                f"AO CLI exited code {ao_result.exit_code}: {ao_result.stderr}",
            )

        log.info("[%s] AO CLI succeeded (%d chars output)", trace_id, len(ao_result.text))

        # 3. Parse response
        try:
            parsed = self.parse_response(ao_result.text)
        except Exception as exc:
            log.exception("[%s] parse_response failed", trace_id)
            return self._error_result(trace_id, f"parse_response failed: {exc}")

        # 4. Enrich with metadata
        parsed.setdefault("agent_id", self.agent_id)
        parsed.setdefault("trace_id", trace_id)
        parsed.setdefault("status", "success")
        parsed.setdefault("output", ao_result.text)

        return parsed

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _error_result(self, trace_id: str, detail: str) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "trace_id": trace_id,
            "status": "error",
            "error": detail,
            "output": "",
        }

    @staticmethod
    def _safe_json_parse(raw: str) -> dict[str, Any] | None:
        """Try to parse *raw* as JSON. Returns None on failure."""
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None

    def __repr__(self) -> str:
        return f"<{type(self).__name__} agent_id={self.agent_id!r}>"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

REGISTRY: dict[str, type[AgentAdapter]] = {}
"""Global registry mapping ``agent_id`` → ``AgentAdapter`` subclass.

Populated by ``agents/__init__.py`` imports.
"""


def register(adapter_cls: type[AgentAdapter]) -> type[AgentAdapter]:
    """Decorator to register an adapter class in the global registry.

    Usage::

        @register
        class CeoAdapter(AgentAdapter):
            agent_id = "ceo"
            ...
    """
    agent_id = adapter_cls.agent_id or adapter_cls.__name__.lower().replace("adapter", "")
    REGISTRY[agent_id] = adapter_cls
    log.debug("Registered AO adapter: %s → %s", agent_id, adapter_cls.__name__)
    return adapter_cls


def get_adapter(agent_id: str, ao_client: AOClient | None = None) -> AgentAdapter:
    """Look up *agent_id* in the registry and return an instantiated adapter.

    Raises ``KeyError`` if the agent is not registered.
    """
    cls = REGISTRY.get(agent_id)
    if cls is None:
        raise KeyError(
            f"Unknown agent {agent_id!r}. "
            f"Available: {', '.join(sorted(REGISTRY))}"
        )
    return cls(ao_client=ao_client)


def list_agents() -> list[dict[str, str]]:
    """Return metadata for all registered agents."""
    return [
        {
            "agent_id": cls.agent_id,
            "display_name": cls.display_name,
            "description": cls.description,
        }
        for cls in REGISTRY.values()
    ]


# ---------------------------------------------------------------------------
# Central Bus integration
# ---------------------------------------------------------------------------


def process_ao_request(bus_message: Any) -> dict[str, Any] | None:
    """Process a Central Bus ``AO_REQUEST`` message and return response payload.

    Parameters
    ----------
    bus_message:
        A ``BusMessage`` instance (or duck-typed object) with:
          - ``type == "AO_REQUEST"``
          - ``payload.agent_id`` — which agent to invoke
          - ``payload.context`` — context dict forwarded to the adapter

    Returns
    -------
    Response payload dict (to be wrapped in a new ``BusMessage(type="AO_RESPONSE")``),
    or ``None`` if the message is not a valid AO_REQUEST.
    """
    from central_bus.models import BusMessage  # lazy import

    if not isinstance(bus_message, BusMessage):
        return None
    if bus_message.type != AO_REQUEST_TYPE:
        return None

    trace_id = bus_message.trace_id
    payload = bus_message.payload
    agent_id = payload.get("agent_id", "")
    context = payload.get("context", {})

    # Enrich context with trace info from the bus message
    context.setdefault("trace_id", trace_id)
    context.setdefault("project_id", bus_message.project_id)
    context.setdefault("phase", bus_message.phase)
    context.setdefault("from_dept", bus_message.from_dept)

    try:
        adapter = get_adapter(agent_id)
    except KeyError as exc:
        log.error("[%s] %s", trace_id, exc)
        return {
            "agent_id": agent_id,
            "trace_id": trace_id,
            "status": "error",
            "error": str(exc),
            "output": "",
        }

    log.info("[%s] Processing AO_REQUEST agent=%s project=%s",
             trace_id, agent_id, bus_message.project_id)

    result = adapter.invoke(context)

    # Add correlation info
    result["correlation_id"] = bus_message.id
    result["project_id"] = bus_message.project_id
    result["phase"] = bus_message.phase

    return result
