# ADR-004: Central Bus Agent — v0.6 Implementation Spec

> **Status:** Draft | **Date:** 2026-06-28 | **Author:** พี่ทรงศักดิ์ (Head of Architect)
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

