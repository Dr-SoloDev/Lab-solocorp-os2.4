---
name: "@axis/cto/deploy"
version: 1.0.0-dualrun
category: cto
platforms: [opencode, grok]
trigger: "/cto-deploy"
mirror_check: L2
---

# 🚀 Deploy (CTO shadow) — forward to Engineering

> CTO dual-run shim — **forward-only** ไม่ implement เอง ไม่แตะ logic เดิม

## Purpose
รับคำสั่ง deploy ในสาย CTO แล้ว forward ไปยัง owner ตัวจริง (Engineering) ผ่าน Bus เดิม

## Inputs
| Field | Required | Description |
|:------|:--------:|:------------|
| `action` | Yes | `deploy` / `status` / `rollback` (ส่งต่อตรง) |
| `environment` | Yes | `dev`, `staging`, `production` |
| `service` | Yes | ชื่อ service |
| `ref` | No | commit hash หรือ tag |
| `reason` | No | เหตุผล |

## Steps
1. ตรวจ Phase 1 scope — deploy อยู่ใน Build (07 alias) → owner = Engineering (ช่างฟูล)
2. Forward payload ทั้งก้อนไปยัง `@axis/engineering/deploy` (endpoint `/v1/skills/engineering/deploy`, queue `skill.eng.invoke`) — ห้ามแปลง ห้ามตัด
3. บันทึก `cto_shadow: true, dual_run_weight: 10` ใน audit trail เพื่อเทียบผล byte-identical กับสายเดิม 90%
4. ถ้า production → Mirror L2 ผ่าน CEO ก่อน (เหมือนเดิม)
5. CTO ห้าม merge/deploy เอง — รอ Engineering ดำเนินการ

## Output
เหมือน `@axis/engineering/deploy` ทุกไบต์ + เพิ่ม `via: cto-shadow`

## Integration
- Forward to: `POST /v1/skills/engineering/deploy`
- Queue: `skill.eng.invoke` (เดิม — ไม่สร้าง queue ใหม่)
- Mirror: L2 (เหมือน engineering/deploy)
- Evidence: `bus/evidence/cto-migration/*/dual-run-20calls.json`
