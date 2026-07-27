---
name: mirror-check
description: Mirror Check Protocol — ตรวจสอบ decision สะท้อน Dr.solodev Owner
---

# Mirror Check

Mirror Check Protocol — verify decisions reflect Owner's vision.

## Usage
```
/mirror-check <decision> [priority]
```

## Protocol (from 01-receive.md Escalation Filter L1-L5)
1. **3 Mirror Check Questions**
   - Does this align with Owner's vision?
   - Would Owner approve this decision?
   - What's the worst case if wrong?
2. **Alignment Score** (0-100)
3. **Audit Trail** — record decision + reasoning
4. **Verdict**: PASS / FAIL / ESCALATE

## Levels
- **L1-L2**: Auto-pass (low risk)
- **L3**: LLM evaluation required
- **L4-L5**: CEO/Owner approval required

## Example
```
/mirror-check Migrate to new LLM provider L4
```
