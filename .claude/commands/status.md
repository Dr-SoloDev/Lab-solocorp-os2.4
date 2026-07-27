---
name: status
description: ดูสถานะภาพรวมของ SoloCorp OS pipeline
---

# Status

Full status report of SoloCorp OS — pipeline, departments, queue, health.

## Usage
```
/status [department]
```

## Sources
Read from:
- `loop_runner/state.py` — loop runner state
- `bus/projects/` — project statuses
- `bus/dispatch/` — active dispatches
- `bus/queue/` — pending queue
- `central_bus/health.py` — service health

## Output
Structured dashboard showing:
- Active projects by department
- Queue depth + SLA
- Health check results
- Pending decisions
- Blockers

## Example
```
/status engineering
```
