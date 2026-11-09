# Registry Schema Rollback

How to recover when `config/module-registry.json` was written by a newer build
than the code that is now reading it.

**Covers:** schema v2 (C2) and later. For the first v1→v2 rollback the old code
has no `RegistryDowngradeError`, so the message is plain text — see
"What this cannot do".

---

## Symptom

```
python -c "from axis_mcp.module_registry import ModuleRegistry as R; print(R().validate())"
# {'valid': False, 'errors': ['config downgrade: .../config/module-registry.json was
#  written by a newer config schema (schema_version 2; this build supports 1)...'],
#  'warnings': [], 'stale_state': [], 'state_error': None, 'error_kind': 'downgrade'}
```

or, on the app surface, `status()["error_kind"] == "downgrade"` with
`valid: false`. Nothing is broken on disk: the file is intact, the reader is
just older than the writer. **The registry refuses to overwrite it**, so
`register()` / `update()` fail too — by design (write is gated by a successful
read).

## Why a restart comes first

An MCP server loads its code once at startup. A process started before the
rollback still holds the newer code and will keep writing (or rejecting) the
old schema.

```bash
scripts/restart-mcp.sh          # report only, safe
scripts/restart-mcp.sh --yes    # kill every axis_mcp process; host respawns
```

Do this **before** step 1 and again after step 3.

## Recovery

### 0. Restart stale processes

```bash
scripts/restart-mcp.sh --yes
```

### 1. Diagnose

```bash
source .venv/bin/activate && export PYTHONPATH=.
python -c "from axis_mcp.module_registry import ModuleRegistry as R; print(R().validate())"
```

Read `error_kind`:

| `error_kind` | Meaning | Where to go |
|:--|:--|:--|
| `downgrade` | config is newer than code | step 2a or 2b |
| `corrupt` | file is not JSON / not UTF-8 | restore from git, then restart |
| `invalid` | file parses but violates the schema | restore from git, then restart |

### 2a. Primary — revert the paired commit

The schema change was committed with code + config + tests + runbook together,
so one revert puts both sides back:

```bash
git log --oneline -- config/module-registry.json | head -5
git revert --no-edit <paired-sha>
```

### 2b. Secondary — module registered after the upgrade

A revert would drop that entry. Strip only the fields the target schema cannot
read and keep every module:

```bash
python scripts/registry-repair.py --to-schema 1 --keep-modules          # dry run, prints a diff
python scripts/registry-repair.py --to-schema 1 --keep-modules --yes    # write
```

The script writes atomically and never calls the registry code (that code is
what is refusing to read the file). It does not touch
`central_bus/module-registry.state.json`.

Fallback if the script cannot run: the previous config is snapshotted next to
the live file before every config write.

```bash
cp config/module-registry.json.bak config/module-registry.json
```

`.bak` is git-ignored and only as fresh as the last config write.

### 3. Verify

```bash
python -c "from axis_mcp.module_registry import ModuleRegistry as R; print(R().validate())"
scripts/restart-mcp.sh          # confirm no process is stale
```

`valid: true` and `error_kind: None` means the registry is readable again. The
next config write re-stamps `_meta.schema_version` with the running build's
version.

## Do not

- **Never `git checkout -- .`** — it reverts every unrelated change in the
  working tree, including files outside the registry.
- **Never delete the config to "fix" it.** That reseeds `DEFAULT_MODULES` and
  silently discards what the human actually configured.
- **Never hand-edit `_meta.schema_version` upward** to silence a warning. It
  will only move the failure to the next reader.

## State file: nothing to do

`central_bus/module-registry.state.json` is derived data. If a newer state meets
older code, validation fails, the file is quarantined as a **warning** (never a
config error), and the next heartbeat rewrites it in the old shape.
`stale_state` / `state_error` explain what was ignored. No manual step.

## What this cannot do

The first bump (v1→v2) is one-way in the UI sense: v1 code has no
`RegistryDowngradeError`, so a v1 reader reports
`schema_version must be 1, got 2` — readable by a human, not classifiable by an
UI. Rollback for that step is **revert + this runbook**, not a one-click
action. Classification works in full from v2→v3 onward.
