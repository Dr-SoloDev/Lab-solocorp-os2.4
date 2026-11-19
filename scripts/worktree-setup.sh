#!/usr/bin/env bash
# worktree-setup.sh — Worktree MCP Contract: สร้าง worktree แบบกันแดงซ้ำ
#
# ทำ 3 อย่างที่ manual git worktree add ไม่ทำ:
#   1) ln -s /data/projects/Lab-solocorp-os2.4/.venv .venv  (absolute symlink)
#   2) ตรวจ opencode.json(c) ไม่มี ".venv/bin/python3" แบบ relative เหลือ
#   3) verify ด้วย session-bootstrap + restart-mcp dry-run
#
# Usage:
#   scripts/worktree-setup.sh <path> <branch>   # สร้างใหม่ (branch ใหม่หรือมีอยู่แล้ว)
#   scripts/worktree-setup.sh --fix-only        # ซ่อม worktree ปัจจุบัน (ไม่สร้างใหม่)
#   scripts/worktree-setup.sh --help
#
# Contract: docs/runbooks/WORKTREE-MCP-CONTRACT.md

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CANONICAL_VENV="/data/projects/Lab-solocorp-os2.4/.venv"
CANONICAL_PY="$CANONICAL_VENV/bin/python3"

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \?//'
  exit 0
}

FIX_ONLY=0
WT_PATH=""
BRANCH=""

for arg in "$@"; do
  case "$arg" in
    --help|-h) usage ;;
    --fix-only) FIX_ONLY=1 ;;
    --*) echo "unknown option: $arg (try --help)" >&2; exit 2 ;;
    *)
      if [[ -z "$WT_PATH" ]]; then WT_PATH="$arg"
      elif [[ -z "$BRANCH" ]]; then BRANCH="$arg"
      else echo "too many args: $arg" >&2; exit 2
      fi
      ;;
  esac
done

if [[ "$FIX_ONLY" -eq 1 ]]; then
  WT_PATH="$ROOT"
else
  if [[ -z "$WT_PATH" || -z "$BRANCH" ]]; then
    echo "Usage: scripts/worktree-setup.sh <path> <branch>  |  --fix-only  |  --help" >&2
    exit 2
  fi
fi

# --- 0. pre-check canonical venv ---
if [[ ! -x "$CANONICAL_PY" ]]; then
  echo "🔴 CANONICAL VENV BROKEN: $CANONICAL_PY not executable" >&2
  exit 1
fi

# --- 1. git worktree add (unless --fix-only) ---
if [[ "$FIX_ONLY" -eq 0 ]]; then
  if [[ -e "$WT_PATH" ]]; then
    echo "🔴 path exists: $WT_PATH — choose another path or use --fix-only" >&2
    exit 1
  fi
  # branch exists? then attach, else create
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    echo "→ git worktree add $WT_PATH $BRANCH (attach existing branch)"
    git worktree add "$WT_PATH" "$BRANCH"
  else
    echo "→ git worktree add $WT_PATH -b $BRANCH"
    git worktree add "$WT_PATH" -b "$BRANCH"
  fi
  TARGET="$WT_PATH"
else
  TARGET="$ROOT"
fi

# --- 2. .venv symlink (absolute) ---
VENV_LINK="$TARGET/.venv"

# linked worktree? git-dir ≠ git-common-dir (main checkout: both .git)
IS_LINKED_WORKTREE=0
if _gd="$(git -C "$TARGET" rev-parse --git-dir 2>/dev/null)" \
   && _gcd="$(git -C "$TARGET" rev-parse --git-common-dir 2>/dev/null)"; then
  if [[ "$_gd" != "$_gcd" ]]; then IS_LINKED_WORKTREE=1; fi
fi

# main checkout: .venv ที่ใช้งานได้คือพอ — ห้ามสร้าง symlink ไปตัวเอง
if [[ "$IS_LINKED_WORKTREE" -eq 0 ]]; then
  if [[ -x "$VENV_LINK/bin/python3" ]]; then
    echo "ℹ️  $TARGET เป็นโฟลเดอร์หลัก — .venv ใช้งานได้ (directory จริงใช้ได้ ไม่ต้อง symlink) ปฏิเสธการแก้"
    exit 0
  fi
  echo "🔴 โฟลเดอร์หลัก: $VENV_LINK ใช้งานไม่ได้ (ไม่มี bin/python3)" >&2
  if [[ -e "$VENV_LINK" || -L "$VENV_LINK" ]]; then
    echo "   fix: mv $VENV_LINK $VENV_LINK.bak-$(date +%Y%m%d%H%M%S) && python3 -m venv $VENV_LINK" >&2
  else
    echo "   fix: python3 -m venv $VENV_LINK" >&2
  fi
  exit 1
