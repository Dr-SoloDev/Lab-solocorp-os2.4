# Schema Review Request — Behavior-Centric Routing

**ถึง:** @product-produck (Product)
**จาก:** @architect-songsak (Architect)
**วันที่:** 2026-07-20

---

## สรุป

เราเพิ่ม **Behavior Layer** ใน routing pipeline — classify user intent ก่อน keyword matching

## สิ่งที่ Product ต้อง Review

### 1. 26 Behaviors — ครอบคลุมทุก Use Case?

ตรวจสอบว่า 26 behaviors นี้ cover ทุก scenarios ที่ Product เคยเจอ:

| Domain | Behavior | Description |
|:-------|:---------|:------------|
| leadership | `vision_strategy` | วิสัยทัศน์ กลยุทธ์ |
| leadership | `owner_decision` | การตัดสินใจ CEO |
| finance | `budget_approval` | อนุมัติงบ |
| finance | `cost_analysis` | วิเคราะห์ต้นทุน |
| marketing | `campaign_management` | แคมเปญ |
| marketing | `brand_strategy` | แบรนด์ |
| content | `content_production` | เนื้อหา |
| operations | `pipeline_coordination` | ประสานงาน |
| architecture | `architecture_design` | ออกแบบระบบ |
| architecture | `routing_monitoring` | เฝ้าระบบ |
| product | `feature_definition` | Feature PRD |
| product | `roadmap_planning` | Roadmap |
| engineering | `backend_development` | Backend |
| engineering | `frontend_development` | Frontend |
| engineering | `bug_fixing` | แก้บั๊ก |
| design | `visual_design` | Visual |
| design | `ux_research` | UX Research |
| quality | `qa_testing` | QA |
| sales | `sales_deal` | ขาย |
| support | `customer_support` | Support |
| legal | `legal_compliance` | Compliance |
| legal | `contract_management` | สัญญา |
| web3 | `smart_contract_defi` | Web3 |
| network | `network_operations` | Network |
| security | `security_incident` | Security |
| psychology | `behavioral_research` | Psychology |

### 2. ไฟล์ที่เปลี่ยนแปลง

| ไฟล์ | การเปลี่ยนแปลง |
|:-----|:--------------|
| `central_bus/db.py` | Added `behavior_taxonomy`, `behavior_route_map`, `schema_migrations` tables |
| `central_bus/behavior_migration.py` | **New** — migration script + 26 behaviors seed |
| `docs/adrs/ADR-016-behavior-centric-routing.md` | **New** — Architecture Decision Record |
| `profiles/05-architect/routing.yaml` | Added behavior tasks (v2.1) |

### 3. Flow Diagram

```
[User Message]
    │
    ▼
Behavior Classifier (New!)
    │
    ├── Confidence >= 0.9 → Route to primary_dept ✓
    │
    └── Confidence < 0.9 → Keyword (Tier 1) → Semantic (Tier 2) → CEO (Tier 3)
```

## Request

ช่วย review:

1. **26 behaviors** — ครอบคลุมทุก feature ที่ Product วางแผนไว้หรือไม่?
2. **Behavior mapping** — behavior → department ถูกต้องไหม?
3. **Keywords** — มี keyword สำคัญที่ขาดหายไปไหม?

**ตอบกลับภายใน:** 24 ชม.
