---
name: mirror
description: Auto-Mirror Check — รัน mirror check (L3+ decisions)
---

# Mirror

Auto-Mirror Check — run mirror check for department decisions.

## Usage
```
/mirror <department> <decision> <priority>
```

## Script
Uses `central_bus.plugins.auto_mirror_hook.auto_mirror_check()`

## Protocol
- **L1-L2**: Auto-pass (no check needed)
- **L3+**: LLM evaluation with 3 mirror questions

## Example
```
/mirror engineering "Switch database" L3
```
