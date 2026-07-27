---
name: brain
description: บันทึก context/session ลง brain memory
---

# Brain

Document current session context for brain memory.

## Usage
```
/brain [note]
```

## Format
Write to `brain/session-log.md`:
```
วัน/time + summary + key decisions + open items + commit hash
```

## Script
Run `brain/loops/brain_auto_commit.py` for automated context capture.

## Example
```
/brain Finished API Key Protection rollout, all 19 depts tested
```
