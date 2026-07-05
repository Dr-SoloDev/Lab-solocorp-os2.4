# PRD: Central Bus v0.6 — The Reliability Release

| Meta | Value |
|------|-------|
| **Product** | SoloCorp OS v2.5 "The Reliability Release" |
| **Feature** | Central Bus v0.6 |
| **Status** | Draft v2 |
| **Owner** | Product (โปรดัค) |
| **Architect** | Architect (พี่ทรงศักดิ์) |
| **Engineering** | Engineering (ช่างฟูล) |
| **Target** | 3 weeks (21 days) |

---

## 1. ปัญหา (Problem Statement)

SoloCorp OS มี 15 departments, 20+ agents, 84 skills แต่ **ไม่มีระบบขนส่งกลางที่เชื่อถือได้**:

- **Queue ปัจจุบัน**: ใช้ JSONL (`bus/queue/high.jsonl`, `bus/queue/normal.jsonl`) — ไม่มี query, ไม่มี ACID, audit trail ต้อง grep
- **No durable state**: Facts, routing rules, handoff logs กระจัดกระจาย — ไม่มีประวัติที่ recoverable
- **No retry mechanism**: ถ้า message ล้ม ไม่มี retry policy → data loss
- **No API contract**: Agent → Bus, Bus → Agent ไม่มี interface ที่ชัดเจน — ทุก pipeline สร้าง custom channel
- **No monitoring**: ไม่มี health check, no latency tracking, no alert

> "We built the brains. Now we need the backbone."

---

## 2. วัตถุประสงค์ (Objectives)

1. **Reliable Messaging** — ACID-guaranteed queue พร้อม retry policy (ตายตัว = ไม่สูญ)
2. **Durable Facts** — ข้อเท็จจริงทั้งหมดของระบบ (routing rules, agent status, pipeline state) อยู่ใน SQLite ที่ queryable
3. **API Contract** — ทุก department สื่อสารผ่าน REST API ที่มี spec ชัดเจน
4. **Observability** — Health endpoint, queue depth, audit trail
5. **Migration Path** — JSONL → SQLite โดยไม่เสียประวัติ และ backward compatible

---

## 3. Scope (ขอบเขต)

### In-Scope (v0.6 — 3 weeks)

| Feature | Description |
|---------|-------------|
| SQLite Backend | Migrate queue, facts, audit trail จาก JSONL → SQLite WAL-mode |
| Bus Daemon (busd) | FastAPI service: 1 process, 4 endpoints |
| Durable Facts Storage | `facts` table — key-value with versioning, metadata |
| Routing Rules Engine | Reload `routing_rules` จาก SQLite พร้อม cache |
| API Contract (v1) | Observe, Context, Update — 3 POST endpoints |
| Retry Policy | 3 tries → dead-letter queue (SQLite) |
| Health Check | `GET /health` — queue depth, DB status, loop status |
| Audit Trail | `audit_log` table — ทุก action บันทึก timestamp + agent_id + payload |
| JSONL Backward Compat | ยังอ่าน JSONL ได้ แต่ write ไป SQLite |
| Migration Script | ย้ายข้อมูลจาก JSONL → SQLite แบบ idempotent |

### Out-of-Scope (Deferred to v2.6)

| Feature | Rationale |
|---------|-----------|
| SSE / WebSocket CDC | Polling เพียงพอสำหรับ v0.6 — real-time ไม่จำเป็น |
| Dashboard UI | CLI + health endpoint พอ — UI รอ v2.6 |
| Hermes Profile Plugin | Central Bus ทำงานเป็น wrapper รอบ Hermes — ไม่ต้องแก้ Hermes core |
| Multi-node / Cluster | v0.6 เป็น single-process — scale ได้ทีหลัง |
| Schema Migrations (Alembic) | Migrate ด้วย script ครั้งเดียว — Alembic รอ v2.6 |
| Agent → Bus Bidirectional Push | Agent pull/poll ก็พอสำหรับ v0.6 |

---

## 4. Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                    Hermes Agent                        │
│  (pipeline_executor, daily_brief, subscription_audit) │
└────────────┬───────────────────────────────┬──────────┘
             │ POST /observe                 │ POST /context
             │ POST /update                  │ POST /facts
             ▼                               ▼
