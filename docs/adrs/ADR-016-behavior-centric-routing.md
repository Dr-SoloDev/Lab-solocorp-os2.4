# ADR-016: Behavior-Centric Routing Architecture

| Field | Value |
|:------|:------|
| **Status** | Proposed |
| **Author** | พี่ทรงศักดิ์ (Architect) |
| **Date** | 2026-07-20 |
| **CEO Order** | Behavior-Centric Routing: Execute |

---

## Context

SoloCorp OS uses a 3-tier routing system:

1. **Tier 0:** Governance event routing (message type)
2. **Tier 1:** Keyword matching (fast path via `routing_rules.json`)
3. **Tier 2:** Semantic matching (TF-IDF + cosine similarity)
4. **Tier 3:** CEO fallback

**Problem:** The current system routes based on *what words the user uses*, not *what the user intends to do*. This causes:

- คำถามเดียวกันแต่ใช้คนละคำ → ไปคนละแผนก
- Behavior ข้ามแผนก (เช่น bug report → Engineering แต่บางครั้งต้องไป QA) ไม่มี fallback
- ไม่มี confidence score — ไม่รู้ว่าควร确信แค่ไหนก่อน route

**Decision:** Add a **Behavior Layer** before Tier 1 keyword matching — classify user *intent* (behavior) first, then route to the appropriate department.

---

## Decision

### Taxonomy Size: 26 behaviors

26 behaviors covering all 18 SoloCorp departments:

| # | Domain | Behavior | Primary Dept | Logic | Priority |
|:-:|:--------|:---------|:-------------|:------|:---------|
| 1 | leadership | `vision_strategy` | CEO | direct | high |
| 2 | leadership | `owner_decision` | CEO | ceo_review | critical |
| 3 | finance | `budget_approval` | CFO | direct | high |
| 4 | finance | `cost_analysis` | CFO | direct | normal |
| 5 | marketing | `campaign_management` | CMO | direct | normal |
| 6 | marketing | `brand_strategy` | CMO | direct | high |
| 7 | content | `content_production` | Content Creator | direct | normal |
| 8 | operations | `pipeline_coordination` | Orchestrator | orchestrator | high |
| 9 | architecture | `architecture_design` | Architect | direct | high |
| 10 | architecture | `routing_monitoring` | Architect | direct | normal |
| 11 | product | `feature_definition` | Product | direct | normal |
| 12 | product | `roadmap_planning` | Product | direct | high |
| 13 | engineering | `backend_development` | Engineering | direct | normal |
| 14 | engineering | `frontend_development` | Engineering | direct | normal |
| 15 | engineering | `bug_fixing` | Engineering | direct | high |
| 16 | design | `visual_design` | Design | direct | normal |
| 17 | design | `ux_research` | Design | direct | normal |
| 18 | quality | `qa_testing` | QA | direct | normal |
| 19 | sales | `sales_deal` | Sales | direct | normal |
| 20 | support | `customer_support` | Support | direct | high |
| 21 | legal | `legal_compliance` | Legal | direct | high |
| 22 | legal | `contract_management` | Legal | direct | normal |
| 23 | web3 | `smart_contract_defi` | Web3 | direct | normal |
| 24 | network | `network_operations` | NetEng | direct | high |
| 25 | security | `security_incident` | CyberSec | direct | critical |
| 26 | psychology | `behavioral_research` | Psychology | direct | normal |

### Confidence Threshold

| Score | Action |
|:------|:-------|
| >= 0.90 | Auto-route to primary_dept |
| 0.70 - 0.89 | Route to secondary_depts (orchestrator) |
| < 0.70 | CEO review / fallback to Tier 1 keyword |

### Routing Logic Types

| Logic | Behavior |
|:------|:---------|
| `direct` | ส่งตรงไป primary_dept ทันที |
| `orchestrator` | ส่งไป Orchestrator เพื่อ协调 workflow |
| `ceo_review` | ส่ง CEO ก่อน แล้ว CEO ส่งต่อ |
| `round_robin` | กระจายระหว่าง departments |

### Migration Strategy: Add-on (Non-Destructive)

```
Before:   [Message] → Keyword (T1) → Semantic (T2) → CEO (T3)

After:    [Message] → Behavior Classifier (New!)
                              ↓
                    Confidence ≥ 0.9? → Route to Dept
                    Confidence < 0.9? → Keyword (T1) → Semantic (T2) → CEO (T3)
```

- Existing `routing_rules.json` **unchanged**
- Existing `RoutingEngine` **unchanged**
- New `BehaviorClassifier` class added as pre-processor

---

## Consequences

### Positive

- **Intent-based routing** — route by what user wants to DO, not what words they use
- **Confidence-driven** — 0.9 threshold gives clear auto-route vs human-review boundary
- **Non-destructive** — existing keyword routing continues working
- **Extensible** — add new behaviors without modifying classifier
- **Training data** — keywords field doubles as training corpus for ML classifier

### Negative

- **Cold start** — classifier needs training data before accurate
- **Overhead** — one more classification step per message
- **Maintenance** — behaviors must be reviewed quarterly for relevance

### Risks

| Risk | Mitigation |
|:-----|:-----------|
| Classifier misclassifies | Fallback to Tier 1 keyword routing |
| Behavior taxonomy incomplete | 26 covers all depts; extendable |
| Threshold too high | Configurable per-behavior in `confidence_threshold` |

---

## Implementation Plan

### Phase 1: Data Schema (วันนี้)
- [x] Add DDL for `behavior_taxonomy`, `behavior_route_map`, `schema_migrations`
- [x] Create `behavior_migration.py` with 26 behaviors seed
- [x] Create Behavior → Department route map

### Phase 2: Classifier (Next Sprint)
- [ ] `BehaviorClassifier` class in `central_bus/behavior_classifier.py`
- [ ] Integrate into `router.py` — pre-process before Tier 1
- [ ] Training endpoint: `POST /api/v1/behavior/train`

### Phase 3: Monitoring (Next Sprint)
- [ ] Dashboard: behavior distribution chart
- [ ] Alert: low-confidence patterns
- [ ] AAR: classification accuracy tracking

---

## References

- `central_bus/db.py` — SCHEMA_SQL with new tables
- `central_bus/behavior_migration.py` — seed 26 behaviors
- `central_bus/router.py` — RoutingEngine (to be updated in Phase 2)
- `bus/system/routing_rules.json` — unchanged (Tier 1)
- `profiles/05-architect/routing.yaml` — updated with behavior tasks
