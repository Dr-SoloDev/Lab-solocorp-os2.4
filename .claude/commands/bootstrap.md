---
name: bootstrap
description: Auto-Session Bootstrap — inject context auto ตอนเริ่ม session
---

# Bootstrap

Auto-Session Bootstrap — inject system state, brain context, active dispatches, and pending items when starting a session.

## Usage
```
/bootstrap
```

## Script
Run `python scripts/session-bootstrap.py`

## What it Injects
1. Current system state (from loop_runner/state.py)
2. Brain memory context
3. Active dispatches from Central Bus
4. Pending queue items
5. Recent session summaries

## Output
Structured briefing for CEO to determine focus areas.

## Example
```
/bootstrap
```
