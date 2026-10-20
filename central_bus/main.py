"""Central Bus v0.6 — FastAPI Daemon (busd).

Endpoints
~~~~~~~~~
* ``POST /v1/observe``       — Receive a task from an agent, enqueue, and route
* ``POST /v1/context``       — Provide context (facts + queue status) to an agent
* ``POST /v1/web-read``      — Read/search a web page with a real browser (no display)
* ``POST /v1/update``        — Report result back; triggers AAR on completion/failure
* ``GET  /v1/health``        — Health check: DB, queue depth, uptime
* ``GET  /v1/aar/{trace_id}``— Retrieve After Action Review entries for a trace
* ``GET  /v1/ab-test/report``— A/B test 50/50: route_v1 vs route_v2 metrics report
* ``GET  /v1/route_v1``      — A/B test variant entry (v1/legacy side)
* ``GET  /v1/route_v2``      — A/B test variant entry (v2/behavior side)

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

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from central_bus.aar import AARGenerator
from central_bus.api_compliance import router as compliance_router
from central_bus.api_keys import validate_key, hash_key, extract_agent_from_key
from central_bus.config import settings
from central_bus.db import DbManager, ensure_db, get_db, new_id, now_iso
from central_bus.facts import FactsService
from central_bus.health import get_health
from central_bus.models import BusMessage
from central_bus.queue import SQLiteQueueManager
from central_bus.router import RoutingEngine, route as jsonl_route
from central_bus.router import get_ab_report
from central_bus.ab_test import router as ab_test_router
from central_bus.ab_test import get_all_reports as get_ab_experiment_reports

log = logging.getLogger(__name__)

# ── Startup timestamp ────────────────────────────────────────────────
_STARTED_AT: float = time.time()


# ═══════════════════════════════════════════════════════════════════════
# Lifespan
# ═══════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def _lifespan(app):
    log.info("Central Bus v0.6.2 starting up (pid=%d)", os.getpid())
    yield
    log.info("Central Bus v0.6.2 shutting down")


# ═══════════════════════════════════════════════════════════════════════
# FastAPI app
# ═══════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Central Bus v0.6",
    version="0.6.2",
    lifespan=_lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Key Authentication Middleware ──────────────────────────────────
_ADMIN_KEY = os.environ.get(
    "SOLOCORP_API_KEY", "sk-solocorp-admin-local-dev-001"
)


@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    """Check API Key for every request (except health/docs/skills)."""
    if request.url.path in (
        "/v1/health", "/docs", "/openapi.json",
        "/v1/skills",
    ) or request.url.path.startswith("/v1/skills/"):
        return await call_next(request)
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        # COMPAT (until 2026-10-04): accept legacy Authorization: Bearer <key>.
        # TODO(2026-10-04): remove Bearer fallback — all clients on X-API-Key.
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            api_key = auth[len("Bearer "):].strip()
            log.warning("compat Bearer auth used on %s — migrate to X-API-Key",
                        request.url.path)
    if api_key == _ADMIN_KEY:
        return await call_next(request)
    if api_key:
        try:
            db = await ensure_db()
            key_data = await validate_key(db, api_key)
            if key_data:
                request.state.agent_id = key_data["agent_id"]
                request.state.key_scope = key_data["scope"]
                return await call_next(request)
        except Exception:
            pass
    return JSONResponse(
        status_code=401,
        content=_error_response(
            code="UNAUTHORIZED",
            message="Invalid or missing API key. Use X-API-Key header.",
            detail={"hint": "Set header: X-API-Key: sk-{agent_id}-{random}"},
            request_id=request.headers.get("X-Request-Id", ""),
        ),
    )


# ── Routers ───────────────────────────────────────────────────────────
app.include_router(compliance_router)
from central_bus.skills_router import router as skills_router
app.include_router(skills_router)
app.include_router(ab_test_router)


# ═══════════════════════════════════════════════════════════════════════
# Error handlers
# ═══════════════════════════════════════════════════════════════════════

def _error_response(code: str, message: str, detail: Any, request_id: str = "") -> dict:
    return {
        "error": {
            "code": code, "message": message, "detail": detail,
            "request_id": request_id or str(uuid.uuid4()),
        }
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    headers = getattr(exc, "headers", None)
    body = _error_response(
        code="HTTP_ERROR", message=exc.detail, detail={},
        request_id=request.headers.get("X-Request-Id", ""),
    )
    return JSONResponse(status_code=exc.status_code, content=body, headers=headers)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled exception on %s %s", request.method, request.url.path)
    body = _error_response(
        code="INTERNAL_ERROR", message="Internal server error",
        detail={"error": str(exc)}, request_id="",
    )
    return JSONResponse(status_code=500, content=body)


# ═══════════════════════════════════════════════════════════════════════
# Lifespan
# ═══════════════════════════════════════════════════════════════════════
# Dependency helpers
# ═══════════════════════════════════════════════════════════════════════

async def _get_services():
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
        return JSONResponse(status_code=400, content=_error_response(
            code="VALIDATION_ERROR", message="Request body must be valid JSON",
            detail={"reason": "invalid JSON"},
            request_id=request.headers.get("X-Request-Id", ""),
        ))

    trace_id = payload.get("trace_id", new_id())
    task_id = payload.get("task_id")
    source_agent = payload.get("source_agent")
    msg_payload = payload.get("payload", {})
    priority = payload.get("priority", "normal")
    target_agent = payload.get("target_agent")

    if not task_id:
        return JSONResponse(status_code=400, content=_error_response(
            code="VALIDATION_ERROR", message="Request payload validation failed",
            detail={"field": "task_id", "reason": "missing"},
            request_id=request.headers.get("X-Request-Id", ""),
        ))
    if not source_agent:
        return JSONResponse(status_code=400, content=_error_response(
            code="VALIDATION_ERROR", message="Request payload validation failed",
            detail={"field": "source_agent", "reason": "missing"},
            request_id=request.headers.get("X-Request-Id", ""),
        ))
    if not isinstance(msg_payload, dict):
        return JSONResponse(status_code=422, content=_error_response(
            code="VALIDATION_ERROR", message="Payload format is invalid",
            detail={"field": "payload", "reason": "expected object, got array"},
            request_id=request.headers.get("X-Request-Id", ""),
        ))

    services = await _get_services()
    qm = services["queue"]
    engine = services["router"]

    msg = await qm.create_message(
        trace_id=trace_id, task_id=task_id, agent_id=source_agent,
        payload=msg_payload, target_agent=target_agent,
        priority=priority, max_retries=payload.get("max_retries", 3),
    )
    msg_id = msg["id"]

    route_to = await engine.match(
        source_agent=source_agent, payload=msg_payload, fallback_department="ceo",
    )
    await qm.update_status(msg_id, "routed")

    await services["db"].execute(
        "INSERT INTO audit_log (id, trace_id, action, agent_id, entity_type, entity_id, payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id(), trace_id, "queue.create", source_agent, "queue", msg_id,
         json.dumps({"route_to": route_to, "priority": priority}), now_iso()),
    )

    # ── report_back = รายงานถึง CEO (ไม่ใช่งานที่ต้องรอ consumer) ──
    # เดิมปล่อยให้ค้างเป็น 'routed' ตลอด → สะสมในคิวโดยไม่มีใครปิดสถานะ
    # (พบ 18 แถวค้างจาก ก.ค. ในรอบตรวจสอบ 2026-10-20)
    if msg_payload.get("action") == "report_back":
        alert_id = await _record_ceo_alert(
            source_agent=source_agent,
            status=msg_payload.get("status", "completed"),
            summary=msg_payload.get("summary", ""),
            details=msg_payload.get("details") or {},
            trace_id=trace_id,
        )
        await qm.update_status(msg_id, "completed")
        return {
            "trace_id": trace_id, "queue_id": msg_id, "status": "completed",
            "route_to": route_to, "alert_id": alert_id,
            "hops": ["queue", "route", "report_back"],
        }

    return {"trace_id": trace_id, "queue_id": msg_id, "status": "routed", "route_to": route_to, "hops": ["queue", "route"]}


async def _record_ceo_alert(
    *,
    source_agent: str,
    status: str,
    summary: str,
    details: dict,
    trace_id: str,
) -> str:
    """บันทึกรายงานจาก agent เข้า ceo_alerts (ให้ CEO อ่าน/ack ได้)"""
    alert_id = new_id()
    severity = "HIGH" if status == "failed" else "NORMAL"
    alert_type = "agent_report_failed" if status == "failed" else "agent_report"
    try:
        services = await _get_services()
        await services["db"].execute(
            """
            INSERT INTO ceo_alerts
                (id, alert_type, severity, source, title, detail,
                 acknowledged, acknowledged_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id, alert_type, severity, source_agent,
                (summary or "(ไม่มี summary)")[:200],
                json.dumps({"details": details, "trace_id": trace_id},
                           ensure_ascii=False)[:2000],
                0, None, now_iso(),
            ),
        )
    except Exception as e:  # pragma: no cover — หลักฐานล้มเหลวไม่ควรทำให้ report พัง
        log.warning("Failed to record ceo_alert: %s", e)
    return alert_id


