# Wave 2 — Architect deprecation-shim plan (Wave 3 ONLY, do NOT execute now)

> Owner constraint: `engineering` + `qa` standalone STAY until CTO green.
> This file is a PLAN for Wave 3 cleanup. No deletion, no wiring change in Wave 2.
> Forbidden paths untouched: product/legal/content/bus_mcp, legal_vault/**.

**Trace:** `cto-wave2-architect-shim-20261113`
**Role:** Architect (พี่ทรงศักดิ์) — stabilize + support Wave 2
**Branch:** `feat/cto-phase1-wave1`

## 1. Current state (Wave 2 — keep)

- `opencode.json` `mcp.servers`: 9 keys — `cto -> axis_mcp.cto.server` + `engineering -> axis_mcp.departments.engineering_mcp` + `qa -> axis_mcp.departments.qa_mcp` (both standalone KEPT).
- `opencode.jsonc`: 4 servers — `stealth-browser` (disabled), `central-bus`, `cto`, `content-creator` (no eng/qa by design; minimal track).
- Tool namespaces in `axis_mcp/cto/server.py`: `architect_*` / `engineering_*` / `qa_*` / `unified_*` (10 tools, `unified_technical_health` preserved). No `cto_*` re-prefix.
- `axis_mcp/departments/cto_mcp.py` (boundary wrapper, `cto_department_info` + 2 tools) exists on disk, NOT host-wired. Single live `cto` key = `axis_mcp.cto.server`. Adjudication before merge to `main` (orchestrator/CEO).

## 2. Wave 3 cleanup — entry conditions (ALL must hold)

1. **CTO stable 48 h:** `unified_technical_health` → healthy ×3 + `database: connected` + `cache: active` in every probe (fresh + live), `restart_required=false`, no tool miss, no health red.
2. **No old caller 7 days:** zero calls to standalone `engineering` / `qa` MCP keys for 7 consecutive days (host catalog / audit log evidence). Any caller → reset clock.
3. **CEO/Owner sign-off:** explicit L4/L5 approval recorded before removal (not silent).
4. **Rollback ready:** `rollback-cto-wave1.md` path still valid (config `.bak` + `restart-mcp.sh --yes`, ≤15 min).

## 3. Shim design (Wave 3 only — draft, not implemented)

- Option A (preferred): keep `engineering` / `qa` keys as **thin deprecation shims** for 1 release — each tool logs `deprecated: use cto` + forwards to the matching `axis_mcp.cto` module function. No logic fork.
- Option B: remove keys outright (only if condition 2 proves zero callers + CEO orders removal).
- In both options: `bus/evidence/**` audit trail kept (never delete), `central_bus/unified_technical.db` source file kept until Wave 3 sign-off, then archive (not `rm -rf`).

## 4. What Wave 2 does NOT do

- Does NOT delete `engineering` / `qa` entries.
- Does NOT re-prefix any tool to `cto_*`.
- Does NOT touch `product_mcp` / `legal_mcp` / `content_mcp` / `bus_mcp` / `legal_vault/**`.
- Does NOT resolve the `cto_mcp.py` wrapper contention (orchestrator/CEO adjudicate before merge).

## 5. Evidence

- Health: `bus/evidence/cto-migration/20261113/w2-architect-health.json` (fresh probe healthy ×3, 10 tools, sha `881da767…`, `restart_required=false`)
- Wiring: `bus/evidence/cto-migration/20261113/w2-architect-wiring.json` (json+jsonc+README consistent)
- Live: `opencode mcp list` → 9 connected + 1 disabled (`cto`, `engineering`, `qa` all connected)
