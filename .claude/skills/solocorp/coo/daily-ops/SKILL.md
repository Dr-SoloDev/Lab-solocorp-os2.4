---
name: "@solocorp/coo/daily-ops"
version: 0.1.0
category: coo
platforms: [opencode, grok]
trigger: "/daily-ops"
mirror_check: L2
---

# 👷 Daily Ops — COO Skill

> รับ daily operations ทั้งหมด — Owner/CEO ไม่ต้องเห็น L1-L3

## Purpose
เมื่อ COO ต้องการ generate daily ops report, route request ไป department ปลายทาง, หรือตรวจสอบ SOP compliance

## Inputs
| Field | Required | Description |
|:------|:--------:|:------------|
| `action` | Yes | `status` (ops report), `route` (ส่ง request), `sop` (ตรวจ compliance) |
| `request` | No | ถ้า action=route — รายละเอียด request ที่ต้องการส่ง |
| `department` | No | ถ้า action=route — ปลายทางที่ต้องการส่ง |
| `priority` | No | P0/P1/P2/P3 |

## Steps
1. ตรวจสอบ action type
2. ถ้า action=status → ดึง queue, dispatch, evidence stats → ops report
3. ถ้า action=route → classify → map department → ส่งเข้า queue
4. ถ้า action=sop → รัน SOP compliance scan → รายงาน coverage
5. L4+ → escalate to CEO | Owner L5 → notify Owner
6. ส่งผลกลับ

## Output
```
👷 COO Daily Ops Report — {date}
   Queue: high={n} normal={n} dead={n}
   Active Dispatches: {n}
   Evidence: {n} entries
   SOP Coverage: {n}/{total} ({percent}%)
   🔴 L4+ Escalations: {n}
   Status: 🟢 All Clear / 🟡 Needs Attention / 🔴 Escalations
```

## Integration
- Central Bus: `POST /v1/skills/coo/daily-ops`
- Queue: `skill.coo.invoke` → coo_process → complete
- Tools: `workers/agents/coo_dispatch_agent.py`, `workers/sop_compliance_check.py`
