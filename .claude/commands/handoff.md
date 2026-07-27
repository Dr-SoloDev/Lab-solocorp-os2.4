---
name: handoff
description: ทำ handoff ระหว่าง departments พร้อม context pack
---

# Handoff

Execute structured handoff between departments with full context pack.

## Usage
```
/handoff <from-department> <to-department> <task description>
```

## Protocol
1. Read 01-receive.md (handoff section)
2. Create handoff brief with:
   - Context summary
   - Requirements
   - Dependencies
   - Deadline
   - Success criteria
3. Route through Central Bus
4. Track evidence in bus/evidence/

## Templates
Handoff templates in: `.opencode/skills/solocorp/handoff-templates/`

## Example
```
/handoff engineering design Implement UI for new dashboard
```
