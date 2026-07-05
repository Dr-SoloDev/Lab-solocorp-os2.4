"""Central Bus v0.6 — FastAPI Daemon (busd).

Endpoints
~~~~~~~~~
* ``POST /v1/observe``       — Receive a task from an agent, enqueue, and route
* ``POST /v1/context``       — Provide context (facts + queue status) to an agent
* ``POST /v1/update``        — Report result back; triggers AAR on completion/failure
* ``GET  /v1/health``        — Health check: DB, queue depth, uptime
* ``GET  /v1/aar/{trace_id}``— Retrieve After Action Review entries for a trace

Error Envelope
~~~~~~~~~~~~~~
All error responses follow::

    {"error": {"code": "<CODE>", "message": "...", "detail": {...}}}

Startup
~~~~~~~
::

    uvicorn central_bus.main:app --host 127.0.0.1 --port 8099
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from central_bus.config import settings
from central_bus.db import DbManager, ensure_db, get_db, new_id, now_iso
from central_bus.facts import FactsService
from central_bus.models import BusMessage
from central_bus.queue import SQLiteQueueManager
from central_bus.router import RoutingEngine, route as jsonl_route

log = logging.getLogger(__name__)

# ── Startup timestamp ────────────────────────────────────────────────
_STARTED_AT: float = time.time()


# ═══════════════════════════════════════════════════════════════════════
# Request / Response models (plain dicts — no Pydantic dependency needed)
# ═══════════════════════════════════════════════════════════════════════

# These are documented inline in the endpoint signatures for clarity.
# Actual validation is done in the handler body for simplicity.


# ═══════════════════════════════════════════════════════════════════════
# Lifespan — FastAPI 0.139 reuse the lifespan pattern
# ═══════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB schema; shutdown: close resources."""
    log.info("Central Bus v0.6 starting up (pid=%d)", settings.pid)
    # DB is lazily initialised on first use via get_db()
    yield
    log.info("Central Bus v0.6 shutting down")


# ═══════════════════════════════════════════════════════════════════════
# FastAPI app
# ═══════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Central Bus v0.6",
    version="0.6.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════
# Error handlers
# ═══════════════════════════════════════════════════════════════════════

def _error_response(
    code: str, message: str, detail: Any, request_id: str = ""
) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
            "request_id": request_id or str(uuid.uuid4()),
        }
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    headers = getattr(exc, "headers", None)
    body = _error_response(
        code="HTTP_ERROR",
        message=exc.detail,
        detail={},
        request_id=request.headers.get("X-Request-Id", ""),
    )
    return JSONResponse(status_code=exc.status_code, content=body, headers=headers)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled exception on %s %s", request.method, request.url.path)
    body = _error_response(
        code="INTERNAL_ERROR",
        message="Internal server error",
        detail={"error": str(exc)},
        request_id=request.headers.get("X-Request-Id", ""),
    )
    return JSONResponse(status_code=500, content=body)


# ═══════════════════════════════════════════════════════════════════════
# Dependency helpers
# ═══════════════════════════════════════════════════════════════════════

async def _get_services():
    """Convenience: get db, queue, facts, routing in one call."""
    db = await ensure_db()
    return {
        "db": db,
        "queue": SQLiteQueueManager(db),
        "facts": FactsService(db),
        "router": RoutingEngine(db),
    }


# ═══════════════════════════════════════════════════════════════════════
# POST /v1/observe
# ═══════════════════════════════════════════════════════════════════════

