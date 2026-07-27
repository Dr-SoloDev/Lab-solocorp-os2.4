---
name: audit
description: ตรวจสอบ pipeline audit trail และ compliance
---

# Audit

Run a pipeline audit — verify handoff integrity, QA evidence, decision trail, compliance.

## Usage
```
/audit [scope]
```

## Audit Checks
1. **Handoff Integrity** — All handoffs have evidence
2. **QA Evidence** — Tests run, results recorded
3. **Decision Trail** — L3+ decisions have mirror check
4. **Compliance** — SOP adherence (SOP-01 through SOP-05)
5. **Queue Health** — No stale items

## Example
```
/audit pipeline
/audit handoff EN-003
```
