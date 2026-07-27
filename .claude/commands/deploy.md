---
name: deploy
description: Deploy ระบบ SoloCorp OS (profiles, skills, config)
---

# Deploy

Deploy SoloCorp OS changes — profiles, skills, config, agents.

## Usage
```
/deploy [target]
```

## Deploy Steps
1. **Build profiles** — `python3 scripts/build-profiles.py`
2. **Export agents** — `python3 scripts/export-codex-agents.py`
3. **Verify** — `python3 scripts/export-codex-agents.py --validate-only`
4. **Commit** — git commit with deploy message
5. **Report** — deployment summary

## Targets
- `profiles` — rebuild department profiles
- `agents` — export all agents
- `skills` — validate skills
- `full` — all of the above (default)

## Example
```
/deploy full
```
