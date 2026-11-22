---
name: status
description: >
  Show SoloCorp pipeline and runtime health. Use when the user runs /status,
  asks if the bus is up, wants governance/queue status, or a system health snapshot.
argument-hint: ""
user-invocable: true
---

# SoloCorp `/status`

Produce a live (best-effort) health snapshot of SoloCorp OS on this machine.

## Steps

Run from repo root with `PYTHONPATH=.` when needed.

### 1. Central Bus

```bash
curl -s -m 2 http://127.0.0.1:8099/v1/health || echo "bus: down"
```

If down, note how to start:

```bash
source .venv/bin/activate && export PYTHONPATH=.
uvicorn central_bus.main:app --host 127.0.0.1 --port 8099
```

### 2. govctl API (if used)

```bash
curl -s -m 2 http://127.0.0.1:8765/api/v1/health || echo "govctl-api: down"
```

### 3. Governance artifacts

```bash
python -m govctl_cli status 2>/dev/null || ./govctl status 2>/dev/null || ls gov/adr gov/rfc gov/guards 2>/dev/null
```

### 4. Queue / projects

- List recent files under `bus/queue/` (high/normal offsets, dead_letter).
- List `bus/projects/*` names and any `state.json` status fields if present.

### 5. Loop runner (optional)

- Check `logs/loop_runner.log` mtime / last lines if file exists.
- Note: loops run via `python -m loop_runner.main`.

## Output format

```markdown
# SoloCorp Status

| Component | State | Detail |
|-----------|-------|--------|
| Central Bus :8099 | up/down | ... |
| govctl API :8765 | up/down | ... |
| Governance | ok | ADR/RFC/Guard counts |
| Queue | ... | depths / offsets |
| Projects | n | names |

## Notes
- ...
## Recommended next actions
- ...
```

## Rules

- Prefer real commands over guesses.
- Do not start long-running servers unless the user asked to bring the system up.
- Thai primary for narrative; keep table labels bilingual if helpful.
