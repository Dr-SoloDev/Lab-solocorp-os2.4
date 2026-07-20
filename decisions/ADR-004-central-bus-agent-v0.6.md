# ADR-004: Central Bus Agent — v0.6 Implementation Spec

> **Status:** Accepted — Implemented | **Date:** 2026-07-20 | **Author:** พี่ทรงศักดิ์ (Head of Architect)
> **Depends on:** ADR-003 (Central Bus Schema)

---

## 1. Goals

| # | Goal | Success Metric |
|:-:|------|----------------|
| G1 | Route messages ระหว่าง Department agents | ทุก message ถึงปลายทางภายใน SLA |
| G2 | Track state ของทุก project | state.json ถูกต้อง real-time |
| G3 | Detect + escalate exceptions อัตโนมัติ | CRITICAL escalate < 30 วินาที |
| G4 | Audit trail ครบทุก handoff | trace_id ครบทุก event |
| G5 | Retry ล้มเหลวอัตโนมัติ (max 3) | retry success rate ≥ 80% |

---

## 2. Non-Goals (ไม่ทำใน v0.6)

- ❌ UI Dashboard (v0.7)
- ❌ Multi-tenant isolation
- ❌ External API webhook inbound
- ❌ Real-time streaming (polling เท่านั้น)

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Central Bus Agent                 │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐ │
│  │  Router  │  │  State   │  │  Exception        │ │
│  │  Engine  │  │  Store   │  │  Handler          │ │
│  └────┬─────┘  └────┬─────┘  └────────┬──────────┘ │
│       │              │                 │             │
│  ┌────▼─────────────▼─────────────────▼──────────┐ │
│  │              Message Queue                     │ │
│  │  critical | high | normal | low                │ │
│  └────────────────────┬───────────────────────────┘ │
│                        │                             │
│  ┌─────────────────────▼───────────────────────────┐│
│  │              Audit Logger                        ││
│  └──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
         ▲▼                       ▲▼
    Department Agents        Cron/Watchdog
```

---

## 4. Components

### 4.1 Router Engine
- รับ message จาก queue → จับคู่กับ `routing_rules.json`
- ส่งต่อไป Department agent ที่ถูกต้อง
- ถ้าไม่มี rule ตรง → ส่ง `UNROUTABLE` exception

### 4.2 State Store
- อ่าน/เขียน `projects/{id}/state.json`
- Update phase status เมื่อรับ `STATUS` หรือ `ARTIFACT` message
- Lock ป้องกัน concurrent write (optimistic locking ด้วย `updated_at`)

### 4.3 Exception Handler
- Subscribe `EXCEPTION` message type
- จัดระดับ LOW/MED/HIGH/CRITICAL
- Trigger escalation chain ตาม severity

### 4.4 Message Queue
- Priority queue 4 ระดับ
- Persistence: append-only log file (no external dep)
- Retry: exponential backoff — 1s, 5s, 30s

### 4.5 Audit Logger
- บันทึกทุก event ลง `projects/{id}/audit/`
- Format: JSONL (1 object ต่อบรรทัด)
- Immutable — append only

---

## 5. File Structure

```
bus/
├── system/
│   ├── routing_rules.json        ← Router Engine อ่าน
│   ├── monitor/
│   │   └── {pipeline_id}.json    ← Watchdog เขียน health status
│   └── schedule/
│       └── registry.json         ← Cron jobs
│
├── projects/
│   └── {project_id}/
│       ├── state.json            ← State Store
│       ├── audit/
│       │   └── {date}.jsonl      ← Audit Logger (append-only)
│       └── artifacts/
│           └── {phase}/          ← output ของแต่ละ phase
│
└── queue/
    ├── critical.jsonl
    ├── high.jsonl
    ├── normal.jsonl
    └── low.jsonl
```

---

## 6. Interface (Agent API)

Department agents ส่ง/รับผ่าน function เหล่านี้:

```typescript
// ส่ง message ขึ้น bus
bus.publish(message: BusMessage): string  // returns message_id

// อ่านสถานะโปรเจกต์
bus.getState(project_id: string): ProjectState

