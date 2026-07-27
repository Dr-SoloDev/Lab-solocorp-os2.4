---
name: "@solocorp/ceo/sprint-plan"
version: 0.1.0
category: ceo
platforms: [opencode, grok, claude]
trigger: "/sprint-plan"
mirror_check: L1
---

# 📋 Sprint Plan — CEO Skill

> Sprint planning, progress tracking, และ status report สำหรับทุก department ใน SoloCorp OS

## Purpose
เมื่อ department ต้องการ sprint plan template, รายงานความคืบหน้า, หรือ dashboard sprint status

## Inputs
| Field | Required | Description |
|:------|:--------:|:------------|
| `department` | Yes | ชื่อ department (ceo, coo, architect, engineering, etc.) |
| `sprint` | Yes | Sprint ID หรือชื่อ (e.g. "Sprint 2", "Master Synthesis v2") |
| `action` | Yes | ต้องการอะไร: `plan` (ขอ template), `report` (รายงาน), `status` (dashboard) |
| `tasks` | No | ถ้า action=report — รายการ tasks ที่ทำเสร็จ/กำลังทำ/ติดขัด |
| `blockers` | No | ถ้ามี blocker — อธิบายปัญหา |

## Steps
1. ตรวจสอบ department + sprint มีในระบบหรือไม่
2. ถ้า action=plan → สร้าง sprint plan template ตาม department
3. ถ้า action=report → บันทึกความคืบหน้า + อัปเดต dashboard
4. ถ้า action=status → ดึง sprint status จาก Central Bus evidence + queue
5. ส่งผลกลับแบบ structured

## Output
```
📋 Sprint Plan — {department}
   Sprint: {sprint}
   Status: 🟢 On Track / 🟡 At Risk / 🔴 Blocked
   Tasks: {completed}/{total} ({progress}%)
   Next Milestone: {date}
   Blockers: {none or list}
```

## Example
```bash
# ขอ sprint plan สำหรับ COO department
curl -X POST http://localhost:8099/v1/skills/ceo/sprint-plan \
  -H "X-API-Key: sk-..." \
  -d '{"department":"coo","sprint":"Sprint 2","action":"plan"}'

# รายงานความคืบหน้า
curl -X POST http://localhost:8099/v1/skills/ceo/sprint-plan \
  -H "X-API-Key: sk-..." \
  -d '{"department":"engineering","sprint":"Sprint 2","action":"report","tasks":[{"id":"EN-03","status":"in_progress"}]}'
```

## Integration
- Central Bus: `POST /v1/skills/ceo/sprint-plan`
- Queue: `skill.ceo.invoke` → ceo review → complete
- Mirror: L1 — ทุก department ใช้ได้โดยไม่ต้อง Mirror Check
