---
name: "@solocorp/qa/smoke-test"
version: 0.1.0
category: qa
platforms: [opencode, grok, claude]
trigger: "/smoke-test"
mirror_check: L1
---

# 🧪 Smoke Test — QA Skill

> รัน smoke test suite สำหรับ service ใด ๆ ใน SoloCorp OS

## Purpose
เมื่อต้องการรัน smoke test ก่อน deploy หรือ check health หลัง deploy

## Inputs
| Field | Required | Description |
|:------|:--------:|:------------|
| `service` | Yes | ชื่อ service (central-bus, agent-worker, etc.) |
| `environment` | Yes | `dev`, `staging`, `production` |
| `scope` | No | `quick` (health check), `full` (full smoke suite) |

## Steps
1. ตรวจสอบ service มี smoke test suite หรือไม่
2. เช็คว่า environment พร้อม
3. รัน smoke test
4. รวบรวมผล pass/fail/skip
5. Report summary
6. QA Gate: ถ้า fail ≥ threshold → block deploy (post evidence)

## Output
```
🧪 Smoke Test — {service}
   Environment: {env}
   Tests: {pass}/{total} | Fail: {fail} | Skip: {skip}
   Duration: {seconds}s
   Gate: ✅ Passed / ❌ Blocked
   Failures:
     - {test_name}: {error}
```

## Integration
- Central Bus: `POST /v1/skills/qa/smoke-test`
- Queue: `skill.qa.invoke` → qa exec → report
- Mirror: L1 — anyone can run smoke tests