@app.get("/v1/ceo-alerts")
async def list_ceo_alerts(acknowledged: str = "all", limit: int = 50):
    """รายงานจาก agent ทั้งหมด (ceo_alerts) — CEO ใช้ดูว่าใครรายงานอะไร

    Query:
        acknowledged: all (default) | true | false
    """
    services = await _get_services()
    sql = "SELECT * FROM ceo_alerts"
    params: list = []
    if acknowledged in ("true", "false"):
        sql += " WHERE acknowledged = ?"
        params.append(1 if acknowledged == "true" else 0)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(max(1, min(int(limit), 500)))
    rows = await services["db"].fetch_all(sql, tuple(params))
    return {"count": len(rows), "alerts": [dict(r) for r in rows]}


# ═══════════════════════════════════════════════════════════════════════
# POST /v1/context
# ═══════════════════════════════════════════════════════════════════════

@app.post("/v1/context")
async def get_context(request: Request):
    """Provide context (facts + queue status) to an agent."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=_error_response(
            code="VALIDATION_ERROR", message="Request body must be valid JSON",
            detail={"reason": "invalid JSON"}, request_id="",
        ))

    trace_id = payload.get("trace_id", new_id())
    agent_id = payload.get("agent_id")
    keys = payload.get("keys", [])

    if not agent_id:
        return JSONResponse(status_code=400, content=_error_response(
            code="VALIDATION_ERROR", message="Request payload validation failed",
            detail={"field": "agent_id", "reason": "missing"}, request_id="",
        ))

    services = await _get_services()
    facts_service = services["facts"]
    qm = services["queue"]

    # Governance (warn-first): wildcard "*" ยังให้ผ่าน แต่ warn + เก็บ log
    # (callers ปัจจุบัน: daily_brief, subscription_audit — แก้เป็น explicit
    #  หลังดู log 2-3 วัน แล้วค่อยปิด wildcard ตอนพลิกเป็น reject)
    from central_bus.bus_tags import log_access, redact_obj

    all_facts = []
    for key_pattern in keys:
        if key_pattern == "*":
            log.warning("[bus-tags:context] wildcard read by %s — ระบุ key ชัดเจนก่อนพลิกเป็น reject", agent_id)
        facts = await facts_service.list_facts(prefix=key_pattern, limit=100)
        all_facts.extend(facts)
        tiers = [str((f.get("metadata") or {}).get("sensitivity", "CONF")) for f in facts]
        top = "CONF" if "CONF" in tiers else ("INT" if "INT" in tiers else "PUB")
        log_access(who=agent_id or "?", key=key_pattern, tier=top)

    pending_count = await qm.count_pending()
    # P1-1: redact ซ้ำตอนอ่าน (กันแถวเก่าที่ยังไม่ถูก redact ตอนเขียน)
    return {
        "trace_id": trace_id, "context_id": new_id(),
        "facts": [{"key": f["key"], "value": redact_obj(f["value"]), "version": f["version"]} for f in all_facts],
        "queue_pending": pending_count, "agent_health": "ok",
    }


# ═══════════════════════════════════════════════════════════════════════
# POST /v1/update
# ═══════════════════════════════════════════════════════════════════════

@app.post("/v1/web-read")
async def web_read(request: Request):
    """อ่านเว็บด้วยเบราว์เซอร์จริง (เรนเดอร์ JavaScript ได้) — ไม่ต้องมี display

    ใช้แทน HTTP ธรรมดาเมื่อเว็บเป็น client-side rendered (React/Vue SPA)
    เพราะ HTTP ธรรมดาดึงได้แค่ source code

    รัน Chromium ใน container → 47.5MB RAM · 0% CPU ตอน idle · ไม่มี display
    ไม่เก็บ cookie → เว็บที่ต้อง login ใช้ไม่ได้

    Body (เลือกอย่างใดอย่างหนึ่ง):
    ```json
    {
        "url": "https://example.com",
        "query": "คำค้น",
        "wait": 12,
        "cols": 120,
        "rows": 40,
        "agent_id": "cmo-mark"
    }
    ```
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=_error_response(
            code="VALIDATION_ERROR", message="Request body must be valid JSON",
            detail={"reason": "invalid JSON"},
            request_id=request.headers.get("X-Request-Id", ""),
        ))

    url = payload.get("url")
    query = payload.get("query")
    if not url and not query:
        return JSONResponse(status_code=400, content=_error_response(
            code="VALIDATION_ERROR", message="Request payload validation failed",
            detail={"field": "url|query", "reason": "missing"},
            request_id=request.headers.get("X-Request-Id", ""),
        ))

    agent_id = payload.get("agent_id") or "anonymous"
    wait = int(payload.get("wait", 12))
    cols = int(payload.get("cols", 120))
    rows = int(payload.get("rows", 40))
    trace_id = payload.get("trace_id") or new_id()
    task_id = payload.get("task_id") or f"web-read-{new_id()[:8]}"

    # lazy import — กัน circular import ระหว่าง central_bus ↔ solocorp_skills
    from solocorp_skills.web import WebError, read_url, search, wrap_untrusted

    started = time.monotonic()
    started_at = now_iso()
    try:
        if url:
            result = await asyncio.to_thread(read_url, url, wait=wait, cols=cols, rows=rows)
        else:
            result = await asyncio.to_thread(
                search, query, limit=int(payload.get("limit", 10)),
                wait=wait, cols=cols, rows=rows,
            )
    except WebError as e:
        await _record_web_evidence(
            trace_id=trace_id, task_id=task_id, agent_id=agent_id,
            status="failed", summary=f"web-read failed: {e}",
            latency_ms=int((time.monotonic() - started) * 1000),
            started_at=started_at,
        )
        return JSONResponse(status_code=400, content=_error_response(
            code="WEB_READ_FAILED", message=str(e),
            detail={"trace_id": trace_id},
            request_id=request.headers.get("X-Request-Id", ""),
        ))
    except Exception as e:  # pragma: no cover
        log.exception("web-read crashed")
        return JSONResponse(status_code=500, content=_error_response(
            code="WEB_READ_ERROR", message=str(e),
            detail={"trace_id": trace_id},
            request_id=request.headers.get("X-Request-Id", ""),
        ))

    latency_ms = int((time.monotonic() - started) * 1000)

    if url:
        body = wrap_untrusted(result["text"], result["url"])
        summary = f"อ่านเว็บ {result['url']} — {result['chars']} chars"
        out = {
            "ok": True,
            "mode": "read",
            "url": result["url"],
            "title": result["title"],
            "chars": result["chars"],
            "lines": result["lines"],
            "content": body,
        }
    else:
        results = result["results"]
        lines = [f"# ผลการค้นหา: {result['query']}", ""]
        for i, r in enumerate(results, 1):
            lines.append(f"## {i}. {r['title']}")
            lines.append(f"URL: {r['url']}")
            lines.append(r["snippet"])
            lines.append("")
        summary = f"ค้นหา '{result['query']}' — ได้ {result['count']} ผลลัพธ์"
        out = {
            "ok": True,
            "mode": "search",
            "query": result["query"],
            "count": result["count"],
            "results": results,
            "content": wrap_untrusted("\n".join(lines), "duckduckgo:" + result["query"]),
        }

    await _record_web_evidence(
        trace_id=trace_id, task_id=task_id, agent_id=agent_id,
        status="completed", summary=summary, latency_ms=latency_ms,
        metadata={"mode": out["mode"], "chars": out.get("chars", 0)},
        started_at=started_at,
    )

    return {"trace_id": trace_id, "latency_ms": latency_ms, **out}


