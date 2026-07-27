---
name: pipeline-bridge
description: Cross-department pipeline bridge — ส่ง task ข้ามแผนก structured handoff + audit trail
---

# Pipeline Bridge

Cross-department pipeline bridge — send task with structured handoff + audit trail.

## Usage
```
/pipeline-bridge <from-dept> <to-dept> <task description>
```

## Protocol
1. **Mirror Check** ก่อนส่ง — ถ้า L3+ ต้องผ่าน filter ใน 01-receive.md
2. Create structured handoff brief
3. Route through Central Bus queue
4. Track in bus/dispatch/

## Example
```
/pipeline-bridge engineering design Fix pixel alignment on dashboard
```
