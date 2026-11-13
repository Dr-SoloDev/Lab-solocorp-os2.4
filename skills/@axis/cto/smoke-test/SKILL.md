---
name: "@axis/cto/smoke-test"
version: 1.0.0-dualrun
category: cto
platforms: [opencode, grok, claude]
trigger: "/cto-smoke-test"
mirror_check: L1
---

# 🧪 Smoke Test (CTO shadow) — forward to QA

> CTO dual-run shim — **forward-only** ไม่ implement เอง ไม่แตะ logic เดิม

## Purpose
รับคำสั่ง smoke-test ในสาย CTO แล้ว forward ไปยัง owner ตัวจริง (QA) ผ่าน Bus เดิม

## Inputs
| Field | Required | Description |
|:------|:--------:|:------------|
| `service` | Yes | ชื่อ service |
| `environment` | Yes | `dev`, `staging`, `production` |
| `scope` | No | `quick` / `full` (ส่งต่อตรง) |

## Steps
1. ตรวจ Phase 1 scope — smoke-test อยู่ใน QA (10 alias) → owner = QA-ทีม
2. Forward payload ทั้งก้อนไปยัง `@axis/qa/smoke-test` (endpoint `/v1/skills/qa/smoke-test`, queue `skill.qa.invoke`) — ห้ามแปลง ห้ามตัด
3. บันทึก `cto_shadow: true, dual_run_weight: 10` ใน audit trail เพื่อเทียบผล byte-identical กับสายเดิม 90%
4. เคารพ QA verdict — FAIL = STOP ห้าม override
5. Mirror: L1 (เหมือน qa/smoke-test)

## Output
เหมือน `@axis/qa/smoke-test` ทุกไบต์ + เพิ่ม `via: cto-shadow`

## Integration
- Forward to: `POST /v1/skills/qa/smoke-test`
- Queue: `skill.qa.invoke` (เดิม — ไม่สร้าง queue ใหม่)
- Mirror: L1
- Evidence: `bus/evidence/cto-migration/*/dual-run-20calls.json`