async def _record_web_evidence(
    *,
    trace_id: str,
    task_id: str,
    agent_id: str,
    status: str,
    summary: str,
    latency_ms: int,
    metadata: Optional[dict] = None,
    started_at: Optional[str] = None,
) -> None:
    """บันทึก evidence + audit + AAR ของการอ่านเว็บ (sync endpoint — ไม่ผ่าน queue)"""
    try:
        services = await _get_services()
        db = services["db"]
        await db.execute(
            """
            INSERT INTO evidence
                (id, task_id, trace_id, agent_id, evidence_type,
                 evidence_file, summary, status, routing_hops,
                 retry_count, latency_ms, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id(), task_id, trace_id, agent_id, "web_read",
                None, summary[:500], status, "[]",
                0, latency_ms, json.dumps(metadata or {}), now_iso(),
            ),
        )
        await db.execute(
            "INSERT INTO audit_log (id, trace_id, action, agent_id, entity_type, entity_id, payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id(), trace_id, "web.read", agent_id, "web", task_id,
             json.dumps({"status": status, "latency_ms": latency_ms,
                         **(metadata or {})}), now_iso()),
        )
        aar_id, _ = await AARGenerator(db).generate(
            trace_id=trace_id,
            queue_id=task_id,
            status=status,
            error=None if status == "completed" else summary,
            updated={
                "task_id": task_id,
                "created_at": started_at or now_iso(),
                "routing_hops": "[]",
                "retry_count": 0,
                "max_retries": 3,
            },
        )
        if aar_id:
            log.info("web-read evidence recorded: %s (trace=%s)", aar_id, trace_id)
    except Exception as e:  # pragma: no cover — หลักฐานล้มเหลวไม่ควรทำให้ request พัง
        log.warning("Failed to record web-read evidence: %s", e)


@app.post("/v1/update")
async def update_message(request: Request):
    """Report result back to the bus.  Triggers AAR on completion/failure."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=_error_response(
            code="VALIDATION_ERROR", message="Request body must be valid JSON",
            detail={"reason": "invalid JSON"}, request_id="",
        ))

    trace_id = payload.get("trace_id")
    queue_id = payload.get("queue_id")
    agent_id = payload.get("agent_id")
    status = payload.get("status", "completed")
    result = payload.get("result")
    error = payload.get("error")

    if not trace_id or not queue_id:
        return JSONResponse(status_code=400, content=_error_response(
            code="VALIDATION_ERROR", message="trace_id and queue_id are required",
            detail={"field": "trace_id/queue_id", "reason": "missing"}, request_id="",
        ))

    services = await _get_services()
    qm = services["queue"]

    # Governance (warn-first): redact PII ในผลลัพธ์ก่อนเก็บ (ใส่ marker ไม่ mutate เงียบ)
    # ชั่วคราวจนกว่า allowlist ต่อ builder (ขั้น 3) จะมาแทน
    from central_bus.bus_tags import redact_obj

    result = redact_obj(result)
    error = redact_obj(error)
    try:
        updated = await qm.update_status(
            message_id=queue_id, status=status, result=result, error=error, agent_id=agent_id,
        )
    except ValueError:
        return JSONResponse(status_code=404, content=_error_response(
            code="NOT_FOUND", message="queue_id not found",
            detail={"entity": "queue", "id": queue_id}, request_id="",
        ))

    await services["db"].execute(
        "INSERT INTO audit_log (id, trace_id, action, agent_id, entity_type, entity_id, payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id(), trace_id, "queue.update", agent_id, "queue", queue_id,
         json.dumps({"status": status, "error": error}), now_iso()),
    )

    aar_id, final_status = await AARGenerator(services["db"]).generate(
        trace_id=trace_id, queue_id=queue_id, status=status, error=error, updated=updated,
    )

    return {
        "trace_id": trace_id, "queue_id": queue_id, "status": final_status,
        "dead_letter": final_status == "dead",
        **({"aar_id": aar_id} if aar_id else {}),
    }