┌───────────────────────────────────────────────────────┐
│               Central Bus Daemon (busd)                │
│                   FastAPI + uvicorn                     │
│                                                         │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌─────────┐ │
│  │ Router  │  │  Queue   │  │  Facts  │  │  Guard  │ │
│  │ Engine  │  │ Manager  │  │ Service │  │ Runner  │ │
│  └────┬────┘  └────┬─────┘  └────┬────┘  └────┬────┘ │
│       │            │             │            │       │
│       └────────────┴─────────────┴────────────┘       │
│                        │                               │
│                  ┌─────┴──────┐                        │
│                  │  SQLite    │                        │
│                  │ (WAL mode) │                        │
│                  └────────────┘                        │
└───────────────────────────────────────────────────────┘
```

### Data Flow

```
Agent → POST /observe {task_id, agent_id, payload} → Queue Manager
  → validate schema → INSERT INTO queue (status='pending')
  → Router Engine → match routing_rules → UPDATE status='routed'
  → Guard Runner → check pre-conditions → UPDATE status='guarded'
  → Return {queue_id, status, route_to}
  
Agent → POST /context {agent_id, task_id} → Facts Service
  → SELECT FROM facts WHERE key LIKE '{agent_id}%'
  → Return {facts: [...], context_id}
  
Agent → POST /update {queue_id, status, result} → Queue Manager
  → UPDATE queue SET status, result, completed_at
  → INSERT INTO audit_log (action='update')
  → If status='completed' or 'failed' → Generate AAR → INSERT INTO aar
  → If status='failed' × 3 → INSERT INTO dead_letter_queue
```

---

## 5. Technical Specification

### 5.1 SQLite Schema

```sql
-- Bus: queue messages
CREATE TABLE queue (
    id              TEXT PRIMARY KEY,          -- UUID v4
    trace_id        TEXT NOT NULL,             -- Trace ID (correlation across hops)
    task_id         TEXT NOT NULL,             -- กลุ่มของ messages (correlation id)
    agent_id        TEXT NOT NULL,             -- source agent
    target_agent    TEXT,                      -- destination agent (nullable = broadcast)
    priority        TEXT DEFAULT 'normal',     -- 'high' | 'normal' | 'low'
    status          TEXT DEFAULT 'pending',    -- pending | routed | guarded | processing | completed | failed | dead
    payload         TEXT NOT NULL,             -- JSON string
    routing_hops    TEXT DEFAULT '[]',          -- JSON array of {from, to, timestamp}
    error_log       TEXT,                      -- JSON array of {attempt, error, timestamp}
    retry_count     INTEGER DEFAULT 0,
    max_retries     INTEGER DEFAULT 3,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    completed_at    TEXT
);

CREATE INDEX idx_queue_status ON queue(status);
CREATE INDEX idx_queue_priority ON queue(priority);
CREATE INDEX idx_queue_agent ON queue(agent_id);
CREATE INDEX idx_queue_trace ON queue(trace_id);
CREATE INDEX idx_queue_created ON queue(created_at);

