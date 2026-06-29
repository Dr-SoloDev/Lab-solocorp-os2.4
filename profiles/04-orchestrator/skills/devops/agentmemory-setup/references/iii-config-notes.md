# iii-sdk Config Structure Notes

## Source: /home/drsolodev/agentmemory-src/iii-config.yaml

Key settings:
- DB: file-based KV store at `./data/state_store.db` (relative to agentmemory-src)
- HTTP port: 3111
- Stream port: 3112

## package.json (v0.9.21)
- SDK: iii-sdk@0.11.2
- Runtime: TypeScript ESM
- Key deps: @anthropic-ai/sdk, zod, dotenv
- Start command: `node dist/cli.mjs`
- Migrate command: `node dist/functions/migrate.js`
- Consolidation pipeline: `node dist/functions/consolidation-pipeline.js`

## KV Key Namespaces (from src/state/schema.ts)
- sessions
- observations
- memories
- summaries
- semantic
- procedural
- graph nodes / edges

## MCP Tool Namespace
All agentmemory MCP tools are prefixed: `mcp_agentmemory_*`

Key tools:
- `mcp_agentmemory_memory_save` — save insight/fact
- `mcp_agentmemory_memory_recall` — search past observations
- `mcp_agentmemory_memory_smart_search` — hybrid semantic+keyword search
- `mcp_agentmemory_memory_sessions` — list recent sessions
- `mcp_agentmemory_memory_export` — export all data as JSON
- `mcp_agentmemory_memory_governance_delete` — delete specific memories
- `mcp_agentmemory_memory_audit` — view audit trail

## Daemon State Files
- `~/.agentmemory/engine-state.json` — engine runtime state
- `~/.agentmemory/iii.pid` — PID file
- `~/.agentmemory/preferences.json` — user preferences

## Consolidation Pipeline
- Requires `CONSOLIDATION_ENABLED=true` in .env
- Has built-in decay logic
- Registered as function `mem::consolidate-pipeline`
- Run: `node dist/functions/consolidation-pipeline.js`