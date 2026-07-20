---
name: "@solocorp/cross-dept/pipeline-bridge"
version: 0.1.0
category: cross-dept
platforms: [opencode, grok]
trigger: "/pipeline-bridge"
mirror_check: L3
---

# 🔗 Pipeline Bridge — Cross-Department Skill

> ส่ง task ข้ามแผนกด้วย structured handoff + audit trail + Mirror Check

## Purpose
เมื่อต้องการส่งงานจาก department หนึ่งไปยังอีก department หนึ่ง โดยมี structured format, audit trail, และ Mirror Check อัตโนมัติ

## Inputs
| Field | Required | Description |
|:------|:--------:|:------------|
| `from_dept` | Yes | ต้นทาง (architect, engineering, cfo, etc.) |
| `to_dept` | Yes | ปลายทาง |
| `task` | Yes | งานที่ต้องการให้ทำ |
| `context` | No | Context เพิ่มเติม |
| `deadline` | No | Deadline |
| `priority` | No | P0/P1/P2/P3 |

## Steps
1. Mirror Check — ตรวจสอบว่าการส่งงานนี้สะท้อน Dr.solodev Owner หรือไม่
2. สร้าง structured handoff payload
3. ส่งเข้า Bus Queue (topic: skill.invoke)
4. บันทึก Audit Trail
5. แจ้ง department ปลายทาง

## Output
```
✅ Pipeline Bridge Complete
   From: {from_dept} → To: {to_dept}
   Task: {task}
   Mirror Check: ✅ PASSED
   Audit Trail: {id}
```

## Integration
- Central Bus: `POST /v1/skills/cross-dept/pipeline-bridge`
- Queue: `skill.invoke` → `skill_complete` → `audit_trail`
- Mirror: Level L3 ขึ้นไป (cross-dept = กระทบ ≥2 departments)
