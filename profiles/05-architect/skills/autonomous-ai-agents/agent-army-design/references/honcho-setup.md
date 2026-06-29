# Honcho Setup — Session Reference (2026-06-16)

**Context:** Honcho is the memory/state backend for SoloCorp OS multi-agent system. Deployed as Docker containers alongside the existing headroom proxy infrastructure.

## Deployment Architecture

```
Hermes Agent → Headroom Proxy (:8787/v1) → zen-proxy.js (:4011/zen/v1) → opencode.ai API → DeepSeek
                       ↓
               Honcho API (:8000) — self-hosted PG + Redis
```

The full LLM chain is **three hops**: `headroom → zen-proxy.js → opencode.ai`. Honcho sits alongside this, not in the path — it receives requests from Hermes directly on port 8000 and makes its own LLM calls through the proxy chain.

## What Was Attempted

Goal: Self-host Honcho (Postgres + Redis + API + Deriver workers) behind the existing headroom proxy, configured for deepseek-v4-flash-free (the only available free model).

### Config Adaptation for Free-Tier Proxy

| Change | Reason |
|--------|--------|
| All models → `deepseek-v4-flash-free` | Only accessible free model via proxy |
| `EMBED_MESSAGES = false` | No compatible free embedding API available |
| All `BACKUP_PROVIDER = ""` | Single-provider mode only |
| All `BACKUP_MODEL = ""` | No fallback model |
| `EMBEDDING_PROVIDER = ""` | Vector search disabled entirely |
| `OPENAI_COMPATIBLE_BASE_URL = ""` | No backup provider |
| Vector dimensions → 768 | Irrelevant with embeddings disabled, but matches pgvector defaults |
| THINKING_BUDGET_TOKENS = 1 | DeepSeek doesn't support Anthropic thinking |

### Config File Locations

| File | Purpose | Status |
|------|---------|--------|
| `~/honcho/.env` | API keys + base URLs | Created (proxy endpoint) |
| `~/honcho/config.toml` | Model, provider, DB, deriver config | Modified (as above) |
| `~/honcho/docker-compose.yml` | Service definitions | Cleaned up |
| `~/honcho-self-hosted/honcho-config.json` | Hermes-to-Honcho wiring | Copied but not deployed |

### .env Content

```bash
# Primary LLM provider (via "vllm" slot)
LLM_VLLM_API_KEY=local-dummy-key
LLM_VLLM_BASE_URL=http://127.0.0.1:8787/v1

# Embeddings — disabled
LLM_EMBEDDING_API_KEY=
LLM_EMBEDDING_BASE_URL=
LLM_EMBEDDING_MODEL=

# No backup provider
LLM_OPENAI_COMPATIBLE_API_KEY=
LLM_OPENAI_API_KEY=local-dummy-key
```

**Note:** The API key value is irrelevant for the headroom proxy — it doesn't validate Bearer tokens. The real auth happens at the zen-proxy layer (x-api-key injected from OPENCODE_ZEN_API_KEY in .hermes/.env).

### Docker Compose Cleanup

The template from `honcho-self-hosted/docker-compose.yml` had several issues:

1. **Duplicated CACHE_URL** — Two entries setting the same variable with different values in the api service's environment block. Removed the Anthropic-specific one (`redis://redis:***@database:5432/honcho`), kept the correct one (`redis://redis:6379/0?suppress=true`).
2. **Merged environment lines** — `POSTGRES_PASSWORD=***      - PGDATA=...` was two variables on one line (YAML syntax error). Fixed by rewriting the compose file cleanly.
3. **No deriver service** — The original compose only defines `api`, `database`, and `redis`. The Deriver is a separate process intended to run independently. It was NOT added to the compose definition.

## Key Observations

### Honcho Project Structure

The main Honcho repo (`~/honcho/`) and the deployment wrapper (`~/honcho-self-hosted/`) are separate git repos:
- `~/honcho/` — Main platform (Python/FastAPI, uv-based). Has Dockerfile + docker/entrypoint.sh.
- `~/honcho-self-hosted/` — Deployment config (config.toml, docker-compose.yml, env.example, setup.sh). The wrapper repo's docker-compose references the main repo's Dockerfile.

Both were cloned to `~/` during setup.

### Deriver Architecture

From Honcho's CLAUDE.md:
- **API server** (`uv run fastapi dev src/main.py`) — handles HTTP, enqueues background work
- **Deriver worker** (`uv run python -m src.deriver`) — long-running queue consumer
- These are two cooperating processes sharing Postgres + Redis
- The Deriver runs as a separate container or process — NOT included in the original docker-compose.yml

## Pitfalls

### .env File Handling

The `write_file` tool blocks `.env` files from being **read** (defense in depth), but **writing** works fine. However, writing via heredoc in terminal had issues:
- Shell heredocs with `$` signs were prone to variable expansion
- Single quotes in heredoc delimiters (`'EOF'`) prevented expansion but some tools still mangled the output
- **Best approach:** Use `echo 'VAR=value' >> file` line by line, or write the .env content to a non-.env temp file and `mv` it.

### Proxy Health ≠ Upstream Health

The headroom proxy health endpoint (`/health`) may report `healthy` while the upstream (opencode-zen) is rate-limited. A healthy proxy + upstream returning 502 = key exhaustion. Always test with an actual `/v1/chat/completions` call, not just the health endpoint.

### Key Rotation Trigger

When Honcho or any client gets 502 errors from the proxy, the fix is:
```bash
~/.local/bin/headroom-rotate-key.sh force-rotate
```
This advances to the next key and restarts the proxy. After restart, wait ~3-5s before testing — connection refused is normal during the startup window. If the new key also returns 502 after waiting, the pool may be fully exhausted.

### Function Calling Uncertainty

DeepSeek-v4-flash-free's function calling (tool use) reliability is untested for Honcho's requirements. Honcho's Deriver, Dialectic, and Dreamer all rely heavily on structured tool calling. If the model doesn't support tools properly, Honcho's background workers will silently fail or produce low-quality conclusions. **Test with a direct tool-call request before relying on Honcho for production.**

## Next Steps (Not Yet Executed)

1. `docker compose up -d` from `~/honcho/` (build image, start Postgres + Redis + API)
2. Verify `curl localhost:8000/v3/workspaces` returns something
3. Start Deriver separately (either as another container or via `docker exec -d`)
4. Wire honcho-config.json into Hermes: `cp ~/honcho-self-hosted/honcho-config.json ~/.hermes/config.memory.json`
5. Verify Hermes writes memory to Honcho
