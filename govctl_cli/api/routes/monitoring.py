"""
Monitoring Routes — Health check, Metrics, System status.

Reads from Central Bus queue/state to provide observability data
for the Dashboard MVP.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter

from ...api.models import MetricSnapshot, HealthCheck, to_dict_skip_empty

log = logging.getLogger("govctl.api.monitoring")

router = APIRouter(prefix="/api/v1", tags=["Monitoring"])


# ═══════════════════════════════════════════════════════════════════════
# Health check
# ═══════════════════════════════════════════════════════════════════════


@router.get("/health")
async def health_check():
    """Health check for all system components.

    Returns 200 if all components are functional,
    503 if any critical component is degraded.
    """
    components = {}

    # 1. API itself — always OK if responding
    components["api"] = {"status": "ok"}

    # 2. Central Bus — check queue accessibility
    try:
        from central_bus.queue import QUEUE_DIR
        from central_bus.state import PROJECTS_DIR

        queue_path = str(QUEUE_DIR)
        queue_exists = QUEUE_DIR.exists()

        # Count total messages
        message_count = 0
        if queue_exists:
            for f in QUEUE_DIR.glob("*.jsonl"):
                try:
                    message_count += len(f.read_text().splitlines())
                except OSError:
                    pass

        # Count dead letters
        dead_count = 0
        dl_dir = QUEUE_DIR / "dead_letter"
        if dl_dir.exists():
            for f in dl_dir.glob("*.jsonl"):
                try:
                    dead_count += len(f.read_text().splitlines())
                except OSError:
                    pass

        bus_status = "ok" if queue_exists else "error"
        components["central_bus"] = {
            "status": bus_status,
            "queue_path": queue_path,
            "message_count": message_count,
            "dead_letter_count": dead_count,
        }
    except ImportError:
        components["central_bus"] = {
            "status": "error",
            "detail": "Central Bus module not available",
        }
    except Exception as exc:
        components["central_bus"] = {
            "status": "error",
            "detail": str(exc),
        }

    # 3. AO CLI — check binary on PATH
    try:
        ao_path = shutil.which("agent_orchestrator")
        if ao_path:
            # Try to get version
            import subprocess
            version = None
            try:
                result = subprocess.run(
                    ["agent_orchestrator", "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    version = result.stdout.strip() or result.stderr.strip()
            except (subprocess.TimeoutExpired, OSError):
                pass

            components["ao_cli"] = {
                "status": "ok",
                "path": ao_path,
                "version": version,
            }
        else:
            components["ao_cli"] = {
                "status": "not_configured",
                "path": "",
                "version": None,
            }
    except Exception as exc:
        components["ao_cli"] = {
            "status": "error",
            "detail": str(exc),
        }

    # 4. Governance directory — check writability
    try:
        gov_dir = Path("gov")
        adr_dir = gov_dir / "adr"
        rfc_dir = gov_dir / "rfc"
        guard_dir = gov_dir / "guards"

        components["gov_dir"] = {
            "status": "ok" if gov_dir.exists() else "error",
            "adr_count": len(list(adr_dir.glob("*.toml"))) if adr_dir.exists() else 0,
            "rfc_count": len(list(rfc_dir.glob("*.toml"))) if rfc_dir.exists() else 0,
            "guard_count": len(list(guard_dir.glob("*.toml"))) if guard_dir.exists() else 0,
        }
    except Exception as exc:
        components["gov_dir"] = {
            "status": "error",
            "detail": str(exc),
        }

    # Determine overall status
    statuses = [c.get("status", "error") for c in components.values()]
    if "error" in statuses:
        overall = "degraded"
    elif "not_configured" in statuses and all(
        s != "error" for s in statuses
    ):
        overall = "degraded"
    else:
        overall = "ok"

    # Return 503 if degraded/unhealthy/error
    from fastapi import HTTPException

    health = HealthCheck(
        status=overall,
        version="1.0.0",
        components=components,
    )

    # FastAPI will still return 200 unless we raise
    if overall in ("degraded", "unhealthy"):
        raise HTTPException(status_code=503, detail=to_dict_skip_empty(health))

    return health


# ═══════════════════════════════════════════════════════════════════════
# System metrics
# ═══════════════════════════════════════════════════════════════════════


@router.get("/metrics")
async def get_metrics(period: str = "current"):
    """Get current system metrics snapshot.

    Args:
        period: Time period — current, last_hour, last_24h, last_7d
                (aggregation varies by period)
    """
    metrics = MetricSnapshot()

    # 1. Count active projects
    try:
        from central_bus.state import PROJECTS_DIR
        if PROJECTS_DIR.exists():
            active = 0
            for p_dir in PROJECTS_DIR.iterdir():
                if not p_dir.is_dir():
                    continue
                state_file = p_dir / "state.json"
                if state_file.exists():
                    try:
                        state = json.loads(state_file.read_text())
                        if state.get("status") in ("in_progress",):
                            active += 1
                    except (json.JSONDecodeError, OSError):
                        pass
            metrics.active_projects = active
    except ImportError:
        pass

    # 2. Count queued messages
    try:
        from central_bus.queue import QUEUE_DIR
        priorities = {"critical": 0, "high": 0, "normal": 0, "low": 0}

        if QUEUE_DIR.exists():
            for priority in priorities:
                queue_file = QUEUE_DIR / f"{priority}.jsonl"
                if queue_file.exists():
                    try:
                        lines = queue_file.read_text().splitlines()
                        priorities[priority] = len([l for l in lines if l.strip()])
                    except OSError:
                        pass

            # Dead letters
            dl_dir = QUEUE_DIR / "dead_letter"
            dead_count = 0
            if dl_dir.exists():
                for f in dl_dir.glob("*.jsonl"):
                    try:
                        dead_count += len(f.read_text().splitlines())
                    except OSError:
                        pass
            metrics.dead_letter_count = dead_count

        metrics.queued_messages = sum(priorities.values())
        metrics.queued_by_priority = priorities
    except ImportError:
        pass

    # 3. Agent call statistics (from state or event log)
    try:
        # Read from all project audit logs for today
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        total_calls = 0
        failed_calls = 0
        total_time_ms = 0

        from central_bus.state import PROJECTS_DIR
        if PROJECTS_DIR.exists():
            for p_dir in PROJECTS_DIR.iterdir():
                if not p_dir.is_dir():
                    continue
                audit_file = p_dir / "audit" / f"{today}.jsonl"
                if not audit_file.exists():
                    continue
                try:
                    for line in audit_file.read_text().splitlines():
                        if not line.strip():
                            continue
                        record = json.loads(line)
                        payload = record.get("payload", {})
                        result = payload.get("result", payload)

                        if record.get("type") == "AO_RESPONSE":
                            total_calls += 1
                            if not result.get("success", False):
                                failed_calls += 1
                            total_time_ms += int(result.get("elapsed", 0) * 1000)
                except (json.JSONDecodeError, OSError):
                    continue

        metrics.agent_calls_total = total_calls
        metrics.agent_calls_failed = failed_calls
        metrics.agent_success_rate = (
            (total_calls - failed_calls) / total_calls if total_calls > 0 else 1.0
        )
        metrics.avg_response_time_ms = (
            total_time_ms / total_calls if total_calls > 0 else 0.0
        )
    except ImportError:
        pass

    # 4. Health score (composite)
    health_score = _compute_health_score(metrics)
    metrics.health_score = health_score

    return metrics


# ═══════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════


def _compute_health_score(metrics: MetricSnapshot) -> float:
    """Compute a composite pipeline health score (0.0 - 1.0).

    Factors:
        - Dead letter ratio:   1 - (dead / total)  weight: 0.25
        - Agent success rate:  success_rate         weight: 0.35
        - Active projects:     min(projects/10, 1)  weight: 0.20
        - Queue pressure:      1 - (queue/100)      weight: 0.20
    """
    total = metrics.queued_messages or 1
    dead_ratio = 1.0 - (metrics.dead_letter_count / total)

    success_rate = metrics.agent_success_rate if metrics.agent_calls_total > 0 else 1.0

    project_score = min(metrics.active_projects / 10.0, 1.0)

    queue_pressure = max(0.0, 1.0 - (metrics.queued_messages / 100.0))

    score = (
        dead_ratio * 0.25
        + success_rate * 0.35
        + project_score * 0.20
        + queue_pressure * 0.20
    )

    return round(min(max(score, 0.0), 1.0), 4)
