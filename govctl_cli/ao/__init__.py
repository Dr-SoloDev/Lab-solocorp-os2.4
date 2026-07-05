"""
govctl AO — Agent Orchestrator Integration Module

Public API:
    - run_agent(agent_id, context)  — Quick agent invoke via adapter
    - check_ao()                    — Check CLI availability
    - get_ao_status()               — Status + version info
    - list_agents()                 — Registered agent adapters
    - get_adapter(agent_id)         — Lookup adapter instance

    - handle_ao_request(msg)        — BusMessage → spawn agent → AO_RESPONSE
    - publish_ao_event(...)         — Audit-trail event publish
    - ao_listener_loop(...)         — Queue polling loop (bridge daemon)
    - process_ao_queue(...)         — One-shot queue processing

Bridge integration (Central Bus → AO):
    ``ao_listener_loop`` ใช้ใน ``govctl_cli.bridge`` daemon เพื่อ
    poll queue สำหรับ AO_REQUEST → spawn agent → publish AO_RESPONSE

Designed by:
    - Software Architect (พี่ทรงศักดิ์): adapter base / registry / agent adapters
    - Backend Architect (คุณ): client layer / bridge integration / CLI
"""

from __future__ import annotations

from typing import Any

# ── Force import of agent modules to populate REGISTRY ──────────────
from . import agents  # noqa: F401

# ── Adapter layer (Software Architect's design) ─────────────────────
from .adapter import (
    REGISTRY,
    AgentAdapter,
    get_adapter,
    list_agents,
    process_ao_request,
)

# ── Client layer (Backend Architect's implementation) ───────────────
from .client import (
    AOClient,
    AOResult,
    AOCliClient,
    get_configured_client,
)

# ── Bridge integration (Backend Architect's implementation) ─────────
from .bridge_integration import (
    handle_ao_request,
    publish_ao_event,
    ao_listener_loop,
    process_ao_queue,
    reset_bridge_client,
)

# ═══════════════════════════════════════════════════════════════════════
# Convenience functions
# ═══════════════════════════════════════════════════════════════════════


def run_agent(
    agent_id: str,
    context: dict[str, Any],
    timeout: int = 300,
) -> dict[str, Any]:
    """Run a single AO agent by *agent_id* with the given *context*.

    Args:
        agent_id: Registered agent ID (ceo, architect, engineering, qa, orchestrator)
        context:  Dict passed to adapter's ``build_prompt()``
        timeout:  Max seconds for AO CLI to respond

    Returns:
        Structured result from the adapter's ``parse_response()``
    """
    adapter = get_adapter(agent_id)
    return adapter.invoke(context, timeout=timeout)


def check_ao() -> bool:
    """Check if the AO CLI binary is available on PATH."""
    return AOClient().check_available()


def get_ao_status() -> dict[str, Any]:
    """Return dict describing AO CLI and agent availability."""
    client = AOClient()
    cli_available = client.check_available()
    agents = list_agents()
    return {
        "cli_available": cli_available,
        "cli_path": client._cli_path,
        "agent_count": len(agents),
        "agents": agents,
    }


# ═══════════════════════════════════════════════════════════════════════
# Exports
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    # Adapter layer
    "REGISTRY",
    "AgentAdapter",
    "get_adapter",
    "list_agents",
    "process_ao_request",
    # Client layer
    "AOClient",
    "AOResult",
    "AOCliClient",
    "get_configured_client",
    # Bridge integration
    "handle_ao_request",
    "publish_ao_event",
    "ao_listener_loop",
    "process_ao_queue",
    "reset_bridge_client",
    # Convenience
    "run_agent",
    "check_ao",
    "get_ao_status",
]
