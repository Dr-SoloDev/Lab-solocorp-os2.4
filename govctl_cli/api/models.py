"""
Admin API — Pydantic Models / Data Classes

All request/response models for the SoloCorp OS Admin REST API.
Split into categories matching the route groups:

    models.py
    ├── Governance (ADR, RFC, Guard)
    ├── Agent (request, response, status)
    ├── Pipeline (status, history, events)
    └── Monitoring (metrics, health, snapshots)

Note on inheritance:
    We *intentionally* re-define fields here instead of importing from
    central_bus.models (BusMessage) or govctl_cli modules, to keep the
    API layer decoupled from internal serialization formats.
    The API translates between wire JSON and internal representation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# ══════════════════════════════════════════════════════════════════════
# Shared base
# ══════════════════════════════════════════════════════════════════════


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


# ══════════════════════════════════════════════════════════════════════
# Governance — ADR
# ══════════════════════════════════════════════════════════════════════


@dataclass
class ADRSummary:
    """Summary view of an Architecture Decision Record."""

    id: str
    title: str
    status: str  # proposed | accepted | deprecated | superseded
    domain: str = ""
    impact: str = ""
    date: str = ""
    author: str = ""


@dataclass
class ADRCreateRequest:
    """Payload for POST /api/v1/gov/adrs."""

    title: str
    status: str = "proposed"
    context: str = ""
    decision: str = ""
    consequences: str = ""
    domain: str = ""
    impact: str = "medium"  # low | medium | high | critical
    author: str = ""


@dataclass
class ADRDetail(ADRSummary):
    """Full ADR content including context, decision, consequences."""

    context: str = ""
    decision: str = ""
    consequences: str = ""
    options: list[dict] = field(default_factory=list)
    path: str = ""


# ══════════════════════════════════════════════════════════════════════
# Governance — RFC
# ══════════════════════════════════════════════════════════════════════


@dataclass
class RFCSummary:
    """Summary view of a Request for Comments."""

    id: str
    title: str
    status: str  # draft | review | approved | rejected | implemented
    domain: str = ""
    author: str = ""
    date: str = ""
    complexity_score: int = 0


@dataclass
class RFCCreateRequest:
    """Payload for POST /api/v1/gov/rfcs."""

    title: str
    status: str = "draft"
    background: str = ""
    proposal: str = ""
    domain: str = ""
    complexity_score: int = 0
    author: str = ""


@dataclass
class RFCDetail(RFCSummary):
    """Full RFC content."""

    background: str = ""
    proposal: str = ""
    alternatives: list[str] = field(default_factory=list)
    implementation: str = ""
    path: str = ""


# ══════════════════════════════════════════════════════════════════════
# Governance — Guard
# ══════════════════════════════════════════════════════════════════════


@dataclass
class GuardSummary:
    """Summary of a verification guard."""

    name: str
    status: str  # pending | running | passed | failed
    project_id: str = ""
    added_at: str = ""


@dataclass
class GuardCreateRequest:
    """Payload for POST /api/v1/gov/guards."""

    name: str
    project_id: str
    phase: str = ""
    description: str = ""


@dataclass
class GuardDetail(GuardSummary):
    """Full guard detail with result data."""

    phase: str = ""
    description: str = ""
    resolved_at: Optional[str] = None
    detail: dict = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════
# Agent
# ══════════════════════════════════════════════════════════════════════


@dataclass
class AgentSummary:
    """Registered agent metadata from REGISTRY."""

    agent_id: str
    display_name: str
    description: str = ""
    mapped_profiles: list[str] = field(default_factory=list)


@dataclass
class AgentRunRequest:
    """Payload for POST /api/v1/agents/{id}/run."""

    context: dict  # forwarded to adapter.build_prompt()
    timeout: Optional[int] = None  # override default timeout


@dataclass
class AgentRunResponse:
    """Immediate response to an accepted agent run request.

    Status is always 'pending' — the client polls via get_agent_status().
    """

    trace_id: str = field(default_factory=_uuid)
    status: str = "pending"  # pending | queued
    agent_id: str = ""
    check_url: str = ""
    message: str = "Agent execution accepted"


@dataclass
class AgentStatusResponse:
    """Current status of an agent execution."""

    trace_id: str
    status: str  # pending | running | success | failed
    agent_id: str = ""
    elapsed_ms: Optional[int] = None
    output: Optional[dict] = None
    error: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════
# Pipeline
# ══════════════════════════════════════════════════════════════════════


@dataclass
class PipelineStatus:
    """Aggregated pipeline status for a project."""

    project_id: str
    name: str = ""
    status: str = "in_progress"  # pending | in_progress | done | failed
    phase: str = "spec"  # spec | design | arch | dev | qa | deploy
    progress_pct: int = 0
    phases: dict = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    guard_status: str = "pending"
    queue_depth: int = 0
    updated_at: str = field(default_factory=_now)


@dataclass
class PipelineEvent:
    """A single pipeline event (for monitoring / audit)."""

    id: str
    type: str  # governance | agent | deploy
    status: str  # pending | running | success | failed
    source: str = ""  # department ID
    timestamp: str = field(default_factory=_now)
    duration_ms: int = 0
    detail: dict = field(default_factory=dict)


@dataclass
class PipelineHistory:
    """Paginated pipeline event history."""

    items: list[PipelineEvent] = field(default_factory=list)
    total: int = 0
    project_id: str = ""


# ══════════════════════════════════════════════════════════════════════
# Monitoring
# ══════════════════════════════════════════════════════════════════════


@dataclass
class MetricSnapshot:
    """Point-in-time snapshot of system metrics."""

    timestamp: str = field(default_factory=_now)
    active_projects: int = 0
    queued_messages: int = 0
    queued_by_priority: dict = field(default_factory=lambda: {
        "critical": 0, "high": 0, "normal": 0, "low": 0,
    })
    agent_calls_total: int = 0
    agent_calls_failed: int = 0
    agent_success_rate: float = 1.0
    avg_response_time_ms: float = 0.0
    dead_letter_count: int = 0
    health_score: float = 1.0


@dataclass
class ComponentHealth:
    """Health status of a single system component."""

    status: str = "ok"  # ok | error | not_configured
    detail: Any = None


@dataclass
class HealthCheck:
    """System-wide health check response."""

    status: str = "ok"  # ok | degraded | unhealthy
    timestamp: str = field(default_factory=_now)
    version: str = "1.0.0"
    components: dict = field(default_factory=lambda: {
        "api": {"status": "ok"},
        "central_bus": {"status": "ok", "queue_path": "", "message_count": 0},
        "ao_cli": {"status": "not_configured", "path": "", "version": None},
        "gov_dir": {"status": "ok", "adr_count": 0, "rfc_count": 0, "guard_count": 0},
    })


# ══════════════════════════════════════════════════════════════════════
# Generic helpers
# ══════════════════════════════════════════════════════════════════════


@dataclass
class ApiError:
    """Standard error response body."""

    code: str
    message: str
    details: Optional[dict] = None


@dataclass
class ApiErrorResponse:
    """Wrapper for error responses."""

    error: ApiError
    trace_id: str = field(default_factory=_uuid)


# ══════════════════════════════════════════════════════════════════════
# Serialization helpers
# ══════════════════════════════════════════════════════════════════════


def to_dict(instance) -> dict:
    """Convert any dataclass instance to a dict, skipping None values.

    Usage:
        return JSONResponse(to_dict(adr_detail))
    """
    result = {}
    for key, value in asdict(instance).items():
        if value is not None:
            result[key] = value
    return result


def to_dict_skip_empty(instance) -> dict:
    """Like to_dict() but also skips empty lists and empty strings."""
    result = {}
    for key, value in asdict(instance).items():
        if value is None:
            continue
        if isinstance(value, (list, dict, str)) and not value:
            continue
        result[key] = value
    return result


__all__ = [
    # Governance
    "ADRSummary", "ADRDetail", "ADRCreateRequest",
    "RFCSummary", "RFCDetail", "RFCCreateRequest",
    "GuardSummary", "GuardDetail", "GuardCreateRequest",
    # Agent
    "AgentSummary", "AgentRunRequest", "AgentRunResponse",
    "AgentStatusResponse",
    # Pipeline
    "PipelineStatus", "PipelineEvent", "PipelineHistory",
    # Monitoring
    "MetricSnapshot", "ComponentHealth", "HealthCheck",
    # Helpers
    "ApiError", "ApiErrorResponse",
    "to_dict", "to_dict_skip_empty",
]
