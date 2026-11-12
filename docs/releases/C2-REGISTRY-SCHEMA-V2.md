# C2 — Registry config schema v2

**Date:** 2026-11-06 · **Scope:** `axis_mcp/module_registry_schema.py`,
`axis_mcp/module_registry.py`, `config/module-registry.json`, department
MCPs, `scripts/registry-repair.py`
**Ticket:** CMD-006 · **Decision:** `bus/evidence/2026-11-06/CMD-006-decision.md`

## Headline

> **config schema v2 — rollback must revert code + config together. Restart
> every MCP process after deploying or rolling back.**

## What changed

### New optional config fields (per module)

| field | meaning | example |
|:--|:--|:--|
| `name` | display name (1–64 chars) | `"Content Creator"` |
| `version` | declared module version, `MAJOR.MINOR.PATCH` | `"0.1.0"` |
| `capabilities` | MCP primitives the module serves: `tools` / `resources` / `prompts` | `["tools", "resources"]` |
| `dependencies` | module ids in the same config, or `busd` | `[]` |
| `permissions` | **declared** scopes of the module's own tools (`public`/`team`/`admin`) — provider-side metadata, never an access gate | `["public"]` |
| `entry_repo` | provenance only (`internal` / path / url), never checked against the filesystem | `"internal"` |

All six are optional. A config written before C2 (schema v1) loads without
migration; the next write stamps `_meta.schema_version: 2`.

### Schema version semantics

- absent `_meta.schema_version` = v1, **accepted**
- `< SCHEMA_VERSION` = **accepted** (this is what makes upgrades safe)
- `> SCHEMA_VERSION` = `RegistryDowngradeError` — fail-closed, classified, and
  it never overwrites the file
- The version is checked **before** field validation, so a newer config fails
  once with one actionable sentence instead of "unknown field" noise.

`status()` and `validate()` gain `error_kind ∈ {"corrupt", "downgrade",
"invalid", None}`. Everything from C1 keeps its name and shape.

### Standalone department MCPs (FR-07)

- Department MCPs no longer construct a registry at import. Importing
  `content_mcp` / `engineering_mcp` / `qa_mcp` writes nothing.
- When a department tool needs the registry it creates it lazily and seeds
  **only its own module**, not all five.
- `module_registry_status` in the Content MCP is **public** (read-only, local,
  no secrets), so a standalone department MCP answers it without
  `SOLOCORP_API_KEY`.

### Writes

- `permissions` are written in canonical scope order (`public`, `team`,
  `admin`). Reads never reorder and never write.
- Before each config write the previous file is copied to
  `config/module-registry.json.bak` (git-ignored).

## Deploy

1. **Stop/restart every MCP process** — an MCP server loads code once.
   ```bash
   scripts/restart-mcp.sh --yes
   ```
2. Deploy code **and** `config/module-registry.json` in the same commit
   (paired-commit rule). A code-only deploy leaves a v1 reader facing a v2
   config.
3. Verify:
   ```bash
   python -c "from axis_mcp.module_registry import ModuleRegistry as R; print(R().validate()['error_kind'])"
   # None
   ```

## Rollback

Revert the paired commit (`git revert --no-edit <sha>`), restart the MCPs, and
follow `docs/runbooks/registry-schema-rollback.md`. If modules were registered
after the upgrade, use
`python scripts/registry-repair.py --to-schema 1 --keep-modules --yes`.

The v1→v2 rollback is **repairable by procedure, not by UI**: v1 code has no
`RegistryDowngradeError`. Do not describe it as zero-pain.

## Not in this release

- `update()` does not patch manifest fields (Phase 1 item 4 — no UI caller yet).
- Transport stays `{"stdio"}`. `TRANSPORT_ENTRY_FIELDS` is in place so adding
  `http` is an enum value + an entry field, not a breaking change.
- No config warnings ("module X has no version") — `warnings` still means
  state only.
