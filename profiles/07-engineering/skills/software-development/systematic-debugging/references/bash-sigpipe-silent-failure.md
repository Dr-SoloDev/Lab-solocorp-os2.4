# Bash SIGPIPE Silent Failure — Debugging Case Study

## The Symptom

A bash script with `set -euo pipefail` runs a `tar -xzf` (extract) command. The output shows:
- Checksum verification passes ✅
- Pack contents preview shows fine
- "Unpack complete!" message appears ✅

**But:** No files are actually extracted. The target directory is empty.

Exit code: `141` (SIGPIPE) — not 0, not a typical error code.

## The Root Cause

The script has this pattern:

```bash
# Line 16
set -euo pipefail

# ...

# Line 116 — Preview contents (BEFORE extraction)
tar -tzf "$PACK_FILE" | grep -v 'manifest' | head -30   # ← THE CULPRIT

# ...

# Line 173 — Actual extraction (NEVER REACHED)
tar -xzf "$PACK_FILE" -C "$TARGET_DIR"
```

### Why it fails

1. **`head -30`** reads 30 lines from the pipe, then **closes its stdin**.
2. **`tar -tzf`** continues trying to write to the pipe, gets **SIGPIPE** (signal 13).
3. **`set -euo pipefail`** (specifically `pipefail`) causes any failure in the pipe chain to abort the **entire script**.
4. The script exits at line 116 with code 141. Lines 117–188 are never executed.
5. **No error message** reaches stderr because SIGPIPE from `head` is silent.

### Why it looks like it worked

- All earlier commands (checksum verify, manifest read) succeed normally.
- The preview output *looks* correct — it shows the first 30 entries.
- The script just dies silently after the preview.

## The Fix

```bash
# Before (⬅️ BROKEN):
tar -tzf "$PACK_FILE" | grep -v '^manifest$' | head -30

# After (✅ FIXED):
tar -tzf "$PACK_FILE" | grep -v '^manifest$' | head -30 || true
```

Adding `|| true` after the piped chain prevents SIGPIPE from propagating as a script failure.

## Deeper Diagnosis

| Exit Code | Signal | Meaning |
|-----------|--------|---------|
| 141 | SIGPIPE (13) | Process wrote to pipe after reader closed |
| 130 | SIGINT (2) | Ctrl+C |
| 137 | SIGKILL (9) | Killed |
| 139 | SIGSEGV (11) | Segmentation fault |

**Key insight:** When `head`, `sed -n '10q'`, `awk '{print; exit}'`, or any **early-terminating pipe consumer** is used in a `set -euo pipefail` script, the writer process gets SIGPIPE. With `pipefail`, the shell treats this as a script-fatal error.

## Debugging Methodology (applied)

| Phase | What we did |
|-------|-------------|
| **1. Root Cause** | Read script code → noticed `set -euo pipefail` + `head -30` before extract → exit 141 = SIGPIPE |
| **2. Pattern** | `head` + pipe + pipefail = known bash pitfall. `tar -tzf` produces all entries then `head` closes early. |
| **3. Hypothesis** | Pipefail kills script at line 116 before extraction at line 173 |
| **4. Fix** | `|| true` — confirmed by re-running: exit 0, files restored correctly |

## Prevention Checklist

When debugging a bash script that silently does less than expected:

- [ ] Check for `set -euo pipefail` (or `set -e` + `set -o pipefail`)
- [ ] Run the script and capture the exact exit code
- [ ] Look for `head`, `sed 'Nq'`, `awk '...exit'`, `read -N`, or any early-terminating pipe consumer
- [ ] Add `|| true` after pipe chains that use early-terminating commands
- [ ] For multi-line pipe chains, wrap in a function or use `{ cmd || true; }` syntax

## Alternative Fixes

```bash
# Store listing in a variable first (avoids pipe issue entirely)
CONTENTS=$(tar -tzf "$PACK_FILE" | grep -v '^manifest$')
echo "$CONTENTS" | head -30 || true
echo "  (... $(echo "$CONTENTS" | wc -l) items total)"

# OR: Use sed to limit output (head replacement with different behavior)
tar -tzf "$PACK_FILE" | grep -v '^manifest$' | sed -n '1,30p; 31q' || true

# OR: Temporarily disable pipefail for the preview
set +o pipefail
tar -tzf "$PACK_FILE" | grep -v '^manifest$' | head -30
set -o pipefail
```

The `|| true` approach is simplest and cleanest for most cases.
