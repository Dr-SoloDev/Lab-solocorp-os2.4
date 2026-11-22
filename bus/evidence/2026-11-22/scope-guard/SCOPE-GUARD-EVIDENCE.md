# P1 Scope Guard — Adapter Back-door Close (evidence)

- Date (UTC): 2026-11-22
- Branch: `fix/p1-scope-guard-adapter` (from `origin/main` tip `357720b`)
- Scope: 2 files only — `axis_mcp/departments/content_mcp.py` (+25), `tests/test_content_mcp.py` (+50, additive)

## 1. Problem (admitted in 8b5c599, learnt 2 พ.ย.)
Front door `axis_mcp/server.py:722,733,742` locked with `_check_scope("team")`.
Back door `axis_mcp/departments/content_mcp.py` task tools had 0 guard — only
`_is_content_task` dept filter. `task_create` in server.py (line 715) is likewise
unguarded; the adapter fix covers all 4 tools (create/get_status/list/update),
making the adapter stricter-or-equal on every path.

## 2. Fix
- Added local `_check_scope()` mirroring `axis_mcp.server._check_scope`
  (own copy so the adapter stays standalone per PRD §6.1), called BEFORE
  try/except in each of the 4 task tools so `PermissionError` propagates
  (FastMCP → isError) instead of being wrapped as JSON.
- Dept filter (`dept == 'content'`, `module == 'content-creator'`) kept intact.
- `module_registry_status` verified PUBLIC, no lock (CMD-006 §4.2) — read-only,
  local, secret-free; FR-07/C2 tests confirm no-key access works.

## 3. Contract tests (tests/test_content_mcp.py)
- `test_task_tools_require_team_scope_without_key`: no key → PermissionError
  ("Requires scope 'team'") on all 4 tools.
- `test_task_tools_accept_team_key_and_registry_status_stays_public`:
  admin dev key → create+list round-trip works; registry status answers
  without key.
- Existing `test_content_task_tools_cannot_read_or_update_other_departments`
  now sets `SOLOCORP_API_KEY` (admin dev key) — it exercises post-auth
  dept isolation, not anonymous access.

## 4. Test results
- Related: `test_content_mcp + test_media_services + test_content_image_generation
  + test_module_registry_c2` → **174 passed, 1 skipped**
- Full suite (`tests/ + central_bus/tests/`, CI paths): **1380 passed, 1 skipped**

## 5. Runtime freshness
- `content_department_info().runtime` → `restart_required: false, status: current`
  (fresh interpreter loads the fix).
- `scripts/restart-mcp.sh` (dry-run): 12 STALE generations (2 cohorts, from
  01:37 and 02:25) predate the edit; busd untouched. `--yes` NOT run —
  processes may belong to sibling worktrees; awaiting CEO confirm before kill.

## 6. Files changed
- `axis_mcp/departments/content_mcp.py`: +25 (import, `_check_scope`, 4 guard lines)
- `tests/test_content_mcp.py`: +50 / −0
