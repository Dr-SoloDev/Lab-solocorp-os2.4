---
name: "@solocorp/engineering/deploy"
version: 0.1.0
category: engineering
platforms: [opencode, grok]
trigger: "/deploy"
mirror_check: L2
---

# 🚀 Deployment — Engineering Skill

> Trigger deploy, check status, rollback — สำหรับทุก deployment ใน SoloCorp OS

## Purpose
เมื่อ engineering team ต้องการ deploy, ตรวจสอบสถานะ deploy, หรือ rollback

## Inputs
| Field | Required | Description |
|:------|:--------:|:------------|
| `action` | Yes | `deploy` (trigger), `status` (check), `rollback` (ย้อนกลับ) |
| `environment` | Yes | `dev`, `staging`, `production` |
| `service` | Yes | ชื่อ service (central-bus, agent-worker, etc.) |
| `ref` | No | commit hash หรือ tag (for deploy) |
| `reason` | No | เหตุผลในการ deploy/rollback |

## Steps
1. Mirror Check — production deploy ต้องผ่าน CEO ก่อน
2. ตรวจสอบ environment + service มีในระบบ
3. action=deploy → จัด queue deploy ไปยัง pipeline
4. action=status → ดึงสถานะจาก pipeline logs
5. action=rollback → revert ไปยัง ref ก่อนหน้า
6. บันทึก audit trail

## Output
```
🚀 Deploy — {service}
   Environment: {env}
   Action: {action}
   Status: ✅ Success / 🔄 Running / ❌ Failed
   Ref: {commit_hash}
   Duration: {seconds}s
   Audit Trail: {id}
```

## Integration
- Central Bus: `POST /v1/skills/engineering/deploy`
- Queue: `skill.eng.invoke` → deploy
- Mirror: L2 (production = destructive → Mirror ต้องผ่าน CEO)