fi

if [[ -L "$VENV_LINK" ]]; then
  cur="$(readlink "$VENV_LINK")"
  if [[ "$cur" == "$CANONICAL_VENV" ]]; then
    echo "✅ .venv symlink OK: $VENV_LINK -> $cur"
  else
    echo "⚠️  .venv symlink points elsewhere: $cur → fixing to $CANONICAL_VENV"
    ln -snf "$CANONICAL_VENV" "$VENV_LINK"
    echo "✅ fixed: $VENV_LINK -> $CANONICAL_VENV"
  fi
elif [[ -e "$VENV_LINK" ]]; then
  echo "🔴 $VENV_LINK exists but is NOT a symlink (copy/dir) — linked worktree requires symlink" >&2
  echo "   fix: mv $VENV_LINK $VENV_LINK.bak-$(date +%Y%m%d%H%M%S) && ln -s $CANONICAL_VENV $VENV_LINK" >&2
  exit 1
else
  ln -s "$CANONICAL_VENV" "$VENV_LINK"
  echo "✅ created: $VENV_LINK -> $CANONICAL_VENV"
fi

# verify executable
if [[ ! -x "$VENV_LINK/bin/python3" ]]; then
  echo "🔴 $VENV_LINK/bin/python3 not executable after link" >&2
  exit 1
fi

# --- 3. opencode.json(c) absolute path check ---
echo "→ checking opencode.json / opencode.jsonc for relative .venv ..."

# relative pattern: ".venv/bin/python3" (quoted, no leading slash)
REL_FOUND=0
for cfg in "$TARGET/opencode.json" "$TARGET/opencode.jsonc"; do
  if [[ -f "$cfg" ]]; then
    if grep -q '\"\.venv/bin/python3\"' "$cfg" 2>/dev/null; then
      echo "🔴 $cfg still has relative \".venv/bin/python3\" — must be $CANONICAL_PY" >&2
      grep -n '\.venv/bin/python3' "$cfg" | head -5
      REL_FOUND=1
    fi
    # also catch any bare .venv without absolute prefix in command arrays
    if grep -q 'command.*\.venv' "$cfg" 2>/dev/null; then
      abs_count="$(grep -c "$CANONICAL_VENV" "$cfg" 2>/dev/null || true)"
      rel_count="$(grep -c '\"\.venv' "$cfg" 2>/dev/null || true)"
      if [[ "$rel_count" -gt 0 ]]; then
        echo "🔴 $cfg has $rel_count relative .venv refs (abs=$abs_count)" >&2
        REL_FOUND=1
      fi
    fi
  fi
done

if [[ "$REL_FOUND" -ne 0 ]]; then
  echo "   fix: replace \".venv/bin/python3\" with \"$CANONICAL_PY\" in opencode.json(c)" >&2
  echo "   hint: sed -i 's|\.venv/bin/python3|$CANONICAL_PY|g' is WRONG if you keep the dot — use absolute" >&2
  exit 1
fi
echo "✅ opencode.json(c) absolute path OK"

# --- 4. session-bootstrap pre-flight ---
echo "→ running session-bootstrap pre-flight ..."
if python3 "$TARGET/scripts/session-bootstrap.py" 2>&1; then
  echo "✅ session-bootstrap OK"
else
  rc=$?
  echo "🔴 session-bootstrap FAIL (exit $rc) — see above for MCP PRE-FLIGHT" >&2
  exit $rc
fi

# --- 5. restart-mcp dry-run ---
echo "→ restart-mcp dry-run ..."
if bash "$TARGET/scripts/restart-mcp.sh" 2>&1; then
  echo "✅ restart-mcp dry-run OK"
else
  echo "⚠️  restart-mcp dry-run returned non-zero (check output above)" >&2
fi

echo ""
echo "✅ worktree-setup done — target: $TARGET"
echo "   next: cd $TARGET && opencode mcp list   # should be 10/10 connected"
