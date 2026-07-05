# SoloCorp OS — Operations Runbook

> **Version:** 0.1.0  
> **Last Updated:** 2026-07-05  
> **Service:** `govctl` — Governance CLI + FastAPI Dashboard Backend  
> **Port:** 8765 (default)

---

## Architecture Overview

SoloCorp OS is a governance-driven orchestration platform. The `govctl` CLI manages
governance artifacts (ADRs, RFCs, Guards) as TOML files in `gov/`, publishes them
to the Central Bus (file-based queue at `bus/queue/`), and tracks project pipeline
state in `bus/projects/`. The Dashboard serves a FastAPI REST API at port 8765
with a dark-themed SPA for monitoring governance, agents, pipeline progress, and
system metrics — plus a terminal-based dashboard via `govctl dashboard`.

```
User
 ├── govctl CLI (terminal)
 │    ├── adr/rfc/guard CRUD
 │    ├── threshold assessment
 │    ├── bridge daemon (watch + publish)
 │    ├── ao agent orchestration
 │    ├── api start/stop
 │    └── dashboard (terminal UI)
 ├── Web Dashboard (http://localhost:8765)
 └── REST API (port 8765)
      ├── GET  /api/v1/health
      ├── GET  /api/v1/gov/*
      ├── GET  /api/v1/agents
      ├── POST /api/v1/agents/{id}/run
      ├── GET  /api/v1/pipeline/status
      └── GET  /api/v1/metrics
```

---

## Commands Reference

### govctl CLI

| Command | Description |
|---------|-------------|
| `govctl validate adr` | Validate all ADRs |
| `govctl threshold assess <path>` | Complexity assessment of a TOML artifact |
| `govctl bridge start` | Start bridge daemon (watches `gov/` for changes) |
| `govctl bridge publish <path>` | Publish a single TOML artifact to Central Bus |
| `govctl bridge status` | Check bridge daemon status |
| `govctl bridge stop` | Stop bridge daemon |
| `govctl bridge ao-start` | Start AO bridge listener |
| `govctl bridge ao-stop` | Stop AO bridge listener |
| `govctl bridge ao-status` | Show AO bridge listener status |
| `govctl ao list` | List AO agents |
| `govctl ao run <agent>` | Run an AO agent (`ceo`, `orchestrator`, `architect`, `engineering`, `qa`) |
| `govctl ao status` | Show AO CLI and agent registry status |
| `govctl ao bridge <start\|stop\|status>` | Manage AO bridge daemon |
| `govctl api start` | Start FastAPI REST server (daemon, port 8765) |
| `govctl api stop` | Stop API server |
| `govctl api status` | Check API server status |
| `govctl dashboard` | Show one-shot terminal dashboard |
| `govctl dashboard --watch` | Live-updating terminal dashboard (refresh every 5s) |
| `govctl dashboard --watch --interval 2` | Live dashboard with 2s refresh |
| `govctl init` | Initialize governance directory structure in `gov/` |
| `govctl status` | Show governance artifact counts |

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve dashboard SPA (`index.html`) |
| GET | `/static/*` | Serve static assets (CSS, JS) |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/gov/adrs` | List ADRs |
| POST | `/api/v1/gov/adrs` | Create a new ADR |
| GET | `/api/v1/gov/rfcs` | List RFCs |
| GET | `/api/v1/gov/guards` | List Guards |
| GET | `/api/v1/agents` | List 5 AO agents |
| POST | `/api/v1/agents/{id}/run` | Run an agent (non-blocking) |
| GET | `/api/v1/pipeline/status` | Pipeline status for all projects |
| GET | `/api/v1/metrics` | System-wide metrics |

---

## Startup Sequence

### 1. Ensure Central Bus directories exist

```bash
ls bus/    # Should show: governance/  projects/  queue/

# If empty, initialize a test project:
python -c "
from central_bus.state import init_project
init_project('example', name='Example Project')
"
```

### 2. Start the bridge daemon (optional — watches gov/ for changes)

```bash
govctl bridge start
# → Bridge daemon started (PID 12345)

# Verify:
govctl bridge status
# → Bridge is running (PID 12345)
```

### 3. Publish existing governance artifacts (one-time)

```bash
govctl bridge publish gov/adr/ADR-001.toml
govctl bridge publish gov/adr/ADR-002.toml
# ... or publish all at once via the bridge watcher (step 2 does this automatically)
```

### 4. Start the API server

```bash
govctl api start
# → API server started (PID 12346) on http://0.0.0.0:8765
```

### 5. Open the web dashboard

```
http://localhost:8765

Expected: Dark-themed SoloCorp OS dashboard with:
  - Green "Online" health indicator
  - Governance artifact counts (ADRs, RFCs, Guards)
  - Agent cards with Run buttons
  - Pipeline project progress bars
  - Monitoring stats + event log
