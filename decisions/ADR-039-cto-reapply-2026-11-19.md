# ADR-039 — CTO Wave1 Re-apply (2026-11-19)

| รายการ | รายละเอียด |
|:-------|:-----------|
| **Status** | Accepted — Owner decision 2026-11-19 ("ฉันอยากได้ชื่อ cto กลับมา") |
| **Supersedes** | ADR-038 (rollback) — re-applies `d12a050` via revert |
| **Scope** | rename `unified_technical` → `cto` + MCP config + routing + profiles/skills/agent |
| **Commit** | this commit (revert of `d12a050`, ADR-038 kept) |

## 1. Context

`d12a050` rolled back CTO Wave1 to `unified_technical` as a clean migration
commit (ADR-038). Owner then requested the `cto` name back. The rollback commit
itself documents the re-apply path: `git revert d12a050`.

## 2. Decision

Re-apply CTO Wave1 by reverting the rollback:

- `axis_mcp/unified_technical/` → `axis_mcp/cto/` (rename back)
- restore `axis_mcp/departments/cto_mcp.py`, `axis_mcp/cto/tools/compat_shims.py`
- restore `cto` MCP entry in `opencode.json` (absolute venv path kept)
- `opencode.jsonc` → `cto` (`axis_mcp.cto.server`)
- `rules/01-receive.md`: `@cto` (alias `@architect-songsak` / `@changful` / `@qa`, 1 release)
- restore `profiles/cto/`, `.opencode/agents/cto.md`, `skills/@axis/cto/`
- regenerate manifest (87 agent files, note derived count includes `cto.md`)
- keep ADR-038 as history (this revert does not delete it)

## 3. Not changed by this re-apply

- Safety fixes kept by the rollback stay kept: W1b model-chain fix,
  `.gitignore` guards, brain filter test + source
- CTO evidence in `bus/evidence/cto-migration/**` untouched
- Safety files (`tests/test_model_health.py`, `workers/llm_provider.py`,
  `.gitignore`, `tests/test_brain_auto_commit_filter.py`,
  `loop_runner/loops/brain_auto_commit.py`) untouched

## 4. Consequences

- MCP namespace is `cto` again (`architect_*` / `engineering_*` / `qa_*` / `unified_*`)
- Routing primary is `@cto`; old slugs kept as alias for 1 release
- Manifest = 87 agent files (unlisted: `axis-ceo`, `cto`)
- Requires MCP restart after merge for the `cto` config to take effect
- Canonical checkout must follow `main` after merge

## 5. Rollback plan (back to unified_technical)

- `git revert <this commit>` (re-applies the ADR-038 tree)
- `opencode.json(c)` back to `unified-technical`; rules back to
  `@architect-songsak` / `@changful` / `@qa`
- regenerate manifest (86 agent files), `--check` must pass
- `scripts/restart-mcp.sh` (dry-run → `--yes`), then `opencode mcp list`
- verify `session-bootstrap.py` pre-flight OK

## 6. Verification (of this commit)

- `python3 scripts/generate-specialist-manifest.py` → 87 agent files, deterministic sha256 `708fa723…`
- `python3 scripts/generate-specialist-manifest.py --check` → exit 0
- `pytest tests/ central_bus/tests/` → 1354 passed, 1 skipped
- after restart: `opencode mcp list` → `cto` connected; health via `cto` server