@app.post("/v1/observe")
async def observe(request: Request):
    """Receive a task from an agent, enqueue it, and route it."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=_error_response(
                code="VALIDATION_ERROR",
                message="Request body must be valid JSON",
                detail={"reason": "invalid JSON"},
                request_id=request.headers.get("X-Request-Id", ""),
            ),
        )

    # Validate required fields
    trace_id = payload.get("trace_id", new_id())
    task_id = payload.get("task_id")
    source_agent = payload.get("source_agent")
    msg_payload = payload.get("payload", {})
    priority = payload.get("priority", "normal")
    target_agent = payload.get("target_agent")

    if not task_id:
        return JSONResponse(
            status_code=400,
            content=_error_response(
                code="VALIDATION_ERROR",
                message="Request payload validation failed",
                detail={"field": "task_id", "reason": "missing"},
                request_id=request.headers.get("X-Request-Id", ""),
            ),
        )
    if not source_agent:
        return JSONResponse(
            status_code=400,
            content=_error_response(
                code="VALIDATION_ERROR",
                message="Request payload validation failed",
                detail={"field": "source_agent", "reason": "missing"},
                request_id=request.headers.get("X-Request-Id", ""),
            ),
        )
    if not isinstance(msg_payload, dict):
        return JSONResponse(
            status_code=422,
            content=_error_response(
                code="VALIDATION_ERROR",
                message="Payload format is invalid",
                detail={"field": "payload", "reason": "expected object, got array"},
                request_id=request.headers.get("X-Request-Id", ""),
            ),
        )

    services = await _get_services()
    qm: SQLiteQueueManager = services["queue"]
    engine: RoutingEngine = services["router"]

    # Create queue entry
    msg = await qm.create_message(
        trace_id=trace_id,
        task_id=task_id,
        agent_id=source_agent,
        payload=msg_payload,
        target_agent=target_agent,
        priority=priority,
        max_retries=payload.get("max_retries", 3),
    )
    msg_id = msg["id"]

    # Route the message
    route_to = await engine.match(
        source_agent=source_agent,
        payload=msg_payload,
        fallback_department="ceo",
    )
    await qm.update_status(msg_id, "routed")

    # Audit trail
    await services["db"].execute(
        """
        INSERT INTO audit_log (id, trace_id, action, agent_id, entity_type, entity_id, payload, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id(),
            trace_id,
            "queue.create",
            source_agent,
            "queue",
            msg_id,
            json.dumps({"route_to": route_to, "priority": priority}),
            now_iso(),
        ),
    )

    return {
        "trace_id": trace_id,
        "queue_id": msg_id,
        "status": "routed",
        "route_to": route_to,
        "hops": ["queue", "route"],
    }


# ═══════════════════════════════════════════════════════════════════════
# POST /v1/context
# ═══════════════════════════════════════════════════════════════════════

@app.post("/v1/context")
async def get_context(request: Request):
    """Provide context (facts + queue status) to an agent."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=_error_response(
                code="VALIDATION_ERROR",
                message="Request body must be valid JSON",
                detail={"reason": "invalid JSON"},
                request_id=request.headers.get("X-Request-Id", ""),
            ),
        )

    trace_id = payload.get("trace_id", new_id())
    agent_id = payload.get("agent_id")
    keys = payload.get("keys", [])

    if not agent_id:
        return JSONResponse(
            status_code=400,
            content=_error_response(
                code="VALIDATION_ERROR",
                message="Request payload validation failed",
                detail={"field": "agent_id", "reason": "missing"},
                request_id=request.headers.get("X-Request-Id", ""),
            ),
        )

    services = await _get_services()
    facts_service: FactsService = services["facts"]
    qm: SQLiteQueueManager = services["queue"]

    # Fetch matching facts
    all_facts: list[dict] = []
    for key_pattern in keys:
        facts = await facts_service.list_facts(prefix=key_pattern, limit=100)
        all_facts.extend(facts)

    # Queue metadata
    pending_count = await qm.count_pending()

    return {
        "trace_id": trace_id,
        "context_id": new_id(),
        "facts": [
            {"key": f["key"], "value": f["value"], "version": f["version"]}
            for f in all_facts
        ],
        "queue_pending": pending_count,
        "agent_health": "ok",
    }


# ═══════════════════════════════════════════════════════════════════════
# POST /v1/update
# ═══════════════════════════════════════════════════════════════════════

@app.post("/v1/update")
async def update_message(request: Request):
    """Report result back to the bus.  Triggers AAR on completion/failure."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=_error_response(
                code="VALIDATION_ERROR",
                message="Request body must be valid JSON",
                detail={"reason": "invalid JSON"},
                request_id=request.headers.get("X-Request-Id", ""),
            ),
        )

    trace_id = payload.get("trace_id")
    queue_id = payload.get("queue_id")
    agent_id = payload.get("agent_id")
    status = payload.get("status", "completed")
    result = payload.get("result")
    error = payload.get("error")

    if not trace_id or not queue_id:
        return JSONResponse(
            status_code=400,
            content=_error_response(
                code="VALIDATION_ERROR",
                message="Request payload validation failed",
                detail={
                    "field": "trace_id/queue_id",
                    "reason": "trace_id and queue_id are required",
                },
                request_id=request.headers.get("X-Request-Id", ""),
            ),
        )

    services = await _get_services()
    qm: SQLiteQueueManager = services["queue"]

    # Update message status
    try:
        updated = await qm.update_status(
            message_id=queue_id,
            status=status,
            result=result,
            error=error,
            agent_id=agent_id,
        )
    except ValueError:
        return JSONResponse(
            status_code=404,
            content=_error_response(
                code="NOT_FOUND",
                message="queue_id not found",
                detail={"entity": "queue", "id": queue_id},
                request_id=request.headers.get("X-Request-Id", ""),
            ),
        )

    # Audit entry
    await services["db"].execute(
        """
        INSERT INTO audit_log (id, trace_id, action, agent_id, entity_type, entity_id, payload, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id(),
            trace_id,
            "queue.update",
            agent_id,
            "queue",
            queue_id,
            json.dumps({"status": status, "error": error}),
            now_iso(),
        ),
    )

    # ── AAR generation hook ──────────────────────────────────────
    aar_id = None
    final_status = status
    is_terminal = status in ("completed", "failed")

    if is_terminal:
        retry_count = updated.get("retry_count", 0)
        max_retries = updated.get("max_retries", 3)
        is_dead = retry_count >= max_retries and status == "failed"

        if is_dead:
            final_status = "dead"

        # Calculate latency
        created_at_str = updated.get("created_at", now_iso())
        try:
            created_dt = datetime.fromisoformat(created_at_str)
            latency_ms = int(
                (datetime.now(timezone.utc) - created_dt).total_seconds() * 1000
            )
        except (ValueError, TypeError):
            latency_ms = 0

        entry = {
            "aar_id": f"aar-{new_id()}",
            "trace_id": trace_id,
            "task_id": updated.get("task_id", ""),
            "queue_id": queue_id,
            "total_hops": len(
                json.loads(updated.get("routing_hops", "[]"))
            ),
            "total_retries": retry_count,
            "final_status": final_status,
            "latency_ms": latency_ms,
            "failure_pattern": (
                error if is_dead else None
            ),
            "notes": None,
            "created_at": now_iso(),
        }

        await services["db"].execute(
            """
            INSERT INTO aar (id, trace_id, task_id, queue_id, total_hops,
                             total_retries, final_status, latency_ms,
                             failure_pattern, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry["aar_id"],
                trace_id,
                entry["task_id"],
                queue_id,
                entry["total_hops"],
                retry_count,
                final_status,
                latency_ms,
                entry["failure_pattern"],
                None,
                entry["created_at"],
            ),
        )
        aar_id = entry["aar_id"]
        log.info(
            "AAR generated: %s (trace=%s, status=%s, latency=%dms)",
            aar_id, trace_id, final_status, latency_ms,
        )

    return {
        "trace_id": trace_id,
        "queue_id": queue_id,
        "status": final_status,
        "dead_letter": final_status == "dead",
        **({"aar_id": aar_id} if aar_id else {}),
    }


