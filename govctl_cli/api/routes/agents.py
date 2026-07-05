"""
Agent Routes — List, Run, Status for AO agents.

These routes bridge between the REST API and the AO module
(govctl_cli/ao/), using the adapter pattern to invoke agents.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from ...api.models import (
    AgentSummary, AgentRunRequest, AgentRunResponse,
    AgentStatusResponse, to_dict,
)

log = logging.getLogger("govctl.api.agents")

router = APIRouter(prefix="/api/v1/agents", tags=["Agent"])


# ═══════════════════════════════════════════════════════════════════════
# List agents
# ═══════════════════════════════════════════════════════════════════════


@router.get("")
async def list_agents():
    """List all registered AO agents with metadata.

    Sources from the AO adapter REGISTRY and profile-to-agent mapping.
    """
    try:
        from govctl_cli.ao import list_agents as ao_list
        from govctl_cli.ao.agents import get_profiles_for_agent
    except ImportError:
        return {"items": [], "total": 0}

    try:
        agents = ao_list()
    except Exception:
        return {"items": [], "total": 0}

    items = []
    for a in agents:
        profiles = []
        try:
            profiles = get_profiles_for_agent(a["agent_id"])
        except (KeyError, Exception):
            pass
        items.append({
            "agent_id": a["agent_id"],
            "display_name": a["display_name"],
            "description": a["description"],
            "mapped_profiles": profiles,
        })

    return {"items": items, "total": len(items)}


# ═══════════════════════════════════════════════════════════════════════
# Run agent (async)
# ═══════════════════════════════════════════════════════════════════════


@router.post("/{id}/run", status_code=202)
async def run_agent(id: str, req: AgentRunRequest):
    """Run an AO agent asynchronously.

    The request is published as an AO_REQUEST message to Central Bus.
    The AO Bridge picks it up, spawns the agent, and publishes the
    response. The caller should poll GET /agents/{id}/status with
    the returned trace_id to get the result.

    For direct synchronous execution (dev/debug), use `govctl ao run`.
    """
    # Validate agent exists
    try:
        from govctl_cli.ao import get_adapter
        adapter = get_adapter(id)
    except KeyError:
        from govctl_cli.ao import list_agents as ao_list
        available = [a["agent_id"] for a in ao_list()]
        raise HTTPException(
            status_code=404,
            detail={
                "code": "AGENT_NOT_FOUND",
                "message": f"Agent '{id}' is not registered.",
                "details": {"available": available},
            },
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="AO module not available")

    # Build context
    context = req.context or {}
    context.setdefault("project_id", context.get("project_id", "default"))
    context.setdefault("trace_id", __import__("uuid").uuid4().hex[:12])

    # Publish AO_REQUEST to Central Bus
    try:
        from central_bus.models import BusMessage
        from central_bus.queue import enqueue

        msg = BusMessage(
            from_dept="architect",
            to_dept="orchestrator",
            type="AO_REQUEST",
            project_id=context.get("project_id", "default"),
            phase=context.get("phase", "general"),
            payload={
                "agent_id": id,
                "context": context,
                "timeout": req.timeout or 300,
            },
            trace_id=context["trace_id"],
            priority="high",
        )
        enqueue(msg)
    except ImportError:
        # Fallback: run synchronously (blocking)
        log.warning("Central Bus not available — running agent synchronously")
        try:
            result = adapter.invoke(context, timeout=req.timeout or 300)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        return AgentRunResponse(
            trace_id=context["trace_id"],
            status="queued",
            agent_id=id,
            check_url=f"/api/v1/agents/{id}/status?trace_id={context['trace_id']}",
            message="Agent executed synchronously (Central Bus unavailable)",
        )

    return AgentRunResponse(
        trace_id=context["trace_id"],
        status="pending",
        agent_id=id,
        check_url=f"/api/v1/agents/{id}/status?trace_id={context['trace_id']}",
        message=f"Agent '{id}' queued — poll status with trace_id",
    )


# ═══════════════════════════════════════════════════════════════════════
# Agent status (poll)
# ═══════════════════════════════════════════════════════════════════════


@router.get("/{id}/status")
async def get_agent_status(id: str, trace_id: str):
    """Poll the status of an agent execution.

    Checks the Central Bus audit log for the matching trace_id.
    If the agent has completed, the result is returned.
    If still pending, the caller should continue polling.
    """
    # Normalise agent_id for lookup
    agent_id = id

    # Try to read result from audit log
    try:
        from central_bus.audit import read as audit_read
        from central_bus.queue import dequeue
    except ImportError:
        raise HTTPException(status_code=503, detail="Central Bus not available")

    # Strategy: look through today's audit log for AO_RESPONSE with matching trace_id
    # In a production system, this would use a proper result store.
    # For Phase 3-4, we scan the audit trail (acceptable for small scale).

    # Check if there's a response message with this trace_id
    import json
    from pathlib import Path
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bus_projects = Path(__file__).parent.parent.parent.parent / "bus" / "projects"

    # Search across all project audit logs
    if bus_projects.exists():
        for proj_dir in bus_projects.iterdir():
            if not proj_dir.is_dir():
                continue
            audit_file = proj_dir / "audit" / f"{today}.jsonl"
            if not audit_file.exists():
                continue
            try:
                for line in audit_file.read_text().splitlines():
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    payload = record.get("payload", {})
                    req_trace = (
                        payload.get("trace_id")
                        or payload.get("request_trace_id")
                        or record.get("trace_id", "")
                    )
                    if req_trace == trace_id:
                        # Found matching response
                        result = payload.get("result", payload)
                        is_success = result.get("success", False) or result.get("status") == "success"
                        return AgentStatusResponse(
                            trace_id=trace_id,
                            status="success" if is_success else "failed",
                            agent_id=agent_id,
                            elapsed_ms=int(result.get("elapsed", 0) * 1000),
                            output=result if is_success else None,
                            error=result.get("error") if not is_success else None,
                        )
            except (json.JSONDecodeError, OSError):
                continue

    # Not found — still pending
    return AgentStatusResponse(
        trace_id=trace_id,
        status="pending",
        agent_id=agent_id,
        message="Agent execution pending or trace_id not found",
    )