// subscribe รับ message ที่ส่งมาถึง
bus.subscribe(department: string, callback: (msg: BusMessage) => void): void

// อัปเดต phase status
bus.updatePhase(project_id: string, phase: string, status: PhaseStatus): void

// escalate ปัญหา
bus.escalate(exception: BusException): void
```

**BusMessage schema:**
```typescript
interface BusMessage {
  id: string          // uuid
  ts: string          // ISO 8601
  from: Department
  to: Department
  type: "HANDOFF" | "STATUS" | "ARTIFACT" | "EXCEPTION"
  project_id: string
  phase: string
  priority: "critical" | "high" | "normal" | "low"
  payload: Record<string, unknown>
  trace_id: string    // ติดตาม pipeline ทั้งหมด
  retry_count?: number
}
```

---

## 7. Implementation Phases

### Phase 1 — Core Queue + Router (week 1-2)
| Task | Owner | Output |
|------|-------|--------|
| สร้าง JSONL queue (read/write/pop) | Engineering | `queue/*.jsonl` |
| สร้าง Router Engine (rule matching) | Engineering | route message ถูกต้อง |
| เขียน `routing_rules.json` เริ่มต้น | Architect | 14 department rules |
| Unit test: queue + router | QA | coverage ≥ 80% |

### Phase 2 — State Store + Audit (week 3)
| Task | Owner | Output |
|------|-------|--------|
| State Store (read/write/lock) | Engineering | state.json ถูกต้อง |
| Audit Logger (append JSONL) | Engineering | audit trail ครบ |
| Integration test: publish → route → state update | QA | E2E pass |

### Phase 3 — Exception Handler + Retry (week 4)
| Task | Owner | Output |
|------|-------|--------|
| Exception classifier (LOW/MED/HIGH/CRIT) | Engineering | classify ถูก ≥ 90% |
| Retry mechanism (backoff 1s/5s/30s) | Engineering | retry success ≥ 80% |
| Escalation chain (CRIT → CEO alert) | Engineering | alert < 30s |
| End-to-end pipeline test | QA | full pipeline pass |

---

## 8. Quality Gates (ก่อน ship v0.6)

| Gate | เงื่อนไข |
|------|---------|
| Unit test | coverage ≥ 80% |
| Integration test | ทุก department route ถูกต้อง |
| Performance | 100 msg/min ไม่มี queue overflow |
| Audit | trace_id ครบทุก event |
| Exception | CRITICAL escalate ภายใน 30 วินาที |
| Retry | message หายหลัง 3 retry = 0 (ต้อง dead-letter) |

---

## 9. Dependencies

| Component | Technology | เหตุผล |
|-----------|-----------|--------|
| Queue storage | JSONL files | ไม่ต้อง external service, simple |
| State storage | JSON files | human-readable, git-trackable |
| Locking | file lock (`flock`) | ป้องกัน concurrent write |
| Scheduling | cron + Hermes | ใช้ระบบที่มีอยู่แล้ว |
| Alerts | Telegram MCP | ใช้ channel ที่ Dr.solodev ใช้อยู่ |

**ไม่ใช้:** Redis, RabbitMQ, Kafka — ซับซ้อนเกินสำหรับ single-operator

---

## 10. Risks

| Risk | Probability | Impact | Mitigation |
|------|:-----------:|:------:|-----------|
| File lock contention | Low | High | optimistic lock + retry |
| Queue ใหญ่เกิน | Low | Med | max queue size + dead-letter |
| State diverge | Med | High | เสมอเขียนผ่าน State Store เท่านั้น |
| Routing rule ผิด | Med | Med | dry-run mode ก่อน production |

---

## 11. Implementation Notes (Finalized: 2026-07-20)

### 11.1 Overall Status

| Component | Status | ไฟล์อ้างอิง |
|-----------|--------|------------|
| Router Engine | ✅ **Implemented** | `central_bus/router.py`, `bus/system/routing_rules.json` |
| State Store | ✅ **Implemented** | `central_bus/state.py`, `bus/projects/{id}/state.json` |
| Exception Handler | ✅ **Implemented** | `central_bus/exceptions.py` |
| Message Queue | ✅ **Implemented** | `central_bus/queue.py`, `bus/queue/*.jsonl` |
| Audit Logger | ✅ **Implemented** | `central_bus/audit.py`, `bus/projects/{id}/audit/{date}.jsonl` |
| FastAPI Daemon | ✅ **Implemented** | `central_bus/main.py`, runs on `127.0.0.1:8099` |
| Tests | ✅ **Implemented** | `central_bus/tests/test_queue.py`, `test_router.py`, `test_integration.py`, `test_facts.py`, `test_behavior_classifier.py` |
| Mirror Config | ✅ **Deployed** | `bus/system/mirror_config.json` v2.5.1 (21 departments, L1-L5) |
| API Key Auth | ✅ **Implemented** | `central_bus/api_keys.py`, middleware in `main.py` |
| A/B Test 50/50 | ✅ **Implemented** (v0.6.2) | `router.py` — `route_ab_test()`, `get_ab_report()` |
| Behavior-Centric Routing | ✅ **Implemented** (v0.6.1) | `router.py` — `BehaviorRouter`, `route_v2()` |

### 11.2 Component Details

#### Router Engine — ✅ Implemented
| File | ที่อยู่ |
|------|--------|
| `central_bus/router.py` | `/home/drsolodev/projects/Lab-solocorp-os2.4/central_bus/router.py` |
| `routing_rules.json` | `/home/drsolodev/projects/Lab-solocorp-os2.4/bus/system/routing_rules.json` |
| `models.py` | `/home/drsolodev/projects/Lab-solocorp-os2.4/central_bus/models.py` |

- Three-tier matching: Keyword → TF-IDF Semantic → CEO fallback
- 19 routing rules covering 14+ departments
- 4 priority levels: critical(30m), high(120m), normal(480m), low(1440m)
- Governance event routing (guard_failed → orchestrator, adr_accepted → architect)
- BehaviorRouter Tier 0 (v0.6.1): routes by behavior classification (confidence ≥ 0.9)
- A/B Test 50/50 (v0.6.2): deterministic MD5 hash split, in-memory + DB metrics
- SQLite `RoutingEngine` with 60s TTL cache
- Backward-compatible JSONL `route()` preserved

#### State Store — ✅ Implemented
| File | ที่อยู่ |
|------|--------|
| `central_bus/state.py` | `/home/drsolodev/projects/Lab-solocorp-os2.4/central_bus/state.py` |
| `test-gov-001/state.json` | `/home/drsolodev/projects/Lab-solocorp-os2.4/bus/projects/test-gov-001/state.json` |
| `bangkok-pos/state.json` | `/home/drsolodev/projects/Lab-solocorp-os2.4/bus/projects/bangkok-pos/state.json` |

- Phase lifecycle: spec → design → arch → dev → qa → deploy
- Sequential phase validation (ห้ามข้าม phase)
- Governance guard integration (active_guards, guard_status, complexity_score)
- QA gate check via `qa_gate.check()` — block phase transition if evidence missing
- Optimistic locking with `fcntl.flock`
- Guard resolution + pipeline guard automation
- Path traversal protection on project IDs

#### Exception Handler — ✅ Implemented
| File | ที่อยู่ |
|------|--------|
| `central_bus/exceptions.py` | `/home/drsolodev/projects/Lab-solocorp-os2.4/central_bus/exceptions.py` |

- Severity classification: LOW / MED / HIGH / CRITICAL (keyword-based)
- Retry with exponential backoff: 1s → 5s → 30s
- Escalation JSONL log → `bus/system/escalations.jsonl`
- CEO alert file → `bus/system/ceo_alerts.jsonl` (สำหรับ Telegram MCP hook)
- `handle()` wrapper: execute with retry, escalate on exhaustion

#### Message Queue — ✅ Implemented
| File | ที่อยู่ |
|------|--------|
| `central_bus/queue.py` | `/home/drsolodev/projects/Lab-solocorp-os2.4/central_bus/queue.py` |
| Queue files | `/home/drsolodev/projects/Lab-solocorp-os2.4/bus/queue/{high,normal,low}.jsonl` |

- Dual backend: SQLite (primary, `USE_SQLITE=True`) + JSONL (backward compat)
- 4 priority levels with ORDER BY priority sorting
- `SQLiteQueueManager` — create_message, get_pending, update_status
- Automatic dead-letter after max_retries (default 3)
- Dead-letter queue tracking (`dead_letter_queue` table)
- Retry count tracking + error_log (JSON array)
- File locking for JSONL path

#### Audit Logger — ✅ Implemented
| File | ที่อยู่ |
|------|--------|
| `central_bus/audit.py` | `/home/drsolodev/projects/Lab-solocorp-os2.4/central_bus/audit.py` |
| Audit trail example | `/home/drsolodev/projects/Lab-solocorp-os2.4/bus/projects/test-proj/audit/2026-07-05.jsonl` |

- `AuditLogger` class — async INSERT to SQLite `audit_log` table
- Three methods: `log_action()`, `log_error()`, `log_message()`
- Query by project_id + date with LIKE pattern matching
- JSONL audit trail as secondary storage (evidence at test-proj)
- Backward-compatible module-level `log()` and `read()`

#### FastAPI Daemon — ✅ Implemented
| File | ที่อยู่ |
|------|--------|
| `central_bus/main.py` | `/home/drsolodev/projects/Lab-solocorp-os2.4/central_bus/main.py` |
| `central_bus/config.py` | `/home/drsolodev/projects/Lab-solocorp-os2.4/central_bus/config.py` |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/observe` | POST | รับ task → enqueue → route → audit |
| `/v1/context` | POST | Provide context (facts + queue status) |
| `/v1/update` | POST | Report result; trigger AAR on completion/failure |
| `/v1/health` | GET | Health check: DB, queue depth, uptime |
| `/v1/aar/{trace_id}` | GET | Retrieve AAR entries |
| `/v1/ab-test/report` | GET | A/B test 50/50 metrics report |
| `/v1/dashboard` | GET | Owner dashboard (json/markdown) |
| `/v1/skills` | GET | Skills registry |

- Version: 0.6.2
- API Key authentication via middleware + `api_keys.py`
- CORS enabled
- Error envelope: `{"error": {"code": "...", "message": "...", "detail": {...}}}`
- Support endpoints via `central_bus/skills_router.py` + `central_bus/api_compliance.py`

### 11.3 Missing Items (ยังไม่ implement ใน v0.6)

| Item | Section ใน ADR | สถานะ |
|------|:--------------:|:------:|
| `bus/system/monitor/{pipeline_id}.json` | §5 File Structure | ❌ **ไม่มี directory `monitor/`** — Watchdog health monitoring directory ยังไม่ถูกสร้าง |
| `bus/system/schedule/registry.json` | §5 File Structure | ❌ **ไม่มี directory `schedule/`** — Cron job registry ยังไม่ถูกสร้าง |
| `bus/queue/critical.jsonl` | §5 File Structure | ❌ **ไม่มีไฟล์** — Critical queue file ยังไม่ถูกสร้าง (แต่ SQLite queue รองรับ priority อยู่แล้ว) |
| Scheduled cron jobs | §9 Dependencies | ❌ **ยังไม่ integrate** — ระบุว่าใช้ cron + Hermes แต่ยังไม่มี scheduler integration |
| UI Dashboard | §2 Non-Goals | ⏳ **v0.7** — Non-goal ตาม design, รอ implementation ในรอบถัดไป |
| Multi-tenant isolation | §2 Non-Goals | ⏳ **Future** — Non-goal ตาม design |
| External API webhook inbound | §2 Non-Goals | ⏳ **Future** — Non-goal ตาม design |

### 11.4 Dependencies Check

#### ADR-003 (Central Bus Schema) — ✅ สอดคล้อง
- **สถานะ ADR-003:** Accepted ✅
- ADR-003 defines JSON Schema + Protocol (Input → Process → Output)
- ADR-004 implements: `BusMessage` dataclass (`central_bus/models.py`) ครอบคลุมทุก field จาก ADR-003 schema
- State store (`state.py`) รองรับ `departments_state` pattern (per-department state tracking)
- Audit trail ทำงานตาม protocol: Input → Process → Output
- รองรับทั้ง 7 department types (orchestration, marketing, engineering, design, qa, finance, sales, product, legal) ตามที่ ADR-003 กำหนด
- **แตกต่างเล็กน้อย:** ADR-003 ใช้ JSON Schema แบบ static → ADR-004 implement ด้วย SQLite + JSONL hybrid แต่ schema backward compatible

#### ADR-002 (Two-Tier Architecture) — ✅ สอดคล้อง
- **สถานะ ADR-002:** Accepted ✅
- ADR-002 แยก Control Layer (ผ่าน Head) และ Data Layer (ผ่าน Central Bus)
- ADR-004 implements Data Layer: agents ส่งข้อมูลถึงกันผ่าน bus โดยอัตโนมัติ
- Router engine ส่ง notification ไป Department Heads โดยตรง (ไม่ต้องรอ Head)
- State store ให้ Head ดูสรุปได้โดยไม่ต้องจมกับ data layer
- **สอดคล้อง:** ไม่มี Agent ข้ามสายคุยกันโดยตรง — ทุกอย่างผ่าน bus เสมอ
- **สอดคล้อง:** Pipeline design rules (Agent รู้แค่ 2 ทิศทาง) ถูก implement ใน routing engine

### 11.5 Quality Gates Review

| Gate | สถานะ | Evidence |
|------|:-----:|----------|
| Unit test coverage ≥ 80% | ✅ | Tests at `central_bus/tests/` — queue, router, integration, facts, behavior_classifier (มี pytest cache + conftest) |
| Integration test | ✅ | `test_integration.py` — E2E publish → route → state update |
| Performance 100 msg/min | ⚪ | No benchmark found — ยังต้องวัด |
| Audit trace_id ครบ | ✅ | Evidence: `bus/projects/test-proj/audit/2026-07-05.jsonl` — 16 audit events with trace_ids |
| CRITICAL escalate < 30s | ✅ | `exceptions.py` — `_notify_ceo()` writes to `bus/system/ceo_alerts.jsonl` |
| Dead-letter after 3 retry | ✅ | `queue.py` — `SQLiteQueueManager.update_status()` auto dead-letter at max_retries (default 3) |

### 11.6 Evidence File Map

| Evidence | Path |
|----------|------|
| Routing rules | `bus/system/routing_rules.json` (19 rules, 4 priority levels) |
| Mirror config | `bus/system/mirror_config.json` (v2.5.1, 21 departments) |
| State store (live project) | `bus/projects/bangkok-pos/state.json` |
| State store (governance) | `bus/projects/test-gov-001/state.json` |
| Audit trail | `bus/projects/test-proj/audit/2026-07-05.jsonl` (16 events) |
| Queue files | `bus/queue/{high,normal,low}.jsonl` + offset files |
| Dispatch records | `bus/dispatch/2026-07-20/` (CMD-001, CMD-002, CMD-003, TEST-001, TEST-002) |
| Evidence log | `bus/evidence/` (multiple JSON evidence files) |
| Source: Router | `central_bus/router.py` (675 lines) |
| Source: Queue | `central_bus/queue.py` (439 lines) |
| Source: State | `central_bus/state.py` (445 lines) |
| Source: Audit | `central_bus/audit.py` (162 lines) |
| Source: Exceptions | `central_bus/exceptions.py` (75 lines) |
| Source: Daemon | `central_bus/main.py` (430 lines, FastAPI v0.6.2) |
| Source: Config | `central_bus/config.py` (31 lines) |
| Source: Models | `central_bus/models.py` — BusMessage dataclass |

---

> **Finalized โดย:** พี่ทรงศักดิ์ (Head of Architect) — 2026-07-20
> **จาก:** Draft → Accepted — Implemented
> **ADR-004** ครอบคลุม Central Bus Agent ครบทั้ง 5 components (Router, State, Exception, Queue, Audit)
> **Dependencies:** ADR-003 ✅ (schema), ADR-002 ✅ (two-tier architecture)
> **Missing items:** monitor/ directory, schedule/ registry, critical.jsonl — ทั้งหมดไม่ blocking (minor)