-- Facts: durable key-value store with versioning
CREATE TABLE facts (
    key             TEXT PRIMARY KEY,           -- e.g. 'agent.status.changful', 'routing.rule.001'
    value           TEXT NOT NULL,              -- JSON string
    version         INTEGER DEFAULT 1,
    metadata        TEXT DEFAULT '{}',           -- JSON: tags, source, ttl
    updated_by      TEXT,                       -- agent_id
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- Routing Rules
CREATE TABLE routing_rules (
    id              TEXT PRIMARY KEY,           -- UUID v4
    name            TEXT NOT NULL,
    description     TEXT,
    source_agent    TEXT NOT NULL,              -- regex pattern
    target_department TEXT NOT NULL,            -- department code
    condition       TEXT,                       -- JSON predicate (optional)
    priority        INTEGER DEFAULT 0,
    enabled         INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- Audit Trail
CREATE TABLE audit_log (
    id              TEXT PRIMARY KEY,           -- UUID v4
    trace_id        TEXT,                       -- Trace ID (optional for correlated lookups)
    action          TEXT NOT NULL,              -- 'queue.create' | 'queue.update' | 'fact.create' | 'fact.update' | 'route.match' | 'error'
    agent_id        TEXT,
    entity_type     TEXT,                       -- 'queue' | 'fact' | 'rule'
    entity_id       TEXT,
    payload         TEXT,                       -- JSON: what changed
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_agent ON audit_log(agent_id);
CREATE INDEX idx_audit_created ON audit_log(created_at);

-- Dead Letter Queue
CREATE TABLE dead_letter_queue (
    id              TEXT PRIMARY KEY,           -- UUID v4
    queue_id        TEXT NOT NULL,              -- reference to original queue.id
    payload         TEXT NOT NULL,              -- original payload
    errors          TEXT NOT NULL,              -- JSON array of errors
    source_agent    TEXT NOT NULL,
    target_agent    TEXT,
    failed_at       TEXT DEFAULT (datetime('now')),
    resolved        INTEGER DEFAULT 0
);

-- After Action Reviews (AAR)
CREATE TABLE aar (
    id              TEXT PRIMARY KEY,
    trace_id        TEXT NOT NULL,
    task_id         TEXT,
    queue_id        TEXT,
    total_hops      INTEGER,
    total_retries   INTEGER,
    final_status    TEXT,
    latency_ms      INTEGER,
    failure_pattern TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
```

### 5.2 API Contract (OpenAPI v3)

#### POST `/v1/observe`
รับ task จาก agent → queue → route

```
Request:
{
    "trace_id": "uuid-string",
    "task_id": "uuid-string",
    "source_agent": "changful",
    "target_agent": null,
    "priority": "high",
    "payload": { ... any JSON ... },
    "context": { ... optional context ... }
}

Response 200:
{
    "trace_id": "uuid-string",
    "queue_id": "uuid-string",
    "status": "routed",
    "route_to": "07-engineering",
    "hops": ["queue", "route"]
}

#### Error Responses (all endpoints)

All endpoints return a consistent error envelope:

```
Response 400 (Validation Error):
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Request payload validation failed",
        "detail": { "field": "source_agent", "reason": "missing" },
        "request_id": "uuid"
    }
}

Response 404 (Not Found):
{
    "error": {
        "code": "NOT_FOUND",
        "message": "queue_id/task_id not found",
        "detail": { "entity": "queue", "id": "uuid-string" },
        "request_id": "uuid"
    }
}

Response 422 (Unprocessable Entity):
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Payload format is invalid",
        "detail": { "field": "payload", "reason": "expected object, got array" },
        "request_id": "uuid"
    }
}

Response 429 (Rate Limited):
{
    "error": {
        "code": "RATE_LIMITED",
        "message": "Too many requests from agent",
        "detail": { "agent_id": "changful", "retry_after_seconds": 5 },
        "request_id": "uuid"
    }
}

Response 500 (Internal Error):
{
    "error": {
        "code": "INTERNAL_ERROR",
        "message": "Internal server error",
        "detail": { "db_error": "database connection failed" },
        "request_id": "uuid"
    }
}
```

#### POST `/v1/context`
ดึง context ให้ agent ก่อนทำงาน

```
Request:
{
    "trace_id": "uuid-string",
    "agent_id": "changful",
    "task_id": "uuid-string",
    "keys": ["facts.agent.*", "routing.rule.*"]
}

Response 200:
{
    "trace_id": "uuid-string",
    "context_id": "uuid-string",
    "facts": [
        {"key": "agent.status.changful", "value": {...}, "version": 3}
    ],
    "queue_pending": 2,
    "agent_health": "ok"
}
```

#### POST `/v1/update`
แจ้งผลลัพธ์กลับ bus

```
Request:
{
    "trace_id": "uuid-string",
    "queue_id": "uuid-string",
    "agent_id": "changful",
    "status": "completed",
    "result": { ... any JSON ... },
    "error": null
}

Response 200:
{
    "trace_id": "uuid-string",
    "queue_id": "uuid-string",
    "status": "completed",
    "dead_letter": false
}
```

#### GET `/v1/health`
Health check

```
Response 200:
{
    "status": "ok",
    "db": {"queue_pending": 3, "queue_failed": 1, "queue_dead": 0},
    "facts_count": 145,
    "routing_rules": 14,
    "loops_active": 4,
    "uptime_seconds": 86400,
    "version": "0.6.0"
}
```

#### GET `/v1/aar/{trace_id}`
After Action Review — retrieve full pipeline trace

```
Response 200:
{
    "aar_id": "uuid-string",
    "trace_id": "uuid-string",
    "task_id": "uuid-string",
    "queue_id": "uuid-string",
    "total_hops": 3,
    "total_retries": 1,
    "final_status": "completed",
    "latency_ms": 1450,
    "failure_pattern": null,
    "notes": "Recovered after 1 retry on guard_runner timeout",
    "created_at": "2025-07-05T12:00:00Z"
}
```

### 5.3 Directory Structure (Final)

```
central_bus/
├── __init__.py
├── main.py              # FastAPI entrypoint (uvicorn)
├── config.py            # Pydantic Settings
├── db.py                # SQLite connection + init schema
├── models.py            # Pydantic models (request/response)
├── queue.py             # QueueManager: CRUD queue
├── facts.py             # FactsService: CRUD facts
├── router.py            # RoutingEngine: match rules
├── guard_runner.py      # GuardRunner: pre-flight checks
├── audit.py             # AuditLogger
├── aar.py               # After Action Review generator
├── health.py            # Health endpoint logic
├── migrate.py           # JSONL → SQLite migration
├── exceptions.py        # Custom exceptions
├── requirements.txt     # dependencies
└── tests/
    ├── test_queue.py
    ├── test_facts.py
    ├── test_router.py
    └── test_integration.py
```

---

## 6. Features by Priority

### P0 — Must Have (Week 1-2)
- [ ] SQLite schema + init script
- [ ] Queue Manager (create, update, query, retry)
- [ ] Facts Service (CRUD key-value)
- [ ] Routing Engine (load από SQLite, match)
- [ ] 3 endpoints: POST `/v1/observe`, `/v1/context`, `/v1/update`
- [ ] Health endpoint: GET `/v1/health`
- [ ] Audit Logger (ทุก action)

### P1 — Should Have (Week 2-3)
- [ ] Retry Policy (max 3 → dead-letter)
- [ ] Guard Runner (pre-condition check ก่อน route)
- [ ] Migration script: JSONL → SQLite (idempotent)
- [ ] Error handling + validation

### P2 — Nice to Have (Week 3)
- [ ] Rate limiting (per agent)
- [ ] CLI tool: `busctl status`
- [ ] JSONL backward compatibility layer

---

## 7. Timeline (3 Weeks / 21 Days)

| Week | Sprint | Deliverable |
|:----:|:------:|-------------|
| W1 | Sprint 1 | SQLite schema + Queue Manager + Facts Service + Routing Engine + **3 core endpoints** |
| W2 | Sprint 2 | Guard Runner + Retry Policy + Audit Trail + **Integration tests** |
| W3 | Sprint 3 | Migration script + CLI tool + JSONL compat + **Smoke test + v2.5 release** |

### Checkpoints

| Day | What |
|:---:|------|
| D7 | Sprint 1 Review: SQLite backend + 3 endpoints working + Ping-pong test |
| D14 | Sprint 2 Review: full pipeline pass (observe → route → guard → update → retry) |
| D21 | v2.5 Release: migration complete, health check green, all pipelines green |

---

### Loop Migration Plan

| Loop | Migration | Timeline | Action |
|:-----|:---------:|:--------:|:-------|
| pipeline_executor | P0 — must migrate in v0.6 | Sprint 1 | Change from direct central_bus.queue import to HTTP POST /v1/observe |
| daily_brief | Deferred to v2.6 | — | Keep standalone |
| subscription_audit | Deferred to v2.6 | — | Keep standalone |
| brain_auto_commit | Deferred to v2.6 | — | Keep standalone |

---

## 8. Success Criteria

### Functional
- [ ] POST `/v1/observe` → message เข้า SQLite, route ถูก department
- [ ] POST `/v1/context` → return facts + queue status
- [ ] POST `/v1/update` → update queue status + audit trail
- [ ] GET `/v1/health` → return all metrics
- [ ] Retry: ถ้า failed × 3 → dead-letter queue
- [ ] Migration: ข้อมูล JSONL ย้ายเข้า SQLite ไม่สูญ

### Non-Functional
- [ ] API response time < 100ms (p99)
- [ ] Zero data loss in retry scenarios
- [ ] SQLite WAL mode — concurrent reads ไม่ lock
- [ ] audit_log ครบทุก action (no silent drops)
- [ ] Every completed pipeline generates an AAR entry
- [ ] AAR contains trace_id + total_hops + total_retries + final_status + latency_ms
- [ ] 4 existing Loops (daily_brief, subscription_audit, brain_auto_commit, pipeline_executor) ยังทำงานปกติ post-migration

### Quality Gates
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration test: observe → route → guard → update full flow
- [ ] Smoke test: run pipeline_executor → verify audit trail

---

## 9. Dependencies

| Dependency | Version | Notes |
|------------|---------|-------|
| Python | 3.11+ | Already used throughout SoloCorp OS |
| FastAPI | 0.110+ | Standard |
| uvicorn | 0.29+ | Already present |
| aiosqlite | >=0.20.0 | Explicit async SQLite driver |
| pydantic | 2.x | Already present |
| anyio | (FastAPI dep) | Already pulled by FastAPI, used for async concurrency |
| httpx | (test only) | Integration tests |

**Zero new external dependencies.** ทุกตัวมีอยู่แล้วหรือเป็น stdlib — aiosqlite, anyio เป็น transitive dep ที่มากับ FastAPI/uvicorn อยู่แล้ว

---

## 10. Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|:----------:|:------:|------------|
| SQLite write lock ภายใต้ concurrent agents | Medium | High | WAL mode + retry on locked. v0.6 = single process, no multi-process race |
| JSONL migration data loss | Low | Critical | Migration idempotent + validate checksum before/after |
| Pipeline breakage post-migration | Medium | High | Soft launch: Old JSONL reader ยังทำงาน parallel 3 days |
| Bus daemon crash mid-queue | Low | High | Queue status = 'pending' recoverable on restart |
| Scope creep (อยากเพิ่ม SSE/CDC) | Medium | Medium | PRD lockdown: P0-P1-P2 ต้อง approval ก่อนเพิ่ม |

---

## 11. Rollback Plan

ถ้า v2.5 production มีปัญหาภายใน 7 วัน หลัง deploy:

1. **Smoke test verification** — Run smoke test suite to confirm the issue is reproducible and not a transient glitch
2. **Stop bus daemon** — `systemctl stop central-bus`
3. **Dead-letter dump** — Run `busctl dump-dead-letter --format=jsonl` เพื่อ dump dead-letter queue กลับเป็น JSONL ป้องกัน data loss
4. **Dual-write guard** — Ensure all in-flight messages are accounted for in both SQLite and JSONL before cutover
5. **Revert JSONL reader flag** (`USE_SQLITE=False`)
6. **Agents fallback** ใช้ JSONL queue
7. **Fix** → re-run migration → switch `USE_SQLITE=True`

> **Note:** 7-day observation window provides sufficient time for edge-case pipelines (e.g., brain_auto_commit with weekly cadence) to exercise the new bus. Dead-letter dump guarantees no message loss during rollback.

---

## Appendices

### A. Migration: JSONL → SQLite

1. Read existing JSONL files
2. Validate JSON structure
3. INSERT INTO queue (transform fields)
4. Verify count(JSONL) == count(SQLite)
5. Mark migration complete

### B. Existing Code References

| File | Lines | Purpose |
|------|:-----:|---------|
| `central_bus/models.py` | 48 | Pydantic Models (Message, RoutingResult) |
| `central_bus/queue.py` | 162 | QueueManager JSONL |
| `central_bus/router.py` | 136 | RoutingEngine |
| `central_bus/semantic.py` | 115 | Semantic routing |
| `central_bus/state.py` | 435 | StateManager (facts + queue status) |
| `central_bus/guard_runner.py` | 177 | GuardRunner (pre-flight checks) |
| `central_bus/webhook_receiver.py` | 221 | Webhook endpoints |
| `central_bus/dashboard.py` | 43 | Streamlit dashboard |
| `central_bus/audit.py` | — | Audit logger |
| `loop_runner/state.db` | — | Existing SQLite (WAL mode) |

60% ของ v0.6 มีโค้ดพร้อมแล้ว — ต้อง refactor JSONL → SQLite + add API endpoints + add retry + add health check

---

*Document maintained by Product (โปรดัค). Updated as implementation progresses.*