```

### 6. (Optional) Start AO bridge

```bash
govctl bridge ao-start
# Requires AO CLI installed and gov/ao_config.toml with [ao].enabled = true
```

---

## Monitoring

### Health Check

```bash
curl http://localhost:8765/api/v1/health
# → {"status":"ok","service":"govctl-api","version":"0.1.0"}
```

### Metrics

```bash
curl http://localhost:8765/api/v1/metrics | python -m json.tool
# → {
#     "timestamp": "2026-07-05T...",
#     "active_projects": 3,
#     "queued_messages": {"critical": 0, "high": 0, "normal": 12, "low": 0},
#     "total_queued": 12,
#     "adr_count": 6,
#     "rfc_count": 1,
#     "guard_count": 1,
#     "agent_count": 5,
#     "recent_events": [...]
#   }
```

### Terminal Dashboard

```bash
# One-shot view
govctl dashboard

# Live-updating (every 5s)
govctl dashboard --watch

# Custom refresh rate
govctl dashboard --watch --interval 2
```

---

## Restart Procedure

Use this procedure to cleanly restart the govctl API server.

### 1. Stop the API server

```bash
govctl api stop
# → API server stopped
```

### 2. Start the API server

```bash
govctl api start
# → API server started (PID ...) on http://0.0.0.0:8765
```

### 3. Verify the server is running

```bash
govctl api status
# → API server is running (PID ...) on port 8765

# Optional: confirm via health endpoint
curl http://localhost:8765/api/v1/health
# → {"status":"ok","service":"govctl-api","version":"0.1.0"}
```

---

## Troubleshooting

### Bridge won't start

```
Symptom:  "Bridge is already running"
Fix:      govctl bridge stop    (kills stale PID)
Confirm:  govctl bridge status  → "Bridge is not running"
Restart:  govctl bridge start
```

If `PID_FILE` (`~/.govctl/bridge.pid`) points to a dead process:

```bash
rm ~/.govctl/bridge.pid
govctl bridge start
```

### API won't start

```
Symptom:  "Port 8765 already in use"
Fix:      govctl api stop
          # or kill manually:
          kill $(lsof -t -i:8765)
          govctl api start

Symptom:  "uvicorn is not installed"
Fix:      pip install uvicorn[standard]
```

### Dashboard shows "Offline" / errors

```
1. Check API server:     govctl api status
2. Check health:         curl http://localhost:8765/api/v1/health
3. Restart API:          govctl api stop && govctl api start
4. Check logs:           cat ~/.govctl/api.log
```

### AO agent fails

```
Symptom:  "AO CLI 'agent_orchestrator' is not available"
Fix 1:    Install AO CLI and ensure it's on PATH
Fix 2:    Set custom path:  export AO_CLI_PATH=/path/to/agent_orchestrator
Fix 3:    Update config:    vi gov/ao_config.toml
                             → set [ao].cli_path
Symptom:  "AO bridge disabled in config"
Fix:      vi gov/ao_config.toml
           → set [ao].enabled = true
```

### Queue messages accumulating

Dead letters accumulate in `bus/queue/dead_letter/`. Inspect them:

```bash
python -c "
from central_bus.queue import list_dead_letters
for dl in list_dead_letters():
    print(dl['message']['id'], dl['reason'])
"
```

### Governance state corruption

If a project `state.json` becomes unreadable, inspect the file:

```bash
cat bus/projects/<project_id>/state.json | python -m json.tool
```

To recover, re-initialise the project state (this is destructive):

```bash
python -c "
from central_bus.state import init_project
init_project('<project_id>', name='Recovered Project')
"
```

---

## Data Layout

```
./
├── bus/
│   ├── governance/           # Guard event logs per project
│   │   └── <project_id>/
│   │       └── guard_events.jsonl
│   ├── projects/             # Pipeline state per project
│   │   └── <project_id>/
│   │       ├── state.json    # Current phase, status, blockers
│   │       └── audit/        # Immutable message audit log
│   │           └── YYYY-MM-DD.jsonl
│   └── queue/                # Message queue (priority-based JSONL)
│       ├── critical.jsonl
│       ├── high.jsonl
│       ├── normal.jsonl
│       ├── low.jsonl
│       └── dead_letter/      # Failed messages after max retries
├── gov/
│   ├── adr/                  # Architecture Decision Records (TOML)
│   ├── rfc/                  # Request for Comments (TOML)
│   ├── guards/               # Verification Guards (TOML)
│   ├── config/               # govctl configuration
│   ├── config.toml           # System config
│   └── ao_config.toml        # Agent Orchestrator config
└── logs/                     # Runtime logs
```
