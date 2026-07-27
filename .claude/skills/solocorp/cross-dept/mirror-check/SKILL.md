---
name: "@solocorp/cross-dept/mirror-check"
version: 0.1.0
category: cross-dept
platforms: [opencode, grok, claude-code]
trigger: "/mirror-check"
---

# 🪞 Mirror Check — Cross-Department Skill

> "decision นี้สะท้อน Dr.solodev Owner หรือไม่?"

## Purpose
เมื่อ department head กำลังจะตัดสินใจสำคัญ ให้รัน `/mirror-check` เพื่อตรวจสอบว่า decision สอดคล้องกับตัวตน ค่านิยม และวิธีคิดของ Dr.solodev Owner

## Inputs
| Field | Required | Description |
|:------|:--------:|:------------|
| `decision` | Yes | decision ที่กำลังจะทำ |
| `department` | Yes | department ที่จะดำเนินการ |
| `impact_level` | No | single-dept / multi-dept / org-wide |
| `context` | No | context เพิ่มเติม |

## Mirror Check Questions
1. "Dr.solodev จะทำแบบนี้ไหม?"
2. "Decision นี้สะท้อนตัวตนของ Dr.solodev หรือไม่?"
3. "ถ้า Owner เห็น decision นี้ จะ approve หรือ reject?"

## Steps
1. รับ decision + context
2. วิเคราะห์ผ่าน Mirror Check Questions
3. ประเมิน alignment score (0-100%)
4. บันทึกผลลง Audit Trail
5. คืนผล: PASS / FAIL / ESCALATE

## Output
```
🪞 Mirror Check Result
   Decision: {decision}
   Department: {dept}
   Score: {score}%
   Result: ✅ PASS / ❌ FAIL / ⚠️ ESCALATE
   Audit Trail: {id}
```

## Integration
- Central Bus: `POST /v1/skills/cross-dept/mirror-check`
- Queue: `governance.mirror`
- Audit: ทุกผลลัพธ์บันทึกใน governance audit trail
