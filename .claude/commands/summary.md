---
name: summary
description: Auto-Brain Summary — สรุป session auto สิ้น session
---

# Summary

Generate structured session summary + append to session-log.md.

## Usage
```
/summary [--save]
```

## Script
Run `python scripts/session-summary.py --save`

## Output
- Structured summary of session work
- Key decisions made
- Open items for next session
- Append to `brain/session-log.md`

## Example
```
/summary --save
```