# ═══════════════════════════════════════════════════════════════════════
# GET /v1/health
# ═══════════════════════════════════════════════════════════════════════

@app.get("/v1/health")
async def health():
    """Health check — DB status, queue depth, uptime."""
    services = await _get_services()
    return await get_health(
        db=services["db"], qm=services["queue"],
        facts_service=services["facts"], engine=services["router"],
        started_at=_STARTED_AT,
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
        "SELECT * FROM aar WHERE trace_id = ? ORDER BY created_at DESC", (trace_id,),
    )
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════
# GET /v1/ab-test/report
# ═══════════════════════════════════════════════════════════════════════

@app.get("/v1/ab-test/report")
async def ab_test_report():
    """A/B test 50/50: route_v1 vs route_v2 metrics report.

    Returns in-memory + DB-backed metrics for the active A/B test between
    route_v2 (Behavior-Centric) and legacy route(), PLUS the experiment
    layer report (``route_split`` v1/v2 counts + split ratio) from
    ``central_bus.ab_test``.

    Access: Admin key required.
    """
    try:
        db = await ensure_db()
        report = get_ab_report(db=db)
    except Exception as e:
        log.warning("Failed to query DB for A/B report: %s", e)
        # Fall back to in-memory-only report
        report = get_ab_report(db=None)
        report["db_unavailable"] = True
    # Merge experiment-layer report (CMD-002-A)
    report["experiments"] = get_ab_experiment_reports()
    return report


# ═══════════════════════════════════════════════════════════════════════
# GET /v1/dashboard
# ═══════════════════════════════════════════════════════════════════════

@app.get("/v1/dashboard")
async def owner_dashboard_api(request: Request):
    """Owner Dashboard — มองปราดเดียวรู้เรื่อง.

    Returns:
        format=json (default) → dict with health, metrics, dispatches
        format=markdown      → formatted markdown string
    """
    fmt = request.query_params.get("format", "json")
    from central_bus.dashboard import owner_dashboard as _od
    result = _od(format=fmt)
    if fmt == "markdown":
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(result)
    return JSONResponse(result)


# ═══════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "central_bus.main:app",
        host=settings.host, port=settings.port,
        log_level=settings.log_level.lower(), reload=False,
    )