# ═══════════════════════════════════════════════════════════════════════
# GET /v1/health
# ═══════════════════════════════════════════════════════════════════════

@app.get("/v1/health")
async def health():
    """Health check — DB status, queue depth, uptime."""
    try:
        services = await _get_services()
        db = services["db"]
        qm: SQLiteQueueManager = services["queue"]
        facts_service: FactsService = services["facts"]
        engine: RoutingEngine = services["router"]

        # Quick DB connectivity check
        await db.fetch_one("SELECT 1 AS ok")

        pending_count = await qm.count_pending()
        failed_count = await qm.count_failed()
        dead_count = await qm.count_dead_letters()
        facts_count = await facts_service.count_facts()
        rules_count = await engine.count_rules()
        uptime = int(time.time() - _STARTED_AT)

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
            "routing_rules": rules_count,
            "loops_active": 0,  # placeholder — injected by orchestrator
            "uptime_seconds": uptime,
            "version": "0.6.0",
        }
    except Exception as exc:
        log.exception("Health check failed")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "detail": str(exc),
                "uptime_seconds": int(time.time() - _STARTED_AT),
                "version": "0.6.0",
            },
        )


# ═══════════════════════════════════════════════════════════════════════
# GET /v1/aar/{trace_id}
# ═══════════════════════════════════════════════════════════════════════

@app.get("/v1/aar/{trace_id}")
async def get_aar(trace_id: str):
    """Retrieve AAR entries for a trace, ordered by created_at DESC."""
    services = await _get_services()
    db = services["db"]
    rows = await db.fetch_all(
        "SELECT * FROM aar WHERE trace_id = ? ORDER BY created_at DESC",
        (trace_id,),
    )
    entries = []
    for row in rows:
        d = dict(row)
        entries.append(d)
    return entries


# ═══════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "central_bus.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )
