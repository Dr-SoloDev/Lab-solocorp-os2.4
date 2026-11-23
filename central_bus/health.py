"""Health check logic for Central Bus."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi.responses import JSONResponse

from central_bus import __version__ as VERSION
from central_bus.facts import FactsService
from central_bus.queue import SQLiteQueueManager
from central_bus.router import RoutingEngine
from central_bus.routing_sync import routing_sync_status

log = logging.getLogger(__name__)


async def get_health(
    db: Any,
    qm: SQLiteQueueManager,
    facts_service: FactsService,
    engine: RoutingEngine,
    started_at: float,
) -> dict | JSONResponse:
    """Return health check data or a JSONResponse(503) on error.

    Args:
        db: DbManager instance — used for a quick connectivity ping.
        qm: SQLiteQueueManager for queue depth counters.
        facts_service: FactsService for facts count.
        engine: RoutingEngine for routing rules count.
        started_at: Unix timestamp (float) of process start, for uptime calc.
    """
    try:
        # Quick DB connectivity check
        await db.fetch_one("SELECT 1 AS ok")

        pending_count = await qm.count_pending()
        failed_count = await qm.count_failed()
        dead_count = await qm.count_dead_letters()
        facts_count = await facts_service.count_facts()
        rules_count = await engine.count_rules()
        # ADR-040 Wave 1 — drift visibility. Direct DB count (not the engine's
        # 60s cache) so a freshly seeded DB is visible without a restart.
        routing_status = await routing_sync_status(db)
        db_rules_count = routing_status["db_rules"]
        oldest_routed = await qm.oldest_routed_age_seconds()
        uptime = int(time.time() - started_at)

        # Degraded status if dead letters exist
        status = "degraded" if dead_count > 0 else "ok"

        return {
            "status": status,
            "db": {
                "queue_pending": pending_count,
                "queue_failed": failed_count,
                "queue_dead": dead_count,
            },
            "facts_count": facts_count,
            "routing_rules": db_rules_count if db_rules_count is not None else rules_count,
            "routing_rules_cached": rules_count,
            "rules_in_sync": routing_status["rules_in_sync"],
            "routing_json_rules": routing_status["json_rules"],
            "oldest_routed_age_seconds": oldest_routed,
            "loops_active": 0,  # placeholder — injected by orchestrator
            "uptime_seconds": uptime,
            "version": VERSION,
        }
    except Exception as exc:
        log.exception("Health check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "detail": "Internal health check error",
                "uptime_seconds": int(time.time() - started_at),
                "version": VERSION,
            },
        )
