---
name: "@solocorp/governance/rfc"
version: 0.1.0
category: governance
platforms: [opencode, grok]
trigger: "/rfc-new"
mirror_check: L3
---

# 📜 RFC — Governance Skill

> สร้างหรือ review RFC สำหรับการเปลี่ยนแปลงสำคัญใน SoloCorp OS

## Purpose
เมื่อต้องการ proposal การเปลี่ยนแปลงที่มีผลกระทบข้าม department → ต้องผ่าน RFC process

## Inputs
| Field | Required | Description |
|:------|:--------:|:------------|
| `action` | Yes | `create` (สร้าง RFC), `review` (give feedback), `approve` / `reject` |
| `title` | Yes | ชื่อ RFC |
| `author` | Yes | ชื่อ department หรือคนที่เสนอ |
| `summary` | Yes | สรุปการเปลี่ยนแปลงที่ต้องการ |
| `impact` | Yes | department ที่ได้รับผลกระทบ |
| `rfc_id` | No | ถ้า action=review/approve/reject — ต้องใส่ RFC ID |

## Steps
1. Mirror Check — RFC ต้องผ่าน Mirror (กระทบ ≥1 department)
2. action=create → กำหนด RFC ID → เปิด comment period
3. action=review → บันทึก feedback ใน RFC thread
4. action=approve → RFC ผ่าน → บันทึก ADR
5. action=reject → RFC ปิด → บันทึกเหตุผล
6. กระจายแจ้งทุก department ที่เกี่ยวข้อง

## Output
```
📜 RFC — {rfc_id}: {title}
   Author: {author}
   Status: 🟡 Draft / 🟢 Open / ✅ Approved / ❌ Rejected
   Impact: {departments}
   Comments: {n}
   Decision Deadline: {date}
```

## Integration
- Central Bus: `POST /v1/skills/governance/rfc`
- Queue: `skill.gov.invoke` → gov review → comment period
- Mirror: L3 — governance change บังคับ Mirror Check

## Dependencies
- `@solocorp/cross-dept/mirror-check` — mandatory on create
- Result → `decisions/` directory as ADR on approval
