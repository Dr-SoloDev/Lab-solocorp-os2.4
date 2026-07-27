---
name: "@solocorp/cfo/budget-check"
version: 0.1.0
category: cfo
platforms: [opencode, grok]
trigger: "/budget-check"
mirror_check: L2
---

# 💰 Budget Check — CFO Skill

> ตรวจสอบงบประมาณ, cost analysis, ROI projection — สำหรับทุก department

## Purpose
เมื่อ department ต้องการตรวจสอบงบประมาณ, วิเคราะห์ cost, หรือขอ ROI projection ก่อนเริ่ม project ใหม่

## Inputs
| Field | Required | Description |
|:------|:--------:|:------------|
| `action` | Yes | `check` (ดูงบ), `analyze` (วิเคราะห์ cost), `project` (ROI) |
| `department` | Yes | ชื่อ department ที่ต้องการตรวจสอบ |
| `period` | Yes | `monthly`, `quarterly`, `ytd` |
| `amount` | No | ถ้า action=project — งบประมาณที่ต้องการขอ |
| `description` | No | รายละเอียดรายการที่ต้องการตรวจสอบ |

## Steps
1. ตรวจสอบ department + period
2. action=check → ดึงงบ current usage vs budget
3. action=analyze → วิเคราะห์ cost trends และ variance
4. action=project → คำนวณ ROI projection + payback period
5. รายงานผล + recommendations

## Output
```
💰 Budget Check — {department}
   Period: {period}
   Budget: {allocated} | Spent: {spent} | Remaining: {remaining}
   Burn Rate: {percent}%
   Status: 🟢 On Track / 🟡 Warning / 🔴 Over Budget
   Recommendations: {n}
```

## Integration
- Central Bus: `POST /v1/skills/cfo/budget-check`
- Queue: `skill.cfo.invoke` → cfo review
- Mirror: L2 — data is read-only, no Mirror required
