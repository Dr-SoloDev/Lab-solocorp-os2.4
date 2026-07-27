---
name: triage
description: Auto-Triage — classify + route queue entries, L1-L2 auto-execute
---

# Triage

Auto-Triage — classify pending queue entries by priority + department.

## Usage
```
/triage
```

## Script
Run `python workers/agents/auto_triage_agent.py`

## Classification
- **L1** (Auto): Execute immediately
- **L2** (Auto): Execute with monitoring
- **L3** (Propose): Present to CEO for approval
- **L4-L5** (Escalate): Forward to CEO/Owner

## Output
- Auto-dispatched items (L1-L2)
- Proposed items (L3)
- Escalated items (L4-L5)

## Example
```
/triage
```
