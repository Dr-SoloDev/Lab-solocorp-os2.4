---
name: agentmemory-setup
description: Setup, configure, and operate agentmemory (iii-sdk) as a production daemon for Hermes Agent — env config, daemon lifecycle, MCP wiring, consolidation pipeline.
tags: [agentmemory, iii-sdk, mcp, memory, daemon, solodordev]
---

# agentmemory Production Setup

**Trigger:** Any task involving agentmemory installation, configuration, daemon management, MCP connection, seeding knowledge, or consolidation pipeline.

## Key Paths

| Item | Path |
|---|---|
| Source | `$AGENTMEMORY_SRC/` |
| Runtime env | `~/.agentmemory/.env` |
| Engine state | `~/.agentmemory/engine-state.json` |
| DB (KV store) | `agentmemory-src/data/state_store.db` |
| iii config | `agentmemory-src/iii-config.yaml` |
| Hermes config | `~/.hermes/config.yaml` |

## Ports

- HTTP API: `3111`
- Stream: `3112`
- Viewer: `3113`
- Engine WS: `ws://localhost:49134`

## Step 1 — Write Production `.env`

Place at `~/.agentmemory/.env` (NOT inside agentmemory-src):

```env
ANTHROPIC_API_KEY=<maxplus-ccsk-key>
CONSOLIDATION_ENABLED=true
GRAPH_EXTRACTION=true
SEMANTIC_MEMORY_ENABLED=true
HTTP_PORT=3111
STREAM_PORT=3112
```

Then lock permissions:
```bash
chmod 600 ~/.agentmemory/.env
```

**MaxPlus quirk:** agentmemory uses the field name `ANTHROPIC_API_KEY` — put the MaxPlus `ccsk-...` key there. The MaxPlus transport is `anthropic_messages` (Anthropic native wire), not OpenAI shim. See `references/maxplus-api-quirks.md`.

## Step 2 — Ensure data/ directory exists

```bash
mkdir -p $AGENTMEMORY_SRC/data
```

## Step 3 — Start Daemon (background)

Always start as background process to avoid terminal timeout (Hermes terminal timeout = 180s):

```bash
cd $AGENTMEMORY_SRC && node dist/cli.mjs &
```

Or via npm:
```bash
npm start &
```

## Step 4 — Verify Daemon

Do NOT rely on `/health` endpoint — it returns 404 (endpoint does not exist by design). Use:

```bash
ss -tlnp | grep 3111
```

Expected output: `iii` process LISTEN on `127.0.0.1:3111`

Also check pid file:
```bash
cat ~/.agentmemory/iii.pid
```

## Step 5 — Verify MCP Connection

agentmemory MCP tools are namespaced `mcp_agentmemory_*`. Test with:

```python
mcp_agentmemory_memory_sessions()
```

If this returns session list, MCP is wired correctly.

## Step 6 — Seed SoloCorp OS Knowledge

Use `mcp_agentmemory_memory_save` to seed core facts:

```python
mcp_agentmemory_memory_save(
    content="...",
    type="fact",        # or: pattern, preference, architecture, bug, workflow
    concepts="solocorp, agent-army, ceo, cfo"
)
```

Key memory types: `fact`, `pattern`, `preference`, `architecture`, `bug`, `workflow`

## Step 7 — Consolidation Cron

Enable nightly consolidation (requires `CONSOLIDATION_ENABLED=true` in `.env`).

**Use Hermes cronjob tool** (NOT system crontab/systemd) — cron jobs run in Hermes agent context so they can call MCP tools directly:

```python
cronjob(
    action="create",
    name="agentmemory-consolidation",
    schedule="0 0 * * *",   # midnight Bangkok = 17:00 UTC
    # DO NOT set enabled_toolsets — leave empty so MCP tools are available
    prompt="""Run agentmemory consolidation pipeline.
Call mcp_agentmemory_memory_sessions to get current session list.
Then trigger consolidation via the mem::consolidate-pipeline function.
Report summary of what was consolidated, merged, or decayed."""
)
```

Verify after creation:
```python
cronjob(action="list")  # check state=scheduled, enabled=true
```

Function registered as `mem::consolidate-pipeline`. Has built-in decay logic.

> ⚠️ Do NOT use system crontab — it cannot call MCP tools. Hermes cronjob is the correct method.

## Pitfalls

- ❌ `/health` returns 404 — NOT an error. Daemon is up if port 3111 is listening. Use `ss -tlnp`.
- ❌ Don't use `find` with broad scope — specify exact paths.
- ❌ Don't start daemon in foreground — Hermes terminal timeout is 180s. Always background.
- ❌ `ANTHROPIC_API_KEY` field takes MaxPlus `ccsk-...` key — not the env var name used by Anthropic directly.
- ❌ DB path is RELATIVE to agentmemory-src (`./data/state_store.db`) — ensure `data/` dir exists before starting.
- ❌ `.env` belongs in `~/.agentmemory/` NOT in `agentmemory-src/` — keep credentials out of source tree.
- ❌ Don't use system crontab for agentmemory consolidation — it can't call MCP tools. Use `cronjob(action='create')` via Hermes tool.
- ❌ After creating a cron job, always verify with `cronjob(action='list')` — confirm `state=scheduled`, `enabled=true`, `toolsets` correct.
- ❌ **CRITICAL: Never set `enabled_toolsets` on the consolidation cron job** — even `["terminal"]` will strip MCP tools and the job will fail silently (Kiro/other agents report "no tools available"). Fix: `cronjob(action='update', job_id=..., enabled_toolsets=[])` to clear the restriction.
- ❌ When Dr.solodev asks "รายงานสถานะ" — report **task progress** (งานที่ทำ, สถานะ phase, next steps), NOT a self-status report of agent components.

## Verification Checklist

- [ ] `~/.agentmemory/.env` exists, chmod 600, contains MaxPlus key
- [ ] `agentmemory-src/data/` directory exists
- [ ] `ss -tlnp | grep 3111` shows iii listening
- [ ] `mcp_agentmemory_memory_sessions()` returns without error
- [ ] `CONSOLIDATION_ENABLED=true` in `.env`

## References

- `references/maxplus-api-quirks.md` — MaxPlus provider quirks for agentmemory
- `references/iii-config-notes.md` — iii-sdk config structure notes